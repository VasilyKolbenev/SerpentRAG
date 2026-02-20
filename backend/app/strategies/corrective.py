"""
Corrective RAG (CRAG) Strategy.
Pipeline: Retrieve → Grade Relevance → Decision (use / supplement / web search) → Refine → LLM

Each retrieved document is graded by the LLM for relevance (0-1).
- High relevance (≥ threshold): use directly
- Medium relevance (≥ threshold * 0.5): supplement with additional retrieval
- Low relevance (< threshold * 0.5): fall back to web search (if enabled)
"""

import json
import logging
from typing import Optional

import httpx

from app.config import settings
from app.services.tracing import TraceRecorder
from app.strategies.base import BaseRAGStrategy

logger = logging.getLogger("serpent.corrective")

GRADING_PROMPT = """You are a relevance grader. For each document, score its relevance to the query
on a scale of 0.0 to 1.0, where 1.0 means perfectly relevant and 0.0 means completely irrelevant.

Query: {query}

Documents to grade:
{documents}

Return ONLY a JSON array of objects with "index", "score", and "reasoning" fields:
[
  {{"index": 0, "score": 0.85, "reasoning": "Directly addresses the query topic"}},
  {{"index": 1, "score": 0.2, "reasoning": "Only tangentially related"}}
]

Grades:"""

QUERY_REWRITE_PROMPT = """Rewrite the following query to be more specific and effective for web
search. Keep it concise (under 50 words).

Original query: {query}

Context about what we're looking for: {context}

Rewritten query:"""

GRADING_BATCH_SIZE = 5


