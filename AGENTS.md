# PodSeek — Agent & Developer Context

This document is the single source of truth for AI assistants and engineers working on this repository.

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
├── AGENTS.md                  # LLM developer guide & invariants (this file)
├── CLAUDE.md                  # Claude Code project context & workflow guide
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

---

## Plan – 2026-11-02 – Public UI + Tracing + Evals

The one-file-per-turn rule in section 0 is overridden for this effort. The user asked for one coordinated, optional feature set and for this section to stay current as the work lands.

### Goals
Make the existing CRAG service publicly usable without rewriting `app/agent/`, the chunker, ingestion, the vector store, or the provider factory.
- Gradio UI that only calls FastAPI (default) or the existing handlers (in-process).
- LangSmith tracing off unless `LANGCHAIN_TRACING_V2` and `LANGCHAIN_API_KEY` are both set.
- Offline-friendly evals: citation timestamp shape and keyword overlap. Optional LLM judge. No Ragas.
- Hugging Face Space entry that does not shadow the `app/` package.
- Docker Compose for the API stays unchanged.

### Files to create
- `app/observability.py` — `configure_tracing()`, `trace_config()`.
- `app/evaluation.py` — timestamp and keyword metrics, offline fixtures.
- `evals/questions.json` — four fixed questions for episode `QmOF0crdyRU`.
- `scripts/evaluate.py` — offline by default; `--live` and `--llm-judge`.
- `tests/test_observability.py`, `tests/test_evaluation.py`, `tests/test_ui_client.py`.
- `ui/client.py`, `ui/app.py`, `ui/__init__.py`.
- `requirements-ui.txt` — Gradio and httpx only.
- `huggingface/app.py`, `huggingface/requirements.txt`, `huggingface/README.md`.

### Files to modify
- `app/api/__init__.py` — call `configure_tracing()` after the router import (dotenv already loaded).
- `app/api/routes.py` — pass trace config into the existing invoke/stream/summary calls. Share one event iterator so the UI does not copy node logic.
- `scripts/ask_agent.py` — same trace gate for the CLI.
- `.env.example` — LangSmith and UI variables, tracing off.
- `README.md` — UI, tracing, eval, Live Demo placeholder, API examples aligned with the real schemas.

### Rationale
The graph, chunker, and Chroma collection naming already work. A thin client and env-gated hooks demonstrate a public UI, tracing, and evals without a second copy of the agent.

### Acceptance criteria
- `python -m pytest -v` passes offline.
- Importing the API with tracing unset forces `LANGCHAIN_TRACING_V2=false`.
- `python ui/app.py` is a Gradio client of the existing API.
- `python -m scripts.evaluate` exits 0 with no API key.
- This section records the plan and, after the work, a change log.

### Change log
- Added optional LangSmith gating in `app/observability.py`. The API calls it on import. Graph nodes were not rewritten. `routes.py` passes `trace_config` into the existing invoke, stream, and summary calls, and `iter_agent_events` is the single SSE payload builder.
- Added `app/evaluation.py`, `evals/questions.json`, and `scripts/evaluate.py`. Default mode is offline fixtures. `--live` hits `POST /ask`. `--llm-judge` is live-only and does not use Ragas.
- Added `ui/client.py` (remote or in-process) and `ui/app.py` (ingest, chat, citation links, agent steps). `requirements-ui.txt` keeps Gradio out of the API image. Docker Compose was not changed.
- Added `huggingface/app.py` as the Space entry so a root `app.py` does not shadow the `app/` package. Demo fallback defaults on only in that entrypoint.
- Documented the UI, tracing, eval, and the Space placeholder in `README.md`. Corrected the API examples to the real fields (`question`, `video_url_or_id`, `rewrites_attempted`, citation shape).
- Open: publish the Space and replace the placeholder URL and `docs/demo.gif`. No show filter, multi-turn memory, or token-level SSE.
- Verified on 2026-11-02: `python -m pytest -q` passed 27 tests. `python -m scripts.evaluate` exited 0 without an API key. `build_demo()` imports and returns a Gradio `Blocks` app. The server was not left running.

---

## Plan – 2026-11-03 – Public UI + Tracing + Evals

