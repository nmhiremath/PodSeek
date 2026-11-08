"""YouTube caption adapter: raw captions -> list[Segment].

Design: the network call (`fetch_raw_captions`) is separate from the pure
transform (`captions_to_segments`), so the transform is unit-testable offline.
"""

import re

from youtube_transcript_api import YouTubeTranscriptApi

from app.schemas import Segment, Show

# Caption noise like "[Music]" or "[Applause]"
_NOISE = re.compile(r"\[[^\]]*\]")

"""
Sample raw response returned by `fetch_raw_captions(video_id)`:
[
    {
        "text": "Welcome to the Huberman Lab Podcast,",
        "start": 0.0,
        "duration": 2.48
    },
    {
        "text": "where we discuss science and science-based tools",
        "start": 2.48,
        "duration": 2.16
    }
]
"""


def extract_video_id(url_or_id: str) -> str:
    """Extract standard 11-char YouTube video ID from a URL or raw ID."""
    clean = url_or_id.strip()
    patterns = [
        r"(?:v=|\/)([0-9A-Za-z_-]{11})(?:[&?]|$)",
        r"^([0-9A-Za-z_-]{11})$",
    ]
    for pat in patterns:
        match = re.search(pat, clean)
        if match:
            return match.group(1)
    return clean


def is_huberman_channel(author_name: str) -> bool:
    """Pure check: return True only when the YouTube channel belongs to Huberman Lab."""
    return "huberman" in author_name.strip().casefold()


def fetch_video_metadata(video_id: str) -> tuple[str, str]:
    """Fetch (title, author_name) using YouTube's public oEmbed endpoint (no API key needed)."""
    import httpx

    url = f"https://www.youtube.com/oembed?url=https://www.youtube.com/watch?v={video_id}&format=json"
    try:
        resp = httpx.get(url, timeout=5.0)
        if resp.status_code == 200:
            data = resp.json()
            title = str(data.get("title") or f"Episode {video_id}")
            author = str(data.get("author_name") or "")
            return title, author
    except Exception:
        pass
    return f"Episode {video_id}", ""


def fetch_video_title(video_id: str) -> str:
    """Fetch video title using YouTube's public oEmbed endpoint (no API key needed)."""
    title, _ = fetch_video_metadata(video_id)
    return title


def _create_youtube_session():
    """Create a requests.Session with human browser headers and optional cookiejar."""
    import http.cookiejar
    from pathlib import Path

    import requests

    session = requests.Session()
    session.headers.update(
        {
            "User-Agent": (
                "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36"
            ),
            "Accept-Language": "en-US,en;q=0.9",
            "Accept": "*/*",
            "Referer": "https://www.youtube.com/",
        }
    )

    # Check for optional exported cookies to bypass IP throttles
    for path in (Path("cookies.txt"), Path("data/cookies.txt"), Path("youtube_cookies.txt")):
        if path.exists():
            try:
                cj = http.cookiejar.MozillaCookieJar(path)
                cj.load(ignore_discard=True, ignore_expires=True)
                session.cookies.update(cj)
                break
            except Exception:
                pass

    return session


def fetch_raw_captions(video_id: str) -> list[dict]:
    """Network call. Returns [{'text': str, 'start': float, 'duration': float}, ...].

    Prioritizes manually created English captions (en, en-US, en-GB, en-CA) for highest
    accuracy and professional formatting, gracefully falling back to auto-generated
    captions when manual transcripts are not provided by the creator.
    """
    langs = ("en", "en-US", "en-GB", "en-CA")
    session = _create_youtube_session()
    api = YouTubeTranscriptApi(http_client=session)

    try:
        transcript_list = api.list(video_id)
        # 1. Prefer creator-uploaded manual captions first
        try:
            transcript = transcript_list.find_manually_created_transcript(langs)
        except Exception:
            # 2. Fall back to auto-generated speech recognition captions
            try:
                transcript = transcript_list.find_generated_transcript(langs)
            except Exception:
                # 3. Fall back to any matching language transcript
                transcript = transcript_list.find_transcript(langs)

        fetched = transcript.fetch()
        return fetched.to_raw_data()
    except Exception:
        # Direct fallback attempt
        fetched = api.fetch(video_id, languages=langs)
        return fetched.to_raw_data()


def captions_to_segments(
    raw: list[dict],
    *,
    show: Show,
    episode_id: str,
    episode_title: str,
    speaker: str,
) -> list[Segment]:
    """Pure transform: clean caption text and wrap each snippet in a Segment."""
    segments: list[Segment] = []
    for cap in raw:
        text = _NOISE.sub("", cap["text"]).replace("\n", " ").strip()
        if not text:  # snippet was only noise like "[Music]"
            continue
        segments.append(
            Segment(
                show=show,
                episode_id=episode_id,
                episode_title=episode_title,
                speaker=speaker,
                start_seconds=cap["start"],
                end_seconds=cap["start"] + cap["duration"],
                text=text,
            )
        )
    return segments
