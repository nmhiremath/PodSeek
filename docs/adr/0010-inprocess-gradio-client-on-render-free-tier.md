# 10. In-Process Gradio Client on Render Free Tier

> Recorded retroactively on 2026-11-10; decision originally made in commit `986dfb1` and refined in commit `826fa6e`.

## Status
Accepted

## Context
Render.com's free web service tier limits container resources to 512 MB of total RAM. Running a separate Uvicorn FastAPI backend process alongside a separate Gradio frontend process inside the same container (or across two containers) either exceeds the 512 MB memory boundary or requires multiple services. At the same time, decoupled microservice architecture (separate FastAPI API and Gradio client) is standard for local development and Docker deployments.

## Decision
Support dual client architectures via `ui/client.py`:
1. **RemoteClient:** Connects over HTTP/SSE to a standalone FastAPI server (`http://localhost:8000`).
2. **InProcessClient:** Directly imports and invokes FastAPI route handlers and LangGraph event generators (`iter_agent_events`) within the same Python process.

On Render (`render.yaml`), `PODSEEK_UI_MODE` is set to `inprocess`, and the entrypoint executes `python -m ui.app`. When `make_client()` detects `inprocess` mode (or no remote URL is configured), it selects `InProcessClient`. The Dockerfile remains dedicated to running the standalone FastAPI API container.

## Alternatives Considered
1. **Supervisord / Dual Process in Docker:** Run Uvicorn on port 8000 and Gradio on port 7860 in the same container. Rejected because two concurrent Python runtimes with LangGraph and ChromaDB loaded simultaneously exceeded 512 MB RAM, triggering OOM kills on Render.
2. **Separate Render Services:** Deploy one web service for FastAPI and another for Gradio. Rejected because Render free tier allows only one active free web service per account without payment.

## Consequences
### Good
- Fits comfortably within 512 MB RAM: memory footprint remains at ~280–350 MB on Render free tier.
- Eliminates internal HTTP network overhead and serialization latency on single-service deployments.
- Maintains complete API parity: `InProcessClient` and `RemoteClient` share the exact same schemas, serialization, and event iterator logic.

### Bad
- In-process execution couples UI threads with agent computation; long CPU-bound tasks in the agent could block the Gradio event loop if not properly awaited.
- Docker container runs FastAPI while cloud deployment runs Gradio in-process, creating a slight runtime topology divergence documented in `Dockerfile`.

## Evidence
- `render.yaml`: `startCommand: python -m ui.app`, `PODSEEK_UI_MODE: inprocess`.
- `ui/client.py`: `InProcessClient`, `RemoteClient`, `make_client()`.
- `Dockerfile`: Documented role running Uvicorn API.
- Git commits: `986dfb1`, `826fa6e`, `d4c0068`.