### Context & Audit of Existing Baseline
An initial pass on `2026-11-02` created the foundational files for the four requested additions (`ui/`, `app/observability.py`, `app/evaluation.py`, `evals/questions.json`, `scripts/evaluate.py`, `huggingface/`, and unit tests). Before shipping, this `2026-11-03` plan audits every file in that baseline and defines the targeted hardening, UX enhancements, static type-safety (`pyright`), lint compliance (`ruff`), and test coverage required to meet production standards without touching `app/agent/`, `app/ingestion/`, `app/vectorstore.py`, or `app/factory.py`.

### Goals
1. **Interactive Public UI (`ui/`):**
   - Preserve the thin-client architecture (`RemoteClient` over HTTP/SSE by default; `InProcessClient` calling FastAPI handlers/event generators directly when `ASKPODCAST_UI_MODE=inprocess`).
   - Enhance `ui/client.py` and `ui/app.py` with an indexed Episode Library viewer (`GET /episodes`) and clickable preset example questions (`gr.Examples`) so visitors can test the UI with a single click.
   - Ensure `ui/app.py` passes `pyright` even when optional UI dependencies (`requirements-ui.txt`) are installed separately from the core API environment.
2. **Observability (`app/observability.py`, `app/api/routes.py`, `scripts/ask_agent.py`):**
   - Keep LangSmith tracing strictly opt-in (`LANGCHAIN_TRACING_V2=true` + non-empty `LANGCHAIN_API_KEY`).
   - Tighten return/input types (`RunnableConfig` in `app/observability.py` and `AgentState` in `app/api/routes.py` and `scripts/ask_agent.py`) so `pyright` and `ruff` pass with zero warnings.
3. **Evaluation Setup (`app/evaluation.py`, `evals/questions.json`, `scripts/evaluate.py`):**
   - Preserve offline-by-default evaluation (`python -m scripts.evaluate`) scoring keyword overlap and citation timestamp/deep-link validity (`HH:MM:SS` and `&t=<int>`), plus optional `--live` and `--llm-judge` flags.
   - Fix strict type narrowing in `app/evaluation.py` and `scripts/evaluate.py` and expand offline test coverage in `tests/test_evaluation.py`.
4. **Hugging Face Space Readiness (`huggingface/` & `README.md`):**
   - Keep `huggingface/app.py` in a dedicated subdirectory (preventing module shadowing of the `app/` package) with `ASKPODCAST_DEMO_FALLBACK=true` for zero-config Spaces demos.
   - Sync the `README.md` Project Structure tree so all new files (`app/factory.py`, `app/observability.py`, `app/evaluation.py`, `evals/`, `ui/`, `huggingface/`, `requirements-ui.txt`) are documented alongside the Live Demo section.

### Files Created (Baseline Inventory) & Files to Modify (2026-11-03 Hardening)
- **Existing Baseline Files (Verified & Retained):**
  - `requirements-ui.txt` — Isolates `gradio>=5,<6` and `httpx>=0.28` from the core API container.
  - `ui/__init__.py` — Package marker for the UI module.
  - `evals/questions.json` — Four ground-truth benchmark questions for episode `QmOF0crdyRU`.
  - `huggingface/app.py`, `huggingface/requirements.txt`, `huggingface/README.md` — Hugging Face Space entrypoint and metadata.
  - `app/api/__init__.py` — Calls `configure_tracing()` after `.env` initialization.
  - `.env.example` — Documents `LANGCHAIN_TRACING_V2`, `LANGCHAIN_API_KEY`, `LANGCHAIN_PROJECT`, `ASKPODCAST_API_URL`, `ASKPODCAST_UI_MODE`, and `ASKPODCAST_DEMO_FALLBACK`.
  - `tests/test_observability.py` — Verifies tracing defaults to `false` without credentials and enables cleanly when both env vars are set.
