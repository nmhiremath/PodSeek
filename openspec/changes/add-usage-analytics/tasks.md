# Tasks

## 1. GoatCounter Page Analytics & Outcome Events

- [x] 1.1 In `ui/components.py`, inject GoatCounter script into head meta if `GOATCOUNTER_CODE` is set and valid (`^[a-z0-9-]+$`); verify with unit tests in `tests/test_ui_client.py`.
- [x] 1.2 In `app/agent/nodes.py` and `app/agent/state.py`, expose refusal and outcome detection (`answered`, `refused`, `cached`); verify with unit tests in `tests/test_agent.py`.
- [x] 1.3 In `ui/app.py`, emit GoatCounter custom event `ask/<mode>/<outcome>` on question completion via hidden tracking element and JS callback; verify no question/answer text is emitted.

## 2. Agent-Based LangSmith Tracing & Telemetry Safety

- [x] 2.1 Update `requirements.txt` to require `langsmith>=0.14.9` and verify environment installation.
- [x] 2.2 In `app/observability.py`, implement four-variable agent gating (`LANGSMITH_TRACING`, `LANGSMITH_API_KEY`, `LANGSMITH_AGENT_ID`, `LANGSMITH_AGENT_ENVIRONMENT`), pop conflicting project variables, and clear env var cache; verify with `tests/test_observability.py`.
- [x] 2.3 In `app/observability.py`, construct an anonymizing client for emails and phone numbers; verify wrapper integration.
- [x] 2.4 In `app/api/routes.py`, wrap `ask_question` and `iter_agent_events` in root `@traceable(name="podseek_ask", run_type="chain")` with metadata, tags, and QA-cache routing; verify execution tracing.
- [x] 2.5 In `ui/app.py`, invoke `configure_tracing()` explicitly during UI startup in in-process mode; verify with monkeypatch test in `tests/test_observability.py`.

## 3. Test Isolation & Runnable Naming

- [x] 3.1 Create `tests/conftest.py` setting `LANGSMITH_TRACING="false"` and `LANGCHAIN_TRACING_V2="false"` at top level, with autouse `tracing_context(enabled=False)` fixture; verify `test_tracing_is_disabled_during_tests`.
- [x] 3.2 Add explicit `.with_config(run_name=...)` names to all runnables in `app/agent/nodes.py` and `app/api/routes.py`.
- [x] 3.3 Add `wait_for_all_tracers()` in `scripts/ask_agent.py` and `scripts/evaluate.py` to flush traces before process exit.
- [x] 3.4 Update `render.yaml` with agent environment variables.

## 4. Documentation, Referrer Links & Privacy Notice

- [x] 4.1 Update demo links to `https://podseek.onrender.com/?utm_source=github-readme` in `README.md` and `https://podseek.onrender.com/?utm_source=github-repo-about` on GitHub repository homepage.
- [x] 4.2 Document agent environment variables and privacy note in `README.md` and `.env.example`.
- [x] 4.3 Update `CHANGELOG.md` with release notes for the analytics and observability updates.
- [x] 4.4 Untrack `data/raw/qa_cache.json` so cache starts empty and operates as runtime state per deploy; verify with missing cache test in `tests/test_api.py`.

## Workflow follow-up

- Archive the change after PR review and merge into main.
- Verify the archived spec deltas in `openspec/specs/`.
