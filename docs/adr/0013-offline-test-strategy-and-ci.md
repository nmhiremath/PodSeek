# 13. Offline Test Strategy and CI Verification

> Recorded retroactively on 2026-11-10; decision originally made in commit `f4f7330` and formalized in CI in commit `d4c0068` (PR #2).

## Status
Accepted

## Context
AI-powered applications often suffer from brittle, slow, and expensive test suites that make live LLM API calls during continuous integration. Live tests fail spuriously due to third-party rate limits, network timeouts, prompt non-determinism, or missing API credentials. Conversely, lack of automated CI allows regressions in schema validation, SSE parsing, and graph edge logic to slip into protected branches.

## Decision
Enforce a 100% offline testing strategy for automated continuous integration:
1. All network operations (`fetch_raw_captions`, YouTube metadata, vector store remote embeddings, LLM generation) are decoupled from pure transformation logic (`captions_to_segments`, `chunk_segments`, state graph edges, SSE parsers, evaluation metrics).
2. All 41 unit tests in `tests/` execute completely offline without network access or API keys.
3. GitHub Actions CI (`.github/workflows/ci.yml`) runs on every push and PR to `main`, executing Ruff linter (`ruff check .`) and Pytest (`pytest -v`) under Python 3.13.
4. Evaluation harness (`scripts/evaluate.py`) runs offline by default using static fixture answers, testing keyword overlap and citation link formats in milliseconds.

## Alternatives Considered
1. **Live Model Calls in CI:** Run live Gemini API calls with repository secrets. Rejected because API rate limits and network jitter create flaky builds, and billing charges accumulate on every pull request.
2. **VCR.py / Record-and-Replay HTTP Mocks:** Record real HTTP requests. Rejected as overly complex for pure logic tests, adding maintenance overhead whenever prompt wording changes slightly.

## Consequences
### Good
- Lightning-fast CI execution: full test suite of 41 tests runs in under 1 second.
- 100% deterministic builds: zero flakiness from network disruptions or external model provider outages.
- Free and accessible: anyone can clone the repository and run `pytest -v` immediately without creating Google AI Studio or OpenAI developer accounts.

### Bad
- Does not test live model API connectivity or end-to-end prompt adherence in CI (live evaluation remains an explicit manual operator workflow: `python -m scripts.evaluate --live`).

## Evidence
- `.github/workflows/ci.yml`: GitHub Actions workflow definition running `ruff check .` and `pytest -v`.
- `tests/`: 41 unit tests across schemas, chunking, agent graph routing, UI client, observability, and evaluation.
- `app/evaluation.py`: Offline evaluation fixtures.
- Git commits: `f4f7330`, `d6b1795`, `d4c0068`.
