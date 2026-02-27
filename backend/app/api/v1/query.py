"""
Main RAG query endpoints — sync and streaming.
"""

import asyncio
import json
import logging
import time
import uuid

from fastapi import APIRouter, Depends, Header, Request
from sse_starlette.sse import EventSourceResponse
from typing import Optional

from app.dependencies import get_current_user
from app.schemas.query import (
    CompareRequest,
    CompareResponse,
    CompareResult,
    QueryRequest,
    QueryResponse,
    SourceInfo,
)

logger = logging.getLogger("serpent.query")

router = APIRouter(tags=["query"])

MAX_HISTORY_MESSAGES = 20  # 10 turns


async def _load_session(app, user_id: str, session_id: Optional[str]):
    """Load chat session from Redis, return (session_id, history)."""
    cache = app.state.cache
    sid = session_id or str(uuid.uuid4())
    history = await cache.get_chat_session(user_id, sid) or []
    return sid, history


async def _save_session(app, user_id: str, session_id: str, history: list[dict]):
    """Save chat session to Redis with message limit."""
    cache = app.state.cache
    trimmed = history[-MAX_HISTORY_MESSAGES:]
    await cache.set_chat_session(user_id, session_id, trimmed)


def _get_user_id(current_user: Optional[dict]) -> str:
    """Extract user_id from JWT payload or fallback to anonymous."""
    if current_user and current_user.get("sub"):
        return current_user["sub"]
    return "anonymous"


@router.post("/query", response_model=QueryResponse)
async def query_documents(
    request: QueryRequest,
    req: Request,
    current_user: Optional[dict] = Depends(get_current_user),
):
    """Main RAG query endpoint — retrieves context and generates answer."""
    app = req.app
    factory = app.state.strategy_factory
    tracing = app.state.tracing_service
    llm_service = app.state.llm_service

    # Session management
    user_id = _get_user_id(current_user)
    session_id, history = await _load_session(app, user_id, request.session_id)

    # Query rewriting for follow-ups
    retrieval_query = request.query
    if history:
        retrieval_query = await llm_service.rewrite_query(request.query, history)

    strategy = factory.get(request.strategy)
    trace = tracing.create_recorder(
        query=request.query,
        strategy=request.strategy.value,
        collection=request.collection,
    )

    # Retrieve (use rewritten query for better retrieval)
    context = await strategy.retrieve(
        query=retrieval_query,
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
                    query=retrieval_query,
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
                    session_id=session_id,
                )

    # Generate (pass conversation history for contextual answers)
    answer = await strategy.generate(
        query=request.query,
        context=context,
        trace=trace,
        model=request.model,
        temperature=request.temperature,
        history=history or None,
    )

    # Save trace
    await tracing.save_trace(
        trace,
        chunks_retrieved=len(context),
        answer_length=len(answer),
        model=request.model,
    )

    # Update session history
    history.append({"role": "user", "content": request.query})
    history.append({"role": "assistant", "content": answer})
    await _save_session(app, user_id, session_id, history)

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
            "query_rewritten": retrieval_query != request.query,
        },
        latency_ms=trace.total_latency_ms,
        trace_id=trace.trace_id,
        session_id=session_id,
    )


@router.post("/query/stream")
async def query_stream(
    request: QueryRequest,
    req: Request,
    current_user: Optional[dict] = Depends(get_current_user),
):
    """Streaming RAG query endpoint via SSE."""
    app = req.app
    factory = app.state.strategy_factory
    tracing = app.state.tracing_service
    llm_service = app.state.llm_service

    # Session management (load before generator to avoid race conditions)
    user_id = _get_user_id(current_user)
    session_id, history = await _load_session(app, user_id, request.session_id)

    # Query rewriting for follow-ups
    retrieval_query = request.query
    if history:
        retrieval_query = await llm_service.rewrite_query(request.query, history)

    async def event_generator():
        strategy = factory.get(request.strategy)
        trace = tracing.create_recorder(
            query=request.query,
            strategy=request.strategy.value,
            collection=request.collection,
        )

        # Phase 1: Retrieval (use rewritten query)
        yield {
            "event": "status",
            "data": json.dumps({"phase": "retrieving"}),
        }

        context = await strategy.retrieve(
            query=retrieval_query,
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

        # Phase 3: Streaming generation (with history)
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
            history=history or None,
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

        # Update session history
        history.append({"role": "user", "content": request.query})
        history.append({"role": "assistant", "content": answer_text})
        await _save_session(app, user_id, session_id, history)

        # Phase 4: Done (include session_id)
        yield {
            "event": "done",
            "data": json.dumps({
                "trace_id": trace.trace_id,
                "latency_ms": trace.total_latency_ms,
                "strategy": request.strategy.value,
                "chunks_retrieved": len(context),
                "session_id": session_id,
                "query_rewritten": retrieval_query != request.query,
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
