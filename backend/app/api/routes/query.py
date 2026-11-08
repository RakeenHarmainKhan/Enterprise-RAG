"""RAG query endpoints with optional SSE streaming."""

from __future__ import annotations

import json
from typing import Any

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from app.api.dependencies import (
    EventBusDep,
    GenerationDep,
    GuardInputDep,
    GuardOutputDep,
    RetrievalDep,
    SemanticCacheDep,
    YamlConfigDep,
)

router = APIRouter(prefix="/query", tags=["query"])


class QueryBody(BaseModel):
    query: str = Field(..., min_length=1, max_length=8000)
    collection_id: str | None = None
    stream: bool = False
    use_cache: bool = True


class BatchQueryItem(BaseModel):
    query: str
    collection_id: str | None = None


class BatchQueryBody(BaseModel):
    items: list[BatchQueryItem] = Field(default_factory=list, max_length=32)


@router.post("")
async def run_query(
    body: QueryBody,
    gen: GenerationDep,
    retrieval: RetrievalDep,
    cache: SemanticCacheDep,
    yaml_cfg: YamlConfigDep,
    bus: EventBusDep,
    input_g: GuardInputDep,
    output_g: GuardOutputDep,
) -> Any:
    await bus.publish({"type": "query_start", "query": body.query[:200]})
    in_res = await input_g.process(body.query)
    if in_res.blocked:
        raise HTTPException(status_code=400, detail={"blocked": True, "warnings": in_res.warnings})

    q = in_res.text
    if body.use_cache and yaml_cfg.cache.backend == "redis":
        cached = await cache.lookup(q, body.collection_id)
        if cached:
            await bus.publish({"type": "query_cache_hit"})
            return {"cached": True, **cached}

    if yaml_cfg.generation.streaming and body.stream:

        async def event_stream():
            chunks = await retrieval.retrieve(q, collection_id=body.collection_id)
            ctx = {
                "retrieval_chunks": [
                    {"text": c.text, "chunk_id": c.chunk_id, "document_id": c.document_id} for c in chunks
                ]
            }
            buf: list[str] = []
            async for token in gen.generate_stream(q, collection_id=body.collection_id, chunks=chunks):
                buf.append(token)
            full = "".join(buf)
            out_res = await output_g.process(full, context=ctx)
            if out_res.blocked:
                yield f"data: {json.dumps({'error': 'blocked', 'warnings': out_res.warnings})}\n\n"
                return
            if out_res.warnings:
                yield f"data: {json.dumps({'warnings': out_res.warnings})}\n\n"
            text = out_res.text
            for i in range(0, len(text), 64):
                chunk = text[i : i + 64]
                yield f"data: {json.dumps({'token': chunk})}\n\n"
            payload = {"answer": text, "warnings": out_res.warnings}
            if body.use_cache and yaml_cfg.cache.backend == "redis":
                await cache.store(q, payload, body.collection_id)
            yield f"data: {json.dumps({'done': True, 'answer': text})}\n\n"
            await bus.publish({"type": "query_done", "stream": True})

        return StreamingResponse(event_stream(), media_type="text/event-stream")

    result = await gen.generate(q, collection_id=body.collection_id)
    out_res = await output_g.process(
        result["answer"],
        context={"retrieval_chunks": result.get("retrieval_chunks", [])},
    )
    if out_res.blocked:
        raise HTTPException(status_code=400, detail={"blocked": True, "warnings": out_res.warnings})
    result["answer"] = out_res.text
    result["guardrail_warnings"] = out_res.warnings + in_res.warnings
    if body.use_cache and yaml_cfg.cache.backend == "redis":
        await cache.store(
            q, {k: v for k, v in result.items() if k != "chunks_used"}, body.collection_id
        )
    await bus.publish({"type": "query_done", "stream": False})
    return result


@router.post("/batch")
async def batch_query(
    body: BatchQueryBody,
    gen: GenerationDep,
    input_g: GuardInputDep,
    output_g: GuardOutputDep,
) -> dict[str, Any]:
    out: list[dict[str, Any]] = []
    for item in body.items:
        in_res = await input_g.process(item.query)
        if in_res.blocked:
            out.append({"query": item.query, "blocked": True, "warnings": in_res.warnings})
            continue
        res = await gen.generate(in_res.text, collection_id=item.collection_id)
        o_res = await output_g.process(res["answer"])
        if o_res.blocked:
            out.append({"query": item.query, "blocked": True, "warnings": o_res.warnings})
            continue
        res["answer"] = o_res.text
        res["guardrail_warnings"] = o_res.warnings
        out.append(res)
    return {"results": out}
