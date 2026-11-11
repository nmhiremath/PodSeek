# Capability Specification: Ingestion

## Purpose
The ingestion capability fetches YouTube transcripts, enforces channel guardrails (Phase 1: Huberman Lab), performs speaker-aware sliding-window chunking with preserved timestamps, generates structured multi-tier summaries, and indexes chunks into ChromaDB.

## Requirements

### Requirement: YouTube ID Extraction and Channel Verification
The system SHALL parse 11-character YouTube video IDs from URLs and verify that the video belongs to the Huberman Lab channel via oEmbed metadata.

#### Scenario: Valid Huberman Lab video URL
- **WHEN** a URL like `https://www.youtube.com/watch?v=QmOF0crdyRU` is submitted to `/ingest`
- **THEN** the video ID `QmOF0crdyRU` is extracted
- **AND** `fetch_video_metadata` retrieves the channel title and author
- **AND** `is_huberman_channel` verifies that `"huberman"` is present in the author name.

#### Scenario: Non-Huberman video rejection
- **WHEN** a video from a non-Huberman channel is submitted
- **THEN** `is_huberman_channel` evaluates to `False`
- **AND** the API rejects the request with HTTP 400 and detail message `"PodSeek Phase 1 only indexes Huberman Lab episodes."`

### Requirement: Captions Fetching and Noise Cleaning
The system SHALL retrieve YouTube captions prioritizing creator-provided manual English transcripts over auto-generated transcripts, stripping non-speech audio cues.

#### Scenario: Caption extraction and cleaning
- **WHEN** captions are fetched for an episode
- **THEN** manual English captions (`en`, `en-US`, `en-GB`, `en-CA`) are fetched if available, falling back to auto-generated captions
- **AND** bracketed audio noise matching `\[[^\]]*\]` (e.g. `[Music]`, `[Applause]`) is stripped from segment text.

### Requirement: Speaker-Aware Sliding-Window Chunking
The system SHALL merge contiguous segments into chunks targeting ~200 words with ~40 words overlap, forcing chunk boundaries on speaker transitions while preserving exact timestamp bounds.

#### Scenario: Window chunking with speaker boundary
- **WHEN** segments are processed by `chunk_segments`
- **THEN** words accumulate up to `target_words = 200`
- **AND** if a segment changes speaker, the chunk closes immediately
- **AND** each chunk records exact `start_seconds` from the first segment and `end_seconds` from the last segment
- **AND** window advances using `overlap_words = 40`.

### Requirement: Structured Multi-Tier Summarization and Disk Caching
The system SHALL synthesize executive summaries, detailed summaries, key takeaways, and keywords using structured output, caching transcripts to disk.

#### Scenario: Episode analysis and persistence
- **WHEN** an episode is ingested
- **THEN** `EpisodeAnalysis` structured output extracts a short summary, long summary, 4-6 key takeaways, and 10-15 keywords
- **AND** raw transcripts and metadata are saved to `data/raw/huberman_lab/<episode_id>.json`
- **AND** chunks are indexed into ChromaDB.
