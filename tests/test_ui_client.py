"""SSE parsing, client mode selection, and pure UI components. Does not import Gradio."""

import re

from app.ingestion.youtube import is_huberman_channel
from ui.client import InProcessClient, RemoteClient, make_client, parse_sse_chunk
from ui.components import (
    _is_submittable_question,
    load_theme_css,
    render_chat_session_html,
    render_episodes_html,
    render_head_meta_html,
    render_header_brand_html,
    render_header_controls_html,
    render_ingest_status_html,
    render_ingest_workflow_graph_html,
    render_mode_slider_html,
    render_workflow_graph_html,
)


def test_is_submittable_question():
    assert _is_submittable_question("") is False
    assert _is_submittable_question("   ") is False
    assert _is_submittable_question("ab") is False
    assert _is_submittable_question(" ab ") is False
    assert _is_submittable_question("abc") is True
    assert _is_submittable_question("  sleep  ") is True
    assert _is_submittable_question(None) is False
    notice_chat = render_chat_session_html([], episode_count=23, notice="Enter a question of at least 3 characters.")
    assert "ap-composer-notice" in notice_chat
    assert "Enter a question of at least 3 characters." in notice_chat


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
    monkeypatch.delenv("ASKPODCAST_API_URL", raising=False)
    monkeypatch.setenv("PODSEEK_API_URL", "http://example.test:9000/")
    remote = make_client()
    assert isinstance(remote, RemoteClient)
    assert remote.base_url == "http://example.test:9000"

    monkeypatch.setenv("PODSEEK_UI_MODE", "inprocess")
    inproc = make_client()
    assert isinstance(inproc, InProcessClient)
    assert inproc.health() == {"status": "ok", "app": "PodSeek"}


