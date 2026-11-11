# Capability Specification: Retrieval

## Purpose
The retrieval capability queries the persistent ChromaDB vector store for top semantic transcript chunks matching the user's question, scores cosine distances, detects exact quote matches, and supports high-confidence fast-path routing.

## Requirements

### Requirement: Vector Similarity Retrieval with Cosine Distance
The system SHALL retrieve top-k ($k=4$) documents from ChromaDB matching the current question along with their cosine distance scores.

#### Scenario: Standard semantic retrieval
- **WHEN** `retrieve(state)` is invoked with a user question
- **THEN** ChromaDB is queried via `similarity_search_with_score(query=question, k=4)`
- **AND** the resulting documents are returned in `documents`
- **AND** `top_distance` is recorded as a float rounded to 4 decimal places.

### Requirement: Exact Quote Detection and Hoisting
The system SHALL detect explicit quoted phrases of 4 or more characters within the question and verify whether the quoted phrase appears verbatim in any retrieved chunk.

#### Scenario: Verbatim quote in question matches transcript
- **WHEN** the question contains a quoted string like `"Sauna use of 12 minutes"` of 4 or more characters
- **AND** a retrieved chunk contains the string case-insensitively in `page_content`
- **THEN** `is_exact_match` is set to `True`
- **AND** the matching chunk is hoisted to index 0 of `documents`
- **AND** `top_distance` is clamped to at most `0.08`
- **AND** `relevant_documents` is initialized with `[documents[0]]`.

### Requirement: Fast-Path Pre-Population
The system SHALL automatically populate `relevant_documents` during retrieval when operating in Turbo mode, when an exact quote match is found, or when Balanced mode achieves high semantic confidence ($top\_distance < 0.35$).

#### Scenario: High semantic confidence in Balanced mode
- **WHEN** `mode` is `"balanced"`
- **AND** `top_distance` is strictly less than `0.35`
- **THEN** `relevant_documents` is populated with all retrieved `documents`
- **AND** downstream grading is bypassed.

#### Scenario: Turbo mode retrieval
- **WHEN** `mode` is `"turbo"`
- **THEN** `relevant_documents` is populated with all retrieved `documents`.
