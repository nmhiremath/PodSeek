"""Gradio UI controller and layout for PodSeek.

The widgets call AskPodcastClient. View rendering lives in `ui/components.py`
and stylesheets live in `ui/styles/theme.css`.
"""

import os
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Any

# Ensure repository root is on sys.path for `gradio ui/app.py` hot-reloading
_REPO_ROOT = str(Path(__file__).resolve().parent.parent)
if _REPO_ROOT not in sys.path:
    sys.path.insert(0, _REPO_ROOT)

import gradio as gr  # noqa: E402 # pyright: ignore[reportMissingImports]

from ui.client import AskPodcastClient, make_client  # noqa: E402
from ui.components import (  # noqa: E402
    format_citations,
    format_event,
    load_theme_css,
    render_chat_session_html,
    render_episodes_html,
    render_header_brand_html,
    render_ingest_status_html,
    render_ingest_workflow_graph_html,
    render_mode_slider_html,
    render_sse_log_html,
    render_stats_for_nerds_html,
    render_workflow_graph_html,
)

DEFAULT_SHOW = "huberman_lab"
DEFAULT_SPEAKER = "Andrew Huberman"

PRESET_QUESTIONS = [
    "What causes a dopamine crash and how do I prevent it?",
    "How does deliberate cold exposure affect dopamine levels?",
    "What is the mind-muscle connection?",
]

DEMO_ANSWER = (
    "**Viewing bright sunlight** within 30–60 minutes of waking triggers an optimal cortisol peak "
    "and elevates baseline dopamine levels throughout the day [00:20:45]."
)
DEMO_CITATIONS = [
    {
        "episode_title": "Controlling Your Dopamine For Motivation, Focus & Satisfaction",
        "episode_id": "QmOF0crdyRU",
        "speaker": "Andrew Huberman",
        "timestamp": "00:20:45",
        "start_seconds": 1245.0,
        "url": "https://youtu.be/QmOF0crdyRU?t=1245",
    }
]

_INIT_UI_JS = """() => {
    window.podSeekSelectMode = (modeVal) => {
        const btn = document.getElementById('ap-mode-slider');
        if (btn) {
            btn.classList.remove('is-turbo', 'is-balanced', 'is-rigorous');
            if (modeVal.includes('Turbo')) btn.classList.add('is-turbo');
            else if (modeVal.includes('Rigorous')) btn.classList.add('is-rigorous');
            else btn.classList.add('is-balanced');
        }
        const labels = document.querySelectorAll('#ap-mode-radio label');
        for (const lbl of labels) {
            if (lbl.textContent.includes(modeVal) ||
                (modeVal.includes('Turbo') && lbl.textContent.includes('Turbo')) ||
                (modeVal.includes('Balanced') && lbl.textContent.includes('Balanced')) ||
                (modeVal.includes('Rigorous') && lbl.textContent.includes('Rigorous'))) {
                lbl.click();
                break;
            }
        }
    };
    const setupPodSeekUI = () => {
        const isDark = document.documentElement.classList.contains('ap-dark') ||
                       document.body.classList.contains('ap-dark') ||
                       document.body.classList.contains('dark');
        if (isDark) {
            document.documentElement.classList.add('ap-dark', 'dark');
            document.body.classList.add('ap-dark', 'dark');
            document.querySelector('.gradio-container')?.classList.add('ap-dark');
        }
        const bg = isDark ? '#111113' : '#F8F9FA';
        document.documentElement.style.setProperty('background-color', bg, 'important');
        document.body.style.setProperty('background-color', bg, 'important');
        const gApp = document.querySelector('gradio-app');
        if (gApp) gApp.style.setProperty('background-color', bg, 'important');

        const epList = document.querySelector('.ap-episodes-list');
        if (epList) {
            epList.style.setProperty('min-height', '0px', 'important');
            epList.style.setProperty('max-height', 'calc(100vh - 370px)', 'important');
        }

        const ingestTa = document.querySelector('#ap-ingest-input textarea, #ap-ingest-input input');
        if (ingestTa && !ingestTa.dataset.psBound) {
            ingestTa.dataset.psBound = '1';
            ingestTa.addEventListener('keydown', (e) => {
                if (e.key === 'Enter') {
                    e.preventDefault();
                    document.getElementById('ap-ingest-btn')?.click();
                }
            });
        }
        const ta = document.querySelector('#ap-distill-input textarea');
        if (ta && !ta.dataset.psBound) {
            ta.dataset.psBound = '1';
            ta.addEventListener('keydown', (e) => {
                if (e.key === 'Enter' && !e.shiftKey) {
                    e.preventDefault();
                    document.getElementById('ap-distill-btn')?.click();
                }
            });
        }
    };
    setupPodSeekUI();
    const obs = new MutationObserver(() => {
        setupPodSeekUI();
        const chatEl = document.getElementById('ap-chat-scroll');
        if (chatEl) chatEl.scrollTop = chatEl.scrollHeight;
        const sseEl = document.getElementById('ap-sse-scroll');
        if (sseEl) sseEl.scrollTop = sseEl.scrollHeight;
    });
    obs.observe(document.body, { childList: true, subtree: true });
}"""

