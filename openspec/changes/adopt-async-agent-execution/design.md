# Design: Adopt Async Agent Execution

## Context

See `proposal.md` for background. PodSeek is hosted on a single 512 MB container running both the FastAPI backend and Gradio Bento Studio interface. In synchronous execution mode, each streaming client consumes a thread from the threadpool for the duration of transcript retrieval, document grading, query rewriting, and LLM token generation. Native async execution unifies the runtime under FastAPI's asyncio event loop.

## Goals / Non-Goals

**Goals:**
- Provide true non-blocking asynchronous execution end-to-end for both `POST /ask` and `POST /ask/stream`.
- Free OS threadpool threads during I/O waits (network calls to LLM providers and streaming token delivery).
- Automatically abort active graph runs when a client disconnects during SSE streaming.
- Retain identical telemetry metadata (`outcome`, `mode`, `cached`, `rewrites`) and `@traceable` PII anonymization.
- Support offline unit testing with async test harnesses (`anyio` or `asyncio`).

**Non-Goals:**
- Replacing ChromaDB with an async vector database engine (ChromaDB has no native async client; `asyncio.to_thread` provides clean isolation).
- Altering the Corrective RAG routing heuristics, mode circuit breakers, or prompt contents.
- Implementing distributed background task queues (e.g. Celery).

## Decisions

### 1. Asynchronous Graph Nodes and Chat Model Invocations
- **Decision:** Define `retrieve`, `grade_documents`, `rewrite_query`, and `generate` as `async def` functions. Use `await model.ainvoke(...)` for grading, rewriting, and summarization, and `model.astream(...)` for answer generation deltas.
- **Rationale:** LangGraph natively supports compiling graphs with async nodes, enabling `agent.ainvoke()` and `agent.astream()`.

### 2. Offloading Synchronous ChromaDB Queries via `asyncio.to_thread`
- **Decision:** Wrap ChromaDB vector collection searches (`collection.query(...)`) inside `await asyncio.to_thread(...)` within the `retrieve` node.
- **Rationale:** ChromaDB's Python client does not provide a native asyncio API. Running SQLite vector similarity searches in `asyncio.to_thread` prevents vector distance math from blocking the asyncio event loop while avoiding external database dependencies.

### 3. Native Async API Handlers and SSE Streaming
- **Decision:**
  - `POST /ask` defined as `async def ask_question(...)` awaiting `_ask_traced(...)` with `await corrective_rag_agent.ainvoke(...)`.
  - `POST /ask/stream` defined as `async def stream_question(...)` returning a `StreamingResponse` whose content is an `async def event_generator()` yielding Server-Sent Events from `corrective_rag_agent.astream(...)`.
- **Rationale:** Direct async generators allow Starlette to push SSE frames directly to the socket without threadpool handoffs.

### 4. Client Disconnect Detection and Graph Cancellation
- **Decision:** In `stream_question`, listen for client disconnects (via `request.is_disconnected()`) and wrap graph iteration with `asyncio.CancelledError` handling. Upon cancellation, abort active LLM tasks and set `outcome = "aborted"` in trace metadata.
- **Rationale:** When users close the browser tab or hit "Stop", ongoing token generation should cease immediately to conserve inference quota.

### 5. Asynchronous Client Adapters
- **Decision:**
  - `InProcessClient` directly awaits the async route handlers or consumes their async generators.
  - `RemoteClient` migrates from `httpx.Client` to `httpx.AsyncClient` for streaming and question queries.
  - Gradio UI generator functions in `ui/app.py` iterate the async generators natively using `async for`.
- **Rationale:** Gradio 5 natively supports `async def` event listener generators on the event loop.

### 6. Tracing Parity on Async Callables
- **Decision:** LangSmith's `@traceable` decorator natively wraps both sync and async functions. The `_ask_traced` helper will become `async def _ask_traced(...)` returning `(response, outcome)`, preserving `process_outputs` and run tree metadata tagging.

## Alternatives Considered

1. **Retain Sync Execution in Starlette Threadpool:**
   - *Pros:* Simple code, no async refactoring.
   - *Cons:* Thread allocation scales linearly with concurrent streams ($O(N)$ threads), risking thread exhaustion and higher stack memory usage on 512 MB instances.
2. **ProcessPoolExecutor Multi-Processing:**
   - *Pros:* Isolates CPU-bound vector operations across processes.
   - *Cons:* Memory overhead of multiple Python processes exceeds Render's 512 MB memory limit; SQLite and ChromaDB multi-process locks are fragile.

## Risks / Trade-offs

- **[Risk: Provider SDK Async Inconsistencies]** → *Mitigation:* `langchain-google-genai` and `langchain-openai` both expose battle-tested `ainvoke`/`astream` methods adhering to LangChain's Runnable interface.
- **[Risk: Test Suite Complexity]** → *Mitigation:* Pytest runs offline tests using `anyio` or `asyncio.run()`, maintaining 100% offline isolation without live network sockets.
- **[Risk: Gradio Event Loop Blocking]** → *Mitigation:* When `PODSEEK_UI_MODE=inprocess`, Gradio and FastAPI share the same event loop. Native async generators yield control between tokens, keeping UI interactions responsive.
