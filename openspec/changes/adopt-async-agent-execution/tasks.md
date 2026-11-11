# Tasks

## 1. Asynchronous Graph Nodes & State Machine

- [ ] 1.1 In `app/agent/nodes.py`, convert `retrieve` to `async def` and wrap ChromaDB vector queries in `asyncio.to_thread`.
- [ ] 1.2 In `app/agent/nodes.py`, convert `grade_documents`, `rewrite_query`, and `generate` to `async def` using `await model.ainvoke(...)` and `model.astream(...)`.
- [ ] 1.3 In `app/agent/graph.py`, verify compiled `corrective_rag_agent` supports `ainvoke` and `astream`.

## 2. Asynchronous API Endpoints & Streaming

- [ ] 2.1 In `app/api/routes.py`, convert `_ask_traced` and `ask_question` to `async def` utilizing `await corrective_rag_agent.ainvoke(...)`.
- [ ] 2.2 In `app/api/routes.py`, convert `iter_agent_events` to an async generator (`async def`) consuming `corrective_rag_agent.astream(...)`.
- [ ] 2.3 In `app/api/routes.py`, convert `stream_question` to return an async generator SSE response with client disconnect cancellation handling (`asyncio.CancelledError`).

## 3. UI Client Async Support

- [ ] 3.1 In `ui/client.py`, update `InProcessClient` to support async invocation and streaming event consumption.
- [ ] 3.2 In `ui/client.py`, update `RemoteClient` to use `httpx.AsyncClient` for non-blocking HTTP and SSE requests.
- [ ] 3.3 In `ui/app.py`, wire Gradio event generators to consume async client iterators with `async for`.

## 4. Test Suite & Verification

- [ ] 4.1 In `tests/test_api.py`, add concurrency test asserting two simultaneous `POST /ask/stream` calls complete in ~1x the stub delay.
- [ ] 4.2 In `tests/test_api.py`, add test verifying client disconnection cancels the graph run and tags trace outcome as `aborted`.
- [ ] 4.3 In `tests/test_observability.py`, verify cached `/ask` outcome `outputs["outcome"] == "cached"` is preserved under async `@traceable`.
- [ ] 4.4 Verify all unit tests continue executing completely offline without network access.

## 5. Documentation & Architectural Decision Records

- [ ] 5.1 Author ADR `docs/adr/0015-native-async-agent-execution.md` recording motivation, threadpool vs event-loop trade-offs, and memory implications.
- [ ] 5.2 Update `docs/design/observability-and-tracing.md` and `docs/design/reliability-and-failure-modes.md` to reflect async execution and cancellation handling.
- [ ] 5.3 Add release notes entry in `CHANGELOG.md` upon completion of implementation.
