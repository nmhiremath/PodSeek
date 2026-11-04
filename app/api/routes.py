"""FastAPI route definitions for AskPodcast."""

import json
from collections.abc import AsyncGenerator
from pathlib import Path
from typing import Any, cast

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.prompts import ChatPromptTemplate
from pydantic import BaseModel, Field

from app.agent.graph import corrective_rag_agent
from app.agent.state import AgentState
from app.factory import get_chat_model
from app.ingestion import (
    captions_to_segments,
    chunk_segments,
    extract_video_id,
    fetch_raw_captions,
)
from app.ingestion.youtube import fetch_video_metadata, is_huberman_channel
from app.observability import trace_config
from app.schemas import (
    AskRequest,
    AskResponse,
    Citation,
    EpisodeSummary,
    IngestRequest,
    IngestResponse,
    Show,
)
from app.vectorstore import index_chunks

router = APIRouter()


# --- Structured Output Schema for Summarization ---
class EpisodeAnalysis(BaseModel):
    """Pydantic schema for structured multi-tier summarization and entity extraction."""

    short_summary: str = Field(description="1-2 sentence executive overview.")
    long_summary: str = Field(description="2-3 paragraph detailed breakdown of main themes and mechanisms.")
    key_takeaways: list[str] = Field(description="4-6 actionable takeaways.")
    keywords: list[str] = Field(description="10-15 core scientific concepts, protocols, or entities.")


def _get_chat_llm(temperature: float = 0.2) -> BaseChatModel:
    return get_chat_model(temperature=temperature)


def _analyze_episode(full_text: str, title: str) -> EpisodeAnalysis:
    """Generate structured multi-tier summaries and keywords using Gemini."""
    llm = _get_chat_llm(temperature=0.2)
    structured_analyzer = llm.with_structured_output(EpisodeAnalysis)

    prompt = ChatPromptTemplate.from_messages(
        [
            (
                "system",
                "You are an expert scientific editor and podcast analyst. "
                "Analyze the provided podcast transcript and produce a structured breakdown:\n"
                "1. A concise 1-2 sentence short summary.\n"
                "2. A 2-3 paragraph comprehensive long summary.\n"
                "3. 4-6 high-impact actionable key takeaways.\n"
                "4. 10-15 key scientific concepts, entities, and search tags.",
            ),
            ("human", "Episode Title: {title}\n\nTranscript Content:\n{transcript}"),
        ]
    )

    chain = prompt | structured_analyzer
    # Cap transcript at ~40,000 words to ensure rapid execution within token bounds
    trimmed = " ".join(full_text.split()[:40000])
    result = chain.invoke({"title": title, "transcript": trimmed}, config=trace_config("/ingest"))

    if isinstance(result, EpisodeAnalysis):
        return result
    return EpisodeAnalysis.model_validate(result)


def _build_citations(documents: list) -> list[Citation]:
    """Build structured, clickable YouTube citation models from document metadata."""
    citations: list[Citation] = []
    seen = set()

    for doc in documents:
        meta = doc.metadata
        chunk_id = meta.get("chunk_id", "")
        if chunk_id in seen:
            continue
        seen.add(chunk_id)

        start_sec = int(meta.get("start_seconds", 0))
        ep_id = meta.get("episode_id", "")
        deep_link = f"https://youtu.be/{ep_id}?t={start_sec}" if ep_id else ""

        citations.append(
            Citation(
                episode_title=meta.get("episode_title", "Unknown Episode"),
                episode_id=ep_id,
                speaker=meta.get("speaker", "Speaker"),
                timestamp=meta.get("timestamp", "00:00:00"),
                start_seconds=meta.get("start_seconds", 0.0),
                url=deep_link,
            )
        )
    return citations


def _initial_state(question: str) -> AgentState:
    return {
        "question": question,
        "documents": [],
        "relevant_documents": [],
        "rewrite_count": 0,
        "generation": "",
    }


def _node_event(node_name: str, node_output: dict) -> dict:
    """Shape one graph update the way POST /ask/stream emits it."""
    event_data = {
        "node": node_name,
        "rewrites": node_output.get("rewrite_count", 0),
    }
    if node_name == "retrieve":
        event_data["chunks_retrieved"] = len(node_output.get("documents", []))
    elif node_name == "grade_documents":
        relevant = node_output.get("relevant_documents", [])
        event_data["relevant_chunks"] = len(relevant)
        event_data["citations"] = [citation.model_dump() for citation in _build_citations(relevant)]
    elif node_name == "rewrite_query":
        event_data["rewritten_query"] = node_output.get("question", "")
    elif node_name == "generate":
        event_data["generation"] = node_output.get("generation", "")
    return event_data


def iter_agent_events(question: str):
    """Yield the same node payloads as POST /ask/stream, without the SSE framing."""
    for event in corrective_rag_agent.stream(_initial_state(question), config=trace_config("/ask/stream")):
        for node_name, node_output in event.items():
            yield _node_event(node_name, node_output)


# ==============================================================================
# Endpoints
# ==============================================================================
@router.get("/health")
def health_check() -> dict[str, str]:
    """Health check probe for container readiness."""
    return {"status": "ok", "app": "PodSeek"}


