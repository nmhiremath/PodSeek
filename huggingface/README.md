---
title: PodSeek
emoji: 🎙️
colorFrom: blue
colorTo: indigo
sdk: gradio
app_file: huggingface/app.py
pinned: false
---

# PodSeek

Gradio client for the Corrective RAG podcast agent.

This Space is meant to be created from the **full repository**, with the app file set to `huggingface/app.py`. A root-level `app.py` would shadow the Python `app/` package.

## Point it at a public API

Set a Space secret or variable:

```
ASKPODCAST_API_URL=https://your-public-api.example.com
ASKPODCAST_UI_MODE=remote
```

The UI calls `POST /ingest`, `POST /ask`, and `POST /ask/stream`. It does not run the graph itself.

Hugging Face installs the repository-root `requirements.txt` for a full-repo Space. `huggingface/requirements.txt` is the slim Gradio + httpx list, for a mirror that only proxies a public API.

## In-process demo

`ASKPODCAST_UI_MODE=inprocess` loads the compiled LangGraph inside the Space. That needs the full dependency set, a model API key, and a Chroma directory that already contains an episode. Leave this off on a free Space.

If the API is down, `ASKPODCAST_DEMO_FALLBACK` (on by default in `huggingface/app.py`) shows one canned citation instead of a blank error.

<!-- GIF placeholder: docs/demo.gif -->
