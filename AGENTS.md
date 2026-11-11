# PodSeek — Contributor & Agent Guide

PodSeek is an open-source podcast transcript search engine and Corrective RAG (CRAG) agent. This document defines the technical stack, directory layout, core engineering invariants, developer commands, and change workflow for AI agents and human contributors.

---

## 1. Tech Stack
- **Python:** 3.13 (`.venv` in project root)
- **Chat Model:** `gemini-3.8-flash` (configurable via `.env`)
- **Embedding Model:** `models/gemini-embedding-2` (dim=3072, configurable via `.env`)
- **Vector DB:** Embedded `chromadb>=1.5` (persisted in `chroma_db/`)
- **Orchestration:** `langchain>=1.4`, `langgraph>=1.2`, `langchain-google-genai>=4.4`
- **API & UI:** `fastapi>=0.142,<1`, `uvicorn`, `gradio>=5,<6`, `httpx>=0.28`
- **Validation & Tooling:** Pydantic v2, Ruff, Pyright, pytest

---

## 2. Directory Layout
```
PodSeek/
├── AGENTS.md                  # Contributor & agent engineering guide (this file)
├── CLAUDE.md                  # Pointer to AGENTS.md
├── requirements.txt           # Core backend dependencies
├── requirements-ui.txt        # Gradio Studio UI dependencies
├── pyproject.toml             # Pytest, Ruff, and Pyright configuration
├── render.yaml                # Render.com free-tier deployment blueprint
├── .env.example               # Environment variable template
├── data/raw/                  # Cached transcript JSON files & QA cache
├── chroma_db/                 # Committed ChromaDB SQLite index (72 MB, 2,052 vectors)
├── app/
│   ├── factory.py             # LLM/embedding provider factory with LRU caching
│   ├── vectorstore.py         # ChromaDB wrapper & vector collections
│   ├── observability.py       # Opt-in LangSmith tracing configuration
│   ├── evaluation.py          # Deterministic citation and keyword metrics
│   ├── schemas/               # Pydantic schemas (transcripts, API, citations)
│   ├── ingestion/             # YouTube captions adapter & sliding-window chunker
│   ├── agent/                 # LangGraph Corrective RAG state graph & nodes
│   └── api/                   # FastAPI application & route endpoints
├── ui/                        # Gradio 3-column Bento Studio interface
├── scripts/                   # CLI ingestion, query, and benchmark scripts
├── evals/                     # Benchmark questions (evals/questions.json)
├── openspec/                  # OpenSpec baseline capability specifications & changes
└── tests/                     # Offline pytest test suite (41 tests)
```

---

## 3. Engineering Rules & Invariants
1. **Isolated I/O & Offline Tests:** Network I/O (YouTube fetching, oEmbed, external APIs) must remain isolated from pure business logic (chunking, scoring, formatting). All 41 unit tests run offline without network access or API keys.
2. **Scalar Metadata Only:** ChromaDB accepts only scalar metadata (`str`, `int`, `float`, `bool`). Always use `Chunk.to_metadata()`.
3. **No Hardcoded Models or Secrets:** Models and API keys are loaded exclusively from environment variables (`CHAT_MODEL`, `EMBEDDING_MODEL`), never hardcoded in application logic.
4. **Strong Typing & Error Handling:** Use strict type hints (`AgentState`, Pydantic models). Never catch bare exceptions (`except:`); catch specific exceptions with clean error surfaces.
5. **Conventional Commits & Protected Main:** Direct pushes to `main` are disabled. All work happens on dedicated branches and merges via Pull Requests following Conventional Commits (`feat:`, `fix:`, `docs:`, `chore:`).

---

## 4. Developer Commands
```bash
# Activate environment
source .venv/bin/activate

# Run API backend (port 8000)
uvicorn app.api:app --reload --port 8000

# Run Gradio Studio UI (in-process mode)
python -m ui.app

# Linting & Type Checking
ruff check .
pyright

# Run full offline unit test suite (41 tests)
pytest -v

# Run offline benchmark evaluation
python -m scripts.evaluate

# Run live benchmark evaluation across modes (requires running API at --api-url, default http://localhost:8000)
python -m scripts.evaluate --live --mode turbo
python -m scripts.evaluate --live --mode balanced
python -m scripts.evaluate --live --mode rigorous
```

---

## 5. OpenSpec Specification-Driven Workflow
Before implementing non-trivial features, architectural changes, or capability alterations:
1. **Propose:** Create an OpenSpec change proposal in `openspec/changes/<change-name>/` containing `proposal.md`, `tasks.md`, and spec deltas in `specs/<capability>/spec.md` (`ADDED`, `MODIFIED`, or `REMOVED` requirements).
2. **Validate:** Run `npx @fission-ai/openspec validate --all --strict --no-interactive`.
3. **Branch & Implement:** Work on a dedicated feature branch. Ensure linter (`ruff check .`) and offline tests (`pytest`) pass.
4. **Archive:** Upon PR merge into `main`, archive the proposal into `openspec/changes/archive/` using `npx @fission-ai/openspec archive <change-name>` and update baseline capability specs under `openspec/specs/`.
