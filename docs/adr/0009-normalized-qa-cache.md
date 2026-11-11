# 9. Normalized QA Cache with Composite Keys

> Recorded retroactively on 2026-11-10; decision originally made in commit `9a36aea`.

## Status
Accepted

## Context
Frequently asked questions (e.g. preset demo buttons in the UI like "What causes a dopamine crash?" or "How does morning sunlight affect cortisol?") are triggered repeatedly by visitors to the public demo. Running the full CRAG workflow on repeated questions drains free-tier API quotas and incurs redundant latency. However, a naive string-keyed cache risks serving stale answers if new episodes are ingested or if the embedding model changes.

## Decision
Implement a persistent, normalized JSON QA cache (`_QA_CACHE` in `app/api/routes.py`, backed by `data/raw/qa_cache.json`). The cache key is a composite string constructed from:
1. Active collection name (embedding-model-scoped).
2. Sorted list of currently indexed episode IDs.
3. Execution mode (`turbo`, `balanced`, `rigorous`).
4. Alphanumerically normalized question text (`re.sub(r"[^a-z0-9]+", " ", q.lower()).strip()`).

If a query hits the cache, both `/ask` and `/ask/stream` return the precomputed answer, structured citations, and node event history instantly.

## Alternatives Considered
1. **Redis Cache:** Deploy a Redis instance. Rejected to stay within zero-cost single-container constraints.
2. **In-Memory Only Cache:** Cache in a Python dictionary without disk persistence. Rejected because Render free tier spins down idle containers; disk persistence allows pre-seeding and surviving cold restarts.
3. **Semantic Embedding Cache (e.g. GPTCache):** Embed incoming queries and match if similarity > 0.95. Rejected for initial implementation to avoid latency and quota cost of embedding every query before checking the cache, though flagged as a candidate future enhancement.

## Consequences
### Good
- Immediate response times for pre-seeded questions without executing retrieval or model calls.
- Automatic invalidation: ingesting a new episode alters the sorted episode ID list, automatically preventing stale cache hits without needing manual cache flushes.
- Normalization prevents trivial misses caused by trailing punctuation, casing, or extra whitespace.

### Bad
- Exact normalized string matching means slight rephrasings (e.g. "causes of dopamine crash" vs "what causes dopamine crash") miss the cache.
- Single JSON file on disk requires write operations that do not scale across multiple concurrent server replicas.

## Evidence
- `app/api/routes.py`: `_QA_CACHE`, `_qa_cache_key()`, `_get_cached_qa()`, `_set_cached_qa()`.
- `data/raw/qa_cache.json`: Pre-seeded responses for top benchmark and demo questions.
- Git commit: `9a36aea`.
