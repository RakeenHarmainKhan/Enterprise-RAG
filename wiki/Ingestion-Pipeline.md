# From file bytes to searchable chunks

**Your documents are not born as vectors.** They arrive as PDFs, docx blobs, HTML, Markdown—messy, human-shaped things. The ingestion pipeline’s job is to turn that noise into **consistent chunk documents** OpenSearch can score. The implementation lives in **`backend/app/ingestion/pipeline.py`** as **`IngestionPipeline.ingest_file`**: **parse → chunk → enrich → embed → index**.

```mermaid
flowchart LR
  classDef primary fill:#f59e0b,stroke:#d97706,color:#451a03
  classDef secondary fill:#10b981,stroke:#059669,color:#fff
  classDef store fill:#0f172a,stroke:#f59e0b,color:#fcd34d

  F[File on disk] --> P[Parse]
  P --> C[Chunk]
  C --> M[MetadataEnricher]
  M --> E[Embed]
  E --> I[Index]
  I --> OS[(OpenSearch)]

  class F,P,C,M,E primary
  class I secondary
  class OS store
```

---

## Parser plugins

Registered in **`parsers.py`** on **`parser_registry`**.

| Name | Implementation | Notes |
|------|----------------|-------|
| `pdf` | PyMuPDF (`fitz`) | Page-wise `get_text("text")`, joined with blank lines |
| `docx` | `python-docx` | Paragraph text joined |
| `html` | BeautifulSoup | Strips `script`/`style`, `get_text` with newlines |
| `markdown` | Regex | Removes fenced code, inline code, leading `#` headings — **plain text** for chunking |

**Extension override:** Even if **`ingestion.parser`** is `pdf`, uploading **`.md`** forces the **`markdown`** parser (same pattern for docx/html).

> [!TIP]
> Markdown parsing is intentionally **lossy**—it wants **chunkable plain text**, not a rendered blog. If you need structure-aware Markdown, that is a custom parser-shaped opportunity.

---

## Chunking strategies

Registered on **`chunker_registry`** in **`chunkers.py`**.

### `fixed` — `FixedSizeChunker`

Sliding character windows: **`chunk_size`**, **`chunk_overlap`**. Fast, no extra model calls.

### `recursive` — `RecursiveChunker`

Uses **LlamaIndex** **`SentenceSplitter`** (`llama_index.core.node_parser`) for sentence-aware splits. Parameters: **`chunk_size`**, **`chunk_overlap`** (characters, LlamaIndex semantics).

### `semantic` — `SemanticChunker`

Splits text into sentences (regex on `.?!`). Embeds each sentence; walks forward comparing **cosine similarity** between adjacent sentences. When similarity drops below **`similarity_threshold`** **and** the current group has at least **`min_sentences_per_chunk`** sentences, starts a new chunk.

The pipeline injects **`embed_fn=lambda sents: embedder.embed_many(sents)`** so semantic chunking uses the **same embedder** as indexing.

Example **`config.yaml`** fragment:

```yaml
ingestion:
  chunker: semantic
  chunker_params:
    similarity_threshold: 0.72
    min_sentences_per_chunk: 2
```

> [!NOTE]
> Semantic chunking trades CPU for coherence—great when sentences should stick together, wasteful when your docs are already short.

---

## Embedding providers

**`embedders.py`** — **`build_embedder(name, settings, **params)`**.

| Name | Class | Notes |
|------|-------|-------|
| `openai` | `OpenAIEmbedder` | HTTP POST to `https://api.openai.com/v1/embeddings`; requires **`OPENAI_API_KEY`**; batched with retries (`tenacity`) |
| `local` | `LocalEmbedder` | `sentence_transformers.SentenceTransformer`; **`model`** defaults to **`all-MiniLM-L6-v2`** |

**`dimension`** is used by **`OpenSearchIndexer.ensure_index`** to set **`knn_vector.dimension`**.

---

## Indexing to OpenSearch

**`OpenSearchIndexer`** (`indexers.py`):

- **`ensure_index`:** Creates index with **`knn: true`** and **`embedding`** as **`knn_vector`** (HNSW, L2, Lucene engine).
- **`bulk_index`:** Uses **`opensearchpy.helpers.bulk`** with **`refresh=wait_for`**.
- **Document shape:** `chunk_id`, `document_id`, `collection_id`, `text`, `title`, `embedding`, `metadata` (object).

**`indexer_params.index_name`** defaults to **`enterprise_rag_chunks`**.

> [!WARNING]
> Changing embedding **dimension** after data exists is a classic footgun—you may need a new **`index_name`** or a careful reindex plan.

---

## Metadata enrichment

**`MetadataEnricher.enrich`**:

- **`title`:** First non-trivial line (10–120 chars) or filename.
- **`extracted_dates`:** ISO **`YYYY-MM-DD`** and **`M/D/YYYY`** patterns.
- **`entities`:** Capitalized multi-word phrases (heuristic, not NER), capped at 20.
- **`enriched_at`:** UTC ISO timestamp.

The pipeline merges **`chunk_index`** and **`source_file`** into metadata.

---

## Creating a custom parser

1. Implement **`parse(self, file_path: Path, **kwargs) -> str`**.
2. Register with **`@parser_registry.register("my_format")`** on a class, or register a factory.
3. Set **`ingestion.parser: my_format`** for default use, or use a file extension if you extend **`ingest_file`** logic.

Minimal pattern:

```python
from pathlib import Path
from app.ingestion.parsers import parser_registry

@parser_registry.register("plaintext")
class PlainTextParser:
    def parse(self, file_path: Path, **kwargs) -> str:
        return file_path.read_text(encoding="utf-8", errors="replace")
```

Rebuild the parser registry import path so the decorator runs at startup (ensure the module is imported from **`parsers.py`** or from **`app.ingestion`** package init).

---

## Creating a custom indexer

Implement **`IndexerPlugin`**: **`ensure_index`**, **`bulk_index`**, **`delete_by_document`**. Register on **`indexer_registry`** and set **`ingestion.indexer`** in YAML. **`build_indexer`** currently special-cases **`opensearch`**; extend it similarly to **`build_embedder`**.

---

## Related pages

- [Configuration](Configuration.md)
- [Architecture](Architecture.md)
- [Retrieval Engine](Retrieval-Engine.md)
