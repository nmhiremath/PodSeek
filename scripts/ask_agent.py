"""CLI runner to test the LangGraph Corrective RAG agent with real queries.

Run:  python -m scripts.ask_agent "What causes a dopamine crash and how do I prevent it?"
"""

import sys

from app.agent.graph import corrective_rag_agent
from app.agent.state import AgentState
from app.observability import configure_tracing, trace_config

configure_tracing()

if len(sys.argv) < 2:
    query = "What causes a dopamine crash and how do I prevent it?"
else:
    query = " ".join(sys.argv[1:])

print(f"User Query: {query!r}\n")
print("Executing LangGraph Corrective RAG workflow...\n")

initial_state: AgentState = {
    "question": query,
    "documents": [],
    "relevant_documents": [],
    "rewrite_count": 0,
    "generation": "",
}

final_answer = ""

# Stream node execution events so we can watch the state machine in real-time
for event in corrective_rag_agent.stream(initial_state, config=trace_config("cli")):
    for node_name, node_output in event.items():
        print(f"--> [Node: {node_name}]")
        if node_name == "retrieve":
            docs = node_output.get("documents", [])
            print(f"    Fetched {len(docs)} chunks from ChromaDB.")
        elif node_name == "grade_documents":
            rel = node_output.get("relevant_documents", [])
            print(f"    Evaluated chunks: {len(rel)} passed relevance grading.")
        elif node_name == "rewrite_query":
            new_q = node_output.get("question", "")
            count = node_output.get("rewrite_count", 0)
            print(f"    [Fallback] Rewrote query ({count}): {new_q!r}")
        elif node_name == "generate":
            final_answer = node_output.get("generation", "")
            print("    Answer generated.")
        print()
print("=" * 60)
print("FINAL ANSWER WITH CITATIONS:")
print("=" * 60)
print(final_answer)
print("=" * 60)
