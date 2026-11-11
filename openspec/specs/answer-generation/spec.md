# Capability Specification: Answer Generation

## Purpose
The answer generation capability synthesizes grounded responses strictly from verified transcript excerpts, produces inline timestamp citations, streams generated tokens in real time, and enforces a refusal contract to prevent hallucinations.

## Requirements

### Requirement: Strict Grounding and Context Formatting
The system SHALL format each verified transcript chunk with its metadata header `[{episode_title} | {speaker} @ {timestamp}]` and require the LLM to answer using only the provided context.

#### Scenario: Grounded synthesis with citations
- **WHEN** `generate` executes with non-empty `relevant_documents`
- **THEN** transcript excerpts are formatted with timestamp headers
- **AND** the generation prompt instructs the model to cite exact timestamps in `[HH:MM:SS]` format
- **AND** the temperature is set to `0.1` for deterministic, faithful synthesis.

### Requirement: Real-Time Token Streaming
The system SHALL stream generated answer tokens as they arrive from the language model via the LangGraph stream writer.

#### Scenario: Streaming tokens during generation
- **WHEN** the generation LLM emits token chunks
- **THEN** each token is written to the LangGraph stream writer as `{"delta": token}`
- **AND** if streaming fails or raises an exception, the node gracefully falls back to `invoke()`.

### Requirement: Circuit-Breaker Refusal Contract
The system SHALL return a standardized refusal message without citations whenever relevant documents are unavailable.

#### Scenario: Empty context refusal
- **WHEN** `generate` executes with an empty list of relevant documents
- **THEN** the system outputs the exact refusal string:
  `"I could not find any relevant information in the podcast transcripts to answer your question."`
- **AND** `relevant_documents` is set to `[]`
- **AND** no citations are produced.

### Requirement: Post-Generation Refusal Detection
The system SHALL inspect the generated text for refusal phrasing and suppress citations if the model expresses an inability to answer from context.

#### Scenario: Model generates a refusal despite context
- **WHEN** the generated text contains `"could not find any relevant information"`, `"cannot find any relevant information"`, `"no relevant information"`, or `"not mentioned in the"`
- **THEN** `relevant_documents` is reset to an empty list `[]`
- **AND** downstream citation builders emit zero citations.
