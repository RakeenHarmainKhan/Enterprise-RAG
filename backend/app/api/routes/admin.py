"""Operational endpoints."""

from __future__ import annotations

import asyncio
from pathlib import Path
from typing import Any

from fastapi import APIRouter, Request

from app.api.dependencies import SemanticCacheDep, YamlConfigDep
from app.ingestion.pipeline import IngestionPipeline

router = APIRouter(prefix="/admin", tags=["admin"])


@router.get("/stats")
async def admin_stats(request: Request, cache: SemanticCacheDep) -> dict[str, Any]:
    state = request.app.state.app_state
    index = str(state.yaml_config.ingestion.indexer_params.get("index_name", "enterprise_rag_chunks"))
    doc_count = 0
    try:
        r = state.opensearch.count(index=index)
        doc_count = int(r.get("count", 0))
    except Exception:
        pass
    registry = await state.documents.list_docs()
    return {
        "opensearch_index": index,
        "chunk_documents_approx": doc_count,
        "registered_documents": len(registry),
        "reindex_requested": state.reindex_requested,
    }


@router.post("/reindex")
async def admin_reindex(request: Request, yaml_cfg: YamlConfigDep) -> dict[str, Any]:
    state = request.app.state.app_state
    state.reindex_requested = True
    pipeline: IngestionPipeline = state.ingestion
    docs = await state.documents.list_docs()

    async def _job() -> int:
        n = 0
        try:
            for meta in docs:
                if meta.get("status") != "ready":
                    continue
                p = meta.get("path")
                if not p:
                    continue
                path = Path(p)
                if not path.is_file():
                    continue
                await asyncio.to_thread(
                    pipeline.ingest_file,
                    path,
                    document_id=meta["id"],
                    collection_id=meta.get("collection_id"),
                )
                n += 1
            return n
        finally:
            state.reindex_requested = False

    asyncio.create_task(_job())
    return {"status": "started", "documents_scheduled": len([d for d in docs if d.get("status") == "ready"])}


@router.get("/config")
async def admin_config(yaml_cfg: YamlConfigDep) -> dict[str, Any]:
    return yaml_cfg.model_dump()
