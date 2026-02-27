"""
Hybrid RAG Strategy.
Pipeline: Query → [Dense Vector + BM25 Sparse] → RRF Fusion → Cross-Encoder Re-rank → LLM
"""

import logging
import re
from typing import Optional

from rank_bm25 import BM25Okapi

from app.services.tracing import TraceRecorder
from app.strategies.base import BaseRAGStrategy

logger = logging.getLogger("serpent.hybrid")


class HybridRAGStrategy(BaseRAGStrategy):
    """Combines dense + sparse retrieval with RRF fusion and cross-encoder re-ranking."""

    _reranker = None

    async def retrieve(
        self,
        query: str,
        collection: str,
        trace: TraceRecorder,
        top_k: int = 10,
        sparse_weight: float = 0.3,
        enable_reranking: bool = True,
        reranker_type: str = "cross-encoder",
        **kwargs,
    ) -> list[dict]:
        fetch_k = top_k * 3  # Over-fetch for fusion

        # 1. Embed query
        trace.start_step("embedding", input_summary=f"query_length={len(query)}")
        query_vector = await self.embedding.embed_query(query)
        trace.end_step(output_summary=f"dimensions={len(query_vector)}")

        # 2. Dense retrieval (vector)
        trace.start_step("dense_retrieval", input_summary=f"fetch_k={fetch_k}")
        dense_results = await self.vector_store.search(
            collection_name=collection,
            query_vector=query_vector,
            limit=fetch_k,
        )
        trace.end_step(
            output_summary=f"found={len(dense_results)}",
            result_count=len(dense_results),
        )

        # 3. Sparse retrieval (BM25)
        trace.start_step("sparse_retrieval", input_summary="BM25")
        sparse_results = self._bm25_search(
            query, [r.content for r in dense_results], fetch_k
        )
        trace.end_step(
            output_summary=f"scored={len(sparse_results)}",
            result_count=len(sparse_results),
        )

        # 4. RRF Fusion
        trace.start_step(
            "rrf_fusion",
            input_summary=f"dense={len(dense_results)}, sparse={len(sparse_results)}, weight={sparse_weight}",
        )
        fused = self._reciprocal_rank_fusion(
            dense_results, sparse_results, sparse_weight
        )
        trace.end_step(
            output_summary=f"fused={len(fused)}",
            result_count=len(fused),
        )

        # 5. Re-ranking (cross-encoder or colbert)
        if enable_reranking and fused:
            trace.start_step(
                "reranking",
                input_summary=f"candidates={len(fused)}, type={reranker_type}",
            )
            if reranker_type == "colbert":
                reranked = await self._colbert_rerank(query, fused)
            else:
                reranked = await self._cross_encoder_rerank(query, fused)
            trace.end_step(
                output_summary=f"reranked={len(reranked)}, type={reranker_type}",
                result_count=len(reranked),
                details={"reranker_type": reranker_type},
            )
            final = reranked[:top_k]
        else:
            final = fused[:top_k]

        return final

    def _bm25_search(
        self, query: str, documents: list[str], top_k: int
    ) -> list[dict]:
        """BM25 sparse search over document texts."""
        if not documents:
            return []

        tokenized_docs = [re.findall(r'\b\w+\b', doc.lower()) for doc in documents]
        bm25 = BM25Okapi(tokenized_docs)
        tokenized_query = re.findall(r'\b\w+\b', query.lower())
        scores = bm25.get_scores(tokenized_query)

        # Pair documents with scores and sort
        scored = list(zip(range(len(documents)), scores))
        scored.sort(key=lambda x: x[1], reverse=True)

        return [
            {"index": idx, "bm25_score": float(score)}
            for idx, score in scored[:top_k]
        ]

    def _reciprocal_rank_fusion(
        self,
        dense_results,
        sparse_results: list[dict],
        sparse_weight: float,
        k: int = 60,
    ) -> list[dict]:
        """Reciprocal Rank Fusion to merge dense and sparse results."""
        rrf_scores: dict[int, float] = {}
        content_map: dict[int, dict] = {}

        # Dense scores
        dense_weight = 1.0 - sparse_weight
        for rank, result in enumerate(dense_results):
            idx = rank
            rrf_scores[idx] = rrf_scores.get(idx, 0) + dense_weight / (k + rank + 1)
            content_map[idx] = {
                "content": result.content,
                "score": result.score,
                "metadata": result.metadata,
            }

        # Sparse scores
        for rank, sp_result in enumerate(sparse_results):
            idx = sp_result["index"]
            rrf_scores[idx] = rrf_scores.get(idx, 0) + sparse_weight / (k + rank + 1)

        # Sort by RRF score
        sorted_indices = sorted(rrf_scores.keys(), key=lambda x: rrf_scores[x], reverse=True)

        return [
            {
                **content_map.get(idx, {"content": "", "score": 0, "metadata": {}}),
                "rrf_score": rrf_scores[idx],
            }
            for idx in sorted_indices
            if idx in content_map
        ]

    async def _cross_encoder_rerank(
        self, query: str, candidates: list[dict]
    ) -> list[dict]:
        """Re-rank using cross-encoder model."""
        try:
            if HybridRAGStrategy._reranker is None:
                from sentence_transformers import CrossEncoder

                HybridRAGStrategy._reranker = CrossEncoder(
                    "cross-encoder/ms-marco-MiniLM-L-12-v2"
                )

            pairs = [[query, c["content"]] for c in candidates]
            scores = HybridRAGStrategy._reranker.predict(pairs)

            for i, score in enumerate(scores):
                candidates[i]["rerank_score"] = float(score)

            candidates.sort(key=lambda x: x.get("rerank_score", 0), reverse=True)
            return candidates

        except ImportError:
            logger.warning("CrossEncoder not available, skipping re-ranking")
            return candidates

    async def _colbert_rerank(
        self, query: str, candidates: list[dict]
    ) -> list[dict]:
        """Re-rank using ColBERT late-interaction model via RAGatouille."""
        try:
            from ragatouille import RAGPretrainedModel

            if not hasattr(HybridRAGStrategy, "_colbert_model") or \
               HybridRAGStrategy._colbert_model is None:
                HybridRAGStrategy._colbert_model = RAGPretrainedModel.from_pretrained(
                    "colbert-ir/colbertv2.0"
                )

            documents = [c["content"] for c in candidates]
            results = HybridRAGStrategy._colbert_model.rerank(
                query=query, documents=documents, k=len(documents)
            )

            # Map rerank scores back to candidates
            score_map = {r["content"]: r["score"] for r in results}
            for candidate in candidates:
                candidate["rerank_score"] = score_map.get(candidate["content"], 0.0)

            candidates.sort(key=lambda x: x.get("rerank_score", 0), reverse=True)
            return candidates

        except ImportError:
            logger.warning(
                "RAGatouille not available, falling back to cross-encoder"
            )
            return await self._cross_encoder_rerank(query, candidates)
