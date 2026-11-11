# Capability Specification: Observability

## Purpose
The observability capability provides opt-in, telemetry-safe tracing integration with LangSmith alongside real-time Server-Sent Events workflow inspection, preventing accidental telemetry emission during development and testing.

## Requirements

### Requirement: Strict Opt-In LangSmith Tracing
The system SHALL require explicit, dual-key opt-in before enabling LangSmith tracing, forcing tracing off whenever credentials are incomplete.

#### Scenario: Tracing disabled when credentials missing
- **WHEN** `LANGCHAIN_TRACING_V2` is unset or `LANGCHAIN_API_KEY` is empty
- **THEN** `configure_tracing()` forces `os.environ["LANGCHAIN_TRACING_V2"] = "false"`
- **AND** returns `False`
- **AND** no external trace telemetry is emitted.

#### Scenario: Tracing enabled with explicit key
- **WHEN** `LANGCHAIN_TRACING_V2` is set to `"true"`
- **AND** `LANGCHAIN_API_KEY` contains a non-empty key
- **THEN** `configure_tracing()` sets `LANGCHAIN_PROJECT` (default: `"podseek"`)
- **AND** returns `True`.

### Requirement: Workflow Trace Configuration
The system SHALL inject contextual run names, tags, and path metadata into LangGraph invocations via `trace_config()`.

#### Scenario: Tracing an ingest operation
- **WHEN** `trace_config("/ingest")` is called
- **THEN** a `RunnableConfig` is returned with `run_name="podseek_ingest"`, `tags=["podseek", "crag"]`, and `metadata={"path": "/ingest"}`.

#### Scenario: Tracing a question query
- **WHEN** `trace_config("/ask")` is called
- **THEN** a `RunnableConfig` is returned with `run_name="podseek_ask"`, `tags=["podseek", "crag"]`, and `metadata={"path": "/ask"}`.
