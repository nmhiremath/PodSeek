# 5. Speaker-Aware Sliding-Window Chunking with Timestamp Bounds

> Recorded retroactively on 2026-11-10; decision originally made in commit `d6b1795`.

## Status
Accepted

## Context
Raw YouTube caption tracks consist of fragmented, 2-to-5-second audio snippets without punctuation or paragraph structure. Blind character-based or token-based chunking splits sentences arbitrarily and destroys speaker attribution. Furthermore, citations require pinpoint timestamp ranges (`start_seconds`, `end_seconds`) so users can click deep links to watch the exact moment on YouTube.

## Decision
Implement a pure, speaker-aware sliding-window chunking algorithm (`chunk_segments` in `app/ingestion/chunking.py`). The chunker accumulates words up to a target size (`target_words = 200`), maintains an overlap window (`overlap_words = 40`), and immediately forces a chunk boundary if the speaker transitions. Each chunk inherits the start timestamp of its first segment and the end timestamp of its final segment.

## Alternatives Considered
1. **Fixed Token Chunking (RecursiveCharacterTextSplitter):** Ignores speaker turns and caption segment boundaries, making accurate timestamp deep-linking difficult.
2. **Semantic Similarity Splitters (e.g. embedding-distance boundary detection):** Requires running an embedding model over every sentence during ingestion, adding significant ingestion overhead with minimal improvement over sliding windows on conversational speech.
3. **Single Segment as Chunk:** Indexing each 3-second caption snippet. Rejected because individual snippets lack sufficient semantic context for vector retrieval.

## Consequences
### Good
- Crisp speaker attribution: a chunk never mingles statements from two different speakers.
- Accurate YouTube deep linking: every chunk preserves exact `start_seconds` and `end_seconds` corresponding to real video playback time.
- Sufficient semantic density: ~200 words (~1.5 minutes of speech) provides ideal semantic context for vector embedding while remaining compact.
- Pure function: `chunk_segments` has no I/O or network dependencies, making it 100% unit-testable offline.

### Bad
- Monologues (e.g. Huberman speaking alone for 2 hours) rely entirely on the word-count threshold rather than natural semantic topic shifts.
- Overlapping segments duplicate some words across consecutive chunks, slightly increasing the total vector store index size.

## Evidence
- `app/ingestion/chunking.py`: `chunk_segments(segments, target_words=200, overlap_words=40)`.
- `app/schemas/transcripts.py`: `Segment` and `Chunk` Pydantic models.
- `tests/test_chunking.py`: Boundary and speaker transition unit tests.
- Git commit: `d6b1795`.