@router.get("/episodes", response_model=list[EpisodeSummary])
def list_episodes() -> list[EpisodeSummary]:
    """List all indexed episodes currently stored in the knowledge library."""
    episodes: list[EpisodeSummary] = []
    raw_dir = Path("data/raw")
    if not raw_dir.exists():
        return episodes

    for json_file in raw_dir.glob("*/*.json"):
        try:
            data = json.loads(json_file.read_text())
            ep_id = data.get("episode_id", json_file.stem)
            episodes.append(
                EpisodeSummary(
                    episode_id=ep_id,
                    episode_title=data.get("title", f"Episode {ep_id}"),
                    show=data.get("show", "huberman_lab"),
                    speaker=data.get("speaker", "Andrew Huberman"),
                    url=f"https://youtu.be/{ep_id}",
                    short_summary=data.get("short_summary"),
                    long_summary=data.get("long_summary"),
                    key_takeaways=data.get("key_takeaways", []),
                    keywords=data.get("keywords", []),
                )
            )
        except Exception:
            continue
    return episodes


@router.post("/ingest", response_model=IngestResponse)
def ingest_episode(request: IngestRequest) -> IngestResponse:
    """Ingest a YouTube episode, chunk transcript, analyze, and index into ChromaDB."""
    video_id = extract_video_id(request.video_url_or_id)
    if not video_id:
        raise HTTPException(status_code=400, detail="Invalid YouTube URL or video ID.")

    try:
        cache_dir = Path("data/raw") / request.show
        cache_dir.mkdir(parents=True, exist_ok=True)
        cache_file = cache_dir / f"{video_id}.json"

        # 1. Load or fetch transcript
        payload: dict[str, Any]
        if cache_file.exists():
            payload = json.loads(cache_file.read_text())
            title = str(payload.get("title", f"Episode {video_id}"))
            captions = list(payload.get("captions", []))
        else:
            title, author_name = fetch_video_metadata(video_id)
            if not is_huberman_channel(author_name):
                raise HTTPException(
                    status_code=400,
                    detail=(
                        f"Only Huberman Lab episodes can be ingested (detected channel: {author_name or 'Unknown'})."
                    ),
                )
            captions = fetch_raw_captions(video_id)
            payload = {
                "show": request.show,
                "episode_id": video_id,
                "title": title,
                "speaker": request.speaker,
                "captions": captions,
            }
            cache_file.write_text(json.dumps(payload, indent=2))

        # 2. Build segments & chunks
        segments = captions_to_segments(
            captions,
            show=cast(Show, request.show),
            episode_id=video_id,
            episode_title=title,
            speaker=request.speaker,
        )
        chunks = chunk_segments(segments)
        indexed_count = index_chunks(chunks)

        # 3. Load or generate multi-tier summary and keywords
        short_summary: str
        long_summary: str
        key_takeaways: list[str]
        keywords: list[str]

        if "short_summary" in payload and isinstance(payload["short_summary"], str) and payload["short_summary"]:
            short_summary = payload["short_summary"]
            long_summary = str(payload.get("long_summary", ""))
            raw_takeaways = payload.get("key_takeaways", [])
            key_takeaways = [str(x) for x in raw_takeaways] if isinstance(raw_takeaways, list) else []
            raw_keywords = payload.get("keywords", [])
            keywords = [str(x) for x in raw_keywords] if isinstance(raw_keywords, list) else []
        else:
            full_text = " ".join(s.text for s in segments)
            analysis = _analyze_episode(full_text, title)
            short_summary = analysis.short_summary
            long_summary = analysis.long_summary
            key_takeaways = analysis.key_takeaways
            keywords = analysis.keywords

            # Cache the analysis into the JSON file
            payload["short_summary"] = short_summary
            payload["long_summary"] = long_summary
            payload["key_takeaways"] = key_takeaways
            payload["keywords"] = keywords
            cache_file.write_text(json.dumps(payload, indent=2))

        return IngestResponse(
            status="success",
            episode_id=video_id,
            episode_title=title,
            segments_parsed=len(segments),
            chunks_indexed=indexed_count,
            short_summary=short_summary,
            long_summary=long_summary,
            key_takeaways=key_takeaways,
            keywords=keywords,
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to ingest episode: {e}")


@router.post("/ask", response_model=AskResponse)
def ask_question(request: AskRequest) -> AskResponse:
    """Submit a question and receive a complete answer with clickable timestamp citations."""
    try:
        final_state = corrective_rag_agent.invoke(_initial_state(request.question), config=trace_config("/ask"))
        relevant_docs = final_state.get("relevant_documents", [])
        citations = _build_citations(relevant_docs)

        return AskResponse(
            question=request.question,
            answer=final_state.get("generation", ""),
            citations=citations,
            rewrites_attempted=final_state.get("rewrite_count", 0),
            relevant_chunks_used=len(relevant_docs),
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Agent execution failed: {e}")


@router.post("/ask/stream")
async def stream_question(request: AskRequest) -> StreamingResponse:
    """Stream LangGraph node events and final answer in real-time via Server-Sent Events."""

    async def event_generator() -> AsyncGenerator[str]:
        for event_data in iter_agent_events(request.question):
            yield f"data: {json.dumps(event_data)}\n\n"

    return StreamingResponse(event_generator(), media_type="text/event-stream")
