"""FastAPI route definitions for PodSeek."""

import json
import logging
import re
import time
from collections.abc import AsyncGenerator
from pathlib import Path
from typing import Any, cast

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.prompts import ChatPromptTemplate
from langsmith import get_current_run_tree, traceable
from pydantic import BaseModel, Field, ValidationError

from app.agent.graph import corrective_rag_agent
from app.agent.nodes import determine_outcome
from app.agent.state import AgentState
from app.factory import get_chat_model, get_collection_name
from app.ingestion import (
    captions_to_segments,
    chunk_segments,
    extract_video_id,
    fetch_raw_captions,
)
from app.ingestion.youtube import fetch_video_metadata, is_huberman_channel
from app.observability import anonymizer_client, trace_config, with_anonymized_client
from app.schemas import (
    AskRequest,
    AskResponse,
    Citation,
    EpisodeSummary,
    IngestRequest,
    IngestResponse,
    Show,
)
from app.vectorstore import get_vectorstore, index_chunks

router = APIRouter()
logger = logging.getLogger(__name__)


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

    chain = (prompt | structured_analyzer).with_config(run_name="summarize_episode")
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


def _initial_state(question: str, mode: str = "balanced") -> AgentState:
    return {
        "question": question,
        "documents": [],
        "relevant_documents": [],
        "rewrite_count": 0,
        "generation": "",
        "mode": mode,  # type: ignore[typeddict-item]
        "top_distance": 1.0,
        "is_exact_match": False,
    }


_QA_CACHE: dict[str, dict[str, Any]] = {}
_QA_CACHE_LOADED = False
_QA_CACHE_FILE = Path("data/raw/qa_cache.json")


def _qa_cache_key(question: str, mode: str = "balanced") -> str:
    """Build a normalized cache key scoped to the active collection, indexed episode set, and mode."""
    norm_q = re.sub(r"[^a-z0-9]+", " ", question.strip().lower()).strip()
    raw_dir = Path("data/raw")
    ep_ids: list[str] = []
    if raw_dir.exists():
        ep_ids = sorted(p.stem for p in raw_dir.glob("*/*.json"))
    return f"{get_collection_name()}::{','.join(ep_ids)}::{mode}::{norm_q}"


def _get_cached_qa(question: str, mode: str = "balanced") -> dict[str, Any] | None:
    """Return a cached QA entry if the normalized question was already answered for the current library and mode."""
    global _QA_CACHE_LOADED
    if not _QA_CACHE_LOADED:
        _QA_CACHE_LOADED = True
        if _QA_CACHE_FILE.exists():
            try:
                loaded = json.loads(_QA_CACHE_FILE.read_text())
                if isinstance(loaded, dict):
                    _QA_CACHE.update(loaded)
            except (OSError, json.JSONDecodeError, ValueError) as exc:
                logger.warning("Failed to load QA cache from %s: %s", _QA_CACHE_FILE, exc)
    return _QA_CACHE.get(_qa_cache_key(question, mode=mode))


def _set_cached_qa(question: str, entry: dict[str, Any], mode: str = "balanced") -> None:
    """Persist a verified QA entry to memory and disk cache."""
    key = _qa_cache_key(question, mode=mode)
    _QA_CACHE[key] = entry
    try:
        _QA_CACHE_FILE.parent.mkdir(parents=True, exist_ok=True)
        _QA_CACHE_FILE.write_text(json.dumps(_QA_CACHE, indent=2))
    except (OSError, TypeError, ValueError) as exc:
        logger.warning("Failed to persist QA cache to %s: %s", _QA_CACHE_FILE, exc)


def _node_event(node_name: str, node_output: dict) -> dict:
    """Shape one graph update the way POST /ask/stream emits it."""
    event_data = {
        "node": node_name,
        "rewrites": node_output.get("rewrite_count", 0),
    }
    if "mode" in node_output:
        event_data["mode"] = node_output["mode"]
    if "top_distance" in node_output:
        event_data["top_distance"] = node_output["top_distance"]
    if "is_exact_match" in node_output:
        event_data["is_exact_match"] = node_output["is_exact_match"]
    if node_name == "retrieve":
        event_data["chunks_retrieved"] = len(node_output.get("documents", []))
        if "top_distance" in node_output:
            event_data["top_distance"] = node_output["top_distance"]
        if "relevant_documents" in node_output:
            event_data["citations"] = [
                citation.model_dump() for citation in _build_citations(node_output["relevant_documents"])
            ]
    elif node_name == "grade_documents":
        relevant = node_output.get("relevant_documents", [])
        event_data["relevant_chunks"] = len(relevant)
        event_data["citations"] = [citation.model_dump() for citation in _build_citations(relevant)]
    elif node_name == "rewrite_query":
        event_data["rewritten_query"] = node_output.get("question", "")
    elif node_name == "generate":
        event_data["generation"] = node_output.get("generation", "")
        if "relevant_documents" in node_output:
            event_data["citations"] = [
                citation.model_dump() for citation in _build_citations(node_output["relevant_documents"])
            ]
    return event_data


