# How everything connects

If you only read one wiki page after Getting Started, make it this one: **it is the map for where your bytes go, where they get scored, and where policy intercepts them.**

---

## The system at a glance

```mermaid
flowchart TB
  classDef primary fill:#f59e0b,stroke:#d97706,color:#451a03
  classDef secondary fill:#10b981,stroke:#059669,color:#fff
  classDef accent fill:#fffbeb,stroke:#f59e0b,color:#78350f
  classDef store fill:#0f172a,stroke:#f59e0b,color:#fcd34d

  subgraph Client
    UI[React SPA]
  end

  subgraph API[FastAPI]
    H[health]
    DOC[documents]
    Q[query]
    COL[collections]
    EV[evaluation]
    ADM[admin]
  end

  subgraph Core
    ING[IngestionPipeline]
    RET[RetrievalEngine]
    GEN[GenerationEngine]
    GIN[GuardrailChain input]
    GOUT[GuardrailChain output]
    CACHE[SemanticCache]
  end

  subgraph Data
    OS[(OpenSearch)]
    RD[(Redis)]
    FS[uploads/ JSON stores]
  end

  subgraph Obs
    LF[Langfuse client]
    EB[EventBus]
  end

  UI --> H & DOC & Q & COL & EV & ADM
  DOC --> ING
  ING --> OS
  Q --> GIN --> CACHE
  CACHE -.miss.-> RET
  RET --> OS
  RET --> GEN
  GEN --> GOUT
  GIN & RET & GEN -.-> LF
  Q --> EB
  DOC & COL --> FS

  class UI,H,DOC,Q,COL,EV,ADM primary
  class ING,RET,GEN,GIN,GOUT,CACHE secondary
  class EB accent
  class OS,RD,FS,LF store
```

> [!NOTE]
> **Semantic cache** sits on the query path **before** retrieval when enabled. A hit short-circuits the expensive bits—think of it as “someone already paid the embedding tax for a very similar question.”

---

## How plugins assemble (ingestion + retrieval factories)

```mermaid
flowchart LR
  classDef primary fill:#f59e0b,stroke:#d97706,color:#451a03
  classDef secondary fill:#10b981,stroke:#059669,color:#fff
  classDef store fill:#0f172a,stroke:#f59e0b,color:#fcd34d

  subgraph ingestion
    P[build_parser]
    C[build_chunker]
    M[MetadataEnricher]
    E[build_embedder]
    I[build_indexer]
    PL[IngestionPipeline]
    PL --> P --> C --> M
    PL --> E --> I
  end

  subgraph retrieval
    RTR[build_router]
    ST[build_retriever x N]
    F[build_fusion]
    RR[build_reranker]
    RE[RetrievalEngine]
    RE --> RTR
    RE --> ST
    ST --> F --> RR
  end

  I --> OS[(OpenSearch)]
  ST --> OS
  E --> APIE[Embedding provider]

  class P,C,M,E,I,PL,RTR,ST,F,RR,RE primary
  class APIE secondary
  class OS store
```

---

## Ingestion flow (document upload)

**Why this order matters:** you cannot embed what you did not chunk, and you cannot enrich metadata you never extracted. The pipeline is deliberately linear: **parse → chunk → enrich → embed → index**.

1. **HTTP:** `POST /documents/upload` saves bytes under `uploads/{doc_id}/`, registers metadata in **`DocumentStore`**, and calls **`IngestionPipeline.ingest_file`** in a thread pool.
2. **Parser selection:** `parser` from YAML is overridden by extension: `.pdf` → `pdf`, `.docx` → `docx`, `.html`/`.htm` → `html`, `.md`/`.markdown` → `markdown`.
3. **Chunking:** `build_chunker` produces a list of text chunks. **`semantic`** chunking injects **`embed_fn`** from the pipeline so consecutive sentences are grouped by embedding cosine similarity.
4. **Enrichment:** **`MetadataEnricher`** adds `title`, `extracted_dates`, `entities` (capitalized-phrase heuristic), `enriched_at`, plus `chunk_index` / `source_file`.
5. **Embedding:** **`embed_many`** batches vectors; dimension drives index mapping.
6. **Indexing:** **`OpenSearchIndexer.ensure_index`** creates the index with **knn** settings if missing; **`bulk_index`** writes chunk documents including **`collection_id`** (default **`default`**).

