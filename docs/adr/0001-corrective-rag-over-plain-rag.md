# 1. Corrective RAG over Plain RAG

> Recorded retroactively on 2026-11-10; decision originally made in commit `a57c9ce`.

## Status
Accepted

## Context
Standard Retrieval-Augmented Generation (RAG) retrieves top-k chunks from a vector store and immediately injects them into an LLM generation prompt. In podcast audio transcripts, conversational drift, tangents, and sponsor reads frequently produce chunks that match query keywords semantically but contain zero answerable facts. In plain RAG, the generator either hallucinates an answer or synthesizes misleading conclusions based on irrelevant context.

## Decision
Implement Corrective RAG (CRAG), adding a dedicated grading step between retrieval and generation. An LLM relevance evaluator grades retrieved chunks before generation. If retrieved chunks are irrelevant, the system invokes a query rewriter to optimize the search query and retries retrieval.

## Alternatives Considered
1. **Plain Naive RAG:** Retrieve top-k chunks and feed directly to synthesis. Rejected because irrelevant podcast banter caused hallucinations and bad citations.
2. **Re-ranking with Cross-Encoder (e.g. Cohere / BGE Reranker):** Add a cross-encoder model to sort chunks by relevance. Rejected for Phase 1 to avoid additional binary dependencies, specialized GPU memory requirements, and external API latency.
3. **Web Search Fallback:** Fallback to Google / Tavily search when podcast retrieval fails. Rejected because PodSeek is explicitly designed to answer from verified podcast transcripts only, not general internet knowledge.

## Consequences
### Good
- Completely filters out tangential podcast banters and sponsor reads before synthesis.
- Prevents hallucinated answers when initial semantic retrieval returns low-quality matches.
- Enables query reformulation tailored for semantic vector search.

### Bad
- Adds an extra LLM evaluation call, increasing end-to-end latency when chunks must be graded.
- Requires robust error handling if the grading prompt fails.

## Evidence
- `app/agent/nodes.py`: `grade_documents()` function and `BatchGradeResult` schema.
- `app/agent/graph.py`: State graph routing between `retrieve`, `grade_documents`, `rewrite_query`, and `generate`.
- Git commits: `a57c9ce`, `4d0697c`.
