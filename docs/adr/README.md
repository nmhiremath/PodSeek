# Architecture Decision Records (ADRs)

This directory documents the key architectural and design decisions made in PodSeek. In accordance with MADR (Markdown Architectural Decision Records), each record captures the context, decision, alternatives considered, consequences, and code-level evidence.

> Note: All records were recorded retroactively on 2026-11-10 to provide complete architectural provenance from initial commits through merged PR #2.

| Number | Title | Status | Originally Decided In | Key Files |
| :--- | :--- | :--- | :--- | :--- |
| [0001](0001-corrective-rag-over-plain-rag.md) | Corrective RAG over Plain RAG | Accepted | `a57c9ce` | `app/agent/nodes.py`, `app/agent/graph.py` |
| [0002](0002-langgraph-state-machine.md) | LangGraph State Machine over Free-Form Loop | Accepted | `a57c9ce` | `app/agent/graph.py`, `app/agent/state.py` |
| [0003](0003-deterministic-rewrite-ceiling-and-refusal.md) | Deterministic Rewrite Ceiling and Refusal Contract | Accepted | `a57c9ce`, `4d0697c` | `app/agent/graph.py`, `app/agent/nodes.py` |
| [0004](0004-embedded-chromadb-with-committed-index.md) | Embedded ChromaDB with Committed Index | Accepted | `c752704`, `826fa6e` | `app/vectorstore.py`, `chroma_db/` |
| [0005](0005-speaker-aware-sliding-window-chunking.md) | Speaker-Aware Sliding-Window Chunking | Accepted | `d6b1795` | `app/ingestion/chunking.py`, `app/schemas/` |
| [0006](0006-multi-tier-execution-modes-and-distance-fast-path.md) | Multi-Tier Execution Modes & Distance Fast-Path | Accepted | `9a36aea`, `d4c0068` | `app/agent/graph.py`, `app/agent/nodes.py` |
| [0007](0007-in-repo-provider-factory-vs-proxy-gateway.md) | In-Repo Provider Factory vs Proxy Gateway | Accepted | `56aaa0b` | `app/factory.py` |
| [0008](0008-sse-streaming-contract-with-token-deltas.md) | SSE Streaming Contract with Token Deltas | Accepted | `bfe747c`, `d4c0068` | `app/api/routes.py`, `ui/client.py` |
| [0009](0009-normalized-qa-cache.md) | Normalized QA Cache with Composite Keys | Accepted | `43ad054` | `app/api/routes.py`, `data/raw/qa_cache.json` |
| [0010](0010-inprocess-gradio-client-on-render-free-tier.md) | In-Process Gradio Client on Render Free Tier | Accepted | `986dfb1`, `826fa6e` | `render.yaml`, `ui/client.py`, `ui/app.py` |
| [0011](0011-strict-opt-in-langsmith-tracing.md) | Strict Opt-In LangSmith Tracing | Accepted | `d4c0068` | `app/observability.py`, `tests/` |
| [0012](0012-channel-gated-youtube-ingestion.md) | Channel-Gated YouTube Ingestion | Accepted | `4d0697c` | `app/ingestion/youtube.py`, `app/api/` |
| [0013](0013-offline-test-strategy-and-ci.md) | Offline Test Strategy and CI Verification | Accepted | `f4f7330`, `d4c0068` | `.github/workflows/ci.yml`, `tests/` |
| [0014](0014-askpodcast-to-podseek-rebrand.md) | AskPodcast to PodSeek Rebrand | Accepted | `4d0697c`, `d4c0068` | `ui/client.py`, `app/api/routes.py` |