- **Files to Modify in This Pass:**
  1. `app/observability.py` — Return `RunnableConfig` from `trace_config(path: str)` for LangChain/LangGraph type compatibility.
  2. `app/api/routes.py` — Type `_initial_state(question: str) -> AgentState` and clean up exception string formatting for `ruff` / `pyright` compliance.
  3. `scripts/ask_agent.py` — Annotate `initial_state: AgentState` so `corrective_rag_agent.stream(initial_state, config=trace_config("cli"))` passes strict `pyright` checks.
  4. `app/evaluation.py` — Guard `citation.get("start_seconds")` against `None` before converting to `float` to satisfy `pyright`.
  5. `scripts/evaluate.py` — Narrow structured-output return type in `llm_relevance()` using `getattr(result, "score", 1)` for `pyright` safety.
  6. `ui/client.py` — Add `episodes()` method on `RemoteClient` (`GET /episodes`) and `InProcessClient` (`list_episodes()`).
  7. `ui/app.py` — Add `gr.Examples` for one-click question testing, display indexed episodes in the Ingest tab, and ensure clean `pyright` handling for optional `gradio` import.
  8. `tests/test_ui_client.py` — Expand unit tests to cover `make_client()` mode selection, `InProcessClient.health()`, `format_citations()`, and `format_event()` without requiring a running server.
  9. `tests/test_evaluation.py` — Add offline tests for `scripts.evaluate.main([])` exit code `0` and mocked `llm_relevance()`.
  10. `README.md` — Update the `## 📂 Project Structure` tree to reflect all new UI, observability, evaluation, and Hugging Face Space files.

### Rationale
- **Thin UI Client (`ui/client.py`):** Routing the UI through `RemoteClient` (HTTP/SSE) or `InProcessClient` (shared `iter_agent_events` generator in `app/api/routes.py`) guarantees zero duplication of LangGraph node logic, grading prompts, or citation formatting.
- **Strict Opt-In Tracing (`app/observability.py`):** Explicitly setting `os.environ["LANGCHAIN_TRACING_V2"] = "false"` unless both `LANGCHAIN_TRACING_V2=true` and `LANGCHAIN_API_KEY` are present prevents accidental background telemetry or noisy errors during offline `pytest` runs.
- **Lightweight Offline-First Evals (`app/evaluation.py`):** Deterministic checks on timestamp formatting (`HH:MM:SS`), YouTube deep-link query parameters (`t=<seconds>`), and expected domain keywords run in milliseconds in CI without an API key, while `--live --llm-judge` uses the existing `get_chat_model()` factory rather than pulling heavy `ragas` dependencies.
- **Subdirectory HF Space (`huggingface/app.py`):** Placing the Space entrypoint in `huggingface/app.py` avoids creating a root `app.py` that would shadow Python imports from the `app/` package.

### Acceptance Criteria
- `python -m pytest -v` passes all unit tests completely offline.
- `pyright` and `ruff check .` pass with zero errors across the entire repository.
- `python -m scripts.evaluate` exits `0` offline without an API key.
- Importing `app.api` with tracing unset forces `LANGCHAIN_TRACING_V2=false`.
- `AGENTS.md` and `README.md` are fully synchronized with a final change log.

### Change log
- Hardened static typing across `app/observability.py` (`RunnableConfig`), `app/api/routes.py` (`AgentState`), `scripts/ask_agent.py` (`AgentState`), `app/evaluation.py` (`None`-safe `start_seconds` parsing), `scripts/evaluate.py` (`getattr` fallback on structured output), and `tests/test_observability.py` so `pyright` and `ruff check .` pass with zero errors or warnings.
- Enhanced `ui/client.py` with `episodes()` on `AskPodcastClient`, `RemoteClient`, and `InProcessClient`, and updated `ui/app.py` with preset `gr.Examples` for episode `QmOF0crdyRU` and an Indexed Episodes view on the Ingest tab while preserving the Server Free-Tier Key + automatic Offline Demo Fallback setup.
- Expanded offline unit tests in `tests/test_ui_client.py` (mode selection + in-process health check + `[DONE]` SSE handling) and `tests/test_evaluation.py` (`scripts.evaluate.main([]) == 0`).
- Updated `README.md` project structure tree to document all new UI, observability, evaluation, and Hugging Face Space modules.
- Verified on 2026-11-03: `.venv/bin/python -m pytest -v` passed 29/29 offline tests, `.venv/bin/pyright` reported 0 errors, `.venv/bin/ruff check .` passed all checks, and `.venv/bin/python -m scripts.evaluate` exited 0 offline.

