# Proposal: Adopt Async Agent Execution

## Why

Currently, `/ask` and `/ask/stream` execute the LangGraph Corrective RAG agent synchronously. While moving streaming execution into Starlette's worker threadpool (via `fix/stream-blocking`) removes stalls on the primary asyncio event loop, it caps overall concurrency at the threadpool worker limit and ties up an entire OS thread per active stream. On memory-constrained hosting (such as Render's 512 MB single-instance container), thread-per-stream execution increases memory overhead and contention during concurrent requests.

Migrating to end-to-end native asynchronous execution allows concurrent streaming requests to share the asyncio event loop efficiently without dedicated OS worker threads, reduces memory pressure, and enables immediate request cancellation when clients disconnect.

## What Changes

- Refactor LangGraph state graph nodes (`retrieve`, `grade_documents`, `rewrite_query`, `generate`) to native `async def` coroutines.
- Use `ainvoke` and `astream` on underlying chat models and compiled graphs.
- Offload synchronous ChromaDB SQLite queries in `retrieve` to worker threads via `asyncio.to_thread`.
- Expose native async endpoint handlers:
  - `POST /ask` uses `await corrective_rag_agent.ainvoke(...)`.
  - `POST /ask/stream` uses an `async def` SSE event generator consuming `corrective_rag_agent.astream(...)`.
- Update UI clients (`InProcessClient` and `RemoteClient` with `httpx.AsyncClient`) to support asynchronous question and event generation.
- Implement streaming connection cancellation: when an SSE client disconnects mid-stream, catch `asyncio.CancelledError`, immediately abort in-flight graph execution, and record the trace outcome as `aborted`.
- Preserve the root `@traceable(name="podseek_ask", run_type="chain")` span, PII masking, and cached outcome reporting across asynchronous invocations.

## Out of Scope

- Changing the LangGraph state machine topology, node routing transitions, or edge definitions.
- Modifying the three execution modes (`turbo`, `balanced`, `rigorous`) or confidence distance thresholds.
- Altering prompt templates or document grading heuristic logic.

## Capabilities

### Modified Capabilities
- `streaming-api`: Update `/ask` and `/ask/stream` requirements to mandate native asynchronous execution and client-disconnect cancellation.
- `corrective-loop`: Update node execution contracts to asynchronous coroutines and ChromaDB thread offloading.

## Impact

- **Backend:** `app/agent/nodes.py`, `app/agent/graph.py`, `app/api/routes.py`, `app/observability.py`.
- **UI:** `ui/client.py`, `ui/app.py`.
- **Testing:** `tests/test_api.py`, `tests/test_agent.py`, `tests/test_observability.py`.
- **Documentation:** Architectural decision record, streaming design doc, reliability design doc.
