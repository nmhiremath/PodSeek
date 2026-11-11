# Pillar 5: Grounding & Hallucination Control

## 1. What This Pillar Means in Production AI Systems
Grounding and hallucination control encompasses the mechanisms that ensure language model outputs remain strictly faithful to source documents, produce accurate citations, and gracefully refuse to answer when verifiable evidence is absent. In production, ungrounded answers erode user trust and present severe liability risks; systems must actively police context boundaries rather than relying on LLM goodwill.

## 2. What PodSeek Does
PodSeek enforces multi-layered grounding and hallucination controls throughout the lifecycle of every query:
- **Pre-Synthesis Document Grading (`app/agent/nodes.py:grade_documents`):** Retrieved chunks are filtered by an LLM classifier requiring explicit binary relevance. Chunks that do not directly answer the question are discarded before synthesis.
- **Defensive Context Injection (`app/agent/nodes.py:generate`):** Context is injected with structured timestamp headers `[{episode_title} | {speaker} @ {timestamp}]`. The system prompt enforces strict rules:
  1. Ground all claims strictly in the excerpts.
  2. Cite exact timestamps in `[HH:MM:SS]` format for every claim.
  3. If the excerpts do not contain the answer, state that honestly.
- **Circuit-Breaker Refusal Contract (`app/agent/nodes.py:generate`):** When retrieval yields no relevant chunks after allowable retries, `generate` returns a hardcoded refusal string: `"I could not find any relevant information in the podcast transcripts to answer your question."` with `relevant_documents = []`.
- **Post-Generation Refusal Detection (`app/agent/nodes.py:generate`):** If the LLM generates an apology or indicates missing information (matching phrases like `"could not find any relevant information"` or `"not mentioned in the"`), the node resets `relevant_documents = []` to prevent hallucinated citations from reaching the frontend.
- **Deep-Link Citation Verification (`app/api/routes.py:_build_citations`):** Citations are built solely from verified `relevant_documents`, calculating numeric YouTube deep-links (`https://youtu.be/{episode_id}?t={start_seconds}`).

## 3. Enterprise Approach
At enterprise scale, organizations deploy:
- **Programmable Guardrail Frameworks:** NeMo Guardrails (Colang policies) or Guardrails AI to intercept inputs and outputs.
- **Automated Hallucination Detection Services:** Dedicated NLI (Natural Language Inference) models scoring entailment vs contradiction between context and generation before streaming to users.
- **Post-Hoc Citation Attributors:** Running secondary LLM passes to verify that each citation link actually supports the sentence it follows.

## 4. Why We Didn't Need It Here, and How PodSeek Achieves the Same Intent
For a focused podcast question-answering assistant:
- Heavy guardrail frameworks add 1–2 seconds of latency and substantial memory requirements unsuitable for free-tier hosting.
- PodSeek's combination of pre-generation batch grading, low synthesis temperature (`temperature=0.1`), hard circuit-breaker refusal, and post-generation regex inspection achieves 100% adherence on out-of-scope refusals in benchmark evals (`evals/questions.json`).
- Timestamp-bound sliding chunks ensure that every citation links to the exact second the statement was spoken.

## 5. Where Our Approach Breaks Down
PodSeek's grounding architecture breaks down under the following triggers:
- **Turbo Mode Ingestion of Noise:** In Turbo mode, document grading is skipped. If a query semantically retrieves tangential banter, the generator prompt must rely entirely on its internal rule #5 to refuse; in benchmark evals, Turbo mode achieved 93.8% citation validity (15/16) compared to 100% in Balanced and Rigorous modes.
- **Fine-Grained Semantic Entailment:** If a chunk contains 80% relevant facts and 20% irrelevant speculation, the model might occasionally blend speculative comments into its answer without triggering a refusal.

## 6. Trade-Offs Accepted
- **Strict Refusals vs Speculative Helpfulness:** Accepted flat refusals on out-of-scope questions rather than providing general knowledge answers.
- **Regex Phrasing Inspection vs NLI Classifier:** Accepted fast regex matching on refusal phrases rather than running an expensive NLI entailment model.
- **Fixed Refusal Message:** Accepted a standardized, rigid refusal text to guarantee zero spurious citations.

## 7. Pitfalls Encountered
- **Phantom Citations on Refusal Answers:** In early versions, when the LLM answered "I don't know based on these clips", the citation builder still grabbed `relevant_documents` metadata and displayed clickable YouTube chips for an unhelpful answer. Fixed in commit `4d0697c` with `is_refusal` regex matching that empties `relevant_documents` before building citations.
- **Off-Topic Topic Drift:** Out-of-scope questions about cooking or software engineering originally retrieved irrelevant health clips and attempted to answer them metaphorically. Fixed in commit `a57c9ce` with batch grading and `d4c0068` with expanded benchmark test cases.

## 8. Next Steps (Candidate OpenSpec Changes)
- `sentence-level-citation-verification`: Verify that each inline `[HH:MM:SS]` timestamp corresponds directly to the sentence it is attached to using token-span alignment.
- `hallucination-scoring-telemetry`: Compute and log an automated RAG grounding score in `AskResponse.metadata`.
