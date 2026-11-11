# 14. AskPodcast to PodSeek Rebrand and Backward Compatibility

> Recorded retroactively on 2026-11-10; decision originally made in commit `4d0697c` and finalized across all modules in commit `d4c0068` (PR #2).

## Status
Accepted

## Context
The project was originally scaffolded under the descriptive working title `AskPodcast`. As the system evolved from a simple prototype into a multi-tier agentic search engine featuring custom Bento Studio styling, interactive workflow flowcharts, and production-grade Corrective RAG, a distinct, professional brand identity was required: **PodSeek**. However, an abrupt rename risked breaking existing deployments, Docker Compose setups, client scripts, and environment variable configurations.

## Decision
Rebrand the user-facing product, API headers, Gradio UI, and documentation to **PodSeek**, while maintaining strict backward compatibility for all legacy `ASKPODCAST_*` configuration hooks:
1. Environment variables prioritize `PODSEEK_*` with fallback to `ASKPODCAST_*` (e.g. `PODSEEK_API_URL` or `ASKPODCAST_API_URL`, `PODSEEK_UI_MODE` or `ASKPODCAST_UI_MODE`).
2. Client protocol exports `PodSeekClient` as the primary protocol while retaining `AskPodcastClient = PodSeekClient` as a typed alias in `ui/client.py`.
3. Docker Compose container names, package docstrings, LangSmith project tags, and test fixtures updated to PodSeek.

## Alternatives Considered
1. **Hard Breaking Cutover:** Immediately deprecate and drop all `ASKPODCAST_*` variables. Rejected because existing cloud deployments and test scripts would immediately fail on upgrade.
2. **Dual-Branded Hybrid:** Retain `AskPodcast` for backend modules and `PodSeek` for UI only. Rejected as confusing and inconsistent for open-source contributors.

## Consequences
### Good
- Polished, cohesive product identity with custom brand badges, favicons, and social preview meta tags.
- Zero breaking changes for existing automated setups or environment files using legacy variable names.
- Clean code cleanliness without dead branches or duplicate logic.

### Bad
- Maintaining fallback `or os.getenv("ASKPODCAST_*")` checks adds minor boilerplate across configuration resolution points.

## Evidence
- `ui/client.py`: `AskPodcastClient = PodSeekClient` backward-compatible protocol alias.
- `app/api/routes.py`: Fallback support for `ASKPODCAST_*` environment variables.
- `app/__init__.py`, `ui/__init__.py`: Package docstrings updated to PodSeek.
- Git commits: `4d0697c`, `d4c0068`.
