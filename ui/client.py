"""Thin clients for the PodSeek API.

Remote mode talks to FastAPI over HTTP. In-process mode calls the existing
route helpers. Neither path reimplements retrieval, grading, or generation.
"""

import json
import os
from collections.abc import Iterator
from typing import Protocol, cast

import httpx

from app.schemas import Show

DEFAULT_API_URL = "http://localhost:8000"


def _raise_clean_api_error(response: httpx.Response) -> None:
    """Raise a clean ValueError with FastAPI's `detail` string instead of raw httpx Mozilla URLs."""
    if not response.is_error:
        return
    try:
        payload = response.json()
        if isinstance(payload, dict) and payload.get("detail"):
            raise ValueError(str(payload["detail"]))
    except ValueError:
        raise
    except Exception:
        pass
    response.raise_for_status()


def parse_sse_chunk(line: str) -> dict | None:
    """Parse one `data: {json}` line from POST /ask/stream. Other lines are ignored."""
    stripped = line.strip()
    if not stripped.startswith("data:"):
        return None
    payload = stripped[len("data:") :].strip()
    if not payload or payload == "[DONE]":
        return None
    try:
        value = json.loads(payload)
    except json.JSONDecodeError:
        return None
    if not isinstance(value, dict):
        return None
    return value


class AskPodcastClient(Protocol):
    def health(self) -> dict: ...

    def episodes(self) -> list[dict]: ...

    def ingest(self, video_url_or_id: str, show: str, speaker: str) -> dict: ...

    def ask(self, question: str, mode: str = "balanced") -> dict: ...

    def ask_stream(self, question: str, mode: str = "balanced") -> Iterator[dict]: ...


PodSeekClient = AskPodcastClient


class RemoteClient:
    """HTTP client for a running PodSeek FastAPI server."""

    def __init__(self, base_url: str = DEFAULT_API_URL):
        self.base_url = base_url.rstrip("/")

    def health(self) -> dict:
        with httpx.Client(timeout=5.0) as client:
            response = client.get(f"{self.base_url}/health")
            _raise_clean_api_error(response)
            return response.json()

    def episodes(self) -> list[dict]:
        with httpx.Client(timeout=10.0) as client:
            response = client.get(f"{self.base_url}/episodes")
            _raise_clean_api_error(response)
            return list(response.json())

    def ingest(self, video_url_or_id: str, show: str, speaker: str) -> dict:
        with httpx.Client(timeout=300.0) as client:
            response = client.post(
                f"{self.base_url}/ingest",
                json={"video_url_or_id": video_url_or_id, "show": show, "speaker": speaker},
            )
            _raise_clean_api_error(response)
            return response.json()

    def ask(self, question: str, mode: str = "balanced") -> dict:
        with httpx.Client(timeout=120.0) as client:
            response = client.post(f"{self.base_url}/ask", json={"question": question, "mode": mode})
            _raise_clean_api_error(response)
            return response.json()

    def ask_stream(self, question: str, mode: str = "balanced") -> Iterator[dict]:
        with httpx.Client(timeout=120.0) as client:
            with client.stream(
                "POST", f"{self.base_url}/ask/stream", json={"question": question, "mode": mode}
            ) as response:
                _raise_clean_api_error(response)
                for line in response.iter_lines():
                    event = parse_sse_chunk(line)
                    if event is not None:
                        yield event


class InProcessClient:
    """Call the existing FastAPI handlers and graph inside this process."""

    def health(self) -> dict:
        from app.api.routes import health_check

        return health_check()

    def episodes(self) -> list[dict]:
        from app.api.routes import list_episodes

        return [ep.model_dump() for ep in list_episodes()]

    def ingest(self, video_url_or_id: str, show: str, speaker: str) -> dict:
        from fastapi import HTTPException

        from app.api.routes import ingest_episode
        from app.schemas import IngestRequest

        try:
            result = ingest_episode(
                IngestRequest(video_url_or_id=video_url_or_id, show=cast(Show, show), speaker=speaker)
            )
            return result.model_dump()
        except HTTPException as exc:
            raise ValueError(str(exc.detail)) from exc

    def ask(self, question: str, mode: str = "balanced") -> dict:
        from typing import Literal

        from app.api.routes import ask_question
        from app.schemas import AskRequest

        mode_val = cast(
            Literal["turbo", "balanced", "rigorous"], mode if mode in {"turbo", "balanced", "rigorous"} else "balanced"
        )
        result = ask_question(AskRequest(question=question, mode=mode_val))
        return result.model_dump()

    def ask_stream(self, question: str, mode: str = "balanced") -> Iterator[dict]:
        from app.api.routes import iter_agent_events

        yield from iter_agent_events(question, mode=mode)


def make_client() -> RemoteClient | InProcessClient:
    """remote (default) uses PODSEEK_API_URL / ASKPODCAST_API_URL. inprocess imports the API handlers."""
    mode = (os.getenv("PODSEEK_UI_MODE") or os.getenv("ASKPODCAST_UI_MODE", "remote")).strip().lower()
    if mode == "inprocess":
        return InProcessClient()
    url = os.getenv("PODSEEK_API_URL") or os.getenv("ASKPODCAST_API_URL", DEFAULT_API_URL)
    return RemoteClient(url)
