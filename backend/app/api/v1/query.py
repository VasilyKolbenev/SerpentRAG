"""
Main RAG query endpoints — sync and streaming.
"""

import asyncio
import json
import time
import uuid

from fastapi import APIRouter, Request
from sse_starlette.sse import EventSourceResponse

from app.schemas.query import (
    CompareRequest,
    CompareResponse,
    CompareResult,
    QueryRequest,
    QueryResponse,
    SourceInfo,
)

router = APIRouter(tags=["query"])


@router.post("/query", response_model=QueryResponse)
async def query_documents(request: QueryRequest, req: Request):
    """Main RAG query endpoint — retrieves context and generates answer."""
    app = req.app
    factory = app.state.strategy_factory
    tracing = app.state.tracing_service

    strategy = factory.get(request.strategy)
    trace = tracing.create_recorder(
        query=request.query,
        strategy=request.strategy.value,
        collection=request.collection,
    )

    # Retrieve
    context = await strategy.retrieve(
        query=request.query,
        collection=request.collection,
        trace=trace,
        top_k=request.top_k,
        # Agentic
        max_iterations=request.max_iterations,
        enable_planning=request.enable_planning,
        enable_reflection=request.enable_reflection,
        # Graph
        max_hops=request.max_hops,
        entity_types=request.entity_types,
        # Hybrid
        sparse_weight=request.sparse_weight,
        enable_reranking=request.enable_reranking,
        reranker_type=request.reranker_type,
        # MemoRAG
        light_model=request.light_model,
        # CRAG
        relevance_threshold=request.relevance_threshold,
        web_search_enabled=request.web_search_enabled,
    )

    # Sufficient Context Check
    if request.check_sufficiency and context:
        is_sufficient, score = await strategy.check_context_sufficiency(
            query=request.query,
            context=context,
            trace=trace,
            threshold=request.sufficiency_threshold,
            model=request.model,
        )
        if not is_sufficient:
            if request.sufficiency_action == "retry":
                context = await strategy.retrieve(
                    query=request.query,
                    collection=request.collection,
                    trace=trace,
                    top_k=request.top_k * 2,
                    light_model=request.light_model,
                    relevance_threshold=request.relevance_threshold,
                    web_search_enabled=request.web_search_enabled,
                    sparse_weight=request.sparse_weight,
                    enable_reranking=request.enable_reranking,
                    reranker_type=request.reranker_type,
                )
            elif request.sufficiency_action == "abstain":
                await tracing.save_trace(
                    trace,
                    chunks_retrieved=len(context),
                    answer_length=0,
                    model=request.model,
                )
                sources = [
                    SourceInfo(
                        content=c["content"][:200],
                        score=c.get("score", 0),
                        metadata=c.get("metadata", {}),
                    )
                    for c in context
                ]
                return QueryResponse(
                    answer=(
                        f"Insufficient context to answer confidently "
                        f"(sufficiency score: {score:.0%}). "
                        f"Try uploading more relevant documents or rephrasing the query."
                    ),
                    sources=sources,
                    strategy_used=request.strategy,
                    metadata={
                        "model": request.model,
                        "top_k": request.top_k,
                        "chunks_retrieved": len(context),
                        "sufficiency_score": score,
                        "abstained": True,
                    },
                    latency_ms=trace.total_latency_ms,
                    trace_id=trace.trace_id,
                )

    # Generate
    answer = await strategy.generate(
        query=request.query,
        context=context,
        trace=trace,
        model=request.model,
        temperature=request.temperature,
    )

    # Save trace
    await tracing.save_trace(
        trace,
        chunks_retrieved=len(context),
        answer_length=len(answer),
        model=request.model,
    )

    sources = [
        SourceInfo(
            content=c["content"][:200],
            score=c.get("score", 0),
            metadata=c.get("metadata", {}),
        )
        for c in context
    ]

    return QueryResponse(
        answer=answer,
        sources=sources,
        strategy_used=request.strategy,
        metadata={
            "model": request.model,
            "top_k": request.top_k,
            "chunks_retrieved": len(context),
        },
        latency_ms=trace.total_latency_ms,
        trace_id=trace.trace_id,
    )


