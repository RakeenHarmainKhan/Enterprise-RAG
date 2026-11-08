"""Collection CRUD."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from app.api.dependencies import CollectionsDep

router = APIRouter(prefix="/collections", tags=["collections"])


class CollectionCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=200)
    description: str = ""


class CollectionUpdate(BaseModel):
    name: str | None = None
    description: str | None = None


@router.get("")
async def list_collections(store: CollectionsDep) -> dict[str, object]:
    return {"collections": await store.list_all()}


@router.post("")
async def create_collection(body: CollectionCreate, store: CollectionsDep) -> dict[str, object]:
    rec = await store.create(body.name, body.description)
    return rec


@router.get("/{collection_id}")
async def get_collection(collection_id: str, store: CollectionsDep) -> dict[str, object]:
    rec = await store.get(collection_id)
    if not rec:
        raise HTTPException(status_code=404, detail="Not found")
    return rec


@router.patch("/{collection_id}")
async def patch_collection(
    collection_id: str,
    body: CollectionUpdate,
    store: CollectionsDep,
) -> dict[str, object]:
    rec = await store.update(collection_id, name=body.name, description=body.description)
    if not rec:
        raise HTTPException(status_code=404, detail="Not found")
    return rec


@router.delete("/{collection_id}")
async def delete_collection(collection_id: str, store: CollectionsDep) -> dict[str, object]:
    ok = await store.delete(collection_id)
    if not ok:
        raise HTTPException(status_code=400, detail="Cannot delete or not found")
    return {"deleted": True}
