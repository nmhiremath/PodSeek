"""SSE parsing, client mode selection, and pure UI components. Does not import Gradio."""

from app.ingestion.youtube import is_huberman_channel
from ui.client import InProcessClient, RemoteClient, make_client, parse_sse_chunk
from ui.components import (
    load_theme_css,
    render_chat_session_html,
    render_episodes_html,
    render_ingest_status_html,
    render_ingest_workflow_graph_html,
    render_workflow_graph_html,
)


def test_parse_sse_chunk_reads_data_json():
    event = parse_sse_chunk('data: {"node": "retrieve", "chunks_retrieved": 4}')
    assert event == {"node": "retrieve", "chunks_retrieved": 4}


def test_parse_sse_chunk_ignores_noise():
    assert parse_sse_chunk("") is None
    assert parse_sse_chunk(": keep-alive") is None
    assert parse_sse_chunk("data: [1, 2]") is None
    assert parse_sse_chunk("data: {not json}") is None
    assert parse_sse_chunk("event: node_start") is None
    assert parse_sse_chunk("data: [DONE]") is None


def test_make_client_selects_remote_or_inprocess(monkeypatch):
    monkeypatch.delenv("PODSEEK_UI_MODE", raising=False)
    monkeypatch.delenv("ASKPODCAST_UI_MODE", raising=False)
    monkeypatch.setenv("ASKPODCAST_API_URL", "http://example.test:9000/")
    remote = make_client()
    assert isinstance(remote, RemoteClient)
    assert remote.base_url == "http://example.test:9000"

    monkeypatch.setenv("ASKPODCAST_UI_MODE", "inprocess")
    inproc = make_client()
    assert isinstance(inproc, InProcessClient)
    assert inproc.health() == {"status": "ok", "app": "PodSeek"}


def test_theme_css_and_components_render_without_gradio():
    css = load_theme_css("theme.css")
    assert "--bg-canvas" in css
    assert ".wf-node" in css
    assert "a.gai-pill" in css

    graph = render_workflow_graph_html(active_node="rewrite_query", chunks=4, relevant=0, rewrites=1)
    assert "is-retrying" in graph
    assert "Rewrites: 1 / 2" in graph
    assert "Retries &lt; 2?" in graph

    aborted_graph = render_workflow_graph_html(
        active_node="abort", chunks=4, relevant=0, rewrites=2, done=True, aborted=True
    )
    assert "is-aborted" in aborted_graph
    assert "Max retries (2/2)" in aborted_graph
    assert "Skipped" in aborted_graph

    ingest_graph = render_ingest_workflow_graph_html(active_step="chunk")
    assert "Workflow · Episode Ingestion" in ingest_graph
    assert "Huberman Lab?" in ingest_graph
    assert "3. Chunker" in ingest_graph

    ingest_aborted = render_ingest_workflow_graph_html(active_step="abort", error=True, abort_reason="Bryan Johnson")
    assert "is-aborted" in ingest_aborted
    assert "Bryan Johnson" in ingest_aborted

    loading_card = render_ingest_status_html("loading", "Chunking transcript...", "400w sliding window")
    assert "ap-spin" in loading_card
    assert "ap-shimmer-fill" in loading_card

    episodes = render_episodes_html(
        [
            {
                "episode_id": "QmOF0crdyRU",
                "episode_title": "Controlling Your Dopamine",
                "url": "https://youtu.be/QmOF0crdyRU",
            }
        ]
    )
    assert "Controlling Your Dopamine" in episodes
    assert "QmOF0crdyRU · Huberman Lab" not in episodes

    chat = render_chat_session_html(
        [
            {
                "question": "What causes a dopamine crash?",
                "answer": "**Baseline depletion** happens after steep spikes ([Controlling Your Dopamine @ 00:20:45], `[01:04:33]`).",
                "citations": [
                    {
                        "episode_id": "QmOF0crdyRU",
                        "episode_title": "Controlling Your Dopamine",
                        "timestamp": "00:20:45",
                        "url": "https://youtu.be/QmOF0crdyRU?t=1245",
                    },
                    {
                        "episode_id": "QmOF0crdyRU",
                        "episode_title": "Controlling Your Dopamine",
                        "timestamp": "01:04:33",
                        "url": "https://youtu.be/QmOF0crdyRU?t=3873",
                    },
                ],
            }
        ]
    )
    assert "<strong>Baseline depletion</strong>" in chat
    assert "gai-pill" in chat
    assert "Controlling Your Dopamine · 20:45" in chat
    assert "Controlling Your Dopamine · 01:04:33" in chat
    assert "<code>" not in chat
    assert ")." not in chat


def test_is_huberman_channel_verifier():
    assert is_huberman_channel("Andrew Huberman") is True
    assert is_huberman_channel("Huberman Lab Clips") is True
    assert is_huberman_channel("Rick Astley") is False
    assert is_huberman_channel("") is False
