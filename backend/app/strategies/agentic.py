"""
Agentic RAG Strategy.
Pipeline: Query → Plan → [Search/Retrieve/Calculate]* → Reflect → Answer
"""

import json
import logging
from typing import Optional

from app.services.graph_store import Neo4jService
from app.services.tracing import TraceRecorder
from app.strategies.base import BaseRAGStrategy

logger = logging.getLogger("serpent.agentic")


class AgenticRAGStrategy(BaseRAGStrategy):
    """Autonomous multi-step reasoning with planning, tool use, and self-reflection."""

    def __init__(self, graph_store: Neo4jService, **kwargs) -> None:
        super().__init__(**kwargs)
        self.graph_store = graph_store

    async def retrieve(
        self,
        query: str,
        collection: str,
        trace: TraceRecorder,
        top_k: int = 10,
        max_iterations: int = 5,
        enable_planning: bool = True,
        enable_reflection: bool = True,
        **kwargs,
    ) -> list[dict]:
        all_context: list[dict] = []

        # 1. Planning phase
        if enable_planning:
            trace.start_step("planning", input_summary=f"query_length={len(query)}")
            sub_questions = await self._plan(query)
            trace.end_step(
                output_summary=f"sub_questions={len(sub_questions)}",
                result_count=len(sub_questions),
                details={"sub_questions": sub_questions},
            )
        else:
            sub_questions = [query]

        # 2. Iterative retrieval with tool use
        for iteration in range(max_iterations):
            trace.start_step(
                f"iteration_{iteration + 1}",
                input_summary=f"sub_questions={len(sub_questions)}",
            )

            iteration_results = []
            for sub_q in sub_questions:
                # Select tool
                tool = await self._select_tool(sub_q, all_context)

                # Execute tool
                if tool == "vector_search":
                    results = await self._vector_search_tool(sub_q, collection, top_k)
                elif tool == "graph_search":
                    results = await self._graph_search_tool(sub_q, collection)
                elif tool == "summarize":
                    results = await self._summarize_tool(sub_q, all_context)
                else:
                    results = await self._vector_search_tool(sub_q, collection, top_k)

                iteration_results.extend(results)

            all_context.extend(iteration_results)

            trace.end_step(
                output_summary=f"new_chunks={len(iteration_results)}, total={len(all_context)}",
                result_count=len(iteration_results),
            )

            # 3. Reflection
            if enable_reflection and all_context:
                trace.start_step(
                    "reflection",
                    input_summary=f"total_context={len(all_context)}",
                )
                is_sufficient = await self._reflect(query, all_context)
                trace.end_step(
                    output_summary=f"sufficient={is_sufficient}",
                    details={"sufficient": is_sufficient},
                )

                if is_sufficient:
                    break

                # Replan
                sub_questions = await self._replan(query, all_context)

        # Deduplicate
        return self._deduplicate(all_context)[:top_k]

    async def _plan(self, query: str) -> list[str]:
        """Decompose query into sub-questions using LLM."""
        prompt = (
            "You are a research planner. Decompose the following complex query into "
            "2-4 specific sub-questions that, when answered together, will fully address "
            "the original query. Return ONLY a JSON array of strings.\n\n"
            f"Query: {query}\n\nSub-questions (JSON array):"
        )

        try:
            response = await self.llm.structured_extract(prompt, temperature=0.0)
            response = response.strip()
            if response.startswith("```"):
                response = response.split("\n", 1)[1].rsplit("```", 1)[0]
            sub_questions = json.loads(response)
            if isinstance(sub_questions, list) and sub_questions:
                return [str(q) for q in sub_questions]
        except (json.JSONDecodeError, Exception) as e:
            logger.warning(f"Planning failed: {e}")

        return [query]

    async def _select_tool(self, sub_question: str, context: list[dict]) -> str:
        """Select the best tool for a sub-question using LLM."""
        available_tools = ["vector_search", "graph_search", "summarize"]

        prompt = (
            f"Given this sub-question: '{sub_question}'\n"
            f"And {len(context)} existing context chunks.\n"
            f"Select the best tool from: {available_tools}\n"
            "Rules:\n"
            "- 'vector_search': for finding specific information in documents\n"
            "- 'graph_search': for entity relationships and connections\n"
            "- 'summarize': when you have enough context and need synthesis\n"
            "Return ONLY the tool name, nothing else."
        )

        try:
            response = await self.llm.structured_extract(prompt, temperature=0.0)
            tool = response.strip().lower().replace("'", "").replace('"', "")
            if tool in available_tools:
                return tool
        except Exception as e:
            logger.warning(f"Tool selection failed: {e}")

        return "vector_search"

    async def _vector_search_tool(
        self, query: str, collection: str, top_k: int
    ) -> list[dict]:
        """Execute vector search."""
        query_vector = await self.embedding.embed_query(query)
        results = await self.vector_store.search(
            collection_name=collection,
            query_vector=query_vector,
            limit=top_k,
        )
        return [
            {"content": r.content, "score": r.score, "metadata": r.metadata}
            for r in results
        ]

    async def _graph_search_tool(
        self, query: str, collection: str
    ) -> list[dict]:
        """Execute graph search."""
        # Simple entity extraction and lookup
        entities_prompt = (
            f"Extract key entity names from: '{query}'\n"
            "Return ONLY a JSON array of strings."
        )
        try:
            response = await self.llm.structured_extract(entities_prompt, temperature=0.0)
            response = response.strip()
            if response.startswith("```"):
                response = response.split("\n", 1)[1].rsplit("```", 1)[0]
            entities = json.loads(response)
            if isinstance(entities, list) and entities:
                found = await self.graph_store.find_entities(
                    [str(e) for e in entities], collection
                )
                return [
                    {
                        "content": f"Entity: {n.name} (type: {n.type})",
                        "score": 0.85,
                        "metadata": {"source": "knowledge_graph", "entity": n.name},
                    }
                    for n in found
                ]
        except Exception as e:
            logger.warning(f"Graph search failed: {e}")

        return []

    async def _summarize_tool(
        self, query: str, context: list[dict]
    ) -> list[dict]:
        """Summarize existing context."""
        if not context:
            return []

        context_str = "\n".join(c["content"][:200] for c in context[:10])
        prompt = (
            f"Summarize the following context to answer: '{query}'\n\n"
            f"Context:\n{context_str}\n\n"
            "Summary:"
        )

        try:
            summary = await self.llm.structured_extract(prompt, temperature=0.1)
            return [
                {
                    "content": summary,
                    "score": 0.95,
                    "metadata": {"source": "agent_summary", "tool": "summarize"},
                }
            ]
        except Exception:
            return []

    async def _reflect(self, query: str, context: list[dict]) -> bool:
        """Evaluate if collected context is sufficient to answer the query."""
        context_preview = "\n".join(c["content"][:100] for c in context[:10])
        prompt = (
            f"Query: {query}\n\n"
            f"Available context ({len(context)} chunks):\n{context_preview}\n\n"
            "Is this context sufficient to fully answer the query? "
            "Answer ONLY 'yes' or 'no'."
        )

        try:
            response = await self.llm.structured_extract(prompt, temperature=0.0)
            return "yes" in response.strip().lower()
        except Exception:
            return True  # Default to sufficient to avoid infinite loops

    async def _replan(self, query: str, context: list[dict]) -> list[str]:
        """Generate new sub-questions based on what we know so far."""
        context_preview = "\n".join(c["content"][:100] for c in context[:5])
        prompt = (
            f"Original query: {query}\n\n"
            f"Information gathered so far:\n{context_preview}\n\n"
            "What additional specific questions should we research to fully answer "
            "the original query? Return ONLY a JSON array of 1-3 strings."
        )

        try:
            response = await self.llm.structured_extract(prompt, temperature=0.1)
            response = response.strip()
            if response.startswith("```"):
                response = response.split("\n", 1)[1].rsplit("```", 1)[0]
            questions = json.loads(response)
            if isinstance(questions, list) and questions:
                return [str(q) for q in questions]
        except Exception:
            pass

        return [query]

    @staticmethod
    def _deduplicate(context: list[dict]) -> list[dict]:
        """Remove duplicate chunks by content prefix."""
        seen = set()
        unique = []
        for item in context:
            key = item["content"][:100]
            if key not in seen:
                seen.add(key)
                unique.append(item)
        return unique