__all__ = ["build_demo", "format_citations", "format_event"]


def _demo_fallback_enabled() -> bool:
    val = os.getenv("PODSEEK_DEMO_FALLBACK") or os.getenv("ASKPODCAST_DEMO_FALLBACK", "false")
    return val.strip().lower() in {"1", "true", "yes"}


def build_demo(client: AskPodcastClient | None = None, stylesheet: str = "theme.css") -> Any:
    if client is None:
        client = make_client()

    def load_episodes_html() -> str:
        try:
            return render_episodes_html(client.episodes())
        except Exception:
            return render_episodes_html([])

    def on_ingest(video_url_or_id: str):
        cleaned = video_url_or_id.strip()
        current_eps = load_episodes_html()
        if not cleaned:
            err_box = render_ingest_status_html(
                "error", "Missing episode link", "Paste a Huberman Lab YouTube URL or video ID."
            )
            err_logs = [("✕ [ingest] Missing episode link", "#EF4444")]
            yield (
                err_box,
                current_eps,
                render_ingest_workflow_graph_html(active_step="abort", error=True, abort_reason="Empty link"),
                render_sse_log_html(err_logs, endpoint="POST /ingest"),
                "",
            )
            time.sleep(3.2)
            yield (
                "",
                current_eps,
                render_workflow_graph_html(),
                render_sse_log_html(err_logs, endpoint="POST /ingest"),
                "",
            )
            return

        stages = [
            (
                "verify",
                "Verifying channel...",
                "oEmbed check",
                "→ [verify] Checking YouTube oEmbed channel metadata...",
            ),
            (
                "captions",
                "Fetching captions...",
                "YouTube transcript",
                "→ [captions] Downloading raw caption segments...",
            ),
            (
                "chunk",
                "Chunking transcript...",
                "400w sliding window",
                "→ [chunker] Building timestamp-bounded chunks...",
            ),
            (
                "embed",
                "Embedding & analyzing...",
                "ChromaDB + Gemini",
                "→ [chromadb] Indexing vectors & generating summary...",
            ),
        ]
        ingest_logs: list[tuple[str, str]] = [(stages[0][3], "var(--accent)")]

        # Always show Stage 1 (Verify Channel) first and clear input box immediately
        yield (
            render_ingest_status_html("loading", stages[0][1], stages[0][2]),
            current_eps,
            render_ingest_workflow_graph_html(active_step="verify"),
            render_sse_log_html(ingest_logs, endpoint="POST /ingest"),
            "",
        )

        with ThreadPoolExecutor(max_workers=1) as pool:
            future = pool.submit(client.ingest, cleaned, DEFAULT_SHOW, DEFAULT_SPEAKER)
            time.sleep(0.6)
            stage_idx = 1
            while not future.done():
                step_key, title_txt, detail_txt, log_line = stages[min(stage_idx, len(stages) - 1)]
                if len(ingest_logs) <= stage_idx and stage_idx < len(stages):
                    ingest_logs.append((log_line, "var(--accent)"))
                yield (
                    render_ingest_status_html("loading", title_txt, detail_txt),
                    current_eps,
                    render_ingest_workflow_graph_html(active_step=step_key),
                    render_sse_log_html(ingest_logs, endpoint="POST /ingest"),
                    "",
                )
                time.sleep(0.55)
                if stage_idx < len(stages) - 1:
                    stage_idx += 1

            try:
                payload = future.result()
                title = str(payload.get("episode_title") or "Huberman Lab Episode")
                chunks_n = int(payload.get("chunks_indexed", 0))
                status_val = str(payload.get("status") or "success")
                is_cached = status_val == "cached"
                updated_eps = load_episodes_html()
                if is_cached:
                    ingest_logs.append(
                        (f"⚡ [cache] Already in library ({chunks_n} chunks) · 0 API calls", "var(--done-stroke)")
                    )
                    banner_title = f"⚡ Already in library ({chunks_n} chunks)"
                else:
                    ingest_logs.append((f"✓ [ingest] Indexed {chunks_n} chunks · {title}", "var(--done-stroke)"))
                    banner_title = f"Absorbed {chunks_n} chunks"

                yield (
                    render_ingest_status_html("success", banner_title, title),
                    updated_eps,
                    render_ingest_workflow_graph_html(active_step="done", chunks_indexed=chunks_n, cached=is_cached),
                    render_sse_log_html(ingest_logs, endpoint="POST /ingest"),
                    "",
                )
                time.sleep(3.2)
                yield (
                    "",
                    updated_eps,
                    render_workflow_graph_html(),
                    render_sse_log_html(ingest_logs, endpoint="POST /ingest"),
                    "",
                )
            except Exception as exc:
                err_text = str(exc)
                ingest_logs.append((f"✕ [abort] {err_text}", "#EF4444"))
                if "Only Huberman Lab episodes can be ingested" in err_text:
                    detail = err_text.replace("Only Huberman Lab episodes can be ingested", "").strip(" ().")
                    status_box = render_ingest_status_html("error", "Huberman Lab episodes only", detail or err_text)
                    reason = detail.replace("detected channel:", "").strip() or "Non-Huberman"
                else:
                    status_box = render_ingest_status_html("error", "Could not absorb episode", err_text)
                    reason = "Invalid link"

                yield (
                    status_box,
                    current_eps,
                    render_ingest_workflow_graph_html(active_step="abort", error=True, abort_reason=reason),
                    render_sse_log_html(ingest_logs, endpoint="POST /ingest"),
                    "",
                )
                time.sleep(4.0)
                yield (
                    "",
                    current_eps,
                    render_workflow_graph_html(),
                    render_sse_log_html(ingest_logs, endpoint="POST /ingest"),
                    "",
                )

    def on_mode_change(mode_label: str):
        mode_val = (
            "turbo"
            if "turbo" in (mode_label or "").lower()
            else ("rigorous" if "rigorous" in (mode_label or "").lower() else "balanced")
        )
        logs = [(f"⚡ Switched execution mode to {mode_label}", "var(--accent)")]
        return render_workflow_graph_html(mode=mode_val), render_sse_log_html(logs), render_mode_slider_html(mode_val)

    def on_ask(question: str, history: list[dict], mode_label: str = "⚖️ Balanced"):
        cleaned = question.strip()
        current_history = list(history or [])
        mode_val = (
            "turbo"
            if "turbo" in (mode_label or "").lower()
            else ("rigorous" if "rigorous" in (mode_label or "").lower() else "balanced")
        )
        if len(cleaned) < 3:
            yield (
                render_chat_session_html(current_history),
                current_history,
                render_workflow_graph_html(mode=mode_val),
                render_sse_log_html([("Enter a question of at least 3 characters.", "var(--retry-stroke)")]),
                question,
                gr.update(visible=(len(current_history) == 0)),
            )
            return

        logs: list[tuple[str, str]] = [("→ [retrieve] Searching ChromaDB (k=4)...", "var(--accent)")]
        chunks = 0
        relevant = 0
        rewrites = 0
        aborted = False
        is_cached = False
        answer = ""
        streaming_answer = ""
        citations: list[dict] = []
        top_dist: float | None = None

        # Clear input immediately and hide sample questions once first question is asked
        wf_state = {
            "active_node": "retrieve",
            "chunks": 0,
            "relevant": 0,
            "rewrites": 0,
            "mode": mode_val,
            "top_distance": None,
            "done": False,
            "aborted": False,
        }
        yield (
            render_chat_session_html(
                current_history + [{"question": cleaned, "answer": "", "citations": [], "workflow": wf_state}]
            ),
            current_history,
            render_workflow_graph_html(active_node="retrieve", mode=mode_val),
            render_sse_log_html(logs),
            "",
            gr.update(visible=False),
        )

        try:
            for event in client.ask_stream(cleaned, mode=mode_val):
                # Handle real-time token deltas emitted during the generate stage
                if "delta" in event and event["delta"]:
                    streaming_answer += str(event["delta"])
                    answer = streaming_answer
                    wf_state = {
                        "active_node": "generate",
                        "chunks": chunks,
                        "relevant": relevant,
                        "rewrites": rewrites,
                        "mode": mode_val,
                        "top_distance": top_dist,
                        "done": False,
                        "aborted": aborted,
                    }
                    preview_history = current_history + [
                        {
                            "question": cleaned,
                            "answer": streaming_answer,
                            "citations": citations,
                            "workflow": wf_state,
                        }
                    ]
                    yield (
                        render_chat_session_html(preview_history),
                        current_history,
                        render_workflow_graph_html(
                            active_node="generate",
                            chunks=chunks,
                            relevant=relevant,
                            rewrites=rewrites,
                            done=False,
                            aborted=aborted,
                            cached=is_cached,
                            mode=mode_val,
                            top_distance=top_dist,
                        ),
                        render_sse_log_html(logs),
                        "",
                        gr.update(visible=False),
                    )
                    continue

                node = str(event.get("node", ""))
                rewrites = max(rewrites, int(event.get("rewrites") or 0))
                if "top_distance" in event and event["top_distance"] is not None:
                    top_dist = float(event["top_distance"])

                if node == "retrieve":
                    chunks = int(event.get("chunks_retrieved", 0))
                    dist_info = f" (dist={top_dist:.2f})" if top_dist is not None else ""
                    logs.append((f"→ [retrieve] Fetched {chunks} chunks from ChromaDB{dist_info}", "var(--accent)"))
                    next_active = (
                        "generate"
                        if mode_val == "turbo" or (mode_val == "balanced" and top_dist is not None and top_dist < 0.35)
                        else "grade_documents"
                    )
                elif node == "grade_documents":
                    relevant = int(event.get("relevant_chunks", 0))
                    if event.get("citations"):
                        citations = list(event["citations"])
                    color = "var(--done-stroke)" if relevant > 0 else "var(--retry-stroke)"
                    logs.append((f"→ [grade_documents] {relevant}/{chunks} chunks relevant", color))
                    if relevant > 0:
                        next_active = "generate"
                    elif rewrites >= 2:
                        aborted = True
                        logs.append(
                            ("✕ [circuit_breaker] Rewrite limit (2/2) exceeded — aborting synthesis", "#EF4444")
                        )
                        next_active = "abort"
                    else:
                        rewrites = min(rewrites + 1, 2)
                        next_active = "rewrite_query"
                elif node == "rewrite_query":
                    rq = str(event.get("rewritten_query", ""))
                    logs.append((f"↻ [rewrite_query] Retry #{rewrites}: {rq}", "var(--retry-stroke)"))
                    next_active = "retrieve"
                elif node == "generate":
                    answer = str(event.get("generation") or streaming_answer or "")
                    if not citations and event.get("citations"):
                        citations = list(event["citations"])
                    if aborted or (relevant == 0 and rewrites >= 2):
                        aborted = True
                        logs.append(("✕ [abort] Returned circuit-breaker refusal response", "#EF4444"))
                        next_active = "abort"
                    elif event.get("cached"):
                        is_cached = True
                        logs.append(
                            (
                                f"⚡ [cache] Served cached answer with {len(citations)} citations (0 LLM calls)",
                                "var(--done-stroke)",
                            )
                        )
                        next_active = "done"
                    else:
                        logs.append(
                            (f"✓ [generate] Distilled answer with {len(citations)} citations", "var(--text-main)")
                        )
                        next_active = "done"
                else:
                    next_active = node

                wf_state = {
                    "active_node": next_active,
                    "chunks": chunks,
                    "relevant": relevant,
                    "rewrites": rewrites,
                    "mode": mode_val,
                    "top_distance": top_dist,
                    "done": (next_active in {"done", "abort"}),
                    "aborted": aborted,
                }
                preview_history = current_history + [
                    {
                        "question": cleaned,
                        "answer": answer or "Distilling grounded response...",
                        "citations": citations,
                        "workflow": wf_state,
                    }
                ]
                yield (
                    render_chat_session_html(preview_history),
                    current_history,
                    render_workflow_graph_html(
                        active_node=next_active,
                        chunks=chunks,
                        relevant=relevant,
                        rewrites=rewrites,
                        done=(next_active in {"done", "abort"}),
                        aborted=aborted,
                        cached=is_cached,
                        mode=mode_val,
                        top_distance=top_dist,
                    ),
                    render_sse_log_html(logs),
                    "",
                    gr.update(visible=False),
                )
        except Exception as exc:
            if _demo_fallback_enabled():
                demo_wf = {
                    "active_node": "done",
                    "chunks": 4,
                    "relevant": 1,
                    "rewrites": 0,
                    "mode": mode_val,
                    "done": True,
                }
                demo_turn = {
                    "question": cleaned,
                    "answer": DEMO_ANSWER,
                    "citations": DEMO_CITATIONS,
                    "workflow": demo_wf,
                }
                updated = current_history + [demo_turn]
                logs.append(("✓ [demo_fallback] Loaded cached example response", "var(--done-stroke)"))
                yield (
                    render_chat_session_html(updated),
                    updated,
                    render_workflow_graph_html(
                        active_node="done", chunks=4, relevant=1, rewrites=0, done=True, mode=mode_val
                    ),
                    render_sse_log_html(logs),
                    "",
                    gr.update(visible=False),
                )
                return
            logs.append((f"✕ Error: {exc}", "var(--retry-stroke)"))
            yield (
                render_chat_session_html(current_history),
                current_history,
                render_workflow_graph_html(
                    active_node="idle", chunks=chunks, relevant=relevant, rewrites=rewrites, mode=mode_val
                ),
                render_sse_log_html(logs),
                "",
                gr.update(visible=(len(current_history) == 0)),
            )
            return

        if not answer:
            try:
                payload = client.ask(cleaned, mode=mode_val)
                answer = str(payload.get("answer", ""))
                citations = list(payload.get("citations") or [])
                rewrites = int(payload.get("rewrites_attempted", rewrites))
                if payload.get("top_distance") is not None:
                    top_dist = float(payload["top_distance"])
            except Exception as exc:
                if _demo_fallback_enabled():
                    answer = DEMO_ANSWER
                    citations = DEMO_CITATIONS
                else:
                    answer = f"Distill failed: {exc}"

        wf_final = {
            "active_node": "abort" if aborted else "done",
            "chunks": chunks,
            "relevant": relevant,
            "rewrites": rewrites,
            "mode": mode_val,
            "top_distance": top_dist,
            "done": True,
            "aborted": aborted,
        }
        final_history = current_history + [
            {"question": cleaned, "answer": answer, "citations": citations, "workflow": wf_final}
        ]
        yield (
            render_chat_session_html(final_history),
            final_history,
            render_workflow_graph_html(
                active_node="abort" if aborted else "done",
                chunks=chunks,
                relevant=relevant,
                rewrites=rewrites,
                done=True,
                aborted=aborted,
                cached=is_cached,
                mode=mode_val,
                top_distance=top_dist,
            ),
            render_sse_log_html(logs),
            "",
            gr.update(visible=False),
        )

    def on_clear():
        return render_chat_session_html([]), [], gr.update(visible=True)

    with gr.Blocks(title="PodSeek", css=load_theme_css(stylesheet)) as demo:
        chat_state = gr.State([])

        # Top Header Bar: Brand on Left + Single-Click Oval Toggle Sliders Flush Right
        with gr.Row(elem_classes=["ap-card", "ap-header-row"]):
            gr.HTML(render_header_brand_html(), elem_classes=["ap-header-brand"])
            gr.HTML(
                '<div class="ap-slider-wrap">'
                '<button id="ap-theme-slider" type="button" title="Toggle Light / Dark theme" '
                'onclick="(() => {'
                "const isDark = !document.documentElement.classList.contains('ap-dark');"
                "document.documentElement.classList.toggle('ap-dark', isDark);"
                "document.documentElement.classList.toggle('dark', isDark);"
                "document.body.classList.toggle('ap-dark', isDark);"
                "document.body.classList.toggle('dark', isDark);"
                "document.querySelector('.gradio-container')?.classList.toggle('ap-dark', isDark);"
                "const bg = isDark ? '#111113' : '#F8F9FA';"
                "document.documentElement.style.setProperty('background-color', bg, 'important');"
                "document.body.style.setProperty('background-color', bg, 'important');"
                "const gApp = document.querySelector('gradio-app');"
                "if (gApp) gApp.style.setProperty('background-color', bg, 'important');"
                '})()">'
                '<span class="ts-thumb"></span>'
                '<span class="ts-icon ts-sun">'
                '<svg width="14" height="14" viewBox="0 0 24 24" fill="currentColor" stroke="currentColor" '
                'stroke-width="2" stroke-linecap="round" stroke-linejoin="round">'
                '<circle cx="12" cy="12" r="4"/>'
                '<path d="M12 2v2M12 20v2M4.93 4.93l1.41 1.41M17.66 17.66l1.41 1.41M2 12h2M20 12h2'
                'M6.34 17.66l-1.41 1.41M19.07 4.93l-1.41 1.41"/>'
                "</svg></span>"
                '<span class="ts-icon ts-moon">'
                '<svg width="14" height="14" viewBox="0 0 24 24" fill="currentColor" stroke="currentColor" '
                'stroke-width="2" stroke-linecap="round" stroke-linejoin="round">'
                '<path d="M21 12.79A9 9 0 1 1 11.21 3 7 7 0 0 0 21 12.79z"/>'
                "</svg></span>"
                "</button>"
                "</div>",
                elem_classes=["ap-header-controls"],
            )

        # PAGE 1: 3-Column Studio View
        with gr.Row(visible=True, elem_id="ap-studio-view"):
            # ENTITY 1 (Left 3 cols): Unified Command Capsule ("✦ Absorb" inside box) + Episodes by Title
            with gr.Column(scale=3, elem_classes=["ap-card", "ap-col-left"]):
                gr.HTML('<div style="font-size:12.5px;font-weight:700;margin-bottom:6px;">Ingest Episode</div>')
                with gr.Row(elem_classes=["ap-ingest-capsule"]):
                    video_input = gr.Textbox(
                        label="",
                        show_label=False,
                        container=False,
                        placeholder="Paste Huberman Lab link...",
                        lines=2,
                        max_lines=3,
                        elem_id="ap-ingest-input",
                        elem_classes=["ap-capsule-input"],
                    )
                    ingest_btn = gr.Button(
                        "✦ Absorb",
                        variant="primary",
                        size="sm",
                        elem_id="ap-ingest-btn",
                        elem_classes=["ap-capsule-btn"],
                    )
                ingest_status = gr.HTML("")
                gr.HTML(
                    '<div style="border-top:1px solid var(--border-hairline);margin:10px 0 8px;padding-top:10px;'
                    'font-size:12.5px;font-weight:700;">Indexed Episodes</div>'
                )
                episodes_html = gr.HTML(load_episodes_html)

            # ENTITY 2 (Center 5 cols): Hero Session Chat + Collapsible Presets + Multiline Capsule ("Distill ->")
            with gr.Column(scale=5, elem_classes=["ap-card", "ap-col-center"]):
                with gr.Row(elem_classes=["ap-inline-row"]):
                    gr.HTML(
                        '<div style="flex:1;"><span style="font-size:13px;font-weight:700;">Session Chat</span> '
                        '<span class="ap-muted" style="font-size:12px;">· Ephemeral session history</span></div>'
                    )
                    clear_btn = gr.Button("Clear", size="sm", elem_classes=["ap-btn-ghost"])

                chat_html = gr.HTML(render_chat_session_html([]))

                with gr.Row(elem_classes=["ap-presets-row"], visible=True) as presets_row:
                    preset_1 = gr.Button(PRESET_QUESTIONS[0], size="sm", elem_classes=["ap-preset-pill"])
                    preset_2 = gr.Button(PRESET_QUESTIONS[1], size="sm", elem_classes=["ap-preset-pill"])
                    preset_3 = gr.Button(PRESET_QUESTIONS[2], size="sm", elem_classes=["ap-preset-pill"])

                with gr.Row(elem_classes=["ap-mode-bar"]):
                    mode_slider_html = gr.HTML(render_mode_slider_html("balanced"))
                    mode_radio = gr.Radio(
                        choices=["⚡ Turbo", "⚖️ Balanced", "🎯 Rigorous"],
                        value="⚖️ Balanced",
                        show_label=False,
                        container=False,
                        elem_id="ap-mode-radio",
                        elem_classes=["ap-view-hidden"],
                    )

                with gr.Row(elem_classes=["ap-distill-capsule"]):
                    question_input = gr.Textbox(
                        label="",
                        show_label=False,
                        container=False,
                        placeholder="Ask a question across episodes...",
                        lines=2,
                        max_lines=5,
                        elem_id="ap-distill-input",
                        elem_classes=["ap-capsule-input"],
                    )
                    ask_btn = gr.Button(
                        "Distill →",
                        variant="primary",
                        size="sm",
                        elem_id="ap-distill-btn",
                        elem_classes=["ap-capsule-btn"],
                    )

            # ENTITY 3 (Right 4 cols): Cyclic Workflow Graph + Color-Coded SSE Stream
            with gr.Column(scale=4, elem_classes=["ap-col-right"]):
                graph_html = gr.HTML(render_workflow_graph_html(mode="balanced"))
                sse_html = gr.HTML(render_sse_log_html([]))

        # PAGE 2: Stats for Nerds View
        with gr.Row(visible=True, elem_id="ap-nerds-view", elem_classes=["ap-view-hidden"]):
            with gr.Column(scale=12):
                gr.HTML(render_stats_for_nerds_html())

        def load_initial_view() -> tuple[str, str]:
            return load_episodes_html(), render_workflow_graph_html(mode="balanced")

        demo.load(load_initial_view, outputs=[episodes_html, graph_html], show_progress="hidden", js=_INIT_UI_JS)
        mode_radio.change(
            on_mode_change,
            inputs=[mode_radio],
            outputs=[graph_html, sse_html, mode_slider_html],
            show_progress="hidden",
        )

        ingest_outputs = [ingest_status, episodes_html, graph_html, sse_html, video_input]
        ingest_btn.click(
            on_ingest,
            inputs=[video_input],
            outputs=ingest_outputs,
            show_progress="hidden",
        )
        video_input.submit(
            on_ingest,
            inputs=[video_input],
            outputs=ingest_outputs,
            show_progress="hidden",
        )

        ask_outputs = [chat_html, chat_state, graph_html, sse_html, question_input, presets_row]
        ask_btn.click(
            on_ask,
            inputs=[question_input, chat_state, mode_radio],
            outputs=ask_outputs,
            show_progress="hidden",
        )
        question_input.submit(
            on_ask,
            inputs=[question_input, chat_state, mode_radio],
            outputs=ask_outputs,
            show_progress="hidden",
        )
        clear_btn.click(on_clear, outputs=[chat_html, chat_state, presets_row], show_progress="hidden")

        preset_1.click(lambda: PRESET_QUESTIONS[0], outputs=question_input, show_progress="hidden").then(
            on_ask,
            inputs=[question_input, chat_state, mode_radio],
            outputs=ask_outputs,
            show_progress="hidden",
        )
        preset_2.click(lambda: PRESET_QUESTIONS[1], outputs=question_input, show_progress="hidden").then(
            on_ask,
            inputs=[question_input, chat_state, mode_radio],
            outputs=ask_outputs,
            show_progress="hidden",
        )
        preset_3.click(lambda: PRESET_QUESTIONS[2], outputs=question_input, show_progress="hidden").then(
            on_ask,
            inputs=[question_input, chat_state, mode_radio],
            outputs=ask_outputs,
            show_progress="hidden",
        )

    return demo


if __name__ == "__main__":
    port = int(os.environ.get("PORT", "7860"))
    build_demo().launch(server_name="0.0.0.0", server_port=port)
