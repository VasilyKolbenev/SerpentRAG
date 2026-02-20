"""
Knowledge Graph Explorer endpoint.
"""

from typing import Optional

from fastapi import APIRouter, Request

router = APIRouter(tags=["graph"])


@router.get("/graph/explore")
async def explore_graph(
    req: Request,
    collection: str = "default",
    entity: Optional[str] = None,
    depth: int = 2,
    limit: int = 100,
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
    except Exception:
        return {"nodes": [], "edges": []}
