"""Graph nodes for Corrective RAG: retrieve, grade, rewrite, and generate."""

import logging
import re
from typing import Literal

from langchain_core.documents import Document
from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.prompts import ChatPromptTemplate
from langgraph.config import get_stream_writer
from pydantic import BaseModel, Field

from app.agent.state import AgentState
from app.factory import get_chat_model
from app.vectorstore import get_vectorstore

logger = logging.getLogger(__name__)


def _get_chat_llm(temperature: float = 0.0) -> BaseChatModel:
    """Helper to instantiate the active chat model configured in .env."""
    return get_chat_model(temperature=temperature)


def is_refusal(answer: str) -> bool:
    """Return True if the generated answer is a refusal due to missing information."""
    lowered = (answer or "").lower()
    return (
        "could not find any relevant information" in lowered
        or "cannot find any relevant information" in lowered
        or "no relevant information" in lowered
        or "not mentioned in the" in lowered
    )


def determine_outcome(answer: str, cached: bool = False, aborted: bool = False) -> str:
    """Determine outcome status for metrics and analytics: 'cached', 'refused', or 'answered'."""
    if cached:
        return "cached"
    if aborted or is_refusal(answer):
        return "refused"
    return "answered"


# ==============================================================================
# Node 1: Retrieve (with Cosine Distance Scoring & Exact Substring Detection)
# ==============================================================================
def retrieve(state: AgentState) -> dict:
    """Query ChromaDB for top chunks matching the current question with distance scores."""
    question = state["question"]
    vs = get_vectorstore()

    # Detect exact quote search (e.g. "Sauna use of 12 minutes...")
    quote_match = re.search(r'["\']([^"\']{4,})["\']', question)
    exact_phrase = quote_match.group(1).strip() if quote_match else ""

    # similarity_search_with_score returns list[tuple[Document, float]] (cosine distance)
    results = vs.similarity_search_with_score(query=question, k=4)
    documents = [doc for doc, _ in results]
    top_dist = float(results[0][1]) if results else 1.0

    is_exact = False
    if exact_phrase:
        for i, doc in enumerate(documents):
            if exact_phrase.lower() in doc.page_content.lower():
                is_exact = True
                if i != 0:
                    matching_doc = documents.pop(i)
                    documents.insert(0, matching_doc)
                top_dist = min(top_dist, 0.08)
                break

    mode = state.get("mode", "balanced")
    out: dict = {
        "documents": documents,
        "top_distance": round(top_dist, 4),
        "is_exact_match": is_exact,
    }

    # Pre-populate relevant documents for Turbo or high-confidence Balanced modes
    if mode == "turbo" or (mode == "balanced" and top_dist < 0.35) or is_exact:
        out["relevant_documents"] = [documents[0]] if is_exact else list(documents)

    return out


# ==============================================================================
# Node 2: Grade Documents (Single-Call Batch Relevance Classifier)
# ==============================================================================
class GradeResult(BaseModel):
    """Pydantic schema enforcing a strict binary score from the LLM."""

    binary_score: Literal["yes", "no"] = Field(
        description="Relevance score: 'yes' if chunk is relevant to the question, 'no' otherwise."
    )


class BatchGradeResult(BaseModel):
    """Pydantic schema enforcing binary relevance scores for all retrieved chunks in a single LLM call."""

    binary_scores: list[Literal["yes", "no"]] = Field(
        description="List of 'yes' or 'no' relevance scores corresponding 1-to-1 with each numbered excerpt."
    )


