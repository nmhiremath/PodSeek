"""API integration tests."""

from fastapi.testclient import TestClient

from app.api import app

client = TestClient(app)


def test_health_endpoint():
    """Verify health probe returns status 200."""
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok", "app": "PodSeek"}


def test_ask_validation_rejects_empty_payload():
    """Verify input validation rejects questions shorter than 3 characters."""
    response = client.post("/ask", json={"question": "hi"})
    assert response.status_code == 422


def test_stream_validation_rejects_empty_payload():
    """Verify streaming endpoint rejects invalid input."""
    response = client.post("/ask/stream", json={"question": "no"})
    assert response.status_code == 422


def test_list_episodes_returns_list():
    """Verify /episodes endpoint returns a valid list of episodes."""
    response = client.get("/episodes")
    assert response.status_code == 200
    assert isinstance(response.json(), list)


def test_ingest_validation_rejects_empty_video_id():
    """Verify /ingest rejects empty video ID."""
    response = client.post("/ingest", json={"video_url_or_id": ""})
    assert response.status_code == 400


def test_qa_cache_missing_file_yields_no_hits_and_no_errors(tmp_path, monkeypatch):
    """Verify that a missing QA cache file produces no cache hits and raises no errors."""
    from app.api import routes

    missing_cache = tmp_path / "data" / "raw" / "qa_cache.json"
    monkeypatch.setattr(routes, "_QA_CACHE_FILE", missing_cache)
    monkeypatch.setattr(routes, "_QA_CACHE_LOADED", False)
    monkeypatch.setattr(routes, "_QA_CACHE", {})

    assert not missing_cache.exists()
    cached = routes._get_cached_qa("What causes dopamine crash?", mode="balanced")
    assert cached is None
