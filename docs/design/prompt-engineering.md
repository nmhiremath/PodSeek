# Pillar 3: Prompt Engineering

## 1. What This Pillar Means in Production AI Systems
Prompt engineering in production AI systems is not about subjective prompt tweaking; it is the discipline of creating typed, deterministic, and testable interfaces between software systems and probabilistic language models. This includes schema enforcement via structured outputs, system prompt isolation, role boundary definition, explicit refusal contracts, and defensive context formatting to eliminate hallucination.

## 2. What PodSeek Does
PodSeek isolates prompts within their respective node definitions using LangChain `ChatPromptTemplate` and Pydantic schemas:
- **Single-Call Batch Document Grading (`app/agent/nodes.py:grade_documents`):** Uses `llm.with_structured_output(BatchGradeResult)`. The prompt injects all $N$ numbered excerpts at once and requires the model to return exactly $N$ binary scores (`binary_scores: list[Literal["yes", "no"]]`).
- **Query Optimization (`app/agent/nodes.py:rewrite_query`):** System prompt acts as a specialized search query optimizer, instructing the model to rephrase the question into a keyword-rich query suited for vector semantic retrieval, outputting ONLY the new query string.
- **Grounded Answer Synthesis (`app/agent/nodes.py:generate`):** Formats context excerpts with explicit citation metadata headers: `[{episode_title} | {speaker} @ {timestamp}]:\n"{doc.page_content}"`. The system prompt enforces 3 core rules:
  1. Ground all claims strictly in the excerpts.
  2. Cite exact timestamp and episode title (e.g. `[00:57:54]`).
  3. If excerpts do not contain the answer, state that honestly.
  - Adds conditional pinpoint instructions for exact quote searches and Turbo mode refusal overrides.
- **Episode Summarization (`app/api/routes.py:_analyze_episode`):** Uses `llm.with_structured_output(EpisodeAnalysis)` to extract 1-2 sentence executive summaries, 2-3 paragraph breakdowns, 4-6 key takeaways, and 10-15 keywords.

## 3. Enterprise Approach
At enterprise scale, organizations manage prompts using:
- **Prompt Registries and Management Hubs:** Langfuse, Humanloop, Agenta, or LangSmith Prompt Hub with semantic versioning, staging/production tags, and rollbacks.
- **A/B Testing & Canary Deployments:** Routing 10% of traffic to experimental prompt variants and evaluating win-rates against production baselines.
- **Few-Shot Dynamic Injection:** Using vector stores to retrieve dynamically relevant few-shot examples for the grading and generation prompts.

## 4. Why We Didn't Need It Here, and How PodSeek Achieves the Same Intent
For a focused podcast question-answering assistant:
- Storing prompts as Python constants within `app/agent/nodes.py` guarantees that prompt changes are tracked directly in Git alongside the code that consumes them.
- Batch Pydantic structured output (`BatchGradeResult`) collapses $k$ independent LLM grading calls into a single call, eliminating 75% of grading latency and token overhead.
- Rigorous automated offline unit tests (`tests/test_agent.py`) and keyword evaluation benchmarks (`evals/questions.json`) verify prompt behavior without requiring a complex prompt registry.

## 5. Where Our Approach Breaks Down
PodSeek's prompt architecture breaks down under the following triggers:
- **Cross-Model Prompt Portability:** Prompts optimized for `gemini-3.8-flash` may exhibit minor formatting variances when switched to smaller open-source models (e.g. `llama-3.1-8b` via Ollama) that struggle with complex multi-rule system instructions.
- **No In-Flight Hot Reloading:** Updating prompt instructions requires a code commit and redeployment rather than updating a database configuration.
- **Very Long Context Documents:** Ingesting 4-hour podcast transcripts requires truncating context to ~40,000 words during summarization (`app/api/routes.py:_analyze_episode`).

## 6. Trade-Offs Accepted
- **In-Code Prompts vs External Registry:** Accepted redeployment for prompt edits in exchange for zero external service dependencies and version-controlled Git history.
- **Zero-Shot Grading vs Few-Shot:** Accepted zero-shot structured prompts for document grading to conserve input token budgets on free-tier quotas.
- **Fixed Refusal Phrasing:** Accepted an exact standardized refusal sentence rather than letting the LLM invent creative apologies.

## 7. Pitfalls Encountered
- **Sequential Grading Overhead:** Initial implementations called the LLM once per retrieved chunk (4 sequential calls per retrieval), multiplying grading latency and token overhead. Fixed in commit `9a36aea` by switching to `BatchGradeResult`, grading all retrieved chunks in a single batch prompt.
- **Hallucinated Citations on Partial Refusals:** When the LLM apologized for missing info, it occasionally cited irrelevant chunks in its bibliography. Fixed in commit `9a36aea` by implementing post-generation refusal regex detection in `generate()`, which clears `relevant_documents = []` if refusal phrasing is detected.

## 8. Next Steps (Candidate OpenSpec Changes)
- `externalized-prompt-templates`: Move prompt strings to YAML template files under `app/prompts/` for cleaner separation from node logic.
- `few-shot-grading-examples`: Add 2 curated few-shot examples of relevant vs irrelevant podcast banter to the batch grader prompt.
