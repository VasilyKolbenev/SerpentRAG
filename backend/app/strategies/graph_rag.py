"""
Graph RAG Strategy.
Pipeline: Query → Entity Extract → Graph Traverse → Subgraph → Context Build → LLM
"""

import json
import logging
from typing import Optional

from app.services.graph_store import Neo4jService
from app.services.tracing import TraceRecorder
from app.strategies.base import BaseRAGStrategy

logger = logging.getLogger("serpent.graph_rag")


class GraphRAGStrategy(BaseRAGStrategy):
    """Knowledge graph-enhanced retrieval combining graph traversal with vector search."""

    def __init__(self, graph_store: Neo4jService, **kwargs) -> None:
        super().__init__(**kwargs)
        self.graph_store = graph_store

    async def retrieve(
        self,
        query: str,
        collection: str,
        trace: TraceRecorder,
        top_k: int = 10,
        max_hops: int = 3,
        entity_types: Optional[list[str]] = None,
        **kwargs,
    ) -> list[dict]:
        # 1. Extract entities from query using LLM
        trace.start_step("entity_extraction", input_summary=f"query_length={len(query)}")
        entities = await self._extract_entities(query)
        trace.end_step(
            output_summary=f"entities={entities}",
            result_count=len(entities),
        )

        # 2. Graph traversal
        graph_context = []
        if entities:
            trace.start_step(
                "graph_traversal",
                input_summary=f"entities={len(entities)}, max_hops={max_hops}",
            )
            nodes, edges = await self.graph_store.traverse(
                entity_names=entities,
                max_hops=max_hops,
                collection=collection,
            )
            trace.end_step(
                output_summary=f"nodes={len(nodes)}, edges={len(edges)}",
                result_count=len(nodes),
                details={
                    "node_types": list({n.type for n in nodes}),
                    "edge_types": list({e.type for e in edges}),
                },
            )

            # Build graph context strings
            for node in nodes:
                graph_context.append({
                    "content": f"Entity: {node.name} (type: {node.type}). Properties: {json.dumps(node.properties, default=str)}",
                    "score": 0.9,
                    "metadata": {"source": "knowledge_graph", "entity": node.name, "type": node.type},
                })
            for edge in edges:
                graph_context.append({
                    "content": f"Relationship: {edge.source} --[{edge.type}]--> {edge.target}",
                    "score": 0.85,
                    "metadata": {"source": "knowledge_graph", "relationship": edge.type},
                })

        # 3. Vector search for additional context
        trace.start_step("vector_search", input_summary=f"top_k={top_k}")
        query_vector = await self.embedding.embed_query(query)
        vector_results = await self.vector_store.search(
            collection_name=collection,
            query_vector=query_vector,
            limit=top_k,
        )
        trace.end_step(
            output_summary=f"found={len(vector_results)}",
            result_count=len(vector_results),
        )

        vector_context = [
            {
                "content": r.content,
                "score": r.score,
                "metadata": r.metadata,
            }
            for r in vector_results
        ]

        # 4. Merge graph + vector context
        trace.start_step(
            "context_merge",
            input_summary=f"graph={len(graph_context)}, vector={len(vector_context)}",
        )
        merged = self._merge_contexts(graph_context, vector_context, top_k)
        trace.end_step(
            output_summary=f"merged={len(merged)}",
            result_count=len(merged),
        )

        return merged

    async def _extract_entities(self, query: str) -> list[str]:
        """Extract entity names from query using LLM."""
        prompt = (
            "Extract all named entities (people, organizations, concepts, technologies, "
            "locations) from the following query. Return ONLY a JSON array of strings.\n\n"
            f"Query: {query}\n\n"
            "Response (JSON array only):"
        )

        try:
            response = await self.llm.structured_extract(prompt, temperature=0.0)
            # Parse JSON array from response
            response = response.strip()
            if response.startswith("```"):
                response = response.split("\n", 1)[1].rsplit("```", 1)[0]
            entities = json.loads(response)
            if isinstance(entities, list):
                return [str(e) for e in entities]
        except (json.JSONDecodeError, Exception) as e:
            logger.warning(f"Entity extraction failed: {e}")

        return []

    @staticmethod
    def _merge_contexts(
        graph_context: list[dict],
        vector_context: list[dict],
        limit: int,
    ) -> list[dict]:
        """Merge graph and vector contexts, deduplicating by content."""
        seen_content = set()
        merged = []

        # Graph context first (higher priority for entity-rich queries)
        for item in graph_context:
            content_key = item["content"][:100]
            if content_key not in seen_content:
                seen_content.add(content_key)
                merged.append(item)

        # Then vector results
        for item in vector_context:
            content_key = item["content"][:100]
            if content_key not in seen_content:
                seen_content.add(content_key)
                merged.append(item)

        return merged[:limit]
