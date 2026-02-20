"""
Collection management endpoints.
"""

from fastapi import APIRouter, Request

from app.schemas.document import CollectionInfo, CollectionListResponse

router = APIRouter(tags=["collections"])


@router.get("/collections", response_model=CollectionListResponse)
async def list_collections(req: Request):
    """List all document collections."""
    vector_store = req.app.state.vector_store

    try:
        collection_names = await vector_store.get_collections()
        collections = []
        for name in collection_names:
            info = await vector_store.collection_info(name)
            collections.append(
                CollectionInfo(
                    name=name,
                    documents=0,  # TODO: count from DB
                    chunks=info.get("points_count", 0),
                )
            )
        return CollectionListResponse(collections=collections)
    except Exception:
        return CollectionListResponse(
            collections=[CollectionInfo(name="default", documents=0, chunks=0)]
        )
