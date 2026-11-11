# Spec Delta

## MODIFIED Requirements

### Requirement: Strict Opt-In LangSmith Tracing
The system SHALL require explicit opt-in across four environment variables (`LANGSMITH_TRACING`, `LANGSMITH_API_KEY`, `LANGSMITH_AGENT_ID`, and `LANGSMITH_AGENT_ENVIRONMENT`) before enabling LangSmith tracing, forcing tracing off and purging conflicting project variables whenever credentials or agent addresses are incomplete.

#### Scenario: Tracing disabled when credentials missing
- **WHEN** `LANGSMITH_TRACING` is unset or `LANGSMITH_API_KEY`, `LANGSMITH_AGENT_ID`, or `LANGSMITH_AGENT_ENVIRONMENT` is missing
- **THEN** `configure_tracing()` forces `LANGSMITH_TRACING="false"` and `LANGCHAIN_TRACING_V2="false"`
- **AND** returns `False`
- **AND** no external trace telemetry is emitted.

#### Scenario: Tracing enabled with explicit key
- **WHEN** `LANGSMITH_TRACING` is set to `"true"` (or `"1"`, `"yes"`)
- **AND** `LANGSMITH_API_KEY` contains a non-empty key
- **AND** both `LANGSMITH_AGENT_ID` and `LANGSMITH_AGENT_ENVIRONMENT` are set
- **THEN** `configure_tracing()` writes `LANGSMITH_TRACING="true"`, deletes `LANGCHAIN_TRACING_V2`, and removes `LANGSMITH_PROJECT`, `LANGCHAIN_PROJECT`, and `LANGCHAIN_SESSION`
- **AND** returns `True`.

### Requirement: Workflow Trace Configuration
The system SHALL inject contextual run names, tags, and path metadata into LangGraph invocations via `trace_config()` and wrap question workflows under an anonymized root traceable chain.

#### Scenario: Tracing an ingest operation
- **WHEN** `trace_config("/ingest")` is called
- **THEN** a `RunnableConfig` is returned with `run_name="podseek_ingest"`, `tags=["podseek", "crag"]`, and `metadata={"path": "/ingest", "ui_mode": "remote"}`.

#### Scenario: Tracing a question query
- **WHEN** `trace_config("/ask", mode="balanced")` is called
- **THEN** a `RunnableConfig` is returned with `run_name="crag_graph"`, `tags=["podseek", "crag", "balanced"]`, and `metadata={"path": "/ask", "mode": "balanced", "ui_mode": "remote"}`.

#### Scenario: Root traceable execution with PII anonymization
- **WHEN** `ask_question` or `iter_agent_events` is executed with tracing enabled
- **THEN** the execution runs within a root `@traceable(name="podseek_ask", run_type="chain")` context
- **AND** an anonymizer masks email addresses and telephone numbers in trace payloads.
