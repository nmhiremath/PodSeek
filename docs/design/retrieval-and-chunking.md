# Pillar 1: Retrieval & Chunking

## 1. What This Pillar Means in Production AI Systems
Retrieval and chunking form the foundation of any Retrieval-Augmented Generation system. In production AI systems, this pillar governs how long-form unstructured documents or audio streams are partitioned into semantically cohesive passages, how spatial metadata is preserved for deep linking, and how vector search identifies relevant context against millions of indexed chunks. Effective retrieval must balance chunk granularity against semantic completeness while bounding vector index memory and query latency.

## 2. What PodSeek Does
PodSeek implements a pure, speaker-aware sliding-window chunking strategy and an embedded vector store:
- **Speaker-Aware Sliding-Window Chunking (`app/ingestion/chunking.py:chunk_segments`):** Captions are accumulated into chunks targeting ~200 words (`target_words=200`) with ~40 words overlap (`overlap_words=40`). If a segment transitions to a new speaker (`seg.speaker != speaker`), the chunk closes immediately to prevent blended attributions. Start and end timestamps are preserved on each `Chunk` model (`app/schemas/transcripts.py:Chunk`).
- **Embedded Vector Store (`app/vectorstore.py:get_vectorstore`):** Chunks are embedded using Google GenAI `models/gemini-embedding-2` (3072 dimensions) and indexed in an embedded ChromaDB instance (`chroma_db/`).
- **Cosine Distance Retrieval (`app/agent/nodes.py:retrieve`):** `retrieve()` queries ChromaDB via `similarity_search_with_score(query=question, k=4)`. Cosine distances are returned and stored in `AgentState["top_distance"]`.
- **Exact Quote Detection & Hoisting (`app/agent/nodes.py:retrieve`):** If a user query contains a quoted string of 4+ characters (`r'["\']([^"\']{4,})["\']'`) and that phrase matches a chunk's `page_content` case-insensitively, that chunk is hoisted to index 0, `is_exact_match` is marked `True`, and `top_distance` is clamped to $\le 0.08$.

## 3. Enterprise Approach
At enterprise scale, organizations typically deploy:
- **Managed Distributed Vector Databases:** Pinecone, Qdrant Cloud, Milvus, or Weaviate with horizontal sharding, dynamic replica autoscaling, and cross-region replication.
- **Hybrid Search:** Dense vector embeddings combined with sparse BM25 / SPLADE lexical inverted indices via Reciprocal Rank Fusion (RRF).
- **Cross-Encoder Re-Rankers:** Cohere Rerank or BGE-Reranker-Large running on specialized GPU instances to rescore candidate chunks from top-50 down to top-5.
- **Hierarchical Parent-Document Retrieval:** Indexing small sentences for retrieval while injecting larger surrounding parent paragraphs into the generation prompt.

## 4. Why We Didn't Need It Here, and How PodSeek Achieves the Same Intent
For a focused podcast corpus of 50 episodes (2,052 chunks in the active `podcast_chunks_gemini-embedding-2` collection) hosted on a 512 MB RAM free-tier container:
- Embedded ChromaDB operates entirely in-process using local sqlite/HNSW files (72 MB in `chroma_db/`), incurring 0 network roundtrip overhead and 0 dollar cost.
- Cosine distance scores from `gemini-embedding-2` provide sufficient semantic separation that an external re-ranker was unnecessary.
- Speaker-boundary splitting and exact quote hoisting provide the primary benefits of hybrid search (finding verbatim statements) without running a full BM25 search daemon.

## 5. Where Our Approach Breaks Down
PodSeek's retrieval architecture breaks down under the following triggers:
- **Corpus Growth:** Storing expanded HNSW indices in embedded ChromaDB will eventually challenge the 512 MB container RAM ceiling on free-tier Render (`TODO(measure):` profile resident memory as corpus size increases).
- **Concurrent Writes:** Embedded ChromaDB SQLite backends experience file-lock contention when multiple concurrent ingestion workers attempt to index episodes simultaneously.
- **Vocabulary Mismatch on Obscure Jargon:** Without sparse BM25 keyword indexing, pure semantic retrieval occasionally misses uncommon medical or chemical names that have low semantic density in general embeddings.

## 6. Trade-Offs Accepted
- **In-Memory Footprint vs Cloud Delegation:** Accepted bundling the index locally in git and RAM rather than paying for cloud vector DB hosting.
- **Fixed Window vs Dynamic Semantic Segmentation:** Accepted fixed 200-word sliding windows rather than embedding every sentence boundary during ingestion.
- **Top-4 Fixed Retrieval Budget:** Accepted retrieving exactly $k=4$ chunks rather than dynamically expanding $k$ based on document density.

## 7. Pitfalls Encountered
- **Vector Dimension Mismatch Across Models:** Changing from `gemini-embedding-2` (`dim=3072`) to OpenAI `text-embedding-3-small` (`dim=1536`) crashed ChromaDB when using a static collection name. Fixed in commit `56aaa0b` by introducing `get_collection_name()` in `app/factory.py`, which isolates collection names dynamically based on the embedding model string.
- **Quote Search Degradation:** Exact quote searches originally returned generic conversational chunks if the phrase appeared in multiple episodes. Fixed in commit `9a36aea` with regex quote detection, hoisting the verbatim match to index 0 and setting `is_exact_match=True`.

## 8. Next Steps (Candidate OpenSpec Changes)
- `hybrid-bm25-retrieval`: Add in-memory SQLite FTS5 lexical search combined with ChromaDB dense scores via Reciprocal Rank Fusion.
- `metadata-filtered-retrieval`: Allow users or the agent to filter retrieval by specific guest speaker or date range via ChromaDB `where` filters.