def _process_ask_inputs(inputs: dict[str, Any]) -> dict[str, Any]:
    req = inputs.get("request")
    if req is not None:
        q = getattr(req, "question", "")
        m = getattr(req, "mode", "balanced") or "balanced"
        return {"question": q, "mode": m}
    return {
        "question": inputs.get("question", ""),
        "mode": inputs.get("mode", "balanced") or "balanced",
    }


def _reduce_agent_events(events: Any) -> dict[str, Any]:
    answer = ""
    citations_count = 0
    cached = False
    aborted = False
    if hasattr(events, "__iter__"):
        for ev in events:
            if not isinstance(ev, dict):
                continue
            if ev.get("cached"):
                cached = True
            if ev.get("aborted"):
                aborted = True
            if "generation" in ev and ev["generation"]:
                answer = str(ev["generation"])
            elif "delta" in ev and ev["delta"]:
                answer += str(ev["delta"])
            if "citations" in ev and isinstance(ev["citations"], list):
                citations_count = len(ev["citations"])
    outcome = determine_outcome(answer, cached=cached, aborted=aborted)
    return {
        "answer": answer,
        "outcome": outcome,
        "citations": citations_count,
    }


@with_anonymized_client
@traceable(
    name="podseek_ask",
    run_type="chain",
    client=anonymizer_client,
    process_inputs=_process_ask_inputs,
    reduce_fn=_reduce_agent_events,
)
def iter_agent_events(question: str, mode: str = "balanced"):
    """Yield the same node payloads as POST /ask/stream, serving from QA cache when available."""
    cached = _get_cached_qa(question, mode=mode)
    if cached and isinstance(cached.get("events"), list):
        rewrites = int(cached.get("rewrites") or 0)
        top_dist = cached.get("top_distance")
        rt = get_current_run_tree()
        if rt:
            rt.add_metadata({"outcome": "cached", "cached": True, "rewrites": rewrites, "top_distance": top_dist})
            rt.add_tags([mode])
        for ev in cached["events"]:
            yield {**ev, "cached": True, "mode": mode}
        return

    collected_events: list[dict[str, Any]] = []
    last_relevant = 0
    last_citations: list[dict[str, Any]] = []
    last_rewrites = 0
    last_answer = ""
    top_distance: float | None = None

    for mode_type, payload in corrective_rag_agent.stream(
        _initial_state(question, mode=mode),
        config=trace_config("/ask/stream", mode=mode),
        stream_mode=["updates", "custom"],
    ):
        if mode_type == "custom" and isinstance(payload, dict) and "delta" in payload:
            delta = str(payload["delta"])
            last_answer += delta
            yield {"node": "generate", "delta": delta, "mode": mode}
            continue

        if mode_type == "updates" and isinstance(payload, dict):
            for node_name, node_output in payload.items():
                shaped = _node_event(node_name, node_output)
                shaped["mode"] = mode
                collected_events.append(shaped)
                last_rewrites = max(last_rewrites, int(shaped.get("rewrites") or 0))
                if shaped.get("citations"):
                    last_citations = list(shaped["citations"])
                if node_name == "retrieve" and "top_distance" in shaped:
                    top_distance = shaped["top_distance"]
                elif node_name == "grade_documents":
                    last_relevant = int(shaped.get("relevant_chunks") or 0)
                elif node_name == "generate":
                    last_answer = str(shaped.get("generation") or last_answer)
                yield shaped

    outcome = determine_outcome(last_answer, cached=False)
    rt = get_current_run_tree()
    if rt:
        rt.add_metadata({"outcome": outcome, "cached": False, "rewrites": last_rewrites, "top_distance": top_distance})
        rt.add_tags([mode])

    if last_answer and (last_relevant > 0 or mode == "turbo"):
        _set_cached_qa(
            question,
            {
                "answer": last_answer,
                "citations": last_citations,
                "rewrites": last_rewrites,
                "relevant_chunks": last_relevant,
                "top_distance": top_distance,
                "mode": mode,
                "events": collected_events,
            },
            mode=mode,
        )


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
        except (OSError, json.JSONDecodeError, ValidationError, KeyError, ValueError) as exc:
            logger.warning("Skipping malformed episode cache file %s: %s", json_file, exc)
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
        active_collection = get_collection_name()

        # 0. Fast-path cache check: if already cached and indexed in active Chroma collection,
        # short-circuit immediately without segmenting, chunking, embedding, or summarizing.
        payload: dict[str, Any]
        already_indexed = False
        if cache_file.exists():
            payload = json.loads(cache_file.read_text())
            title = str(payload.get("title", f"Episode {video_id}"))
            captions = list(payload.get("captions", []))
            indexed_cols = payload.get("indexed_collections", [])
            if isinstance(indexed_cols, list) and active_collection in indexed_cols:
                already_indexed = True
            else:
                existing = get_vectorstore().get(where={"episode_id": video_id}, limit=1, include=[])
                if existing and existing.get("ids"):
                    already_indexed = True

            has_summary = (
                "short_summary" in payload
                and isinstance(payload["short_summary"], str)
                and bool(payload["short_summary"])
            )
            if already_indexed and has_summary:
                raw_takeaways = payload.get("key_takeaways", [])
                raw_keywords = payload.get("keywords", [])
                cached_chunks = int(payload.get("chunks_indexed") or 0)
                cached_segments = int(payload.get("segments_parsed") or len(captions))
                if not cached_chunks:
                    all_ids = get_vectorstore().get(where={"episode_id": video_id}, include=[])
                    cached_chunks = len(all_ids.get("ids", []))
                    payload["chunks_indexed"] = cached_chunks
                if not isinstance(indexed_cols, list) or active_collection not in indexed_cols:
                    payload["indexed_collections"] = [
                        *(indexed_cols if isinstance(indexed_cols, list) else []),
                        active_collection,
                    ]
                    cache_file.write_text(json.dumps(payload, indent=2))
                return IngestResponse(
                    status="cached",
                    episode_id=video_id,
                    episode_title=title,
                    segments_parsed=cached_segments,
                    chunks_indexed=cached_chunks,
                    short_summary=payload["short_summary"],
                    long_summary=str(payload.get("long_summary", "")),
                    key_takeaways=[str(x) for x in raw_takeaways] if isinstance(raw_takeaways, list) else [],
                    keywords=[str(x) for x in raw_keywords] if isinstance(raw_keywords, list) else [],
                )
        else:
            # 1. Fetch metadata & raw captions for a brand-new episode
            title, author_name = fetch_video_metadata(video_id)
            if not is_huberman_channel(author_name):
                raise HTTPException(
                    status_code=400,
                    detail=(
                        f"Only Huberman Lab episodes can be ingested (detected channel: {author_name or 'Unknown'})."
                    ),
                )
            try:
                captions = fetch_raw_captions(video_id)
            except Exception as exc:
                err_str = str(exc)
                if any(
                    marker in err_str
                    for marker in (
                        "blocking requests from your IP",
                        "RequestBlocked",
                        "IpBlocked",
                        "Could not retrieve",
                    )
                ):
                    raise HTTPException(
                        status_code=429,
                        detail=(
                            "YouTube is blocking requests from cloud datacenter IPs. "
                            "Please query from the pre-indexed episode library, "
                            "or download transcripts locally using `python -m scripts.fetch_episode <id>`."
                        ),
                    ) from exc
                raise HTTPException(
                    status_code=400,
                    detail=f"Could not retrieve transcript from YouTube: {err_str[:160]}",
                ) from exc
            payload = {
                "show": request.show,
                "episode_id": video_id,
                "title": title,
                "speaker": request.speaker,
                "captions": captions,
            }
            cache_file.write_text(json.dumps(payload, indent=2))

        # 2. Build segments & chunks; only call embedding model if not already in ChromaDB
        segments = captions_to_segments(
            captions,
            show=cast(Show, request.show),
            episode_id=video_id,
            episode_title=title,
            speaker=request.speaker,
        )
        chunks = chunk_segments(segments)
        indexed_count = len(chunks) if already_indexed else index_chunks(chunks)

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

        # Cache analysis and indexing state into the JSON file
        existing_cols = payload.get("indexed_collections", [])
        cols_list = [str(c) for c in existing_cols] if isinstance(existing_cols, list) else []
        if active_collection not in cols_list:
            cols_list.append(active_collection)
        payload["segments_parsed"] = len(segments)
        payload["chunks_indexed"] = indexed_count
        payload["indexed_collections"] = cols_list
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


