# 3. Deterministic Rewrite Ceiling and Refusal Contract

> Recorded retroactively on 2026-11-10; decision originally made in commit `a57c9ce`.

## Status
Accepted

## Context
When a user asks a question outside the scope of the podcast corpus (e.g. asking Huberman Lab about Linux kernel schedulers or sourdough recipes), naive semantic search returns low-confidence or irrelevant chunks. If the system loops repeatedly trying to rewrite the query, it burns LLM quota, incurs high latency, and eventually risks synthesizing a hallucinated answer or citing irrelevant timestamps.

## Decision
Enforce a hard circuit-breaker ceiling on query rewrites via `MAX_REWRITES = 2` in `app/agent/graph.py` (with mode-specific limits: 0 for Turbo, 1 for Balanced, 2 for Rigorous; note that Turbo's 0-retry branch in `decide_to_generate` is unreachable in practice because Turbo unconditionally bypasses grading). When retries are exhausted without finding relevant documents, the system routes directly to `generate` which is contractually bound to emit a standardized refusal string: `"I could not find any relevant information in the podcast transcripts to answer your question."` and clear all citation metadata (`relevant_documents = []`).

## Alternatives Considered
1. **Fallback to General Web Search:** Query Google / DuckDuckGo / Tavily when podcast retrieval misses. Rejected because the system promise is strict grounding in verified podcast transcripts, not unverified internet content.
2. **Dynamic Stopping based on Cosine Distance:** Stop retrying when similarity score drops below a floor. Rejected because distance scores vary significantly across queries, whereas an explicit retry count provides an absolute latency and cost bound.
3. **Allowing LLM to answer from pre-trained parametric memory:** Let the model answer general knowledge questions without citations. Rejected because users must never mistake parametric LLM memory for cited Huberman statements.

## Consequences
### Good
- Guarantees termination: max 3 retrieval attempts and 2 rewrites in rigorous mode, max 1 in balanced, max 0 in turbo.
- Eliminates hallucinations on out-of-domain questions: benchmark evals confirm 100% adherence on out-of-scope refusals in Balanced and Rigorous modes (`evals/questions.json`). (Turbo mode achieved 93.8% citation validity overall, as it skips grading).
- Prevents spurious citations on negative answers.

### Bad
- Legitimate questions phrased very obscurely might trigger refusal after 2 retries if the rewriter fails to find the right keyword.
- Refusal message is rigid and does not suggest alternative queries to the user.

## Evidence
- `app/agent/graph.py`: `MAX_REWRITES = 2` constant, `decide_to_generate()` router enforcing mode limits.
- `app/agent/nodes.py`: `generate()` refusal string and post-generation refusal regex check.
- `evals/questions.json`: Out-of-scope test cases (`off-topic-gap`, `off-topic-linux-kernel`, `off-topic-sourdough`).
- Git commits: `a57c9ce`, `4d0697c`, `d4c0068`.
