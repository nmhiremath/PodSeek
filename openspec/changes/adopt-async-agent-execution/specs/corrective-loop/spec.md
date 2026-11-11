# Spec Delta

## ADDED Requirements

### Requirement: Asynchronous Node Execution
The system SHALL execute state machine nodes (`retrieve`, `grade_documents`, `rewrite_query`, `generate`) as asynchronous coroutines, delegating synchronous ChromaDB operations to background worker threads via `asyncio.to_thread`.

#### Scenario: Asynchronous document retrieval
- **WHEN** the `retrieve` node executes
- **THEN** semantic similarity querying of ChromaDB runs inside `asyncio.to_thread`
- **AND** retrieved chunks are returned in an updated `AgentState`.

#### Scenario: Asynchronous LLM node execution
- **WHEN** `grade_documents`, `rewrite_query`, or `generate` executes
- **THEN** the underlying chat model is invoked via `ainvoke()` or `astream()`.
