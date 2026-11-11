# Capability Specification: Evaluation

## Purpose
The evaluation capability provides automated benchmark evaluation across 16 fixed questions (13 in-scope and 3 out-of-scope refusals), measuring keyword recall, citation timestamp validity, refusal adherence, and latency percentiles offline or live.

## Requirements

### Requirement: 16-Question Benchmark Suite
The system SHALL evaluate a fixed benchmark dataset (`evals/questions.json`) containing 13 domain questions with expected keywords and 3 out-of-scope questions with expected refusals.

#### Scenario: Running offline benchmark evaluation
- **WHEN** `python -m scripts.evaluate` is executed without `--live`
- **THEN** fixture answers are evaluated offline without invoking any LLM or network endpoints
- **AND** all 16 questions pass citation and keyword checks with exit code 0.

### Requirement: Citation Deep-Link and Timestamp Validation
The system SHALL verify that every citation produced contains a valid `HH:MM:SS` timestamp string and an HTTP deep link containing the parameter `?t=<seconds>`.

#### Scenario: Validating citation timestamps
- **WHEN** an answer includes citations
- **THEN** `check_citations()` validates that `timestamp` matches `^\d{2}:\d{2}:\d{2}$`
- **AND** `url` matches `^https://youtu\.be/[A-Za-z0-9_-]{11}\?t=\d+$`
- **AND** `int(start_seconds)` matches the URL timestamp integer.

### Requirement: Out-of-Scope Refusal Validation
The system SHALL verify that questions designated as out-of-scope produce zero citations.

#### Scenario: Refusal evaluation for off-topic query
- **WHEN** an off-topic question (e.g. Linux kernel, corporate board quotas, sourdough starter) is evaluated
- **AND** `expect_citations` is `false`
- **THEN** the status passes if and only if no citations are returned (`citations == []`).

### Requirement: Latency and Multi-Mode Reporting
The system SHALL measure and report p50 and p95 latency percentiles alongside keyword hit rates across Turbo, Balanced, and Rigorous modes.

#### Scenario: Live multi-mode evaluation
- **WHEN** `python -m scripts.evaluate --live --mode <mode>` is executed
- **THEN** questions are dispatched against `POST /ask`
- **AND** keyword recall, citation validity percentage, p50 latency, and p95 latency are printed in a summary table.
