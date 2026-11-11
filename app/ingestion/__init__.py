"""Ingestion package: adapters and transcript chunking."""

import os

from app.ingestion.chunking import chunk_segments
from app.ingestion.youtube import (
    captions_to_segments,
    extract_video_id,
    fetch_raw_captions,
    fetch_video_title,
)


def is_ingest_enabled() -> bool:
    """Return True if episode ingestion is enabled via PODSEEK_INGEST_ENABLED (default: True).

    Parses 'false', '0', 'no', 'off' case-insensitively as False.
    """
    raw = os.getenv("PODSEEK_INGEST_ENABLED", "true").strip().lower()
    return raw not in {"false", "0", "no", "off"}


__all__ = [
    "captions_to_segments",
    "chunk_segments",
    "extract_video_id",
    "fetch_raw_captions",
    "fetch_video_title",
    "is_ingest_enabled",
]