@with_anonymized_client
@traceable(
    name="podseek_ask",
    run_type="chain",
    client=anonymizer_client,
    process_inputs=_process_ask_inputs,
    process_outputs=lambda r: {
        "answer": r[0].answer,
        "outcome": r[1],
        "citations": len(r[0].citations),
    },
)
def _ask_traced(request: AskRequest) -> tuple[AskResponse, str]:
    start_time = time.perf_counter()
    req_mode = request.mode or "balanced"
    try:
        cached = _get_cached_qa(request.question, mode=req_mode)
        if cached and cached.get("answer"):
            raw_cits = cached.get("citations") or []
            latency = round((time.perf_counter() - start_time) * 1000, 1)
            rewrites = int(cached.get("rewrites") or 0)
            top_dist = cached.get("top_distance")
            rt = get_current_run_tree()
            if rt:
                rt.add_metadata({"outcome": "cached", "cached": True, "rewrites": rewrites, "top_distance": top_dist})
                rt.add_tags([req_mode])
            resp = AskResponse(
                question=request.question,
                answer=str(cached["answer"]),
                citations=[Citation.model_validate(c) for c in raw_cits],
                rewrites_attempted=rewrites,
                relevant_chunks_used=int(cached.get("relevant_chunks") or len(raw_cits)),
                mode=req_mode,
                top_distance=top_dist,
                latency_ms=latency,
            )
            return resp, "cached"

        final_state = corrective_rag_agent.invoke(
            _initial_state(request.question, mode=req_mode), config=trace_config("/ask", mode=req_mode)
        )
        relevant_docs = final_state.get("relevant_documents", [])
        citations = _build_citations(relevant_docs)
        answer = final_state.get("generation", "")
        rewrites = final_state.get("rewrite_count", 0)
        top_dist = final_state.get("top_distance")
        latency = round((time.perf_counter() - start_time) * 1000, 1)
        outcome = determine_outcome(answer, cached=False)
        rt = get_current_run_tree()
        if rt:
            rt.add_metadata({"outcome": outcome, "cached": False, "rewrites": rewrites, "top_distance": top_dist})
            rt.add_tags([req_mode])

        if answer and (relevant_docs or req_mode == "turbo"):
            cit_dicts = [c.model_dump() for c in citations]
            _set_cached_qa(
                request.question,
                {
                    "answer": answer,
                    "citations": cit_dicts,
                    "rewrites": rewrites,
                    "relevant_chunks": len(relevant_docs),
                    "top_distance": top_dist,
                    "mode": req_mode,
                    "events": [
                        {
                            "node": "retrieve",
                            "rewrites": rewrites,
                            "chunks_retrieved": len(final_state.get("documents", [])) or 4,
                            "top_distance": top_dist,
                            "mode": req_mode,
                        },
                        {
                            "node": "grade_documents",
                            "rewrites": rewrites,
                            "relevant_chunks": len(relevant_docs),
                            "citations": cit_dicts,
                            "mode": req_mode,
                        },
                        {"node": "generate", "rewrites": rewrites, "generation": answer, "mode": req_mode},
                    ],
                },
                mode=req_mode,
            )

        resp = AskResponse(
            question=request.question,
            answer=answer,
            citations=citations,
            rewrites_attempted=rewrites,
            relevant_chunks_used=len(relevant_docs),
            mode=req_mode,
            top_distance=top_dist,
            latency_ms=latency,
        )
        return resp, outcome
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Agent execution failed: {e}")


@router.post("/ask", response_model=AskResponse)
def ask_question(request: AskRequest) -> AskResponse:
    """Submit a question and receive a complete answer with clickable timestamp citations."""
    return _ask_traced(request)[0]


@router.post("/ask/stream")
async def stream_question(request: AskRequest) -> StreamingResponse:
    """Stream LangGraph node events and final answer in real-time via Server-Sent Events."""
    req_mode = request.mode or "balanced"

    async def event_generator() -> AsyncGenerator[str]:
        for event_data in iter_agent_events(request.question, mode=req_mode):
            yield f"data: {json.dumps(event_data)}\n\n"

    return StreamingResponse(event_generator(), media_type="text/event-stream")
