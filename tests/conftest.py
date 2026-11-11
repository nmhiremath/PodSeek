"""Pytest test harness configuration: strictly disable LangSmith tracing during test runs."""

from __future__ import annotations

import os

import langsmith
import langsmith.utils
import pytest

# At module top level, before any app import, ensure tracing environment variables are forced to false.
os.environ["LANGSMITH_TRACING"] = "false"
os.environ["LANGCHAIN_TRACING_V2"] = "false"
_cache_clear = getattr(langsmith.utils.get_env_var, "cache_clear", None)
if callable(_cache_clear):
    _cache_clear()


@pytest.fixture(autouse=True)
def disable_tracing_context():
    """Run each test inside langsmith.tracing_context(enabled=False)."""
    cache_clear = getattr(langsmith.utils.get_env_var, "cache_clear", None)
    if callable(cache_clear):
        cache_clear()
    with langsmith.tracing_context(enabled=False):
        yield
    if callable(cache_clear):
        cache_clear()
