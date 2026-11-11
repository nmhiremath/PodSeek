# Capability Specification: Streaming API

## Purpose
The streaming API capability exposes HTTP REST and Server-Sent Events (SSE) endpoints via FastAPI for synchronous question answering, real-time node and token streaming, episode catalog listing, and health checks.

## Requirements

### Requirement: Synchronous Ask Endpoint with QA Caching
The system SHALL serve `POST /ask` accepting an `AskRequest` and returning an `AskResponse` with citations, rewrite counts, and execution latency.

#### Scenario: Answering a question from QA cache
- **WHEN** a client sends `POST /ask` with a previously cached question and mode
- **THEN** the server returns the cached answer and structured citations immediately with measured lookup latency.

#### Scenario: Answering a question via agent invocation
- **WHEN** a client sends `POST /ask` and no cache entry matches
- **THEN** `corrective_rag_agent.invoke()` executes the CRAG workflow
- **AND** structured `Citation` objects are constructed from `relevant_documents`
- **AND** the result is cached in `data/raw/qa_cache.json` if answerable
- **AND** `AskResponse` is returned containing the answer, citations, rewrites, and latency.

### Requirement: Real-Time SSE Streaming Endpoint
The system SHALL serve `POST /ask/stream` returning a `text/event-stream` response with JSON-encoded data frames for workflow node state transitions and token deltas.

#### Scenario: Emitting node transition and token delta frames
- **WHEN** a client opens an SSE connection via `POST /ask/stream`
- **THEN** the server yields unnamed frames formatted strictly as `data: <json>\n\n`
- **AND** node frames include `node` names (`retrieve`, `grade_documents`, `rewrite_query`, `generate`)
- **AND** token frames include `{"node": "generate", "delta": "<token>"}`
- **AND** no `event:` field and no `[DONE]` sentinel string are emitted.

### Requirement: Episode Catalog and Health Endpoints
The system SHALL expose `GET /episodes` to inspect indexed podcast episodes and `GET /health` to verify system and vector store status.

#### Scenario: Listing indexed episodes
- **WHEN** a client requests `GET /episodes`
- **THEN** the server returns a list of `EpisodeSummary` objects read from cached episode metadata files.

#### Scenario: Health check verification
- **WHEN** a client requests `GET /health`
- **THEN** the server reports `status="healthy"`, `service="podseek"`, active collection name, and total chunk count.
