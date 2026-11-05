"""LangGraph workflow definition for Corrective RAG (Self-RAG).

Graph Flow:
START -> retrieve -> grade_documents -> [conditional_edge]
                                           |-> (relevant docs exist OR max rewrites reached) -> generate -> END
                                           |-> (NO relevant docs AND rewrites < max) ----------> rewrite_query -> retrieve
"""

from typing import Any, Literal, cast

from langgraph.graph import END, START, StateGraph
from langgraph.graph.state import CompiledStateGraph

from app.agent.nodes import generate, grade_documents, retrieve, rewrite_query
from app.agent.state import AgentState

# Maximum query rewrites allowed before giving up
MAX_REWRITES = 2


def route_after_retrieve(state: AgentState) -> Literal["generate", "grade_documents"]:
    """Conditional router after retrieve: Turbo mode, exact quote match, or high-confidence Balanced mode bypasses grading."""
    mode = state.get("mode", "balanced")
    top_dist = float(state.get("top_distance") or 1.0)
    is_exact = bool(state.get("is_exact_match"))

    # In Turbo mode, exact quote match, or high-confidence Balanced mode (< 0.35), jump straight to Generate!
    if mode == "turbo" or is_exact or (mode == "balanced" and top_dist < 0.35):
        return "generate"

    return "grade_documents"


def decide_to_generate(state: AgentState) -> Literal["generate", "rewrite_query"]:
    """Conditional router: checks if relevant chunks exist or if retry limit is reached."""
    relevant_docs = state.get("relevant_documents", [])
    rewrite_count = state.get("rewrite_count", 0)
    mode = state.get("mode", "balanced")

    # Happy path: we found relevant chunks -> generate answer
    if relevant_docs:
        return "generate"

    # Mode-based max rewrites limit:
    # Turbo: 0 retries (immediate refusal)
    # Balanced: 1 retry
    # Rigorous: 2 retries (MAX_REWRITES)
    max_retries = 0 if mode == "turbo" else (1 if mode == "balanced" else MAX_REWRITES)

    # Circuit breaker: max retries reached -> generate with refusal message
    if rewrite_count >= max_retries:
        return "generate"

    # Correction path: no relevant chunks yet -> rewrite query and retry retrieval
    return "rewrite_query"


def build_graph() -> CompiledStateGraph:
    """Construct and compile the Corrective RAG workflow."""
    workflow = StateGraph(cast(Any, AgentState))

    # 1. Register Nodes
    workflow.add_node("retrieve", retrieve)
    workflow.add_node("grade_documents", grade_documents)
    workflow.add_node("rewrite_query", rewrite_query)
    workflow.add_node("generate", generate)

    # 2. Add Fixed Edge from START to retrieve
    workflow.add_edge(START, "retrieve")

    # 3. Add Conditional Edge from retrieve (Turbo / High-confidence Balanced fast-path bypass)
    workflow.add_conditional_edges(
        "retrieve",
        route_after_retrieve,
        {
            "generate": "generate",
            "grade_documents": "grade_documents",
        },
    )

    # 4. Add Conditional Edge from grade_documents
    workflow.add_conditional_edges(
        "grade_documents",
        decide_to_generate,
        {
            "generate": "generate",
            "rewrite_query": "rewrite_query",
        },
    )

    # 5. Loop back from rewrite_query to retrieve
    workflow.add_edge("rewrite_query", "retrieve")

    # 6. Finish at END after generating
    workflow.add_edge("generate", END)

    return workflow.compile()


# Pre-compiled singleton instance ready to invoke
corrective_rag_agent = build_graph()