@router.post("/query/stream")
async def query_stream(request: QueryRequest, req: Request):
    """Streaming RAG query endpoint via SSE."""
    app = req.app
    factory = app.state.strategy_factory
    tracing = app.state.tracing_service

    async def event_generator():
        strategy = factory.get(request.strategy)
        trace = tracing.create_recorder(
            query=request.query,
            strategy=request.strategy.value,
            collection=request.collection,
        )

        # Phase 1: Retrieval
        yield {
            "event": "status",
            "data": json.dumps({"phase": "retrieving"}),
        }

        context = await strategy.retrieve(
            query=request.query,
            collection=request.collection,
            trace=trace,
            top_k=request.top_k,
            max_iterations=request.max_iterations,
            enable_planning=request.enable_planning,
            enable_reflection=request.enable_reflection,
            max_hops=request.max_hops,
            entity_types=request.entity_types,
            sparse_weight=request.sparse_weight,
            enable_reranking=request.enable_reranking,
            reranker_type=request.reranker_type,
            light_model=request.light_model,
            relevance_threshold=request.relevance_threshold,
            web_search_enabled=request.web_search_enabled,
        )

        # Phase 2: Sources
        sources = [
            {
                "content": c["content"][:200],
                "score": c.get("score", 0),
                "metadata": c.get("metadata", {}),
            }
            for c in context
        ]
        yield {
            "event": "sources",
            "data": json.dumps(sources, default=str),
        }

        # Phase 3: Streaming generation
        yield {
            "event": "status",
            "data": json.dumps({"phase": "generating"}),
        }

        full_answer = []
        async for token in strategy.stream_generate(
            query=request.query,
            context=context,
            model=request.model,
            temperature=request.temperature,
        ):
            full_answer.append(token)
            yield {
                "event": "token",
                "data": json.dumps({"text": token}),
            }

        # Save trace
        answer_text = "".join(full_answer)
        await tracing.save_trace(
            trace,
            chunks_retrieved=len(context),
            answer_length=len(answer_text),
            model=request.model,
        )

        # Phase 4: Done
        yield {
            "event": "done",
            "data": json.dumps({
                "trace_id": trace.trace_id,
                "latency_ms": trace.total_latency_ms,
                "strategy": request.strategy.value,
                "chunks_retrieved": len(context),
            }),
        }

    return EventSourceResponse(event_generator())


@router.post("/compare", response_model=CompareResponse)
async def compare_strategies(request: CompareRequest, req: Request):
    """A/B comparison — run the same query through multiple strategies."""
    app = req.app
    factory = app.state.strategy_factory
    tracing = app.state.tracing_service

    async def run_strategy(strat_enum):
        strategy = factory.get(strat_enum)
        trace = tracing.create_recorder(
            query=request.query,
            strategy=strat_enum.value,
            collection=request.collection,
        )

        context = await strategy.retrieve(
            query=request.query,
            collection=request.collection,
            trace=trace,
            top_k=request.top_k,
        )

        answer = await strategy.generate(
            query=request.query,
            context=context,
            trace=trace,
            model=request.model,
            temperature=request.temperature,
        )

        await tracing.save_trace(
            trace,
            chunks_retrieved=len(context),
            answer_length=len(answer),
            model=request.model,
        )

        return CompareResult(
            strategy=strat_enum,
            answer=answer,
            sources=[
                SourceInfo(
                    content=c["content"][:200],
                    score=c.get("score", 0),
                    metadata=c.get("metadata", {}),
                )
                for c in context
            ],
            latency_ms=trace.total_latency_ms,
            trace_id=trace.trace_id,
        )

    # Run all strategies in parallel
    results = await asyncio.gather(
        *[run_strategy(s) for s in request.strategies],
        return_exceptions=True,
    )

    # Filter out exceptions
    valid_results = [r for r in results if isinstance(r, CompareResult)]

    return CompareResponse(query=request.query, results=valid_results)