---

## Plan – 2026-11-04 – PodSeek UI Overhaul, Inline Citations & Flowchart Hardening

### Goals
1. **Product Rebranding to PodSeek (`✦ Absorb` & `Distill →`):**
   - Rebrand `AskPodcast` to **PodSeek** across FastAPI (`app/api/`), Gradio Studio (`ui/`), Hugging Face Space (`huggingface/`), `.env.example` (`PODSEEK_*` with backward-compatible `ASKPODCAST_*` fallbacks), and `README.md`.
2. **3-Column Bento Studio UI & Single-Click Oval Toggle Sliders (`ui/styles/theme.css`, `ui/components.py`, `ui/app.py`):**
   - Left column (`scale=3`): Unified Command Capsule (`.ap-ingest-capsule`) with `✦ Absorb` pill centered inside the input box, live animated status banner, and scrollable Indexed Episodes list showing clean episode titles.
   - Center column (`scale=5`): Ephemeral Session Chat (`#ap-chat-scroll`), collapsible sample question pills (auto-hidden after the first question is asked and restored on `Clear`), and multiline `Distill →` capsule (`.ap-distill-capsule`, `Enter` to submit, `Shift+Enter` for newline).
   - Right column (`scale=4`): Coordinate-locked SVG Workflow Flowchart + color-coded `.modern-scroll` SSE Event Stream (`#ap-sse-scroll`).
   - Header controls: Right-aligned single-click oval toggle sliders (`button#ap-view-slider` for `💬 Studio <-> 🤓 Stats for Nerds` and `button#ap-theme-slider` for Light/Dark mode) backed by `:root` and `.ap-dark` CSS custom properties so you can toggle in-place without moving the mouse.
3. **Google AI Overview Inline Stadium Citations (`ui/components.py`, `ui/styles/theme.css`):**
   - Convert inline `[HH:MM:SS]` and `[Episode Title @ HH:MM:SS]` references into compact `a.gai-pill` stadium links with a circular red YouTube play icon (`<Episode Short Title> · <Timestamp>`), stripping backticks and surrounding `()`, `,`, and `];`.
4. **Standard ISO Flowchart with Ingestion Swap & Circuit-Breaker Abort (`ui/components.py`, `ui/app.py`, `app/agent/nodes.py`):**
   - Temporarily swap the workflow panel to **Workflow · Episode Ingestion** (`1. Verify Channel -> 2. Fetch Captions -> 3. Window Chunker -> 4. Embed & Analyze`) during `✦ Absorb` and auto-restore **Workflow · Corrective RAG** on completion.
   - Use standard flowchart shapes in **Workflow · Corrective RAG**: rounded rectangles for process nodes (`🔍 Retrieve`, `⚖️ Grade`, `✍️ Rewrite`, `✨ Generate`), dual SVG Decision Diamonds (`≥1 relevant?` and `Retries < 2?`), and a `🛑 Abort` circuit-breaker terminator node (`Max retries (2/2)`) when `rewrites >= 2` with `0` relevant chunks.
5. **Channel Guardrail & Clean Error Surface (`app/ingestion/youtube.py`, `app/api/routes.py`, `ui/client.py`):**
   - Verify YouTube oEmbed `author_name` via `is_huberman_channel()` so non-Huberman links are rejected with a clean HTTP 400 message, parsed by `_raise_clean_api_error()` without raw `httpx` Mozilla URLs.

### Change log
- Created `ui/styles/theme.css` and `ui/components.py`, and refactored `ui/app.py` and `ui/client.py` to deliver the 3-column PodSeek Bento Studio, single-click oval toggle sliders, unified command capsules, Google AI Overview inline citation pills, temporary Episode Ingestion workflow graph, and dual-diamond Corrective RAG flowchart with `🛑 Abort` circuit breaker.
- Updated `app/ingestion/youtube.py` and `app/api/routes.py` with `fetch_video_metadata()` and `is_huberman_channel()` verification, and fixed `app/agent/nodes.py` (`generate`) to immediately return the circuit-breaker refusal when `relevant_documents` is empty after max rewrites.
- Synchronized `AGENTS.md`, `CLAUDE.md`, and `README.md`, and expanded `tests/test_ui_client.py` and `tests/test_api.py`.
- Verified on 2026-11-04: `.venv/bin/ruff check .` passed with 0 errors and `.venv/bin/python -m pytest -v` passed 31/31 offline tests.

