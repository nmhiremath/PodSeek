# 12. Channel-Gated YouTube Ingestion

> Recorded retroactively on 2026-11-10; decision originally made in commit `4d0697c`.

## Status
Accepted

## Context
PodSeek's Phase 1 domain focus is Huberman Lab. When deployed as a public demo on Render, anyone with access to the UI or API could submit arbitrary YouTube URLs (e.g. music videos, news broadcasts, competitor podcasts) to `POST /ingest`. Ingesting arbitrary content pollutes the curated vector store index, degrades retrieval precision for health and science queries, and exhausts free-tier embedding and summarization quotas.

## Decision
Enforce a channel guardrail at the ingestion boundary. Before fetching raw captions or chunking audio, `fetch_video_metadata()` queries YouTube's public oEmbed endpoint (`https://www.youtube.com/oembed?url=...`) to retrieve the video author name without requiring a YouTube Data API v3 key. The pure function `is_huberman_channel(author_name)` verifies that `"huberman"` is present in the author name. Non-Huberman submissions are rejected immediately with HTTP 400 (`"Only Huberman Lab episodes can be ingested (detected channel: ...)"`).

## Alternatives Considered
1. **Google YouTube Data API v3:** Query the official API with an API key. Rejected because YouTube Data API v3 requires setting up a Google Cloud project with separate credentials and has a strict 10,000 daily quota unit limit. The public oEmbed endpoint requires no credentials and provides the channel name reliably.
2. **Open Ingestion (Any Channel):** Allow any valid YouTube URL to be ingested. Rejected because mixed corpora compromise retrieval domain boundaries and open the public demo to vector store spamming.
3. **Regex Whitelist on Video IDs:** Maintain a hardcoded whitelist of allowed video IDs. Rejected because it prevents legitimate ingestion of new Huberman Lab episodes released after deployment.

## Consequences
### Good
- Completely blocks unrelated YouTube videos from polluting the vector database.
- Zero API credentials required: uses YouTube's public oEmbed HTTP endpoint.
- Protects free-tier LLM summarization and embedding quotas from abuse.
- Clean user feedback: UI surfaces an explicit, understandable error message instead of failing cryptically during retrieval.

### Bad
- Huberman Lab episodes re-uploaded by third-party clip channels or guest appearances on other podcasts (e.g. Lex Fridman, Joe Rogan) are rejected in Phase 1 unless the channel author contains "Huberman".
- If YouTube alters or throttles its public oEmbed endpoint, channel resolution could fail.

## Evidence
- `app/ingestion/youtube.py`: `fetch_video_metadata()`, `is_huberman_channel()`.
- `app/api/routes.py`: `ingest_episode()` calling channel verification.
- `tests/test_youtube_adapter.py`: Offline tests for `is_huberman_channel()` and video ID parsing.
- Git commit: `4d0697c`.
