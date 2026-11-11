# 6. Multi-Tier Execution Modes and Distance Fast-Path

> Recorded retroactively on 2026-11-10; decision originally made in commit `9a36aea`.

## Status
Accepted

## Context
In production RAG workflows, a one-size-fits-all execution strategy forces every query through identical latency-heavy steps. Simple queries with obvious semantic matches take just as long as difficult, ambiguous questions. Users testing or seeking rapid answers suffer unnecessary waiting, while operators burn API rate limits on unnecessary grading calls.

## Decision
Introduce three explicit execution modes (`turbo`, `balanced`, `rigorous`) and a distance-based fast path:
1. **Turbo Mode:** Skips document grading entirely, disables query rewrites (0 retries), and directly feeds top retrieved chunks to generation for minimum latency.
2. **Balanced Mode (Default):** Evaluates cosine distance score $top\_distance$. If $top\_distance < 0.35$ (high semantic similarity) or an exact quote is detected, it takes the fast path directly to generation, skipping LLM grading. If distance is $\ge 0.35$, it grades chunks and allows at most 1 rewrite.
3. **Rigorous Mode:** Always executes LLM batch document grading regardless of distance and permits up to 2 query rewrites (`MAX_REWRITES`).

## Alternatives Considered
1. **Static Uniform Pipeline:** Always grade and allow 2 rewrites for all requests. Rejected because p50 latency was too high (~15–20 seconds) for obvious answers.
2. **Probabilistic Routing:** Use a classifier or prompt to pick a mode. Rejected to give the caller explicit control via API parameter (`AskRequest.mode`) and UI toggle.

## Consequences
### Good
- Significant latency savings: queries matching closely in Balanced mode bypass grading, cutting response time by 40–50%.
- Turbo mode provides ultra-fast responses (measured p50 latency ~7,024 ms vs 12,577 ms in Balanced and 15,106 ms in Rigorous during live evals).
- Exact quote searches (e.g. searching for a verbatim sentence in quotes) hoist the match and fast-path immediately.

### Bad
- In Turbo mode, because grading is skipped, an out-of-scope query might fail to refuse cleanly (as seen in benchmark where Turbo had 93.8% citation validity vs 100% in Balanced and Rigorous).
- Threshold tuning: the 0.35 distance cutoff is tuned for `gemini-embedding-2` cosine distance and may need recalibration if embedding models change.

## Evidence
- `app/agent/graph.py`: `route_after_retrieve()` and `decide_to_generate()` inspecting `mode` and `top_distance`.
- `app/agent/nodes.py`: Distance clamping and fast-path population in `retrieve()`.
- Benchmark evaluation results from PR #2: Turbo p50 7,024 ms, Balanced p50 12,577 ms, Rigorous p50 15,106 ms.
- Git commits: `9a36aea`, `d4c0068`.
