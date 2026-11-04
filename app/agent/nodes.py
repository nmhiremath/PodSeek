"""Graph nodes for Corrective RAG: retrieve, grade, rewrite, and generate."""

from typing import Literal

from langchain_core.documents import Document
from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.prompts import ChatPromptTemplate
from pydantic import BaseModel, Field

from app.agent.state import AgentState
from app.factory import get_chat_model
from app.vectorstore import get_vectorstore


def _get_chat_llm(temperature: float = 0.0) -> BaseChatModel:
    """Helper to instantiate the active chat model configured in .env."""
    return get_chat_model(temperature=temperature)


# ==============================================================================
# Node 1: Retrieve
# ==============================================================================
def retrieve(state: AgentState) -> dict:
    """Query ChromaDB for top chunks matching the current question."""
    question = state["question"]
    vs = get_vectorstore()
    results = vs.similarity_search(query=question, k=4)
    return {"documents": results}


# ==============================================================================
# Node 2: Grade Documents (Binary Relevance Classifier)
# ==============================================================================
class GradeResult(BaseModel):
    """Pydantic schema enforcing a strict binary score from the LLM."""

    binary_score: Literal["yes", "no"] = Field(
        description="Relevance score: 'yes' if chunk is relevant to the question, 'no' otherwise."
    )


def grade_documents(state: AgentState) -> dict:
    """Evaluate each chunk to filter out irrelevant context."""
    question = state["question"]
    documents = state.get("documents", [])

    llm = _get_chat_llm(temperature=0.0)
    # Guarantee structured output parsed into GradeResult
    structured_grader = llm.with_structured_output(GradeResult)

    grader_prompt = ChatPromptTemplate.from_messages(
        [
            (
                "system",
                "You are a strict relevance grader assessing whether a podcast transcript excerpt "
                "is relevant to the user question. Return 'yes' if the excerpt contains information "
                "that helps answer the question, or 'no' if it is irrelevant.",
            ),
            (
                "human",
                "User Question:\n{question}\n\nTranscript Excerpt:\n{context}",
            ),
        ]
    )

    grader_chain = grader_prompt | structured_grader

    relevant_docs: list[Document] = []
    for doc in documents:
        try:
            res = grader_chain.invoke({"question": question, "context": doc.page_content})
            score = ""
            if isinstance(res, GradeResult):
                score = res.binary_score
            elif isinstance(res, dict):
                score = res.get("binary_score", "")
            elif hasattr(res, "binary_score"):
                score = getattr(res, "binary_score", "")

            if score.lower() == "yes":
                relevant_docs.append(doc)
        except Exception:
            # Defensive fallback: if API call hiccups, preserve chunk so recall is not lost
            relevant_docs.append(doc)

    return {"relevant_documents": relevant_docs}


# ==============================================================================
# Node 3: Rewrite Query (Fallback for zero relevant chunks)
# ==============================================================================
def rewrite_query(state: AgentState) -> dict:
    """Rephrase the question to improve semantic retrieval keywords."""
    question = state["question"]
    rewrite_count = state.get("rewrite_count", 0) + 1

    llm = _get_chat_llm(temperature=0.2)

    prompt = ChatPromptTemplate.from_messages(
        [
            (
                "system",
                "You are a search query optimizer for podcast transcripts. "
                "The initial search returned zero relevant excerpts. "
                "Rephrase the question into a direct, keyword-rich search query "
                "better suited for vector semantic retrieval. Output ONLY the new query.",
            ),
            ("human", "Original Question:\n{question}"),
        ]
    )

    chain = prompt | llm
    response = chain.invoke({"question": question})
    new_query = str(getattr(response, "text", getattr(response, "content", response))).strip()

    return {"question": new_query, "rewrite_count": rewrite_count}


# ==============================================================================
# Node 4: Generate (Final Answer with Citations)
# ==============================================================================
def generate(state: AgentState) -> dict:
    """Synthesize final answer grounded strictly in verified chunks with citations."""
    question = state["question"]
    docs = state["relevant_documents"] if "relevant_documents" in state else state.get("documents", [])

    # If even after retries we have zero relevant chunks
    if not docs:
        return {
            "generation": "I could not find any relevant information in the podcast transcripts to answer your question."
        }

    # Format each chunk with its timestamp for easy citation
    formatted_context_blocks = []
    for doc in docs:
        meta = doc.metadata
        ts = meta.get("timestamp", "00:00:00")
        title = meta.get("episode_title", "Unknown Episode")
        speaker = meta.get("speaker", "Speaker")
        formatted_context_blocks.append(f'[{title} | {speaker} @ {ts}]:\n"{doc.page_content}"')
    context_str = "\n\n".join(formatted_context_blocks)

    llm = _get_chat_llm(temperature=0.1)

    prompt = ChatPromptTemplate.from_messages(
        [
            (
                "system",
                "You are an expert AI assistant answering questions about podcast episodes. "
                "Answer the question using ONLY the transcript excerpts provided below.\n\n"
                "RULES:\n"
                "1. Ground all claims strictly in the excerpts.\n"
                "2. Cite the exact timestamp and episode title for your points (e.g. `[00:57:54]`).\n"
                "3. If the excerpts do not contain the answer, state that honestly.\n\n"
                "Excerpts:\n{context}",
            ),
            ("human", "{question}"),
        ]
    )

    chain = prompt | llm
    reply = chain.invoke({"question": question, "context": context_str})
    answer = str(getattr(reply, "text", getattr(reply, "content", reply))).strip()
    return {"generation": answer}