```mermaid
sequenceDiagram
  participant U as Client
  participant API as FastAPI
  participant DS as DocumentStore
  participant PL as IngestionPipeline
  participant OS as OpenSearch

  U->>API: POST /documents/upload
  API->>DS: create_placeholder
  API->>PL: ingest_file(path, document_id, collection_id)
  PL->>PL: parse → chunk → enrich → embed
  PL->>OS: ensure_index + bulk_index
  PL-->>API: chunks count
  API->>DS: mark_ready
  API-->>U: JSON result
```

> [!TIP]
> If uploads succeed but search feels empty, check **`ingestion.indexer_params.index_name`** in Dashboards—you might be staring at the wrong index.

---

## Query flow (RAG)

**The story:** publish intent, scrub input, maybe steal an answer from cache, retrieve honestly, generate with a budget, then let output policy have the last word.

1. **Event:** `EventBus.publish({"type": "query_start", ...})`.
2. **Input guardrails:** `GuardrailChain.process(query)` — may redact, warn, or block (**`HTTP 400`**).
3. **Cache:** If `use_cache` and `cache.backend == redis`, **`SemanticCache.lookup`** compares embedding cosine similarity to stored entries; on hit, returns cached payload.
4. **Retrieval:** `RetrievalEngine.retrieve` embeds the query, **routes** (`hybrid` / `rules` / `classifier`), runs configured **strategies** (e.g. dense + sparse), **fuses** lists (RRF by default), **reranks** (cross-encoder by default).
5. **Generation:** **`GenerationEngine`** builds context within token budget, calls LLM (`generate` or `generate_stream`).
6. **Output guardrails:** Process final answer; may block or attach warnings.
7. **Cache store:** Non-streaming and streaming paths can persist `{answer, ...}` keyed by semantic embedding (see [Generation](Generation.md) for streaming nuances).

```mermaid
sequenceDiagram
  participant U as Client
  participant API as /query
  participant GI as Input guardrails
  participant SC as SemanticCache
  participant RE as RetrievalEngine
  participant OS as OpenSearch
  participant GE as GenerationEngine
  participant GO as Output guardrails

  U->>API: POST {query, collection_id, stream, use_cache}
  API->>GI: process(query)
  alt blocked
    GI-->>API: blocked
    API-->>U: 400
  end
  API->>SC: lookup (optional)
  alt cache hit
    SC-->>API: cached payload
    API-->>U: JSON
  end
  API->>RE: retrieve
  RE->>OS: knn + match queries
  RE-->>API: RetrievedChunk list
  API->>GE: generate / generate_stream
  GE-->>API: answer text
  API->>GO: process(answer, context)
  GO-->>API: final text / blocked
  API-->>U: response or SSE
```

> [!IMPORTANT]
> When **`generation.streaming`** is **true** and the client sends **`stream: true`**, the API still assembles the **full** answer before output guardrails and before SSE chunks go out. See [Generation](Generation.md) for why that matters for UX expectations.

---

## Application lifecycle

`main.py` **`lifespan`** constructs a single **`AppState`**: OpenSearch client, Redis async client, embedder, **`IngestionPipeline`**, **`RetrievalEngine`**, **`GenerationEngine`**, guardrail chains, **`EvaluationEngine`**, **`SemanticCache`**, **`EventBus`**, **`LangfuseTracer`**, document/collection stores. Dependencies in **`api/dependencies.py`** read from **`request.app.state.app_state`**.

---

## Related pages

- [Design Decisions](Design-Decisions.md)
- [Ingestion Pipeline](Ingestion-Pipeline.md)
- [Retrieval Engine](Retrieval-Engine.md)
- [Generation](Generation.md)
