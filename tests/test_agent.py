"""Tests for LangGraph agent structure and routing logic."""

from langchain_core.documents import Document

from app.agent.graph import MAX_REWRITES, build_graph, decide_to_generate, route_after_retrieve
from app.agent.state import AgentState


def test_graph_structure():
    """Verify LangGraph compiles and contains all 4 expected nodes."""
    graph = build_graph()
    node_names = set(graph.nodes.keys())
    expected = {"retrieve", "grade_documents", "rewrite_query", "generate"}
    assert expected.issubset(node_names)


def test_router_routes_to_generate_when_docs_present():
    state: AgentState = {
        "question": "test",
        "documents": [],
        "relevant_documents": [Document(page_content="relevant text")],
        "rewrite_count": 0,
        "generation": "",
    }
    decision = decide_to_generate(state)
    assert decision == "generate"


def test_router_routes_to_rewrite_when_no_relevant_docs():
    state: AgentState = {
        "question": "test",
        "documents": [],
        "relevant_documents": [],
        "rewrite_count": 0,
        "generation": "",
    }
    decision = decide_to_generate(state)
    assert decision == "rewrite_query"


def test_router_hits_circuit_breaker_after_max_rewrites():
    state: AgentState = {
        "question": "test",
        "documents": [],
        "relevant_documents": [],
        "rewrite_count": MAX_REWRITES,
        "generation": "",
    }
    decision = decide_to_generate(state)
    assert decision == "generate"


def test_route_after_retrieve_turbo_bypasses_to_generate():
    state: AgentState = {
        "question": "test",
        "mode": "turbo",
        "top_distance": 0.8,
        "is_exact_match": False,
    }
    assert route_after_retrieve(state) == "generate"


def test_route_after_retrieve_exact_match_bypasses_to_generate():
    state: AgentState = {
        "question": "test",
        "mode": "rigorous",
        "top_distance": 0.9,
        "is_exact_match": True,
    }
    assert route_after_retrieve(state) == "generate"


def test_route_after_retrieve_balanced_threshold_fast_path():
    # Distance < 0.35 -> bypasses straight to generate
    state_high_conf: AgentState = {
        "question": "test",
        "mode": "balanced",
        "top_distance": 0.22,
        "is_exact_match": False,
    }
    assert route_after_retrieve(state_high_conf) == "generate"

    # Distance >= 0.35 -> routes to grade_documents
    state_ambiguous: AgentState = {
        "question": "test",
        "mode": "balanced",
        "top_distance": 0.45,
        "is_exact_match": False,
    }
    assert route_after_retrieve(state_ambiguous) == "grade_documents"


def test_route_after_retrieve_rigorous_always_grades():
    state: AgentState = {
        "question": "test",
        "mode": "rigorous",
        "top_distance": 0.20,
        "is_exact_match": False,
    }
    assert route_after_retrieve(state) == "grade_documents"


def test_turbo_mode_immediate_circuit_breaker():
    state: AgentState = {
        "question": "test",
        "mode": "turbo",
        "relevant_documents": [],
        "rewrite_count": 0,
    }
    # In turbo mode, 0 rewrites are permitted -> immediately routes to generate (refusal)
    assert decide_to_generate(state) == "generate"


def test_generate_preserves_relevant_documents_for_turbo_citations(monkeypatch):
    from unittest.mock import MagicMock

    from app.agent.nodes import generate

    mock_llm = MagicMock()
    mock_reply = MagicMock()
    mock_reply.content = "Light exposure boosts dopamine [00:20:45]."
    mock_llm.invoke.return_value = mock_reply

    monkeypatch.setattr("app.agent.nodes._get_chat_llm", lambda **kwargs: mock_llm)

    doc = Document(page_content="Morning sunlight", metadata={"timestamp": "00:20:45", "episode_id": "QmOF0crdyRU"})
    state: AgentState = {
        "question": "When should I view sunlight?",
        "mode": "turbo",
        "documents": [doc],
        "relevant_documents": [doc],
    }
    result = generate(state)
    assert "generation" in result
    assert result.get("relevant_documents") == [doc]
