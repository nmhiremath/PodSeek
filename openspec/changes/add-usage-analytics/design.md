# Design

## Context

See `proposal.md` for background and motivation. PodSeek runs on Render free tier with an embedded ChromaDB database and in-process Gradio UI. Telemetry and observability must respect user privacy, avoid storing medical/personal question contents in third-party services without permission, and never interfere with local offline testing.

## Goals / Non-Goals

**Goals:**
- Provide zero-cookie page analytics via GoatCounter without logging user questions or answers.
- Track execution outcomes (`answered`, `refused`, `cached`) across modes (`turbo`, `balanced`, `rigorous`) uniformly across in-process and remote UI modes.
- Support agent-addressed LangSmith tracing under a single `podseek` agent ID across `local` and `production` environments.
- Redact PII (email addresses and phone numbers) in LangSmith trace trees.
- Isolate pytest test runs completely so tests never emit network traces.

**Non-Goals:**
- Logging raw question queries, response bodies, or user session identifiers to GoatCounter.
- Supporting multi-tenant agent projects or concurrent project-based and agent-based LangSmith destinations simultaneously.
- Automatic installation or deployment of external tracking servers.

## Decisions

### 1. GoatCounter Event Dispatch via Gradio-Native Hidden HTML & JS Callback
- **Decision:** Use a hidden `gr.HTML` element with CSS `display: none !important;` and a Gradio `.then(..., js=...)` event callback with a companion MutationObserver fallback.
- **Rationale:** Gradio 5 event triggers do not directly expose client-side JavaScript analytics APIs from Python generators. The hidden HTML element conveys the structured `<div id="ap-analytics-tracker" data-mode="..." data-outcome="...">` payload on completion without polluting visible chat messages.
- **Alternatives Considered:**
  - *Custom frontend web component:* Introduces unnecessary complexity and build dependencies.
  - *Server-side webhook to GoatCounter:* Leaks server IP, requires outbound HTTP requests on critical path, and loses client referrer context.

### 2. LangSmith Agent-Based Addressing with Conflicting Variable Cleansing
- **Decision:** Route traces to `LANGSMITH_AGENT_ID=podseek` and `LANGSMITH_AGENT_ENVIRONMENT` while strictly popping `LANGSMITH_PROJECT`, `LANGCHAIN_PROJECT`, and `LANGCHAIN_SESSION`.
- **Rationale:** LangSmith agent-based workspaces reject traces when legacy project destination variables are concurrently populated.
- **Alternatives Considered:**
  - *Keep project-based tracing:* Conflicts with agent-based workspace schemas and lacks multi-environment support under unified agent metrics.

### 3. Masking PII via LangSmith Client Anonymizer
- **Decision:** Construct a dedicated LangSmith `Client` with `create_anonymizer` targeting email and phone patterns, wrapped around the `@traceable` ask execution.
- **Rationale:** Podcast questions frequently contain health and personal details; masking standard PII prevents accidental exposure in shared agent traces while leaving inputs legible to operators unless `LANGSMITH_HIDE_INPUTS` is set.
- **Alternatives Considered:**
  - *Full input/output blanking by default:* Strips all visibility from debug traces, making agent troubleshooting impossible.

### 4. Pytest Test Isolation via Top-Level Environment and Context Fixture
- **Decision:** Set `LANGSMITH_TRACING=false` and `LANGCHAIN_TRACING_V2=false` at module top-level in `tests/conftest.py` and run tests inside an autouse `tracing_context(enabled=False)` fixture.
- **Rationale:** `load_dotenv()` in application modules does not override preexisting environment variables, ensuring developer `.env` files never activate tracing during automated test suites.

## Risks / Trade-offs

- **[Risk: Browser Adblockers block GoatCounter script]** → *Mitigation:* GoatCounter script loads asynchronously; UI logic uses optional chaining (`window.goatcounter?.count`) and gracefully no-ops if blocked.
- **[Risk: Stale SDK Environment Caching]** → *Mitigation:* `configure_tracing()` calls `langsmith.utils.get_env_var.cache_clear()` whenever environment variables are manipulated.
- **[Risk: Double Counting Events on UI Rerenders]** → *Mitigation:* The hidden DOM element sets `data-counted="true"` immediately upon firing to prevent duplicate counts.
