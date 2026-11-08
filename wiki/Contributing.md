# Contributing: keep the plugins flowing

**The best PRs read like a story:** what broke, what you changed, how someone else configures it. This repo is built to grow by **registration**, not by inflating **`main.py`**.

Contributions are welcome via [GitHub Issues](https://github.com/anmolg1997/Enterprise-RAG-System/issues) and pull requests.

```mermaid
flowchart LR
  classDef primary fill:#f59e0b,stroke:#d97706,color:#451a03
  classDef secondary fill:#10b981,stroke:#059669,color:#fff

  FORK[Fork + branch] --> DEV[make setup]
  DEV --> TEST[make test]
  TEST --> LINT[make lint]
  LINT --> PR[Pull request]

  class FORK,PR primary
  class DEV,TEST,LINT secondary
```

---

## How to contribute

1. **Fork** the repository and create a feature branch from **`main`**.
2. **Install** dev dependencies: **`make setup`**.
3. **Run checks** before opening a PR:
   - **`make test`**
   - **`make lint`**
4. **Describe** your change in the PR: motivation, scope, and any config or migration notes.
5. **Docs** — update **`README.md`** or **`wiki/`** when behavior or configuration changes.

> [!TIP]
> If you add a plugin, add a **tiny** example YAML fragment to the relevant wiki page—future you will send thank-you notes.

---

## Adding plugins

### Ingestion

- **Parser / chunker / embedder / indexer:** register on the appropriate **`*_registry`** in **`backend/app/ingestion/`**.
- Export registration by ensuring the module is imported at startup (typically already pulled in via **`parsers.py`** etc.).
- Add tests under **`backend/tests/`** if non-trivial.

### Retrieval

- **Router:** **`router_registry`** in **`router.py`**; wire **`build_router`** if special constructor args are needed.
- **Retriever:** **`retriever_registry`** in **`strategies.py`**; update **`build_retriever`**.
- **Fusion / reranker:** same pattern in **`fusion.py`** / **`rerankers.py`**.

### Guardrails

- Implement async **`run`** returning **`GuardrailResult`**.
- Add to **`_plugin_factory`** mapping in **`guardrails/chain.py`**.
- Document new **`params`** in [Guardrails](Guardrails.md).

---

## Code style

| Area | Tool / convention |
|------|-------------------|
| Python | **Ruff** (`make lint`, `make format`), type hints, `from __future__ import annotations` where used in codebase |
| Imports | Standard library → third party → local `app.*` |
| Frontend | **TypeScript** strict project; **Prettier** for formatting (`npm run format`) |
| API | FastAPI routers in **`app/api/routes/`**; shared DI in **`dependencies.py`** |

> [!NOTE]
> When in doubt, **match the file you edited**—consistency beats personal preference.

---

## Commit messages

Prefer imperative, scoped messages: **`retrieval: add custom foo retriever`**, **`docs: expand wiki configuration`**.

---

## License

By contributing, you agree your contributions are licensed under the project [MIT License](../LICENSE).

---

## Related pages

- [Architecture](Architecture.md)
- [Home](Home.md)
