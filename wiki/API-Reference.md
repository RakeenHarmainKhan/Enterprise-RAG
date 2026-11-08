# HTTP API: curl-friendly truth

Base URL: **`http://localhost:8000`** (local). OpenAPI UI: **`/docs`**.

> [!TIP]
> Prefer **`/docs`** when you are exploring; prefer this page when you want **copy-paste curls** that match production payloads.

---

## Health

### `GET /health/live`

Liveness probe — no dependency checks.

```bash
curl -sS http://localhost:8000/health/live | python3 -m json.tool
```

**200** example:

```json
{ "status": "ok" }
```

### `GET /health/ready`

Readiness — OpenSearch ping + Redis ping.

```bash
curl -sS http://localhost:8000/health/ready | python3 -m json.tool
```

**200** example:

```json
{
  "ready": true,
  "components": {
    "opensearch": { "ping": true },
    "redis": { "ping": true }
  }
}
```

> [!NOTE]
> Wire **`/health/live`** to liveness and **`/health/ready`** to readiness—mixing them up causes Kubernetes to do dramatic, unnecessary things.

---

## Documents

### `POST /documents/upload`

`multipart/form-data` with field **`file`** (required). Optional form field **`collection_id`**.

```bash
curl -sS -X POST http://localhost:8000/documents/upload \
  -F "file=@./sample.pdf" \
  -F "collection_id=support-docs" | python3 -m json.tool
```

**200** success shape:

```json
{
  "status": "ok",
  "document_id": "...",
  "chunks": 42,
  "indexed": 42,
  "filename": "sample.pdf",
  "collection_id": "support-docs"
}
```

**400** — ingestion error (empty extract, embedding mismatch, etc.).

### `GET /documents`

```bash
curl -sS http://localhost:8000/documents | python3 -m json.tool
```

```json
{ "documents": [ { "id": "...", "filename": "...", "status": "ready", "chunks": 10 } ] }
```

### `GET /documents/{doc_id}`

```bash
curl -sS http://localhost:8000/documents/<doc_id> | python3 -m json.tool
```

**404** if unknown.

### `DELETE /documents/{doc_id}`

Removes OpenSearch chunks by **`document_id`**, deletes registry entry and upload directory.

```bash
curl -sS -X DELETE http://localhost:8000/documents/<doc_id> | python3 -m json.tool
```

```json
{ "deleted": true, "chunks_removed": 10 }
```

> [!CAUTION]
> **`DELETE`** is destructive: chunks, registry state, and on-disk uploads for that document go away. Plan backups before you script this in prod.

---

## Query

### `POST /query`

JSON body:

| Field | Type | Description |
|-------|------|-------------|
| `query` | string | Required, 1–8000 chars |
| `collection_id` | string? | Filters retrieval to collection |
| `stream` | bool | SSE when `generation.streaming` is true |
| `use_cache` | bool | Default true — uses Redis semantic cache when enabled |

**Non-streaming:**

```bash
curl -sS -X POST http://localhost:8000/query \
  -H "Content-Type: application/json" \
  -d '{"query":"What is our refund policy?","collection_id":null,"stream":false,"use_cache":true}' \
  | python3 -m json.tool
```

**400** input blocked:

```json
{ "detail": { "blocked": true, "warnings": ["..."] } }
```

**Streaming (SSE):** same URL; **`stream: true`**. Events are **`data: {...}\n\n`** JSON objects with keys like **`token`**, **`warnings`**, **`error`**, **`done`**.

```bash
curl -N -X POST http://localhost:8000/query \
  -H "Content-Type: application/json" \
  -d '{"query":"Hello","stream":true}'
```

> [!IMPORTANT]
> Streaming responses are chunked **after** full generation and output guardrails when **`generation.streaming`** is true—see [Generation](Generation.md).

### `POST /query/batch`

Up to **32** items. No streaming; no semantic cache in loop.

```bash
curl -sS -X POST http://localhost:8000/query/batch \
  -H "Content-Type: application/json" \
  -d '{"items":[{"query":"Q1"},{"query":"Q2","collection_id":"c1"}]}' | python3 -m json.tool
```

Response:

```json
{
  "results": [
    { "answer": "...", "sources": [], "citations": [], "guardrail_warnings": [] }
  ]
}
```

Items may be **`{ "query": "...", "blocked": true, "warnings": [...] }`** if guardrails block.

---

## Collections

### `GET /collections`

```bash
curl -sS http://localhost:8000/collections | python3 -m json.tool
```

### `POST /collections`

```bash
curl -sS -X POST http://localhost:8000/collections \
  -H "Content-Type: application/json" \
  -d '{"name":"Support","description":"Customer-facing articles"}' | python3 -m json.tool
```

### `GET /collections/{collection_id}`

### `PATCH /collections/{collection_id}`

```bash
curl -sS -X PATCH http://localhost:8000/collections/<id> \
  -H "Content-Type: application/json" \
  -d '{"name":"Support v2","description":"Updated"}' | python3 -m json.tool
```

### `DELETE /collections/{collection_id}`

**400** if cannot delete or not found (per **`CollectionStore`** logic).

---

## Evaluation

### `POST /evaluation/run`

```bash
curl -sS -X POST http://localhost:8000/evaluation/run \
  -H "Content-Type: application/json" \
  -d '{
    "question": "What is the SLA?",
    "answer": "99.9% uptime.",
    "contexts": ["SLA section: 99.9% monthly uptime."]
  }' | python3 -m json.tool
```

### `GET /evaluation/results?limit=50`

```bash
curl -sS "http://localhost:8000/evaluation/results?limit=10" | python3 -m json.tool
```

---

## Admin

### `GET /admin/stats`

```bash
curl -sS http://localhost:8000/admin/stats | python3 -m json.tool
```

```json
{
  "opensearch_index": "enterprise_rag_chunks",
  "chunk_documents_approx": 1200,
  "registered_documents": 15,
  "reindex_requested": false
}
```

### `POST /admin/reindex`

Schedules background task to re-run **`ingest_file`** for documents in **`ready`** state with valid paths.

```bash
curl -sS -X POST http://localhost:8000/admin/reindex | python3 -m json.tool
```

```json
{ "status": "started", "documents_scheduled": 12 }
```

### `GET /admin/config`

Returns **`yaml_cfg.model_dump()`** — full active configuration. **Protect in production.**

```bash
curl -sS http://localhost:8000/admin/config | python3 -m json.tool
```

> [!WARNING]
> **`GET /admin/config`** is a configuration exfiltration endpoint if left wide open. Authenticate it. Network-restrict it. Love it from a distance.

---

## CORS

Browser calls from the Vite dev server require **`CORS_ORIGINS`** to include the UI origin (default includes **`http://localhost:5173`**).

---

## Related pages

- [Getting Started](Getting-Started.md)
- [Generation](Generation.md)
- [Guardrails](Guardrails.md)
