# 11. Strict Opt-In LangSmith Tracing

> Recorded retroactively on 2026-11-10; decision originally made in commit `d4c0068` (PR #2).
> 2026-11-11 update: migrated to agent-based workspace addressing (`LANGSMITH_AGENT_ID` and `LANGSMITH_AGENT_ENVIRONMENT`), `LANGSMITH_TRACING` flag, and PII masking.

## Status
Accepted (2026-11-11 update: migrated to agent-based workspace addressing and PII masking)

## Context
LangChain automatically inspects environment variables and enables LangSmith telemetry whenever `LANGCHAIN_TRACING_V2=true` is set. In local development or automated CI environments where an engineer copies a `.env.example` file or sets a flag without providing a valid API key, LangChain emits noisy background errors, slows down test execution, or risks leaking evaluation trace payloads to unwanted endpoints.

## Decision
Implement a strict, multi-gate opt-in module in `app/observability.py`. `configure_tracing()` evaluates `LANGSMITH_TRACING`, `LANGSMITH_API_KEY`, `LANGSMITH_AGENT_ID`, and `LANGSMITH_AGENT_ENVIRONMENT`. Tracing is enabled if and only if:
1. `LANGSMITH_TRACING` matches `{"1", "true", "yes"}`.
2. `LANGSMITH_API_KEY` is non-empty.
3. Both `LANGSMITH_AGENT_ID` and `LANGSMITH_AGENT_ENVIRONMENT` are non-empty.

If any condition is unmet, the system explicitly forces `os.environ["LANGSMITH_TRACING"] = "false"` and `os.environ["LANGCHAIN_TRACING_V2"] = "false"`, completely silencing LangChain's telemetry hooks. Conflicting project-destination variables (`LANGSMITH_PROJECT`, `LANGCHAIN_PROJECT`, `LANGCHAIN_SESSION`) are stripped, and trace runs are routed through an anonymizing client that masks email addresses and phone numbers. The API and UI call `configure_tracing()` upon startup, and CI workflows explicitly inject `LANGSMITH_TRACING: "false"` and `LANGCHAIN_TRACING_V2: "false"`.

## Alternatives Considered
1. **Unconditional OpenTelemetry / Prometheus Exporter:** Instrument all spans via OTel. Rejected because standardizing on LangChain-native LangSmith provides deeper graph-level state inspection without adding heavy collector daemons.
2. **Leaving LangChain Default Behavior:** Allow LangChain to handle env vars natively. Rejected because unset keys produce connection warnings during offline unit testing.

## Consequences
### Good
- Zero telemetry leaks or noisy connection warnings during offline testing and CI.
- One-line activation: setting both env vars immediately produces rich, nested LangGraph traces on LangSmith.
- `trace_config()` safely injects metadata tags (`["podseek", "crag"]`) and path labels (`/ingest`, `/ask`) into graph runs without failing when tracing is off.

### Bad
- Operators who set `LANGCHAIN_TRACING_V2=true` but forget `LANGCHAIN_API_KEY` will have tracing silently forced off rather than raising an immediate configuration error.

## Evidence
- `app/observability.py`: `configure_tracing()` and `trace_config()`.
- `tests/test_observability.py`: Unit tests verifying that partial or missing credentials force tracing off.
- `.github/workflows/ci.yml`: `env: LANGCHAIN_TRACING_V2: "false"`.
- Git commit: `d4c0068`.
