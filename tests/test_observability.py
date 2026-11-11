"""Env gate for optional LangSmith tracing. No network."""

from __future__ import annotations

import os
from unittest.mock import MagicMock

import langsmith.utils

from app.observability import configure_tracing, trace_config


def test_tracing_is_disabled_during_tests():
    """Assert tracing is never enabled during test runs."""
    assert not langsmith.utils.tracing_is_enabled()


def test_tracing_stays_off_without_credentials(monkeypatch):
    monkeypatch.delenv("LANGSMITH_TRACING", raising=False)
    monkeypatch.delenv("LANGCHAIN_TRACING_V2", raising=False)
    monkeypatch.delenv("LANGSMITH_API_KEY", raising=False)
    monkeypatch.delenv("LANGCHAIN_API_KEY", raising=False)

    assert configure_tracing() is False
    assert os.environ["LANGSMITH_TRACING"] == "false"
    assert os.environ["LANGCHAIN_TRACING_V2"] == "false"


def test_tracing_stays_off_with_half_agent_address(monkeypatch):
    monkeypatch.setenv("LANGSMITH_TRACING", "true")
    monkeypatch.setenv("LANGSMITH_API_KEY", "lsv2-test")

    # Only agent ID set
    monkeypatch.setenv("LANGSMITH_AGENT_ID", "podseek")
    monkeypatch.delenv("LANGSMITH_AGENT_ENVIRONMENT", raising=False)
    assert configure_tracing() is False
    assert os.environ["LANGSMITH_TRACING"] == "false"

    # Only agent environment set
    monkeypatch.delenv("LANGSMITH_AGENT_ID", raising=False)
    monkeypatch.setenv("LANGSMITH_AGENT_ENVIRONMENT", "local")
    assert configure_tracing() is False
    assert os.environ["LANGSMITH_TRACING"] == "false"


def test_tracing_turns_on_when_four_variables_set(monkeypatch):
    monkeypatch.setenv("LANGSMITH_TRACING", "true")
    monkeypatch.setenv("LANGSMITH_API_KEY", "lsv2-test")
    monkeypatch.setenv("LANGSMITH_AGENT_ID", "podseek")
    monkeypatch.setenv("LANGSMITH_AGENT_ENVIRONMENT", "local")
    monkeypatch.setenv("LANGCHAIN_TRACING_V2", "false")

    assert configure_tracing() is True
    assert os.environ["LANGSMITH_TRACING"] == "true"
    assert "LANGCHAIN_TRACING_V2" not in os.environ


def test_tracing_normalizes_yes_to_true(monkeypatch):
    monkeypatch.setenv("LANGSMITH_TRACING", "yes")
    monkeypatch.setenv("LANGSMITH_API_KEY", "lsv2-test")
    monkeypatch.setenv("LANGSMITH_AGENT_ID", "podseek")
    monkeypatch.setenv("LANGSMITH_AGENT_ENVIRONMENT", "production")

    assert configure_tracing() is True
    assert os.environ["LANGSMITH_TRACING"] == "true"


def test_project_variables_are_popped_when_agent_set(monkeypatch):
    monkeypatch.setenv("LANGSMITH_TRACING", "true")
    monkeypatch.setenv("LANGSMITH_API_KEY", "lsv2-test")
    monkeypatch.setenv("LANGSMITH_AGENT_ID", "podseek")
    monkeypatch.setenv("LANGSMITH_AGENT_ENVIRONMENT", "local")
    monkeypatch.setenv("LANGSMITH_PROJECT", "custom-project")
    monkeypatch.setenv("LANGCHAIN_PROJECT", "custom-legacy-project")
    monkeypatch.setenv("LANGCHAIN_SESSION", "custom-session")

    assert configure_tracing() is True
    assert "LANGSMITH_PROJECT" not in os.environ
    assert "LANGCHAIN_PROJECT" not in os.environ
    assert "LANGCHAIN_SESSION" not in os.environ


def test_trace_config_names_ingest_separately():
    ask = trace_config("/ask", mode="balanced")
    ingest = trace_config("/ingest")

    assert ask.get("run_name") == "podseek_ask"
    assert ingest.get("run_name") == "podseek_ingest"
    assert ask.get("tags") == ["podseek", "crag", "balanced"]
    assert ask.get("metadata") == {"path": "/ask", "mode": "balanced", "ui_mode": "remote"}
    assert (ingest.get("metadata") or {}).get("path") == "/ingest"


def test_inprocess_ui_startup_calls_tracing_gate(monkeypatch):
    called = False

    def mock_gate():
        nonlocal called
        called = True
        return False

    monkeypatch.setenv("PODSEEK_UI_MODE", "inprocess")
    monkeypatch.setattr("ui.app.configure_tracing", mock_gate)

    from ui.app import build_demo

    mock_client = MagicMock()
    mock_client.episodes.return_value = []
    monkeypatch.setattr("ui.app.make_client", lambda: mock_client)

    build_demo()
    assert called is True
