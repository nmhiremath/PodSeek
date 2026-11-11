# Pillar 6: Evaluation

## 1. What This Pillar Means in Production AI Systems
Evaluation is the rigorous, repeatable measurement of an AI system's performance, correctness, latency, and failure boundaries across standardized datasets. In production, evaluation must prevent regressions, benchmark trade-offs across model versions and execution modes, and provide rapid offline feedback in CI without depending on unstable external services or incurring heavy API costs.

## 2. What PodSeek Does
PodSeek provides a deterministic, offline-first evaluation harness paired with live multi-mode benchmarking:
- **16-Question Curated Benchmark (`evals/questions.json`):** 13 in-scope scientific questions across indexed Huberman episodes (dopamine, sunlight, cold exposure, caffeine delay, physiological sigh, alcohol, neuroplasticity, habit bracketing, time-restricted eating, gut health, hypertrophy, sugar/fructose, meditation) plus 3 out-of-scope refusal test cases: the 1998 FIFA World Cup final (`off-topic-gap`), a custom Linux kernel eBPF kprobe module in Rust (`off-topic-linux-kernel`), and a classic San Francisco sourdough boule schedule (`off-topic-sourdough`).
- **Offline Evaluation Suite (`scripts/evaluate.py`, `app/evaluation.py`):** Scores static fixture answers without external network calls or API keys. Measures:
  1. **In-Scope Keyword Hit Rate:** Fraction of expected domain keywords present in the generated answer.
  2. **Citation Format Validity:** Verifies every returned citation has a valid `HH:MM:SS` timestamp and a valid `https://youtu.be/{id}?t={sec}` deep link where `{sec}` matches the timestamp.
  3. **Refusal Status:** Verifies that out-of-scope questions return zero citations (`status=PASS`).
- **Live Multi-Mode Benchmarking (`scripts/evaluate.py --live --mode <mode>`):** Dispatches the 16 questions against the live API, computing keyword hit rates, citation validity percentages, and p50/p95 latency percentiles.
- **Optional LLM-as-Judge (`scripts/evaluate.py --live --llm-judge`):** Scores answers on a structured 1–5 scale using the configured chat model.

### PR #2 Live Benchmark Results (Run on 2026-11-10)
Executed via `python -m scripts.evaluate --live --mode <mode>` against the 50-episode indexed corpus:

| Mode | Keyword Hit Rate | Citation Validity | p50 Latency | p95 Latency | Notes |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `turbo` | 82.1% | 93.8% (15/16) | 7,024 ms | 11,026 ms | 1 question failed citation check (skipped grading) |
| `balanced` | 89.7% | 100.0% (16/16) | 12,577 ms | 21,438 ms | 100% citation format & refusal pass |
| `rigorous` | 87.2% | 100.0% (16/16) | 15,106 ms | 22,761 ms | Full grading on all chunks, 100% pass |

> Note: Turbo mode failed 1 of 16 citation checks because skipping LLM grading allowed an out-of-scope question to return unverified excerpts rather than cleanly refusing. `TODO(identify): name the Turbo citation failure from the PR #2 live eval output (one of the three off-topic questions). Do not invent it.`

## 3. Enterprise Approach
At enterprise scale, organizations implement:
- **Evaluation Platforms:** Ragas, DeepEval, Arize Phoenix, or TruLens computing Faithfulness, Answer Relevance, Context Precision, and Context Recall.
- **Continuous Production Tracing Datasets:** Sampling 1% of live user conversations in LangSmith or Langfuse and routing them to human annotators or automated evaluation pipelines.
- **Golden Evaluation Sets:** Thousands of multi-turn dialogues with verified reference answers running on nightly cron schedules.

## 4. Why We Didn't Need It Here, and How PodSeek Achieves the Same Intent
For a focused podcast question-answering assistant:
- Frameworks like Ragas pull in heavy dependency trees (hundreds of megabytes) and require multiple LLM calls per metric, dramatically slowing down testing.
- PodSeek's deterministic checks (keyword recall, `HH:MM:SS` timestamp regex, deep-link query parameter matching, and refusal verification) execute in milliseconds and run 100% offline in CI without an API key.
- Live evaluations with p50/p95 latency measurements provide clear empirical trade-offs across execution modes without operational bloat.

## 5. Where Our Approach Breaks Down
PodSeek's evaluation architecture breaks down under the following triggers:
- **Paraphrasing and Synonym Blindness:** Keyword overlap matching fails if the LLM expresses the correct scientific concept using accurate synonyms not present in the keyword list.
- **Small Benchmark Sample Size (16 Questions):** While effective for smoke-testing and regression detection, 16 questions do not provide statistical significance across the entire 50-episode corpus.
- **No Multi-Turn or Conversational Evals:** The harness only evaluates single-turn question-answering.

## 6. Trade-Offs Accepted
- **Offline Keyword Heuristics vs Heavy Ragas Frameworks:** Accepted keyword matching in exchange for fast, zero-cost CI test execution.
- **16-Question Curated Set vs Synthetic 1,000-Question Datasets:** Accepted a small, hand-curated gold set that can be manually inspected and verified.
- **Binary Format Checks vs Semantic Entailment:** Accepted checking citation URL syntax and timestamps rather than running multi-stage NLI validation on every citation.

## 7. Pitfalls Encountered
- **Eval Latency in CI:** Initial eval designs considered running live model calls in CI. This was rejected in commit `d4c0068` in favor of static fixture evaluation, keeping CI runs completely offline and instantaneous.
- **Unmeasured Mode Latency Trade-Offs:** Prior to PR #2, claims about Turbo mode speedups were unverified. Commit `d4c0068` added automated p50/p95 latency logging to `scripts/evaluate.py`, producing verified empirical benchmarks.

## 8. Next Steps (Candidate OpenSpec Changes)
- `expanded-50-question-benchmark`: Expand `evals/questions.json` to 50 questions with 1 representative query per indexed episode.
- `semantic-similarity-eval-metric`: Add offline embedding-based cosine similarity between generated answers and reference summaries as an alternative to keyword overlap.