---

## 6. Performance, Latency & Cost Optimization Log (2026-11-04)

### Benchmark Observations: Free-Tier vs. Paid Tier Latency
- **Paid Tier (Pay-As-You-Go API Key):** Low latency (~1.2s–2.5s for the entire CRAG cycle). Dedicated bandwidth and prioritized queueing on Google AI Studio.
- **Free Tier (Strict Quota API Key):** Significantly higher latency (3.5s–6.5s) caused by server-side queue prioritization, strict 15 RPM / 1M TPM limits, and rate-limiting throttles.

### Implemented Optimizations (Shipped)
1. **Step 0 Ingest Cache Fast-Path (`app/api/routes.py`):**
   - Bypasses raw caption download, segment cleaning, sliding-window chunking, embedding generation (`index_chunks`), and LLM summary generation when the video is already indexed in ChromaDB.
   - Saves 100% of embedding and LLM calls on repeat ingest submissions.
2. **Single-Call Batch Chunk Grading (`app/agent/nodes.py`):**
   - Replaced 4 sequential LLM grading calls (`k=4`) with 1 batch call (`BatchGradeResult`), cutting node latency by ~70% and saving 3 LLM calls per question.
3. **Persistent QA Cache (`app/api/routes.py` & `data/raw/qa_cache.json`):**
   - Normalized question lookup (`<collection>::<ep_ids>::<clean_q>`) serving repeated questions in `<1ms` with 0 embedding and 0 LLM calls.
4. **Client Pooling (`app/factory.py`):**
   - `@lru_cache(maxsize=16)` on `_build_chat_model` and `_build_embedding_model` eliminates repeated HTTP client teardown/reconnect overhead.
5. **Visual Flowchart Cache Indicators (`ui/components.py` & `ui/app.py`):**
   - Added `⚡ DB Cache` node in Ingestion workflow and `⚡ QA Cache` node in CRAG workflow with `⚡ Cache Hit` status pill when served from cache.

### Latency Roadmap (Shipped Milestones)
1. **ChromaDB Distance Threshold Fast-Path (Shipped):**
   - If top retrieved chunks have cosine distance < 0.35 in Balanced mode, bypasses LLM grading and routes directly to `generate`.
2. **Tri-Mode Execution Strategies (Shipped):**
   - Implemented `⚡ Turbo` (0-retry fused retrieval and synthesis), `⚖️ Balanced` (threshold fast-path + 1 retry), and `🎯 Rigorous` (full CRAG + 2 retries).
3. **5-Tier Flowchart Architecture (Shipped):**
   - Expanded workflow canvas to 440px with non-overlapping corridors, retry loopbacks, and circuit-breaker abort nodes.
4. **Refusal Citation Guardrail (Shipped):**
   - Zeroes `relevant_documents` when the LLM refuses an out-of-domain query, preventing misleading citation pill links.
5. **Render.com Cloud Deploy Readiness (Shipped):**
   - Dynamic `$PORT` and `0.0.0.0` binding in `ui/app.py` for free cloud deployment.
6. **Pre-Seeded Library & Datacenter IP Block Guardrail (Shipped):**
   - Un-ignored `data/raw/huberman_lab/` to commit 10 pre-downloaded episodes and persistent `qa_cache.json` directly into Git so cloud hosts (Render/Hugging Face) run without hitting YouTube IP blocks. Added clean HTTP 429 response handling in `app/api/routes.py`.
7. **Viewport-Responsive Layout & Episode Separation (Shipped):**
   - Dynamically clamped chat empty state (`clamp(100px, calc(100vh - 580px), 240px)`), active chat thread, and SSE log height to guarantee all columns fit in `100vh` on laptop displays without window scroll. Added `margin-bottom: 8px` and rounded corners to indexed episode tiles. Removed stats slider from header.
