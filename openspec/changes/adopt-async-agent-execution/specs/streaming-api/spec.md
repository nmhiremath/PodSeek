# Spec Delta

## MODIFIED Requirements

### Requirement: Synchronous Ask Endpoint with QA Caching
The system SHALL serve `POST /ask` asynchronously accepting an `AskRequest` and returning an `AskResponse` with citations, rewrite counts, and execution latency without blocking worker threads.

#### Scenario: Answering a question from QA cache
- **WHEN** a client sends `POST /ask` with a previously cached question and mode
- **THEN** the server returns the cached answer and structured citations immediately with measured lookup latency.

#### Scenario: Answering a question via agent invocation
- **WHEN** a client sends `POST /ask` and no cache entry matches
- **THEN** `await corrective_rag_agent.ainvoke()` executes the CRAG workflow asynchronously
- **AND** structured `Citation` objects are constructed from `relevant_documents`
- **AND** the result is cached in `data/raw/qa_cache.json` if answerable
- **AND** `AskResponse` is returned containing the answer, citations, rewrites, and latency.

### Requirement: Real-Time SSE Streaming Endpoint
The system SHALL serve `POST /ask/stream` returning a `text/event-stream` response with an asynchronous JSON-encoded event generator yielding state transitions and token deltas.

#### Scenario: Emitting node transition and token delta frames
- **WHEN** a client opens an SSE connection via `POST /ask/stream`
- **THEN** the server iterates `corrective_rag_agent.astream()` via an async generator yielding unnamed frames formatted strictly as `data: <json>\n\n`
- **AND** node frames include `node` names (`retrieve`, `grade_documents`, `rewrite_query`, `generate`)
- **AND** token frames include `{"node": "generate", "delta": "<token>"}`
- **AND** no `event:` field and no `[DONE]` sentinel string are emitted.

## ADDED Requirements

### Requirement: Streaming Connection Cancellation
The system SHALL detect client disconnections during active streaming and cancel underlying LangGraph asynchronous tasks immediately.

#### Scenario: Client disconnect during streaming
- **WHEN** an HTTP client disconnects before stream completion
- **THEN** an `asyncio.CancelledError` is caught
- **AND** graph execution halts immediately
- **AND** the outcome metadata is marked as `aborted`.
