"""State definition for the Corrective RAG LangGraph agent."""

from typing import Literal, Required

from langchain_core.documents import Document
from typing_extensions import TypedDict


class AgentState(TypedDict, total=False):
    """The central state of our podcast RAG agent.

    Each node in LangGraph receives this state dictionary and
    returns a dictionary updating one or more of these keys.
    """

    # The active question (original or rewritten)
    question: Required[str]

    # Raw chunks retrieved from ChromaDB
    documents: list[Document]

    # Filtered chunks that passed the relevance grader
    relevant_documents: list[Document]

    # Loop circuit-breaker: incremented each time query is rewritten
    rewrite_count: int

    # Final answer generated with timestamp citations
    generation: str

    # Performance / execution mode: 'turbo', 'balanced', or 'rigorous'
    mode: Literal["turbo", "balanced", "rigorous"]

    # Cosine distance of the top retrieved chunk from vector search
    top_distance: float

    # Whether an exact substring/quote match was detected
    is_exact_match: bool

    # Whether the final answer is a refusal
    is_refusal: bool

    # Execution latency in milliseconds
    latency_ms: float
