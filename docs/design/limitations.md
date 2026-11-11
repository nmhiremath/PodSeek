# Known Limitations & Scale Roadmap

This document consolidates PodSeek's acknowledged design boundaries, operational constraints, and the architectural components required to scale the system to enterprise workloads.

---

## Current Known Limitations

### 1. Corpus Scale & Hosting Boundaries
- **50-Episode Ceiling on Free Tier:** The vector database is committed to Git (~45 MB) and loaded into RAM. Expanding the index beyond ~200 episodes (~150,000 chunks) will exceed Render's 512 MB container memory limit, triggering OOM kills.
- **Single-Replica Deployment:** Embedded ChromaDB SQLite backends and the local `data/raw/qa_cache.json` disk file cannot be safely mounted or concurrently modified by multiple load-balanced web server replicas.
- **Free-Tier Cold Starts:** Because PodSeek is hosted on Render's free tier, the container spins down after 15 minutes of inactivity. The initial wake-up request takes 30–50 seconds before the service begins responding.

### 2. Conversational Capabilities
- **Single-Turn Stateless Queries:** The LangGraph state machine operates on an ephemeral, single-turn state (`AgentState["question"]`). Follow-up queries (e.g. "What did he say about that?") require the user to repeat the full context.
- **Strict Domain Gating:** PodSeek's ingestion is gated exclusively to Huberman Lab in Phase 1 (`is_huberman_channel`). Submitting videos from other creators is rejected by design.

### 3. Retrieval & Ingestion Limitations
- **Pure Semantic Search without Sparse Inverted Index:** PodSeek relies on dense vector search with exact phrase regex hoisting. It lacks a sparse BM25 / SPLADE lexical index, which can cause misses on rare chemical or anatomical terminology if semantic embedding similarity is weak.
- **Synchronous Ingestion:** `POST /ingest` runs synchronously inside the API worker. Ingesting a 3-hour episode takes 15–30 seconds, blocking other operations on single-worker deployments.
- **Public Cloud YouTube IP Throttles:** Fetching transcripts for dozens of new videos in quick succession can trigger YouTube bot detection, requiring manual export of browser session cookies to `cookies.txt`.

### 4. Cache & Evaluation Gaps
- **Syntactic QA Cache Misses:** The QA cache uses normalized string equality. Semantic duplicates phrased with different vocabulary miss the cache and incur full inference latency.
- **Small Benchmark Suite:** The evaluation benchmark contains 16 curated questions. While effective for continuous integration smoke testing, it is not a statistically exhaustive evaluation of the entire corpus.

---

## What We Would Add at Scale (Roadmap)

If scaling PodSeek to a multi-podcast enterprise platform with millions of users and hundreds of thousands of episodes, we would implement:

### 1. Storage & Ingestion Tier
- **Managed Distributed Vector Store:** Migrate from embedded ChromaDB to Qdrant Cloud or Pinecone with HNSW indexing, horizontal sharding, and namespace partitioning by show.
- **Hybrid Search with Reciprocal Rank Fusion (RRF):** Combine Qdrant dense vector search with OpenSearch BM25 sparse search and Cohere Re-Rank cross-encoders.
- **Asynchronous Task Queue:** Move ingestion to an asynchronous worker tier (Celery / Redis Queue or Temporal.io) with webhook notifications on completion.
- **Automated YouTube Proxy Pool:** Integrate rotating residential proxy networks for resilient caption extraction without manual cookie handling.

### 2. Agent & Orchestration Tier
- **Multi-Turn Conversational Checkpointing:** Introduce persistent LangGraph checkpointing backed by PostgreSQL or Redis to retain conversation history across turns.
- **Multi-Agent Show Routing:** Deploy a supervisor agent that routes queries to specialized show-specific sub-agents (Huberman Lab, Joe Rogan, Lex Fridman).
- **Automated LLM Gateway:** Route model calls through LiteLLM Proxy or Portkey with automated cross-provider failover during rate-limit spikes (HTTP 429).

### 3. Observability, Security & Caching
- **Semantic Vector Cache:** Implement GPTCache or Redis Semantic Cache to serve semantic duplicates from cache in $< 20\text{ ms}$.
- **Comprehensive APM:** Stream OpenTelemetry traces and Prometheus metrics to Datadog or Grafana Loki.
- **Input/Output Guardrail Models:** Deploy Llama Guard or NeMo Guardrails to scan for prompt injections and enforce strict content safety before generation.
- **User Authentication & RBAC:** Add OAuth2 / JWT authentication with per-user rate limits and subscription tiers.
