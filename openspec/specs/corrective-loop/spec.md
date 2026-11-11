# Capability Specification: Corrective Loop

## Purpose
The corrective loop governs the self-evaluating Corrective RAG (Self-RAG) state machine in LangGraph. It assesses document relevance via structured output, triggers search query rewrites when retrieval misses, enforces deterministic loop bounds, and aborts to a clean refusal when retries are exhausted.

## Requirements

### Requirement: Post-Retrieval Fast-Path Routing
The system SHALL evaluate whether retrieved documents can bypass LLM grading based on mode configuration, exact phrase matches, or semantic distance thresholds.

#### Scenario: Bypass grading in Turbo mode
- **WHEN** retrieval finishes with `mode == "turbo"`
- **THEN** the router `route_after_retrieve` directs the state graph directly to `generate`.

#### Scenario: Bypass grading in high-confidence Balanced mode
- **WHEN** retrieval finishes with `mode == "balanced"` and `top_distance < 0.35`
- **THEN** the router `route_after_retrieve` directs the state graph directly to `generate`.

#### Scenario: Bypass grading on exact quote match
- **WHEN** retrieval finishes with `is_exact_match == True`
- **THEN** the router `route_after_retrieve` directs the state graph directly to `generate`.

#### Scenario: Standard routing to document grading
- **WHEN** retrieval finishes with `mode == "rigorous"` or `(mode == "balanced" and top_distance >= 0.35)`
- **AND** `is_exact_match == False`
- **THEN** the router `route_after_retrieve` directs the state graph to `grade_documents`.

### Requirement: Single-Call Batch Document Grading
The system SHALL evaluate all retrieved chunks in a single batch LLM call using Pydantic structured output (`BatchGradeResult`) enforcing a 1-to-1 list of `"yes"` or `"no"` relevance scores.

#### Scenario: Successful document relevance classification
- **WHEN** `grade_documents` receives $N$ retrieved documents
- **THEN** an LLM prompt requests exactly $N$ binary scores
- **AND** chunks marked `"yes"` are retained in `relevant_documents`
- **AND** chunks marked `"no"` are filtered out.

#### Scenario: Graceful grading fallback on structured output error
- **WHEN** the batch grading LLM call fails, times out, or raises an exception
- **THEN** a warning is logged
- **AND** all retrieved documents are retained as `relevant_documents` to preserve service continuity.

### Requirement: Decision Router and Loop Bounds
The system SHALL evaluate whether to proceed to answer generation or initiate a query rewrite based on document relevance and mode-specific retry limits.

#### Scenario: Relevant documents identified
- **WHEN** `relevant_documents` contains at least one document
- **THEN** `decide_to_generate` routes execution to `generate`.

#### Scenario: Mode-specific retry limit reached (Circuit Breaker)
- **WHEN** `relevant_documents` is empty
- **AND** `rewrite_count` meets or exceeds `max_retries` (0 for Turbo, 1 for Balanced, 2 for Rigorous; note Turbo's 0-retry limit in `decide_to_generate` is unreachable in practice because Turbo unconditionally bypasses grading)
- **THEN** `decide_to_generate` routes execution to `generate` to issue a refusal.

#### Scenario: Trigger query rewrite
- **WHEN** `relevant_documents` is empty
- **AND** `rewrite_count` is strictly less than `max_retries`
- **THEN** `decide_to_generate` routes execution to `rewrite_query`.

### Requirement: Query Optimization and Rewrite Counter
The system SHALL rephrase the user query into a concise, keyword-rich search query optimized for semantic vector search and increment the rewrite counter.

#### Scenario: Query rewrite execution
- **WHEN** `rewrite_query` is executed
- **THEN** an LLM rephrases `question` into a search-optimized query string
- **AND** `rewrite_count` is incremented by 1
- **AND** control returns to `retrieve` with the updated query.
