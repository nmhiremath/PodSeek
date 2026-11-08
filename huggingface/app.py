"""Hugging Face Spaces entrypoint for PodSeek.

Deploy the full PodSeek repository as the Space and set the app file to
``huggingface/app.py``. Do not put an ``app.py`` at the repository root: it
would shadow the ``app/`` package.

Remote API (default, and the right choice for a free Space):
    ASKPODCAST_API_URL=https://your-public-api.example.com
    ASKPODCAST_UI_MODE=remote

In-process graph (only when the Space installs the full requirements.txt,
has a chat and embedding key, and has a persisted chroma_db):
    ASKPODCAST_UI_MODE=inprocess

ASKPODCAST_DEMO_FALLBACK defaults to true here so the Space can show one
canned answer before a public API is wired up.
"""

import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

os.environ.setdefault("ASKPODCAST_DEMO_FALLBACK", "true")

from ui.app import build_demo  # noqa: E402

demo = build_demo()

if __name__ == "__main__":
    demo.launch(show_api=False)
