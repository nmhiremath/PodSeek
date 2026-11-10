"""Env gate for optional LangSmith tracing. No network."""

import os

from app.observability import configure_tracing, trace_config


def test_tracing_stays_off_without_credentials(monkeypatch):
    monkeypatch.delenv("LANGCHAIN_TRACING_V2", raising=False)
    monkeypatch.delenv("LANGCHAIN_API_KEY", raising=False)

    assert configure_tracing() is False
    assert os.environ["LANGCHAIN_TRACING_V2"] == "false"


def test_tracing_stays_off_when_flag_is_set_without_a_key(monkeypatch):
    monkeypatch.setenv("LANGCHAIN_TRACING_V2", "true")
    monkeypatch.setenv("LANGCHAIN_API_KEY", "")

    assert configure_tracing() is False
    assert os.environ["LANGCHAIN_TRACING_V2"] == "false"


def test_tracing_turns_on_when_flag_and_key_are_set(monkeypatch):
    monkeypatch.setenv("LANGCHAIN_TRACING_V2", "yes")
    monkeypatch.setenv("LANGCHAIN_API_KEY", "lsv2-test")
    monkeypatch.delenv("LANGCHAIN_PROJECT", raising=False)

    assert configure_tracing() is True
    assert os.environ["LANGCHAIN_TRACING_V2"] == "yes"
    assert os.environ["LANGCHAIN_PROJECT"] == "podseek"


def test_existing_project_name_is_kept(monkeypatch):
    monkeypatch.setenv("LANGCHAIN_TRACING_V2", "true")
    monkeypatch.setenv("LANGCHAIN_API_KEY", "lsv2-test")
    monkeypatch.setenv("LANGCHAIN_PROJECT", "custom-project")

    assert configure_tracing() is True
    assert os.environ["LANGCHAIN_PROJECT"] == "custom-project"


def test_trace_config_names_ingest_separately():
    ask = trace_config("/ask")
    ingest = trace_config("/ingest")

    assert ask.get("run_name") == "podseek_ask"
    assert ingest.get("run_name") == "podseek_ingest"
    assert ask.get("tags") == ["podseek", "crag"]
    assert ask.get("metadata") == {"path": "/ask"}
    assert (ingest.get("metadata") or {}).get("path") == "/ingest"
