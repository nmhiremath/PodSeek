# PodSeek — Claude Code & Developer Context

This document is the single source of truth for AI assistants (Claude Code, Antigravity) and engineers working on this repository.

---

## 0. Streamlined Pair Programming & Tutoring Protocol
1. **One File at a Time:** Never create or edit more than ONE file in a single turn.
2. **Direct Action with Transparent Rationale:** Apply file edits directly in the turn while clearly explaining "the why" and the architectural rationale. Do not interrupt with unnecessary intermediate confirmation prompts ("Ready for me to edit?").
3. **Question Isolation:** If the user asks a question, answer the question ONLY. Do not write, modify, or run code in the same turn.
4. **No Speculative Tool Execution:** Do not run test runners, build tools, or terminal commands unless the user explicitly requested them in their prompt.

---

## 1. Project Overview & Resume Item
- **Title:** PodSeek — Podcast Transcript Chatbot & Corrective RAG Agent
- **Target Shows:** Andrew Huberman (Huberman Lab), Joe Rogan, Lex Fridman. (Phase 1 focus: Huberman Lab episodes, enforced at `/ingest` via `is_huberman_channel`).
- **Core Architecture:**
  - Ingestion (`✦ Absorb`): YouTube captions -> channel verification -> cleaned speaker `Segment`s -> sliding-window `Chunk`s (preserving start/end timestamp bounds).
  - Vector DB: ChromaDB collection storing chunks + scalar metadata for citation and filtering.
  - Orchestration (`Distill →`): Stateful LangGraph implementing Self-RAG / Corrective RAG (Retrieve -> Grade relevance -> Decision `≥1 relevant?` -> Decision `Retries < 2?` -> Fallback query rewrite OR Circuit-Breaker Abort / Grounded synthesis with inline timestamp citations).
  - API: FastAPI endpoint serving streaming/JSON answers.
  - UI: 3-column Bento Gradio Studio (`ui/app.py`, `ui/components.py`, `ui/styles/theme.css`) + `🤓 Stats for Nerds` observability view.
  - Deployment: Docker container, pinned reproducible environment, Hugging Face Space (`huggingface/app.py`).

---

## 2. Tech Stack & Environment
- **Python:** 3.13 (`.venv` in project root)
- **Chat Model:** `gemini-3.8-flash` (configured in `.env`)
- **Embedding Model:** `models/gemini-embedding-2` (dim=3072, configured in `.env`)
- **Vector DB:** `chromadb>=1.5`
- **Orchestration:** `langchain>=1.4`, `langgraph>=1.2`, `langchain-google-genai>=4.4`
- **Validation:** Pydantic v2
- **Testing:** pytest

---

## 3. Directory Layout
```
PodSeek/
├── AGENTS.md                  # LLM developer guide & invariants
├── CLAUDE.md                  # Claude Code project context & workflow guide (this file)
├── requirements.txt           # Major-version bounded dependencies
├── requirements-ui.txt        # Gradio & httpx dependencies for public UI
├── pyproject.toml             # Pytest, Ruff, and Pyright configuration
├── .env.example               # Secrets & model ID configuration template
├── data/
│   └── raw/                   # Git-ignored raw JSON transcripts by show
│       └── huberman_lab/
├── app/
│   ├── __init__.py
│   ├── factory.py             # Chat and embedding providers, collection name
│   ├── observability.py       # Optional LangSmith env gate
│   ├── evaluation.py          # Offline citation and keyword metrics
│   ├── schemas/               # Pydantic models (data & API)
│   │   ├── __init__.py
│   │   ├── transcripts.py     # Segment, Chunk, Show
│   │   └── api.py             # AskRequest, AskResponse, Citation
│   ├── ingestion/             # Transcript pipelines
│   │   ├── __init__.py
│   │   ├── chunking.py        # Pure sliding-window chunking
│   │   └── youtube.py         # YouTube adapter (oEmbed title/author, Huberman verifier)
│   ├── vectorstore.py         # ChromaDB wrapper & embeddings
│   ├── agent/                 # LangGraph Self-RAG / CRAG workflow
│   │   ├── __init__.py
│   │   ├── state.py           # AgentState TypedDict
│   │   ├── nodes.py           # retrieve, grade, rewrite, generate (with circuit-breaker refusal)
│   │   └── graph.py           # StateGraph & circuit-breaker
│   └── api/                   # FastAPI endpoints
│       ├── __init__.py        # FastAPI app mounting router
│       └── routes.py          # /health, /episodes, /ingest, /ask, /ask/stream
├── scripts/
│   ├── smoke_test_gemini.py   # Connectivity verification script
│   ├── list_models.py         # Inspect supported models for active API key
│   ├── fetch_episode.py       # CLI tool to download and cache episode transcript
│   ├── index_and_search.py    # Ingests cached episode into ChromaDB & searches
│   ├── ask_agent.py           # Interactive CLI runner for Corrective RAG agent
│   └── evaluate.py            # Offline or live eval of evals/questions.json
├── evals/
│   └── questions.json         # Fixed questions for episode QmOF0crdyRU
├── ui/                        # Gradio 3-Column Bento Studio UI (HTTP/SSE by default)
│   ├── __init__.py
│   ├── app.py                 # Gradio Blocks wiring, event handlers & JS hooks
│   ├── client.py              # RemoteClient (HTTP/SSE) & InProcessClient
│   ├── components.py          # Pure HTML renderers (inline pills, CRAG/Ingest flowcharts)
│   └── styles/
│       └── theme.css          # Light/Dark tokens, unified capsules, oval sliders, animations
├── huggingface/               # Space entrypoint (app file: huggingface/app.py)
│   ├── app.py
│   ├── requirements.txt
│   └── README.md
└── tests/
    ├── test_schemas.py        # Contract validation tests
    ├── test_youtube_adapter.py# Offline adapter tests
    ├── test_chunking.py       # Boundary & speaker chunk tests
    ├── test_agent.py          # Graph routing & circuit-breaker tests
    ├── test_api.py            # API health & validation tests
    ├── test_observability.py  # Tracing stays off without a key
    ├── test_evaluation.py     # Offline citation and keyword metrics
    └── test_ui_client.py      # SSE parser & pure UI component tests (no Gradio import)
```

---

## 4. Key Engineering Invariants
1. **Isolated I/O:** Network operations (e.g., `fetch_raw_captions`) must stay strictly isolated from pure business transformations (`captions_to_segments`, `chunk_segments`). All unit tests run offline.
2. **Scalar Metadata Only:** ChromaDB metadata accepts only `str`, `int`, `float`, and `bool`. Always use `chunk.to_metadata()`.
3. **No Hardcoded Models:** Models are loaded from environment variables (`CHAT_MODEL`, `EMBEDDING_MODEL`), never hardcoded in logic.
4. **Timestamps as Floats:** Store timestamps as numerical seconds (`start_seconds: float`) for filtering and YouTube deep links (`&t=X`), and format to `"HH:MM:SS"` strings only for human display.

---

## 5. Developer Quick Commands
```bash
# Activate environment
source .venv/bin/activate

# Run test suite & linter
python -m pytest -v
ruff check .

# Fetch & cache a test episode
python -m scripts.fetch_episode QmOF0crdyRU

# Start FastAPI backend
uvicorn app.api:app --reload --port 8000

# Start PodSeek Gradio UI (API already running)
pip install -r requirements-ui.txt
python -m ui.app

# Offline eval (no API key)
python -m scripts.evaluate
```
