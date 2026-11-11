# PodSeek Project Specification

## Purpose
PodSeek is an open-source, reference-quality agentic podcast transcript search engine and Corrective Retrieval-Augmented Generation (Self-RAG / CRAG) system. It provides precise, grounded answers with pinpoint timestamp citations to YouTube podcast episodes (Phase 1: Huberman Lab).

## Tech Stack
- **Runtime:** Python 3.13 (`.venv`)
- **Agent Orchestration:** LangGraph (`langgraph>=1.2`), LangChain Core (`langchain-core>=1.2`)
- **Default LLM Provider:** Google GenAI (`gemini-3.8-flash` via `langchain-google-genai>=4.4`)
- **Default Embeddings:** Google GenAI (`models/gemini-embedding-2`, 3072 dimensions)
- **Alternative Providers:** OpenAI, Anthropic, xAI (Grok), Ollama
- **Vector Database:** ChromaDB (`chromadb>=1.5`, `langchain-chroma>=1.1`) embedded persistent on disk (`chroma_db/`)
- **Web API:** FastAPI (`fastapi>=0.115`), Uvicorn (`uvicorn>=0.34`)
- **Web UI:** Gradio 5 Bento Studio (`gradio>=5,<6`), httpx (`httpx>=0.28`)
- **Data Validation:** Pydantic v2 (`pydantic>=2.10`)
- **Code Quality & Testing:** Pytest (`pytest>=8.0`), Ruff (`ruff>=0.8.0`), Pyright (`pyright>=1.1.390`)
- **Observability:** Optional LangSmith (`langsmith>=0.3`), custom Server-Sent Events (SSE) telemetry

## Core Architecture Conventions
1. **Self-RAG / Corrective RAG Workflow:**
   - Graph flow: `START` -> `retrieve` -> `[route_after_retrieve]` -> `grade_documents` (or fast-path bypass) -> `[decide_to_generate]` -> `rewrite_query` (up to max retries) -> `retrieve` OR `generate` -> `END`.
   - Hard circuit breaker: deterministic retry ceiling (`MAX_REWRITES = 2` in `app/agent/graph.py`). No unbounded loops.
   - Refusal contract: When no relevant chunks exist after allowable retries, generate a clean refusal without fabricating citations or hallucinating claims.
2. **Deterministic & Scalar Metadata:**
   - Vector store chunks only carry scalar metadata (`str`, `int`, `float`, `bool`) via `Chunk.to_metadata()`.
   - Timestamps are stored as numerical seconds (`start_seconds: float`) and formatted to `"HH:MM:SS"` strings for human readability.
3. **Isolated I/O:**
   - Network operations (e.g. `fetch_raw_captions`, YouTube oEmbed) are strictly decoupled from pure transforms (`captions_to_segments`, `chunk_segments`). Unit tests run 100% offline.
4. **Provider Abstraction:**
   - Provider models and embeddings are dynamically instantiated through `app/factory.py` using environment variables (`LLM_PROVIDER`, `CHAT_MODEL`, `EMBEDDING_PROVIDER`, `EMBEDDING_MODEL`), never hardcoded.
   - Chroma collection names dynamically incorporate the embedding model name (`podcast_chunks_<model>`) to prevent vector dimension mismatch errors across embedding switches.

## Operational Constraints
- **Hosting Environment:** Render.com free-tier web service (`podseek.onrender.com`, 512 MB RAM limit, ephemeral disk, spin-down after 15 minutes of inactivity).
- **Committed Pre-Indexed ChromaDB:** The `chroma_db/` directory is committed directly to git (under 100 MB) so that cold starts on free-tier cloud containers have instant access to indexed episodes without requiring runtime re-indexing or external database network roundtrips.
- **In-Process UI Mode on Cloud:** On Render, `PODSEEK_UI_MODE=inprocess` executes Gradio and the agent logic in a single unified OS process to stay strictly under the 512 MB memory boundary.
- **Protected Main Branch:** Direct pushes to `main` are disabled. All changes must go through a feature or doc branch, pass automated GitHub Actions CI (`ruff check .`, offline `pytest -v`), and be merged via Pull Request.
- **Offline CI Testing:** CI never invokes external LLM APIs, embedding endpoints, or web services. All 41 unit tests execute strictly offline.
