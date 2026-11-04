"""Offline checks for podcast answers.

These metrics do not call a model. scripts/evaluate.py uses them for the
default run and, when asked, adds an optional LLM judge on top.
"""

import re

TIMESTAMP_RE = re.compile(r"^\d{2}:\d{2}:\d{2}$")
_DEEP_LINK_T = re.compile(r"\?t=\d+")

_GAP_ANSWER = "I could not find any relevant information in the podcast transcripts to answer your question."
_FIXTURE_TITLE = "Controlling Your Dopamine For Motivation, Focus & Satisfaction"


def citation_timestamp_valid(citation: dict) -> bool:
    """A citation is valid when the display time, seconds, and deep link agree in shape."""
    timestamp = str(citation.get("timestamp", ""))
    if TIMESTAMP_RE.match(timestamp) is None:
        return False
    raw_start = citation.get("start_seconds")
    if raw_start is None:
        return False
    try:
        start_seconds = float(raw_start)
    except (TypeError, ValueError):
        return False
    if start_seconds < 0:
        return False
    return _DEEP_LINK_T.search(str(citation.get("url", ""))) is not None


def keyword_relevance(answer: str, keywords: list[str]) -> float:
    """Fraction of expected keywords present in the answer. Empty list scores 0."""
    if not keywords:
        return 0.0
    haystack = answer.casefold()
    hits = sum(1 for keyword in keywords if str(keyword).casefold() in haystack)
    return hits / len(keywords)


def score_example(answer: str, citations: list[dict], keywords: list[str]) -> dict:
    """Score one answer. citations_valid requires at least one fully valid citation."""
    citations_valid = bool(citations) and all(citation_timestamp_valid(item) for item in citations)
    return {
        "keyword_score": keyword_relevance(answer, keywords),
        "citations_valid": citations_valid,
        "citation_count": len(citations),
    }


def offline_fixture(item: dict) -> dict:
    """Deterministic stand-in answer so evaluation runs with no network and no index."""
    episode_id = str(item.get("episode_id") or "QmOF0crdyRU")
    if not item.get("expect_citations", True):
        return {
            "answer": _GAP_ANSWER,
            "citations": [],
            "rewrites_attempted": 0,
        }

    keywords = [str(keyword) for keyword in item.get("keywords", [])]
    return {
        "answer": " ".join(keywords) if keywords else "No keywords provided.",
        "citations": [
            {
                "episode_title": _FIXTURE_TITLE,
                "episode_id": episode_id,
                "speaker": "Andrew Huberman",
                "timestamp": "00:20:45",
                "start_seconds": 1245.0,
                "url": f"https://youtu.be/{episode_id}?t=1245",
            }
        ],
        "rewrites_attempted": 0,
    }
