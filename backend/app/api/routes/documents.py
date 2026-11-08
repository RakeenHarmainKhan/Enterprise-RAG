"""Document upload and lifecycle."""

from __future__ import annotations

import asyncio
import shutil

import aiofiles
from fastapi import APIRouter, File, Form, HTTPException, Request, UploadFile

from app.api.dependencies import DocumentsDep, IngestionDep, SemanticCacheDep, YamlConfigDep
from app.core.exceptions import IngestionError
from app.ingestion.indexers import OpenSearchIndexer

router = APIRouter(prefix="/documents", tags=["documents"])


@router.post("/upload")
async def upload_document(
    documents: DocumentsDep,
    pipeline: IngestionDep,
    yaml_cfg: YamlConfigDep,
    cache: SemanticCacheDep,
    file: UploadFile = File(...),
    collection_id: str | None = Form(default=None),
) -> dict[str, object]:
    doc_id = await documents.create_placeholder(
        filename=file.filename or "upload",
        collection_id=collection_id,
        content_type=file.content_type,
    )
    dest_dir = documents.resolve_upload_dir(doc_id)
    dest_dir.mkdir(parents=True, exist_ok=True)
    dest_path = dest_dir / (file.filename or "document")
    try:
        async with aiofiles.open(dest_path, "wb") as out:
            content = await file.read()
            await out.write(content)
        result = await asyncio.to_thread(
            pipeline.ingest_file,
            dest_path,
            document_id=doc_id,
            collection_id=collection_id,
        )
        await documents.mark_ready(doc_id, chunks=result["chunks"], path=str(dest_path))
        await cache.clear_if_enabled()
        return {"status": "ok", **result}
    except IngestionError as e:
        await documents.mark_failed(doc_id, str(e))
        raise HTTPException(status_code=400, detail=str(e)) from e
    except Exception as e:
        await documents.mark_failed(doc_id, str(e))
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.get("")
async def list_documents(documents: DocumentsDep) -> dict[str, object]:
    return {"documents": await documents.list_docs()}


@router.get("/{doc_id}")
async def get_document(doc_id: str, documents: DocumentsDep) -> dict[str, object]:
    doc = await documents.get(doc_id)
    if not doc:
        raise HTTPException(status_code=404, detail="Not found")
    return doc


@router.delete("/{doc_id}")
async def delete_document(
    doc_id: str,
    request: Request,
    documents: DocumentsDep,
    yaml_cfg: YamlConfigDep,
    cache: SemanticCacheDep,
) -> dict[str, object]:
    state = request.app.state.app_state
    indexer = OpenSearchIndexer(
        state.opensearch,
        index_name=str(yaml_cfg.ingestion.indexer_params.get("index_name", "enterprise_rag_chunks")),
    )
    deleted = indexer.delete_by_document(doc_id, **yaml_cfg.ingestion.indexer_params)
    existed = await documents.delete(doc_id)
    dest = documents.resolve_upload_dir(doc_id)
    if dest.exists():
        shutil.rmtree(dest, ignore_errors=True)
    if deleted:
        await cache.clear_if_enabled()
    if not existed and deleted == 0:
        raise HTTPException(status_code=404, detail="Not found")
    return {"deleted": True, "chunks_removed": deleted}