def grade_documents(state: AgentState) -> dict:
    """Evaluate all retrieved chunks in a single batch LLM call to filter out irrelevant context."""
    question = state["question"]
    documents = state.get("documents", [])
    if not documents:
        return {"relevant_documents": []}

    mode = state.get("mode", "balanced")
    top_dist = float(state.get("top_distance") or 1.0)
    is_exact = bool(state.get("is_exact_match"))

    # Fast-path bypass for turbo mode, high-confidence balanced retrieval, or exact quote match
    if mode == "turbo" or (mode == "balanced" and top_dist < 0.35) or is_exact:
        return {"relevant_documents": [documents[0]] if is_exact else list(documents)}

    llm = _get_chat_llm(temperature=0.0)
    structured_grader = llm.with_structured_output(BatchGradeResult)

    grader_prompt = ChatPromptTemplate.from_messages(
        [
            (
                "system",
                "You are a strict relevance grader assessing whether podcast transcript excerpts "
                "are relevant to the user question. For each numbered excerpt (1 to {count}), return "
                "'yes' in binary_scores if the excerpt contains information that helps answer the question, "
                "or 'no' if it is irrelevant. Return exactly {count} scores in order.",
            ),
            (
                "human",
                "User Question:\n{question}\n\nTranscript Excerpts:\n{context}",
            ),
        ]
    )

    grader_chain = (grader_prompt | structured_grader).with_config(run_name="grade_documents_llm")
    numbered_excerpts = "\n\n".join(f"[Excerpt {i + 1}]\n{doc.page_content}" for i, doc in enumerate(documents))

    relevant_docs: list[Document] = []
    try:
        res = grader_chain.invoke({"question": question, "count": len(documents), "context": numbered_excerpts})
        scores: list[str] = []
        if isinstance(res, BatchGradeResult):
            scores = list(res.binary_scores)
        elif isinstance(res, dict):
            raw = res.get("binary_scores")
            if isinstance(raw, list):
                scores = [str(s) for s in raw]
            elif "binary_score" in res:
                scores = [str(res["binary_score"])] * len(documents)
        elif hasattr(res, "binary_scores"):
            scores = [str(s) for s in getattr(res, "binary_scores", [])]

        for i, doc in enumerate(documents):
            verdict = scores[i].lower() if i < len(scores) else "no"
            if verdict == "yes":
                relevant_docs.append(doc)
    except Exception as exc:
        # Defensive fallback: if API call hiccups, preserve chunks so recall is not lost
        logger.warning(
            "Batch relevance grading failed for question %r; falling back to ungraded chunks: %s",
            question,
            exc,
        )
        relevant_docs = list(documents)

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

    chain = (prompt | llm).with_config(run_name="rewrite_query_llm")
    response = chain.invoke({"question": question})
    new_query = str(getattr(response, "text", getattr(response, "content", response))).strip()

    return {"question": new_query, "rewrite_count": rewrite_count}


# ==============================================================================
# Node 4: Generate (Final Answer with Citations & Pinpoint Quote Formatting)
# ==============================================================================
def generate(state: AgentState) -> dict:
    """Synthesize final answer grounded strictly in verified chunks with citations."""
    question = state["question"]
    docs = state["relevant_documents"] if "relevant_documents" in state else state.get("documents", [])

    # Safe resolution of LangGraph stream writer (handles standalone unit test execution)
    try:
        writer = get_stream_writer()
    except RuntimeError as exc:
        logger.debug("LangGraph stream writer unavailable outside runtime context: %s", exc)
        writer = None

    # If even after retries we have zero relevant chunks
    if not docs:
        refusal_msg = "I could not find any relevant information in the podcast transcripts to answer your question."
        if writer:
            writer({"delta": refusal_msg})
        return {
            "generation": refusal_msg,
            "relevant_documents": [],
            "is_refusal": True,
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

    is_exact = bool(state.get("is_exact_match"))
    mode = state.get("mode", "balanced")

    # Extra guidance for exact quote lookups or Turbo mode
    pinpoint_rule = (
        "\n4. The user is asking for an exact quote, timestamp, or specific statement. Quote the relevant sentence verbatim and provide the exact timestamp citation immediately without unnecessary preamble."
        if is_exact
        else ""
    )
    turbo_refusal_rule = (
        "\n5. If the excerpts do not contain direct evidence to answer the question, reply ONLY with: 'I could not find any relevant information in the podcast transcripts to answer your question.'"
        if mode == "turbo"
        else ""
    )

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
                f"3. If the excerpts do not contain the answer, state that honestly.{pinpoint_rule}{turbo_refusal_rule}\n\n"
                "Excerpts:\n{context}",
            ),
            ("human", "{question}"),
        ]
    )

    chain = (prompt | llm).with_config(run_name="generate_answer_llm")
    full_text = ""
    try:
        for chunk in chain.stream({"question": question, "context": context_str}):
            token = str(getattr(chunk, "text", getattr(chunk, "content", chunk)))
            full_text += token
            if writer:
                writer({"delta": token})
    except Exception as exc:
        logger.warning(
            "Token streaming failed during generate for question %r; falling back to invoke(): %s",
            question,
            exc,
        )

    if not full_text:
        reply = chain.invoke({"question": question, "context": context_str})
        full_text = str(getattr(reply, "text", getattr(reply, "content", reply)))
        if writer:
            writer({"delta": full_text})

    answer = full_text.strip()
    refusal = is_refusal(answer)
    return {
        "generation": answer,
        "relevant_documents": [] if refusal else docs,
        "is_refusal": refusal,
    }
