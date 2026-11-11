# 2. LangGraph State Machine over a Free-Form Agent Loop

> Recorded retroactively on 2026-11-10; decision originally made in commit `a57c9ce`.

## Status
Accepted

## Context
Complex agentic workflows require iterative steps (retrieval, grading, decision branching, rewriting, and synthesis). Free-form ReAct-style agent loops rely on LLM tool-calling to decide their next step dynamically. However, in production RAG systems, free-form loops frequently suffer from non-deterministic branching, runaway token usage, infinite retries, and difficulty in providing real-time frontend telemetry.

## Decision
Use LangGraph (`StateGraph`) with a statically defined state machine and strongly typed state schema (`AgentState`). All transition paths (`route_after_retrieve`, `decide_to_generate`) are deterministic conditional edge functions executing in Python code rather than left to LLM self-direction.

## Alternatives Considered
1. **LangChain ReAct / AgentExecutor:** Let an LLM invoke tools in a while-loop. Rejected because tool selection is nondeterministic, prone to infinite loops on out-of-domain queries, and harder to bound.
2. **Hardcoded Python while-loop:** Implement a simple `while retry < 2` loop in pure Python. Rejected because it lacks standardized node checkpointing, state inspection, LangSmith trace propagation, and token streaming hooks provided by LangGraph.
3. **LlamaIndex Workflow:** Rejected to maintain tight integration with the LangChain / Google GenAI ecosystem.

## Consequences
### Good
- Completely deterministic transition guarantees: every request follows predictable graph paths.
- Typed state (`AgentState` TypedDict) ensures all nodes have clear contracts for reads and writes.
- First-class support for Server-Sent Events (SSE) telemetry and live UI spotlight rendering based on node visit events.
- Zero risk of an agent hallucinating non-existent tools or diverging from the corrective protocol.

### Bad
- Graph topology is fixed at build time; adding new capabilities requires altering code rather than prompting an agent.
- Learning curve for LangGraph compilation and streaming mechanics.

## Evidence
- `app/agent/state.py`: `AgentState` TypedDict definition.
- `app/agent/graph.py`: `StateGraph(AgentState)`, `build_graph()`, and compiled singleton `corrective_rag_agent`.
- Git commit: `a57c9ce`.
