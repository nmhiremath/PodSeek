"""API request and response schemas."""

from typing import Literal

from pydantic import BaseModel, Field


class Citation(BaseModel):
    """Structured citation metadata for clickable UI elements."""

    episode_title: str
    episode_id: str
    speaker: str
    timestamp: str
    start_seconds: float
    url: str


class AskRequest(BaseModel):
    """Incoming user query payload."""

    question: str = Field(min_length=3, max_length=500, description="Question to ask the podcast archive.")
    mode: Literal["turbo", "balanced", "rigorous"] = Field(
        default="balanced",
        description="Execution mode: 'turbo' (fused 1-call), 'balanced' (distance threshold fast-path), or 'rigorous' (full CRAG loop).",
    )


class AskResponse(BaseModel):
    """Structured answer response with citations and execution metadata."""

    question: str
    answer: str
    citations: list[Citation] = Field(default_factory=list)
    rewrites_attempted: int = 0
    relevant_chunks_used: int = 0
    mode: str = Field(default="balanced", description="Execution mode used ('turbo', 'balanced', 'rigorous').")
    top_distance: float | None = Field(default=None, description="Cosine distance of top retrieved chunk if available.")
    latency_ms: float | None = Field(default=None, description="Total execution latency in milliseconds.")


class IngestRequest(BaseModel):
    """Payload to ingest and index a YouTube episode."""

    video_url_or_id: str = Field(description="YouTube video ID or full YouTube URL.")
    show: str = Field(default="huberman_lab", description="Podcast show key.")
    speaker: str = Field(default="Andrew Huberman", description="Primary speaker or host & guest name.")


class IngestResponse(BaseModel):
    """Result of episode ingestion, indexing, and multi-tier summarization."""

    status: str
    episode_id: str
    episode_title: str
    segments_parsed: int
    chunks_indexed: int
    short_summary: str = Field(description="1-2 sentence executive overview.")
    long_summary: str = Field(description="2-3 paragraph detailed breakdown.")
    key_takeaways: list[str] = Field(default_factory=list, description="4-6 actionable takeaways.")
    keywords: list[str] = Field(default_factory=list, description="10-15 topic & entity tags.")


class EpisodeSummary(BaseModel):
    """Manifest item for an indexed episode in the knowledge library."""

    episode_id: str
    episode_title: str
    show: str
    speaker: str
    url: str
    short_summary: str | None = None
    long_summary: str | None = None
    key_takeaways: list[str] = Field(default_factory=list)
    keywords: list[str] = Field(default_factory=list)
