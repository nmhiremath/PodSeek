# Proposal

## Why

PodSeek needs privacy-first usage analytics and agent-level observability to monitor system quality without logging user questions. Cookie-free page analytics track mode and outcome distributions, while agent-addressed LangSmith tracing captures grounded execution traces with PII anonymization.

## What Changes

- Add optional GoatCounter page script injection in `render_head_meta_html()` gated on `GOATCOUNTER_CODE`.
- Emit lightweight GoatCounter outcome events (`ask/<mode>/<outcome>`) for completed questions (`answered`, `refused`, `cached`) without questions, answers, or user identifiers.
- Transition LangSmith tracing from project-based addressing to agent-based workspace addressing (`LANGSMITH_AGENT_ID=podseek` and `LANGSMITH_AGENT_ENVIRONMENT`).
- Enforce strict 4-variable gating for LangSmith tracing, clearing conflicting project destination variables and sanitizing environment caches.
- Wrap question ask pipelines (`ask_question` and `iter_agent_events`) under a root `@traceable(name="podseek_ask", run_type="chain")` run with PII masking (emails and phone numbers).
- Isolate test runs completely from trace emission via `tests/conftest.py` top-level environment overrides and autouse context disabling.
- Update documentation and deployment manifests with referendum links (`?utm_source=github-readme` in README) and privacy guarantees.

## Capabilities

### Modified Capabilities
- `observability`: Update tracing requirements for agent-addressed LangSmith tracing, four-variable gating, conflicting project environment popping, root runnable tracing, and PII anonymization.
- `studio-ui`: Add requirements for optional GoatCounter script injection and privacy-preserving outcome event dispatching.

## Impact

- **Backend:** `app/observability.py`, `app/api/routes.py`, `app/agent/nodes.py`, `app/agent/state.py`.
- **Frontend:** `ui/app.py`, `ui/components.py`, `ui/styles/theme.css`.
- **Testing:** `tests/conftest.py`, `tests/test_observability.py`, `tests/test_agent.py`, `tests/test_ui_client.py`.
- **Deployment & Config:** `render.yaml`, `requirements.txt`, `.env.example`, `README.md`.