class CorrectiveRAGStrategy(BaseRAGStrategy):
    """Self-correcting RAG with relevance grading and web search fallback."""

    THRESHOLD_HIGH: float = 0.7
    THRESHOLD_LOW: float = 0.3

    async def retrieve(
        self,
        query: str,
        collection: str,
        trace: TraceRecorder,
        top_k: int = 10,
        relevance_threshold: float = 0.7,
        web_search_enabled: bool = False,
        **kwargs,
    ) -> list[dict]:
        """CRAG retrieval: retrieve → grade → decide → refine."""
        self.THRESHOLD_HIGH = relevance_threshold
        self.THRESHOLD_LOW = relevance_threshold * 0.5

        # 1. Initial vector retrieval (over-fetch for grading)
        trace.start_step("embedding", input_summary=f"query_length={len(query)}")
        query_vector = await self.embedding.embed_query(query)
        trace.end_step(output_summary=f"dimensions={len(query_vector)}")

        trace.start_step("initial_retrieval", input_summary=f"fetch_k={top_k * 2}")
        initial_results = await self.vector_store.search(
            collection_name=collection,
            query_vector=query_vector,
            limit=top_k * 2,
        )
        trace.end_step(
            output_summary=f"found={len(initial_results)}",
            result_count=len(initial_results),
        )

        if not initial_results:
            return []

        documents = [
            {
                "content": r.content,
                "score": r.score,
                "metadata": r.metadata,
            }
            for r in initial_results
        ]

        # 2. Grade documents for relevance
        graded = await self._grade_documents(query, documents, trace)

        # 3. Decision based on grades
        high_docs = [d for d, s in graded if s >= self.THRESHOLD_HIGH]
        medium_docs = [d for d, s in graded if self.THRESHOLD_LOW <= s < self.THRESHOLD_HIGH]
        low_count = sum(1 for _, s in graded if s < self.THRESHOLD_LOW)

        trace.start_step(
            "decision",
            input_summary=(
                f"high={len(high_docs)}, medium={len(medium_docs)}, low={low_count}"
            ),
        )

        final_docs = list(high_docs)

        if len(high_docs) < top_k // 2:
            # Not enough high-quality docs — supplement
            if web_search_enabled and settings.web_search_api_key:
                web_results = await self._web_search(query, trace)
                final_docs.extend(web_results)
                trace.end_step(
                    output_summary=f"supplemented_with_web={len(web_results)}",
                    details={"action": "web_search"},
                )
            elif medium_docs:
                # Use medium docs as supplement
                final_docs.extend(medium_docs)
                trace.end_step(
                    output_summary=f"supplemented_with_medium={len(medium_docs)}",
                    details={"action": "use_medium"},
                )
            else:
                trace.end_step(
                    output_summary="insufficient_docs_no_supplement",
                    details={"action": "proceed_with_available"},
                )
        else:
            trace.end_step(
                output_summary=f"sufficient_high_quality={len(high_docs)}",
                details={"action": "use_high"},
            )

        # 4. Refine documents (strip irrelevant content)
        refined = await self._refine_documents(query, final_docs[:top_k], trace)

        return refined

    async def _grade_documents(
        self,
        query: str,
        documents: list[dict],
        trace: TraceRecorder,
    ) -> list[tuple[dict, float]]:
        """Grade each document for relevance using LLM."""
        trace.start_step("grading", input_summary=f"documents={len(documents)}")

        graded: list[tuple[dict, float]] = []

        # Grade in batches for efficiency
        for i in range(0, len(documents), GRADING_BATCH_SIZE):
            batch = documents[i:i + GRADING_BATCH_SIZE]
            docs_text = "\n\n".join(
                f"[Document {j}]\n{d['content'][:500]}"
                for j, d in enumerate(batch)
            )

            prompt = GRADING_PROMPT.format(query=query, documents=docs_text)
            raw = await self.llm.structured_extract(
                prompt=prompt, model="gpt-4o", temperature=0.0
            )

            grades = self._parse_grades(raw, len(batch))
            for j, doc in enumerate(batch):
                score = grades.get(j, 0.5)
                graded.append((doc, score))

        avg_score = sum(s for _, s in graded) / len(graded) if graded else 0
        trace.end_step(
            output_summary=f"graded={len(graded)}, avg_score={avg_score:.2f}",
            details={
                "scores": [round(s, 2) for _, s in graded[:10]],
            },
        )
        return graded

    async def _web_search(
        self, query: str, trace: TraceRecorder
    ) -> list[dict]:
        """Search the web using configured provider (Tavily/SerpAPI)."""
        trace.start_step("web_search", input_summary=f"provider={settings.web_search_provider}")

        results: list[dict] = []
        try:
            if settings.web_search_provider == "tavily":
                results = await self._tavily_search(query)
            else:
                logger.warning("Unsupported web search provider: %s", settings.web_search_provider)
        except Exception as e:
            logger.error("Web search failed: %s", e)

        trace.end_step(
            output_summary=f"web_results={len(results)}",
            result_count=len(results),
        )
        return results

    async def _tavily_search(self, query: str) -> list[dict]:
        """Search using Tavily API."""
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.post(
                "https://api.tavily.com/search",
                json={
                    "api_key": settings.web_search_api_key,
                    "query": query,
                    "max_results": 5,
                    "include_answer": False,
                },
            )
            response.raise_for_status()
            data = response.json()

        return [
            {
                "content": r.get("content", ""),
                "score": r.get("score", 0.5),
                "metadata": {
                    "source": r.get("url", "web"),
                    "title": r.get("title", ""),
                    "origin": "web_search",
                },
            }
            for r in data.get("results", [])
        ]

    async def _refine_documents(
        self,
        query: str,
        documents: list[dict],
        trace: TraceRecorder,
    ) -> list[dict]:
        """Refine documents by stripping clearly irrelevant sections."""
        trace.start_step("refinement", input_summary=f"documents={len(documents)}")

        # For efficiency, only refine long documents
        refined = []
        for doc in documents:
            if len(doc["content"]) > 1000:
                # Extract relevant portions via simple heuristic
                paragraphs = doc["content"].split("\n\n")
                query_terms = set(query.lower().split())
                relevant_paras = [
                    p for p in paragraphs
                    if any(term in p.lower() for term in query_terms) or len(p) < 100
                ]
                if relevant_paras:
                    refined_doc = dict(doc)
                    refined_doc["content"] = "\n\n".join(relevant_paras)
                    refined.append(refined_doc)
                else:
                    refined.append(doc)
            else:
                refined.append(doc)

        trace.end_step(
            output_summary=f"refined={len(refined)}",
            result_count=len(refined),
        )
        return refined

    @staticmethod
    def _parse_grades(raw: str, expected_count: int) -> dict[int, float]:
        """Parse grading response into index→score map."""
        try:
            start = raw.find("[")
            end = raw.rfind("]") + 1
            if start >= 0 and end > start:
                parsed = json.loads(raw[start:end])
                if isinstance(parsed, list):
                    return {
                        item["index"]: float(item["score"])
                        for item in parsed
                        if "index" in item and "score" in item
                    }
        except (json.JSONDecodeError, KeyError, ValueError, TypeError):
            pass

        # Fallback: assign middle score
        return {i: 0.5 for i in range(expected_count)}
