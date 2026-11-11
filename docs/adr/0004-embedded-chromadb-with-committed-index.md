# 4. Embedded ChromaDB with Committed Index

> Recorded retroactively on 2026-11-10; decision originally made in commit `c752704` and expanded in commits `826fa6e` and `622c240`.

## Status
Accepted

## Context
Deploying PodSeek as a public demonstration on Render.com free tier imposes severe constraints: 512 MB maximum container RAM, ephemeral filesystem on restart, spin-down after 15 minutes of idle, and zero budget for managed external cloud vector databases (e.g. Pinecone, Qdrant Cloud, Weaviate). When the container boots, downloading or embedding 50 multi-hour podcast transcripts at runtime would exceed startup timeouts and deplete API rate limits.

## Decision
Use embedded ChromaDB (`chromadb`) running locally within the application directory (`chroma_db/`). Commit the pre-indexed vector database files directly to the git repository alongside cached raw transcript JSON files in `data/raw/huberman_lab/`.

## Alternatives Considered
1. **External Managed Vector DB (Pinecone, Qdrant Cloud):** Connect over network API. Rejected to avoid hosting costs, API key management for public users, and network latency on every query.
2. **Runtime Indexing on Cold Boot:** Ingest and embed transcripts on startup. Rejected because embedding 50 full episodes requires numerous external API calls and delays container availability.
3. **SQLite with sqlite-vss:** Rejected in favor of ChromaDB which integrates natively with LangChain (`langchain-chroma`) and provides out-of-the-box persistent cosine distance scoring.

## Consequences
### Good
- Zero infrastructure cost: runs entirely within the free-tier container without external database dependencies.
- Fast container availability: container boots with 50 pre-indexed episodes (72 MB, 2,052 vectors in `chroma_db/`) ready for retrieval without runtime embedding delays.
- Zero network hops during vector search: cosine similarity computations occur in-process in milliseconds.
- Deterministic reproducibility: every clone of the repository has identical vector embeddings and search results.

### Bad
- Repository size increases: `chroma_db/` takes 72 MB of git storage (below GitHub's 100 MB per-file and recommended 1 GB repo limits).
- Not horizontally scalable: embedded storage cannot be concurrently updated by multiple container replicas without shared storage or write locks.

## Evidence
- `app/vectorstore.py`: `DEFAULT_DB_DIR = "chroma_db"`, `get_vectorstore()`.
- Repository tree: `chroma_db/` committed to git.
- Git commits: `c752704`, `826fa6e`, `622c240`.
