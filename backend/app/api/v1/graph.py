"""
Knowledge Graph Explorer endpoint.
"""

import logging
from typing import Optional

from fastapi import APIRouter, Query, Request

logger = logging.getLogger("serpent.api.graph")

router = APIRouter(tags=["graph"])


@router.get("/graph/explore")
async def explore_graph(
    req: Request,
    collection: str = "default",
    entity: Optional[str] = None,
    depth: int = Query(2, ge=1, le=5, description="Max traversal depth"),
    limit: int = Query(100, ge=1, le=500, description="Max nodes to return"),
):
    """Get graph data for the Knowledge Graph Explorer UI."""
    graph_store = req.app.state.graph_store

    try:
        subgraph = await graph_store.get_subgraph(
            collection=collection,
            center_entity=entity,
            depth=depth,
            limit=limit,
        )
        return subgraph
    except Exception as exc:
        logger.warning("Graph explore failed", extra={"error": str(exc)})
        return {"nodes": [], "edges": []}