def test_theme_css_and_components_render_without_gradio():
    css = load_theme_css("theme.css")
    assert "--bg-canvas" in css
    assert ".wf-node" in css
    assert "a.gai-pill" in css

    graph = render_workflow_graph_html(active_node="rewrite_query", chunks=4, relevant=0, rewrites=1, mode="rigorous")
    assert "is-retrying" in graph
    assert "Rewrites: 1 / 2" in graph
    assert "Retries &lt; 2?" in graph

    balanced_graph = render_workflow_graph_html(active_node="generate", mode="balanced", top_distance=0.28)
    assert "Workflow · Balanced RAG" in balanced_graph
    assert "dist &lt; 0.35?" in balanced_graph
    assert "Skip Grading" in balanced_graph
    assert "dist: 0.28" in balanced_graph

    turbo_graph = render_workflow_graph_html(active_node="generate", mode="turbo")
    assert "Workflow · Turbo RAG" in turbo_graph
    assert "⚡ Fused Bypass" in turbo_graph
    assert "✨ Fused Generate &amp; Cite" in turbo_graph

    slider_turbo = render_mode_slider_html("turbo")
    assert "is-turbo" in slider_turbo
    assert "ms-thumb" in slider_turbo
    assert "Turbo" in slider_turbo

    slider_bal = render_mode_slider_html("balanced")
    assert "is-balanced" in slider_bal
    assert "Balanced" in slider_bal
    assert "cycle-icon-badge" in slider_bal
    assert "podSeekCycleMode" in slider_bal
    assert "cycle-chevron" not in slider_bal

    slider_rig = render_mode_slider_html("rigorous")
    assert "is-rigorous" in slider_rig
    assert "Rigorous" in slider_rig

    aborted_graph = render_workflow_graph_html(
        active_node="abort", chunks=4, relevant=0, rewrites=2, done=True, aborted=True, mode="rigorous"
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
    assert 'id="ap-last-turn"' in chat
    assert 'id="ap-last-answer"' in chat
    assert 'data-turn-count="1"' in chat
    assert 'data-turn-done="true"' in chat
    assert "<code>" not in chat
    assert ")." not in chat

    empty_chat = render_chat_session_html([], episode_count=50)
    assert "Find the moment Huberman said it." in empty_chat
    assert "Andrew Huberman is a Stanford neuroscientist" in empty_chat
    assert "50 most viewed episodes" in empty_chat
    assert "Search " in empty_chat and "most viewed episodes" in empty_chat
    assert "ap-kb-count-link" in empty_chat
    assert "Pick a topic or ask a question" in empty_chat
    assert "Choose a mode: Turbo is fast, Rigorous checks every source" in empty_chat
    assert "Tap a timestamp to hear it" in empty_chat
    assert "If the episodes don't cover it, PodSeek says so instead of guessing" in empty_chat
    assert "Independent project, not affiliated with Huberman Lab. Not medical advice." in empty_chat

    refusal_chat = render_chat_session_html(
        [
            {
                "question": "What are the optimal sauna heat protocols for growth hormone release?",
                "answer": "I could not find any relevant information in the podcast transcripts to answer your question.",
                "citations": [],
            }
        ]
    )
    assert "Answers come only from indexed episodes." in refusal_chat


def test_is_huberman_channel_verifier():
    assert is_huberman_channel("Andrew Huberman") is True
    assert is_huberman_channel("Huberman Lab Clips") is True
    assert is_huberman_channel("Rick Astley") is False
    assert is_huberman_channel("") is False


def test_top_50_episodes_list_integrity():
    from scripts.ingest_top_episodes import TOP_50_HUBERMAN_EPISODES

    assert len(TOP_50_HUBERMAN_EPISODES) == 50
    ids = [ep["id"] for ep in TOP_50_HUBERMAN_EPISODES]
    assert len(set(ids)) == 50, "Duplicate episode ID found in TOP_50_HUBERMAN_EPISODES"
    for ep in TOP_50_HUBERMAN_EPISODES:
        assert ep["id"] and len(ep["id"]) == 11, f"Invalid YouTube ID: {ep['id']}"
        assert ep["title"] and len(ep["title"]) > 5, f"Invalid episode title: {ep['title']}"


def test_workflow_all_modes_and_aborted_states():
    # Balanced mode abort state
    bal_aborted = render_workflow_graph_html(
        active_node="abort", chunks=4, relevant=0, rewrites=1, done=True, aborted=True, mode="balanced"
    )
    assert "Workflow · Balanced RAG" in bal_aborted
    assert "is-aborted" in bal_aborted
    assert "Max retries (1/1)" in bal_aborted

    # Turbo mode completion
    turbo_done = render_workflow_graph_html(
        active_node="generate", chunks=4, relevant=4, rewrites=0, done=True, mode="turbo"
    )
    assert "Workflow · Turbo RAG" in turbo_done
    assert "✓ Done" in turbo_done

    # Rigorous mode multiple rewrites
    rig_retry = render_workflow_graph_html(
        active_node="rewrite_query", chunks=4, relevant=0, rewrites=2, mode="rigorous"
    )
    assert "Workflow · Corrective RAG" in rig_retry
    assert "Rewrites: 2 / 2" in rig_retry


def test_theme_css_contains_mobile_scaling_and_capsule_tokens():
    css = load_theme_css("theme.css")
    assert "scale(0.88)" in css
    assert "scale(0.80)" in css
    assert "scale(0.72)" in css
    assert ".ap-ingest-capsule" in css
    assert ".ap-distill-capsule" in css
    assert ".ap-presets-carousel" in css
    assert "button.ap-mode-cycle-btn" in css
    assert "--ap-chat-h" in css
    assert "--ap-studio-h" in css
    assert "--ap-mobile-nav-bottom" in css
    assert "#ap-studio-view .pending" in css
    assert ".ap-lib-btn-label" in css
    assert ".ap-empty-hero" in css
    assert ".ap-empty-title" in css
    assert ".ap-empty-steps" in css
    assert ".ap-step-num" in css
    assert ".ap-empty-footnote" in css
    assert "a.gai-pill > span:not(.gai-yt-circle)" in css
    assert "ap-lib-btn-label" in render_header_controls_html()
    assert '<h1 class="ap-brand-title">PodSeek</h1>' in render_header_brand_html()
    head_meta = render_head_meta_html()
    assert "maximum-scale" not in head_meta
    assert 'rel="icon" type="image/svg+xml"' in head_meta
    assert "%3EPS%3C/text%3E" in head_meta
    assert 'content="https://podseek.onrender.com/"' in head_meta
    assert 'content="Corrective RAG over Huberman Lab transcripts with timestamp citations."' in head_meta
    meta_tags = "".join(re.findall(r"<meta\b[^>]*>", head_meta, re.IGNORECASE))
    assert "gradio" not in meta_tags.lower()


def test_goatcounter_page_analytics(monkeypatch):
    monkeypatch.delenv("GOATCOUNTER_CODE", raising=False)
    assert "data-goatcounter" not in render_head_meta_html()

    monkeypatch.setenv("GOATCOUNTER_CODE", "")
    assert "data-goatcounter" not in render_head_meta_html()

    monkeypatch.setenv("GOATCOUNTER_CODE", "podseek")
    html_out = render_head_meta_html()
    assert 'data-goatcounter="https://podseek.goatcounter.com/count"' in html_out
    assert 'src="//gc.zgo.at/count.js"' in html_out
    assert "{code}" not in html_out

    for bad_code in ["podseek app", "podseek_app", "PODSEEK", "bad/code", "<script>alert(1)</script>"]:
        monkeypatch.setenv("GOATCOUNTER_CODE", bad_code)
        assert "data-goatcounter" not in render_head_meta_html()


def test_system_theme_early_resolution_script():
    """Verify that head meta includes early theme resolution script supporting system theme and localStorage."""
    head_meta = render_head_meta_html()
    assert "podSeekApplyTheme" in head_meta
    assert "prefers-color-scheme: dark" in head_meta
    assert "podseek_theme" in head_meta
    assert "podSeekApplyTheme" in render_header_controls_html()
    assert "localStorage.setItem('podseek_theme'" in render_header_controls_html()


def test_mobile_onboarding_css_structure():
    """Assert mobile onboarding steps/intro rules are consolidated without absolute positioning."""
    import re

    css = load_theme_css("theme.css")

    # 1. Assert mobile media query sets flex-direction: column on steps container
    assert "@media (max-width: 640px)" in css
    media_idx = css.find("@media (max-width: 640px)")
    assert media_idx != -1

    # Extract entire @media (max-width: 640px) block by matching braces
    start_brace = css.find("{", media_idx)
    assert start_brace != -1
    brace_count = 0
    end_brace = -1
    for i in range(start_brace, len(css)):
        if css[i] == "{":
            brace_count += 1
        elif css[i] == "}":
            brace_count -= 1
            if brace_count == 0:
                end_brace = i
                break
    assert end_brace != -1
    mobile_css = css[start_brace:end_brace]

    assert ".ap-empty-steps" in mobile_css
    assert "flex-direction: column" in mobile_css

    # 2. Assert no rule on steps or intro uses position: absolute
    onboarding_patterns = [
        r"\.ap-empty-hero",
        r"\.ap-empty-title",
        r"\.ap-empty-intro",
        r"\.ap-empty-steps",
        r"\.ap-empty-step",
        r"\.ap-step-num",
        r"\.ap-step-text",
        r"\.ap-empty-footnote",
    ]
    for match in re.finditer(r"([^{]+)\{([^}]+)\}", css):
        selector, body = match.group(1), match.group(2)
        if any(re.search(pat, selector) for pat in onboarding_patterns):
            assert "position: absolute" not in body, (
                f"Onboarding rule '{selector.strip()}' must not use position: absolute"
            )
