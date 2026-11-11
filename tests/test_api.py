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


def test_ingest_validation_rejects_empty_video_id(monkeypatch):
    """Verify /ingest rejects empty video ID when ingestion is enabled."""
    monkeypatch.setenv("PODSEEK_INGEST_ENABLED", "true")
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


def test_stream_concurrent_calls_do_not_block_event_loop(monkeypatch):
    """Verify that concurrent /ask/stream calls run in threadpool and do not block each other."""
    import asyncio
    import time

    from httpx import ASGITransport, AsyncClient

    from app.api import routes

    delay = 0.1

    def slow_iter_events(question: str, mode: str = "balanced"):
        time.sleep(delay)
        yield {"node": "generate", "generation": f"Answer for {question}", "mode": mode}

    monkeypatch.setattr(routes, "iter_agent_events", slow_iter_events)

    async def _run():
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
            t0 = time.perf_counter()
            resp1, resp2 = await asyncio.gather(
                ac.post("/ask/stream", json={"question": "first question"}),
                ac.post("/ask/stream", json={"question": "second question"}),
            )
            elapsed = time.perf_counter() - t0
            return resp1, resp2, elapsed

    resp1, resp2, total_time = asyncio.run(_run())

    assert resp1.status_code == 200
    assert resp2.status_code == 200
    assert "Answer for first question" in resp1.text
    assert "Answer for second question" in resp2.text

    # If blocking the event loop, total_time would be >= 2 * delay (0.2s).
    # Since Starlette iterates sync generators in a threadpool, both complete in ~1x delay.
    assert total_time < delay * 1.8


def test_ingest_disabled_refuses_with_403_and_bypasses_pipeline(monkeypatch):
    """Verify that when PODSEEK_INGEST_ENABLED is false, /ingest refuses with 403 before any work."""
    from unittest.mock import MagicMock

    from app.api import routes

    mock_extract = MagicMock()
    mock_metadata = MagicMock()
    mock_captions = MagicMock()
    monkeypatch.setattr(routes, "extract_video_id", mock_extract)
    monkeypatch.setattr(routes, "fetch_video_metadata", mock_metadata)
    monkeypatch.setattr(routes, "fetch_raw_captions", mock_captions)

    monkeypatch.setenv("PODSEEK_INGEST_ENABLED", "false")
    response = client.post("/ingest", json={"video_url_or_id": "https://www.youtube.com/watch?v=QmOF0crdyRU"})

    assert response.status_code == 403
    assert response.json()["detail"] == "Ingestion is disabled on the live demo."
    mock_extract.assert_not_called()
    mock_metadata.assert_not_called()
    mock_captions.assert_not_called()


def test_ingest_enabled_path_unchanged(monkeypatch):
    """Verify that when ingestion is enabled (default), validation proceeds normally."""
    monkeypatch.setenv("PODSEEK_INGEST_ENABLED", "true")
    response = client.post("/ingest", json={"video_url_or_id": ""})
    # Validation error 400 for empty video ID shows it passed the enabled check
    assert response.status_code == 400
    assert "Invalid YouTube URL" in response.json()["detail"]
