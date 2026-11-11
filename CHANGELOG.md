# Changelog

All notable changes to PodSeek will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

> Note: Reconstructed from git history on 2026-11-10.

---

## [Unreleased]

### Added
- **OpenSpec Baseline:** Adopted OpenSpec specification-driven development across 9 baseline capabilities in `openspec/specs/` (`retrieval`, `corrective-loop`, `answer-generation`, `inference-providers`, `streaming-api`, `ingestion`, `studio-ui`, `evaluation`, `observability`) with strict validation.
- **Architectural Decision Records (ADRs):** Authored 14 retroactive MADR-style architectural decision records (`docs/adr/`) documenting technical decisions from project inception through PR #2.
- **Agentic System Design Documentation:** Authored 12 design pillar documents (`docs/design/`), an enterprise tooling comparison matrix (`enterprise-mapping.md`), and a scale limitations roadmap (`limitations.md`).
- **Architecture Diagrams:** Authored D2 architecture source (`docs/diagrams/architecture.d2`), light/dark rendered SVGs, and hand-authored SMIL animated Corrective RAG loop diagrams (`docs/assets/crag-loop-dark.svg` and `docs/assets/crag-loop-light.svg`).

---

## [0.4.0] - 2026-11-10

### Added
- **16-Question Benchmark Suite:** Expanded `evals/questions.json` from 4 to 16 questions (13 in-scope topics, 3 out-of-scope refusals), adding latency p50/p95, citation validity, and keyword hit rate metrics across Turbo, Balanced, and Rigorous modes in `scripts/evaluate.py` (`aa1b2b4`, merged in `d4c0068`).
- **Automated CI Workflow:** GitHub Actions workflow (`.github/workflows/ci.yml`) running Python 3.13 Ruff linter and offline Pytest suite on push and PR to `main` (`1ad5ae6`, merged in `d4c0068`).
- **Open Graph & Twitter Previews:** Added meta tags and social card preview headers for `https://podseek.onrender.com/` (`cedca74`, merged in `d4c0068`).
- **Browser Favicon:** SVG brand badge favicon added to Gradio Studio (`a61e932`, merged in `d4c0068`).

### Changed
- **AskPodcast to PodSeek Completion:** Completed project rename across Docker Compose, package docstrings, LangSmith tags, eval help text, and test fixtures with full backward compatibility (`ecfda39`, merged in `d4c0068`).
- **Live Demo Link:** Swapped Hugging Face Space placeholder with live Render web service `https://podseek.onrender.com/` in `README.md` (`c4c7d6c`).
- **SSE Stream Documentation:** Aligned README documentation with actual API implementation: unnamed `data: <json>` frames containing node updates and token deltas, without `event:` lines or `[DONE]` sentinels (`a5ce284`, merged in `d4c0068`).

### Fixed
- **Mobile & Accessibility UI:** Disabled Distill button for queries under 3 characters, ensured smooth scrolling to latest answers, prevented viewport zooming restrictions, fixed header clipping on mobile, added horizontal scroll to flowchart on small screens, and forced mobile library drawer closed on initial load (`a554e82`, `6c0b83f`, `c736ee6`, `be129bc`, `a3e2ffe`, `2df905b`, `f082295`, `c6c175a`, merged in `d4c0068`).
- **Composer Positioning:** Pinned ask capsule and presets to viewport and fixed page-load dimming (`0008a21`).

---

## [0.3.0] - 2026-11-08

### Added
- **50-Episode Knowledge Library:** Expanded indexed Huberman Lab transcripts from 10 to 50 episodes with committed ChromaDB vectors and JSON metadata (`622c240`).
- **Batch Ingestion Script:** Created `scripts/ingest_top_episodes.py` for automated bulk YouTube transcript processing (`622c240`).
- **End-to-End Token Streaming:** Implemented real-time token-level streaming using LangGraph stream writer from agent through FastAPI SSE (`/ask/stream`) to Gradio UI (`bfe747c`).
- **Flowchart Spotlight:** Added dynamic CSS focus transitions spotlighting active workflow nodes in the desktop SVG diagram (`e79df3d`, `622c240`).

---

## [0.2.0] - 2026-11-04

### Added
- **Bento Studio UI:** 3-column responsive Gradio 5 interface featuring unified command capsules, Google AI Overview-style inline citation stadium chips, and single-click oval sliders for theme and mode toggling (`4d0697c`, `9a36aea`).
- **Execution Modes & Distance Fast-Path:** Introduced Turbo (no grading), Balanced (distance < 0.35 fast-path), and Rigorous modes with mode-specific retry limits (`9a36aea`).
- **Channel Verification Guardrail:** Added YouTube oEmbed channel author validation (`is_huberman_channel`) to protect `/ingest` against non-Huberman videos (`4d0697c`).
- **Circuit-Breaker Flowchart:** Coordinate-locked SVG diagrams for both Episode Ingestion and Corrective RAG with visual circuit-breaker abort nodes (`4d0697c`).
- **Render Deployment Blueprint:** Automated cloud deployment configuration via `render.yaml` with in-process UI client support (`986dfb1`, `826fa6e`).
- **Persistent QA Cache:** Composite-keyed disk cache (`data/raw/qa_cache.json`) for immediate responses on benchmark and preset questions (`9a36aea`).

---

## [0.1.1] - 2026-10-08

### Added
- **Multi-Provider LLM & Embedding Factory:** Pluggable provider abstraction supporting Google GenAI, OpenAI, Anthropic, xAI (Grok), and Ollama with dynamic dimension-safe ChromaDB collection naming (`56aaa0b`).
- **Containerization:** Production Dockerfile and `docker-compose.yml` for containerized FastAPI deployment (`56aaa0b`).
- **Episode Library & Multi-Tier Summarization:** `POST /ingest` multi-tier summary generation and `GET /episodes` manifest endpoint (`3574708`).

---

## [0.1.0] - 2026-10-06

### Added
- **Initial Corrective RAG Workflow:** LangGraph state machine with `retrieve`, `grade_documents`, `rewrite_query`, and `generate` nodes, featuring `MAX_REWRITES = 2` circuit breaker (`a57c9ce`).
- **Vector Store & Ingestion:** Local ChromaDB wrapper with Gemini embeddings and speaker-aware sliding-window chunking (`c752704`, `d6b1795`).
- **FastAPI Endpoints:** Initial REST endpoints for `/health`, `/ask`, and citation formatting (`d335fb6`).
- **Developer Guidelines:** Established project conventions and engineering invariants in `AGENTS.md` (`64d0839`).
