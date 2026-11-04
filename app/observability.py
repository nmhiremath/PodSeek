"""Optional LangSmith tracing.

Tracing stays off unless both LANGCHAIN_TRACING_V2 and LANGCHAIN_API_KEY are set.
LangChain reads those variables itself. This module only normalizes them and
builds the run config passed into existing graph calls.
"""

import os

from dotenv import load_dotenv
from langchain_core.runnables import RunnableConfig

load_dotenv()

_TRUE_VALUES = {"1", "true", "yes"}
DEFAULT_PROJECT = "askpodcast"


def configure_tracing() -> bool:
    """Enable LangSmith only when the operator opted in and supplied a key.

    Returns True when tracing is left on. When it is off, LANGCHAIN_TRACING_V2
    is forced to "false" so a partial environment cannot emit traces.
    """
    flag = os.getenv("LANGCHAIN_TRACING_V2", "").strip().lower()
    api_key = os.getenv("LANGCHAIN_API_KEY", "").strip()
    if flag not in _TRUE_VALUES or not api_key:
        os.environ["LANGCHAIN_TRACING_V2"] = "false"
        return False

    os.environ.setdefault("LANGCHAIN_PROJECT", DEFAULT_PROJECT)
    return True


def trace_config(path: str) -> RunnableConfig:
    """LangGraph/LangChain config. Harmless when tracing is disabled."""
    run_name = "askpodcast_ingest" if path == "/ingest" else "askpodcast_ask"
    return {
        "run_name": run_name,
        "tags": ["askpodcast", "crag"],
        "metadata": {"path": path},
    }
