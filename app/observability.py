"""Optional LangSmith tracing with agent-based addressing and privacy anonymization.

Tracing stays off unless LANGSMITH_TRACING is on, LANGSMITH_API_KEY is non-empty,
and both LANGSMITH_AGENT_ID and LANGSMITH_AGENT_ENVIRONMENT are set.
"""

from __future__ import annotations

import functools
import inspect
import logging
import os
import re
from collections.abc import Callable
from typing import Any

import langsmith.utils
from dotenv import load_dotenv
from langchain_core.runnables import RunnableConfig
from langsmith import Client, tracing_context
from langsmith.anonymizer import StringNodeRule, create_anonymizer

load_dotenv()

logger = logging.getLogger(__name__)

_TRUE_VALUES = {"1", "true", "yes"}
_DEPRECATION_WARNED = False

# Anonymizer masking email addresses and phone numbers
_ANONYMIZER_RULES: list[StringNodeRule] = [
    {"pattern": re.compile(r"[\w.+-]+@[\w-]+\.[\w.-]+"), "replace": "<email>"},
    {"pattern": re.compile(r"\(?\b[0-9]{3}\)?[-.\s]?[0-9]{3}[-.\s]?[0-9]{4}\b"), "replace": "<phone>"},
]
anonymizer_client: Client = Client(anonymizer=create_anonymizer(_ANONYMIZER_RULES))


def _clear_env_var_cache() -> None:
    """Clear LangSmith env var LRU cache."""
    cache_clear = getattr(langsmith.utils.get_env_var, "cache_clear", None)
    if callable(cache_clear):
        cache_clear()


def configure_tracing() -> bool:
    """Enable LangSmith only when the operator opted in, provided a key, and configured the agent address.

    Returns True when tracing is on; False otherwise.
    When off, both LANGSMITH_TRACING and LANGCHAIN_TRACING_V2 are set to 'false'.
    """
    global _DEPRECATION_WARNED

    # Read new names first, fall back to legacy with a one-time deprecation log line
    flag_val = os.getenv("LANGSMITH_TRACING")
    api_key = os.getenv("LANGSMITH_API_KEY")

    if flag_val is None and os.getenv("LANGCHAIN_TRACING_V2") is not None:
        if not _DEPRECATION_WARNED:
            logger.warning("LANGCHAIN_TRACING_V2 is deprecated; use LANGSMITH_TRACING instead.")
            _DEPRECATION_WARNED = True
        flag_val = os.getenv("LANGCHAIN_TRACING_V2")

    if not api_key and os.getenv("LANGCHAIN_API_KEY"):
        if not _DEPRECATION_WARNED:
            logger.warning("LANGCHAIN_API_KEY is deprecated; use LANGSMITH_API_KEY instead.")
            _DEPRECATION_WARNED = True
        api_key = os.getenv("LANGCHAIN_API_KEY")

    flag = (flag_val or "").strip().lower()
    key = (api_key or "").strip()
    agent_id = (os.getenv("LANGSMITH_AGENT_ID") or "").strip()
    agent_env = (os.getenv("LANGSMITH_AGENT_ENVIRONMENT") or "").strip()

    is_on = (flag in _TRUE_VALUES) and bool(key) and bool(agent_id) and bool(agent_env)

    if not is_on:
        os.environ["LANGSMITH_TRACING"] = "false"
        os.environ["LANGCHAIN_TRACING_V2"] = "false"
        _clear_env_var_cache()
        return False

    os.environ["LANGSMITH_TRACING"] = "true"
    if api_key and not os.getenv("LANGSMITH_API_KEY"):
        os.environ["LANGSMITH_API_KEY"] = key
    os.environ.pop("LANGCHAIN_TRACING_V2", None)

    # Pop conflicting project/session destination settings
    for conflict_var in ("LANGSMITH_PROJECT", "LANGCHAIN_PROJECT", "LANGCHAIN_SESSION"):
        if conflict_var in os.environ:
            val = os.environ.pop(conflict_var)
            logger.warning(
                "Removed conflicting destination setting %s=%r; LangSmith agent-based workspace uses LANGSMITH_AGENT_ID and LANGSMITH_AGENT_ENVIRONMENT instead.",
                conflict_var,
                val,
            )

    _clear_env_var_cache()
    return True


def trace_config(path: str, mode: str | None = None) -> RunnableConfig:
    """LangGraph/LangChain config. Harmless when tracing is disabled."""
    run_name = "podseek_ingest" if path == "/ingest" else "crag_graph"
    ui_mode = os.getenv("PODSEEK_UI_MODE", "remote")
    tags = ["podseek", "crag"]
    if mode:
        tags.append(mode)
    metadata: dict[str, Any] = {"path": path, "ui_mode": ui_mode}
    if mode:
        metadata["mode"] = mode
    return {
        "run_name": run_name,
        "tags": tags,
        "metadata": metadata,
    }


def with_anonymized_client(func: Callable[..., Any]) -> Callable[..., Any]:
    """Wrap a root traceable call inside tracing_context(client=anonymizer_client)."""
    if inspect.isgeneratorfunction(func):

        @functools.wraps(func)
        def gen_wrapper(*args: Any, **kwargs: Any):
            with tracing_context(client=anonymizer_client):
                yield from func(*args, **kwargs)

        return gen_wrapper
    else:

        @functools.wraps(func)
        def sync_wrapper(*args: Any, **kwargs: Any):
            with tracing_context(client=anonymizer_client):
                return func(*args, **kwargs)

        return sync_wrapper
