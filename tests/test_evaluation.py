"""Offline evaluation metrics. No network."""

import json
from pathlib import Path

from app.evaluation import (
    citation_timestamp_valid,
    keyword_relevance,
    offline_fixture,
    score_example,
)

VALID = {
    "timestamp": "00:20:45",
    "start_seconds": 1245.0,
    "url": "https://youtu.be/QmOF0crdyRU?t=1245",
}


def test_citation_accepts_a_deep_link_timestamp():
    assert citation_timestamp_valid(VALID)


def test_citation_rejects_bad_timestamp_negative_start_and_missing_link():
    assert not citation_timestamp_valid({**VALID, "timestamp": "20:45"})
    assert not citation_timestamp_valid({**VALID, "start_seconds": -1})
    assert not citation_timestamp_valid({**VALID, "url": "https://youtu.be/QmOF0crdyRU"})
    assert not citation_timestamp_valid({**VALID, "start_seconds": "nope"})


def test_keyword_relevance_is_case_insensitive_fraction():
    assert keyword_relevance("Dopamine crash after a peak", ["dopamine", "crash", "sunlight"]) == 2 / 3
    assert keyword_relevance("anything", []) == 0.0


def test_score_example_requires_every_citation_to_be_valid():
    scored = score_example("dopamine", [VALID, {**VALID, "timestamp": "bad"}], ["dopamine"])
    assert scored["citations_valid"] is False
    assert scored["citation_count"] == 2

    empty = score_example("no idea", [], ["dopamine"])
    assert empty["citations_valid"] is False
    assert empty["keyword_score"] == 0.0


def test_offline_fixtures_match_the_golden_file():
    questions = json.loads(Path("evals/questions.json").read_text())
    assert len(questions) == 4

    for item in questions:
        payload = offline_fixture(item)
        scored = score_example(payload["answer"], payload["citations"], item["keywords"])
        if item["expect_citations"]:
            assert scored["citations_valid"] is True
            assert scored["keyword_score"] == 1.0
        else:
            assert payload["citations"] == []
            assert scored["citations_valid"] is False


def test_evaluate_cli_runs_offline_and_exits_zero():
    from scripts.evaluate import main

    assert main([]) == 0
