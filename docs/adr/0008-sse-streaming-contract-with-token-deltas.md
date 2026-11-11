# 8. Server-Sent Events (SSE) Streaming Contract with Token Deltas

> Recorded retroactively on 2026-11-10; decision originally made in commit `bfe747c` and documentation corrected in `d4c0068`.

## Status
Accepted

## Context
A stateful Corrective RAG workflow takes several seconds to execute when retrieval, grading, and generation run in sequence. In a non-streaming UI, the user faces a blank screen and perceived latency of 10–20 seconds. Streaming is essential both to provide real-time token feedback during synthesis and to update the frontend workflow spotlight diagram as nodes execute.

## Decision
Implement a single unified event generator (`iter_agent_events` in `app/api/routes.py`) exposed via `POST /ask/stream`. The stream strictly follows the Server-Sent Events standard using unnamed `data: <json>\n\n` frames. The stream carries two distinct kinds of JSON payloads:
1. **Node State Transitions:** `{"node": "<node_name>", ...}` emitted as each graph step completes (e.g. `retrieve`, `grade_documents`, `rewrite_query`, `generate`), passing structured citations, distances, and rewrite counters.
2. **Token Deltas:** `{"node": "generate", "delta": "<token>"}` emitted as tokens are streamed from the LLM via LangGraph's `get_stream_writer()`.

The stream does NOT use custom `event:` lines and emits NO `[DONE]` sentinel string; stream completion is signaled naturally by closing the HTTP SSE connection.

## Alternatives Considered
1. **WebSockets:** Establish bidirectional WebSocket connections. Rejected because communication is strictly unidirectional (client submits question, server streams events) and WebSockets add proxy buffering and reconnection complexities on cloud platforms like Render.
2. **Token-Only Streaming:** Stream raw text chunks only. Rejected because the UI requires structured state updates to spotlight flowchart nodes and render citations in separate panels.
3. **Double Stream (Two Endpoints):** One endpoint for telemetry and another for tokens. Rejected to avoid race conditions and synchronization complexity.

## Consequences
### Good
- Single unified stream powers both the Gradio Bento Studio UI and external HTTP API consumers.
- Real-time token streaming gives immediate visual feedback, significantly lowering perceived latency.
- Frontend SVG flowchart smoothly transitions focus from `Retrieve` -> `Grade` -> `Generate` in lockstep with server execution.

### Bad
- Consumers must parse the JSON payload on every line to distinguish node updates from token deltas.
- If intermediate network proxies buffer SSE chunks, streaming benefits can degrade to batch delivery unless `X-Accel-Buffering: no` or flush headers are respected.

## Evidence
- `app/api/routes.py`: `iter_agent_events()` and `stream_question()`.
- `ui/client.py`: `parse_sse_chunk()`.
- Git commits: `bfe747c`, `d4c0068`.
