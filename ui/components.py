"""Pure HTML/SVG UI components and formatters for PodSeek.

This module intentionally does not import Gradio so every view builder and
formatter can be unit-tested in isolation.
"""

from __future__ import annotations

import html
import os
import re
from pathlib import Path

STYLES_DIR = Path(__file__).resolve().parent / "styles"

_YT_BADGE_SVG = (
    '<span class="gai-yt-circle">'
    '<svg width="8" height="8" viewBox="0 0 10 10" fill="#FFFFFF">'
    '<polygon points="3,2 8,5 3,8"/>'
    "</svg></span>"
)


def _is_submittable_question(text: object) -> bool:
    """Return True when the stripped question text has at least 3 characters."""
    if not isinstance(text, str):
        text = str(getattr(text, "value", text or ""))
    return len(text.strip()) >= 3


def load_theme_css(stylesheet: str = "theme.css") -> str:
    """Load a pluggable CSS stylesheet from ui/styles/."""
    css_path = STYLES_DIR / stylesheet
    if css_path.exists():
        return css_path.read_text(encoding="utf-8")
    return ""


PS_FAVICON_DATA_URI = (
    "data:image/svg+xml,"
    "%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 32 32'%3E"
    "%3Cdefs%3E%3ClinearGradient id='g' x1='0%25' y1='0%25' x2='100%25' y2='100%25'%3E"
    "%3Cstop offset='0%25' stop-color='%233B82F6'/%3E"
    "%3Cstop offset='100%25' stop-color='%231D4ED8'/%3E"
    "%3C/linearGradient%3E%3C/defs%3E"
    "%3Crect width='32' height='32' rx='9' fill='url(%23g)'/%3E"
    "%3Ctext x='16' y='21.5' text-anchor='middle' fill='%23FFFFFF' "
    "font-family='ui-monospace,SFMono-Regular,Menlo,monospace' font-weight='800' "
    "font-size='14' letter-spacing='-0.4'%3EPS%3C/text%3E%3C/svg%3E"
)


def render_head_meta_html() -> str:
    """Return HTML head tags for viewport, favicon, SEO description, Open Graph, Twitter cards, and fonts."""
    description = "Corrective RAG over Huberman Lab transcripts with timestamp citations."
    early_theme_js = (
        "<script>"
        "(() => {"
        "window.podSeekApplyTheme = (isDark) => {"
        "const root = document.documentElement;"
        "if (!root) return;"
        "const targets = [root, document.body];"
        "const gC = document.querySelector('.gradio-container');"
        "const gA = document.querySelector('gradio-app');"
        "if (gC) targets.push(gC);"
        "if (gA) targets.push(gA);"
        "targets.forEach(el => {"
        "if (!el) return;"
        "el.classList.toggle('ap-dark', isDark);"
        "if (!isDark) el.classList.remove('dark');"
        "});"
        "const bg = isDark ? '#111113' : '#F8F9FA';"
        "root.style.setProperty('background-color', bg, 'important');"
        "if (document.body) document.body.style.setProperty('background-color', bg, 'important');"
        "if (gA) gA.style.setProperty('background-color', bg, 'important');"
        "};"
        "let isDark = false;"
        "try {"
        "const saved = localStorage.getItem('podseek_theme');"
        "if (saved === 'dark') isDark = true;"
        "else if (saved === 'light') isDark = false;"
        "else isDark = !!(window.matchMedia && window.matchMedia('(prefers-color-scheme: dark)').matches);"
        "} catch (e) {"
        "isDark = !!(window.matchMedia && window.matchMedia('(prefers-color-scheme: dark)').matches);"
        "}"
        "window.podSeekApplyTheme(isDark);"
        "if (!window._podSeekThemeListenerAttached && window.matchMedia) {"
        "window._podSeekThemeListenerAttached = true;"
        "const mq = window.matchMedia('(prefers-color-scheme: dark)');"
        "const onSysChange = (e) => {"
        "let s = null;"
        "try { s = localStorage.getItem('podseek_theme'); } catch (err) {}"
        "if (s !== 'dark' && s !== 'light') {"
        "if (window.podSeekApplyTheme) window.podSeekApplyTheme(e.matches);"
        "}"
        "};"
        "if (mq.addEventListener) mq.addEventListener('change', onSysChange);"
        "else if (mq.addListener) mq.addListener(onSysChange);"
        "}"
        "})();"
        "</script>"
    )
    tags = (
        '<meta name="viewport" content="width=device-width, initial-scale=1, interactive-widget=resizes-content, viewport-fit=cover">'
        f'<link rel="icon" type="image/svg+xml" href="{PS_FAVICON_DATA_URI}">'
        f'<meta name="description" content="{description}">'
        '<meta property="og:title" content="PodSeek">'
        '<meta property="og:type" content="website">'
        '<meta property="og:url" content="https://podseek.onrender.com/">'
        f'<meta property="og:description" content="{description}">'
        '<meta name="twitter:card" content="summary">'
        '<meta name="twitter:title" content="PodSeek">'
        '<meta name="twitter:url" content="https://podseek.onrender.com/">'
        f'<meta name="twitter:description" content="{description}">'
        '<link rel="preconnect" href="https://fonts.googleapis.com">'
        '<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>'
        '<link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&family=JetBrains+Mono:wght@400;500;600;700&display=swap" rel="stylesheet">'
        f"{early_theme_js}"
    )
    code = (os.getenv("GOATCOUNTER_CODE") or "").strip()
    if code and re.fullmatch(r"^[a-z0-9-]+$", code):
        tags += f'<script data-goatcounter="https://{code}.goatcounter.com/count" async src="//gc.zgo.at/count.js"></script>'
    return tags


def format_citations(citations: list[dict]) -> str:
    """Format citations as Markdown links."""
    if not citations:
        return "_No citations._"
    lines = []
    for citation in citations:
        timestamp = citation.get("timestamp", "")
        title = citation.get("episode_title", "Episode")
        speaker = citation.get("speaker", "")
        url = citation.get("url") or ""
        label = f"{timestamp} {title}"
        if speaker:
            label = f"{label} — {speaker}"
        if url:
            lines.append(f"- [{label}]({url})")
        else:
            lines.append(f"- {label}")
    return "\n".join(lines)


def format_event(event: dict) -> str:
    """Format one node event into a concise step line."""
    node = event.get("node", "node")
    if node == "retrieve":
        return f"retrieve: {event.get('chunks_retrieved', 0)} chunks"
    if node == "grade_documents":
        return f"grade: {event.get('relevant_chunks', 0)} relevant"
    if node == "rewrite_query":
        return f"rewrite ({event.get('rewrites', 0)}): {event.get('rewritten_query', '')}"
    if node == "generate":
        return "generate: answer ready"
    return str(node)


def _short_title(title: str, max_len: int = 30) -> str:
    """Shorten long Huberman Lab episode titles for compact inline pills."""
    cleaned = re.sub(r"\s*\|\s*Huberman Lab.*$", "", title, flags=re.IGNORECASE).strip()
    cleaned = re.sub(r"^Dr\.\s+Andrew\s+Huberman:\s*", "", cleaned, flags=re.IGNORECASE).strip()
    if len(cleaned) <= max_len:
        return cleaned
    return cleaned[: max_len - 1].rstrip() + "…"


def _short_timestamp(ts: str) -> str:
    """Convert 00:20:45 -> 20:45 while keeping 01:04:12 intact."""
    if ts.startswith("00:") and len(ts) == 8:
        return ts[3:]
    return ts


def render_inline_pill_html(citation: dict) -> str:
    """Render a Google AI Overview style inline stadium pill for a citation."""
    raw_title = str(citation.get("episode_title") or "Episode")
    short_ep = html.escape(_short_title(raw_title))
    full_title = html.escape(raw_title)
    raw_ts = str(citation.get("timestamp") or "00:00:00")
    short_ts = html.escape(_short_timestamp(raw_ts))
    url = html.escape(str(citation.get("url") or "#"))
    return (
        f'<a href="{url}" target="_blank" rel="noopener noreferrer" '
        f'class="gai-pill" title="{full_title} ({html.escape(raw_ts)})">'
        f"{_YT_BADGE_SVG}"
        f"<span>{short_ep} · {short_ts}</span>"
        f"</a>"
    )


def _format_inline_markdown(escaped_line: str, pill_lookup: dict[str, str]) -> str:
    """Apply inline Markdown formatting and replace inline timestamp tokens with pills."""
    # 1. Strip backticks around timestamp citations so they never get wrapped in dark <code> boxes
    text = re.sub(
        r"`(\s*[\[\(][^`\n]*?\d{1,2}:\d{2}(?::\d{2})?[^`\n]*?[\]\)]\s*)`",
        r"\1",
        escaped_line,
    )

    # 2. Replace bracketed/parenthesized timestamp references BEFORE bold/italic/code
    def _replace_ts(match: re.Match[str]) -> str:
        ts_val = match.group("ts")
        norm_ts = ts_val if len(ts_val.split(":")) == 3 else f"00:{ts_val.zfill(5)}"
        pill = pill_lookup.get(norm_ts) or pill_lookup.get(ts_val)
        if pill:
            return pill
        return match.group(0)

    text = re.sub(
        r"[\[\(]+[^\]\)]*?(?P<ts>\d{1,2}:\d{2}(?::\d{2})?)[^\]\)]*?[\]\)]+",
        _replace_ts,
        text,
    )

    # 3. Clean up any outer parentheses, brackets, or commas around single or multiple pills
    for _ in range(3):
        text = re.sub(r"(</a>)\s*[,;&]+\s*(?:and\s+)?(<a\s+href=)", r"\1 \2", text)
        text = re.sub(r"[\[\(]+\s*((?:<a\s+href=[^>]+class=\"gai-pill\"[^>]*>.*?</a>\s*)+)[\]\)]+", r"\1", text)
        text = re.sub(r"(</a>)\s*[\]\)]+(?=[.;,:]|\s|$)", r"\1", text)
        text = re.sub(r"[\[\(]+\s*(<a\s+href=[^>]+class=\"gai-pill\")", r"\1", text)

    # 4. Convert **bold**, *italic*, `code` on remaining text
    text = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", text)
    text = re.sub(r"(?<!\*)\*([^*\n<>]+?)\*(?!\*)", r"<em>\1</em>", text)
    text = re.sub(r"`([^`\n<>]+?)`", r"<code>\1</code>", text)
    return text


def render_markdown_with_pills(answer: str, citations: list[dict]) -> str:
    """Render Markdown answer text into HTML with Google AI Overview inline citation pills."""
    pill_lookup: dict[str, str] = {}
    ordered_pills: list[tuple[str, str]] = []
    for cit in citations:
        ts = str(cit.get("timestamp") or "")
        pill_html = render_inline_pill_html(cit)
        if ts and ts not in pill_lookup:
            pill_lookup[ts] = pill_html
            short_ts = _short_timestamp(ts)
            pill_lookup[short_ts] = pill_html
            ordered_pills.append((ts, pill_html))

    escaped = html.escape(answer.strip())
    lines = escaped.splitlines()
    blocks: list[str] = []
    in_list = False

    for raw_line in lines:
        stripped = raw_line.strip()
        if not stripped:
            if in_list:
                blocks.append("</ul>")
                in_list = False
            continue

        heading_match = re.match(r"^(#{1,3})\s+(.*)$", stripped)
        if heading_match:
            if in_list:
                blocks.append("</ul>")
                in_list = False
            content = _format_inline_markdown(heading_match.group(2), pill_lookup)
            blocks.append(f'<p style="font-weight:700;margin-top:6px;">{content}</p>')
            continue

        bullet_match = re.match(r"^(?:[-*•]|\d+\.)\s+(.*)$", stripped)
        if bullet_match:
            if not in_list:
                blocks.append("<ul>")
                in_list = True
            content = _format_inline_markdown(bullet_match.group(1), pill_lookup)
            blocks.append(f"<li>{content}</li>")
            continue

        if in_list:
            blocks.append("</ul>")
            in_list = False
        content = _format_inline_markdown(stripped, pill_lookup)
        blocks.append(f"<p>{content}</p>")

    if in_list:
        blocks.append("</ul>")

    rendered = "".join(blocks) or f"<p>{escaped}</p>"

    # Only append fallback pills at the end if the LLM did not cite any timestamps inline
    any_inline_placed = any(pill in rendered for _ts, pill in ordered_pills)
    if not any_inline_placed and ordered_pills:
        pills_str = " " + " ".join(pill for _ts, pill in ordered_pills)
        if rendered.endswith("</p>"):
            rendered = rendered[:-4] + pills_str + "</p>"
        elif rendered.endswith("</li></ul>"):
            rendered = rendered[:-10] + pills_str + "</li></ul>"
        else:
            rendered = f"{rendered}<p>{pills_str.strip()}</p>"

    return f'<div class="ap-md">{rendered}</div>'


def render_ingest_status_html(state: str, title: str = "", detail: str = "") -> str:
    """Render wrapped, non-clipping ingest progress, error, or success cards."""
    safe_title = html.escape(title)
    safe_detail = html.escape(detail)

    if state == "loading":
        spinner_svg = (
            '<svg class="ap-spin" width="13" height="13" viewBox="0 0 24 24" fill="none" '
            'stroke="var(--accent)" stroke-width="2.5" stroke-linecap="round">'
            '<path d="M12 2a10 10 0 0 1 10 10" />'
            "</svg>"
        )
        return (
            '<div class="ap-status-card ap-subtle">'
            '<div style="display:flex;align-items:center;justify-content:space-between;gap:6px;flex-wrap:wrap;">'
            '<span style="display:inline-flex;align-items:center;gap:6px;font-weight:600;color:var(--accent);">'
            f"{spinner_svg}<span>{safe_title or 'Absorbing episode...'}</span></span>"
            f'<span class="ap-muted" style="font-family:monospace;font-size:11px;">{safe_detail or "Verifying & chunking"}</span>'
            "</div>"
            '<div class="ap-shimmer-track"><div class="ap-shimmer-fill"></div></div>'
            "</div>"
        )
    if state == "error":
        return (
            '<div class="ap-status-card" style="background:rgba(239,68,68,0.08);border:1px solid rgba(239,68,68,0.28);">'
            f'<div style="font-weight:600;color:#EF4444;">⚠️ {safe_title or "Could not absorb episode"}</div>'
            f'<div class="ap-muted" style="margin-top:2px;">{safe_detail}</div>'
            "</div>"
        )
    if state == "success":
        return (
            '<div class="ap-status-card" style="background:rgba(22,163,74,0.08);border:1px solid rgba(22,163,74,0.28);">'
            f'<div style="font-weight:600;color:var(--done-stroke);">✓ {safe_title}</div>'
            f'<div class="ap-muted" style="margin-top:2px;">{safe_detail}</div>'
            "</div>"
        )
    return ""


def render_ingest_workflow_graph_html(
    active_step: str = "verify",
    chunks_indexed: int = 0,
    error: bool = False,
    abort_reason: str = "Non-Huberman",
    cached: bool = False,
) -> str:
    """Render the 4-stage Episode Ingestion Workflow Graph with Cache check, 'Huberman Lab?' diamond, and Abort branch."""
    steps_order = ["verify", "captions", "chunk", "embed", "done"]
    is_aborted = error or active_step == "abort"
    is_cached = cached or active_step == "cached"
    idx = steps_order.index(active_step) if active_step in steps_order else 0

    def _node_cls(step_idx: int) -> str:
        if is_cached:
            return "is-completed" if step_idx == 0 else "opacity-60"
        if is_aborted:
            return "is-completed" if step_idx == 0 else "opacity-60"
        if step_idx < idx or active_step == "done":
            return "is-completed"
        if step_idx == idx:
            return "is-running"
        return "opacity-60"

    def _node_status(step_idx: int) -> str:
        if is_cached:
            return "⚡ Cached" if step_idx == 0 else "Skipped"
        if is_aborted:
            return "✓ Checked" if step_idx == 0 else "Skipped"
        if step_idx < idx or active_step == "done":
            return "✓ Done"
        if step_idx == idx:
            return "⟳ Running"
        return "Queued"

    c_ver_cache = "conn-completed" if is_cached else "conn-idle"
    c_ver_dec = (
        "conn-idle"
        if is_cached
        else (
            "conn-completed"
            if (is_aborted or idx > 0 or active_step == "done")
            else ("conn-running" if active_step == "verify" else "conn-idle")
        )
    )
    c_dec_cap = (
        "conn-idle"
        if (is_aborted or is_cached)
        else (
            "conn-running"
            if active_step == "captions"
            else ("conn-completed" if (idx > 1 or active_step == "done") else "conn-idle")
        )
    )
    c_dec_abt = "conn-aborted" if is_aborted else "conn-idle"
    c_cap_chk = (
        "conn-idle"
        if (is_aborted or is_cached)
        else (
            "conn-running"
            if active_step == "chunk"
            else ("conn-completed" if (idx > 2 or active_step == "done") else "conn-idle")
        )
    )
    c_chk_emb = (
        "conn-idle"
        if (is_aborted or is_cached)
        else (
            "conn-running" if active_step == "embed" else ("conn-completed" if active_step == "done" else "conn-idle")
        )
    )

    diamond_stroke = (
        "#EF4444"
        if is_aborted
        else (
            "var(--done-stroke)" if (not is_cached and (idx >= 1 or active_step == "done")) else "var(--border-strong)"
        )
    )
    cache_cls = "is-completed" if (is_cached or active_step == "done") else "opacity-60"
    cache_status = "⚡ Hit" if is_cached else ("✓ Saved" if active_step == "done" else "Miss")
    cache_sub = (
        f"{chunks_indexed} chunks · 0 calls"
        if is_cached
        else ("Indexed in DB" if active_step == "done" else "ChromaDB check")
    )

    abt_cls = "is-aborted" if is_aborted else "opacity-60"
    abt_status = "✕ Blocked" if is_aborted else "Idle"
    short_reason = (
        html.escape(abort_reason[:18] + ("…" if len(abort_reason) > 18 else "")) if is_aborted else "Channel guard"
    )

    badge_text = (
        "⚡ Cache Hit"
        if is_cached
        else ("✕ Aborted" if is_aborted else ("✓ Indexed" if active_step == "done" else "✦ Absorbing"))
    )
    embed_sub = f"{chunks_indexed} chunks indexed" if chunks_indexed else "ChromaDB + Gemini"

    return f"""
    <div class="wf-dot-grid">
      <div style="display:flex;align-items:center;justify-content:space-between;margin-bottom:8px;gap:8px;white-space:nowrap;">
        <span style="font-size:12px;font-weight:700;white-space:nowrap;flex-shrink:0;">Workflow · Episode Ingestion</span>
        <span class="ap-subtle" style="font-size:12px;font-family:monospace;padding:2px 8px;white-space:nowrap;flex-shrink:0;">{badge_text}</span>
      </div>
      <div class="wf-canvas-wrap" data-orig-height="300" style="position:relative;width:330px;height:300px;">
        <svg width="330" height="300" viewBox="0 0 330 300" style="position:absolute;inset:0;pointer-events:none;">
          <!-- 0. Verify Right (178,26) -> Cache Left (192,26) -->
          <path d="M 178 26 L 192 26" class="{c_ver_cache}" />
          <polygon points="188,23 193,26 188,29" fill="var(--border-strong)" />

          <!-- 1. Verify -> Decision Diamond (Top at 94,64) -->
          <path d="M 94 48 L 94 64" class="{c_ver_dec}" />
          <polygon points="91,60 94,65 97,60" fill="var(--border-strong)" />

          <!-- 2. Decision Diamond: Huberman Lab? -->
          <polygon points="94,64 154,88 94,112 34,88"
                   fill="var(--bg-card)" stroke="{diamond_stroke}" stroke-width="1.75" />
          <text x="94" y="91" text-anchor="middle" fill="var(--text-main)"
                font-size="9.5" font-weight="600" font-family="monospace">Huberman Lab?</text>

          <!-- 3. Yes Branch: Diamond Bottom (94,112) -> Fetch Captions Top (94,136) -->
          <path d="M 94 112 L 94 136" class="{c_dec_cap}" />
          <polygon points="91,132 94,137 97,132" fill="var(--border-strong)" />
          <rect x="78" y="116" width="32" height="14" rx="4" fill="var(--bg-card)" stroke="var(--border-hairline)" />
          <text x="94" y="126" text-anchor="middle" fill="var(--done-stroke)" font-size="9.5" font-weight="600" font-family="monospace">Yes</text>

          <!-- 4. No Branch: Diamond Right (154,88) -> Abort Left (192,88) -->
          <path d="M 154 88 L 192 88" class="{c_dec_abt}" />
          <polygon points="188,85 193,88 188,91" fill="var(--border-strong)" />
          <rect x="160" y="80" width="24" height="14" rx="4" fill="var(--bg-card)" stroke="var(--border-hairline)" />
          <text x="172" y="90" text-anchor="middle" fill="#EF4444" font-size="9.5" font-weight="600" font-family="monospace">No</text>

          <!-- 5. Fetch Captions -> Window Chunker -->
          <path d="M 94 180 L 94 194" class="{c_cap_chk}" />
          <polygon points="91,190 94,195 97,190" fill="var(--border-strong)" />

          <!-- 6. Window Chunker -> Embed & Analyze -->
          <path d="M 94 238 L 94 252" class="{c_chk_emb}" />
          <polygon points="91,248 94,253 97,248" fill="var(--border-strong)" />
        </svg>

        <!-- Step 1: Verify Channel & Cache -->
        <div class="wf-node {_node_cls(0)}" style="left:10px;top:4px;width:168px;height:44px;padding:6px 9px;">
          <svg class="node-trace-svg" viewBox="0 0 170 46">
            <rect class="trace-base" x="1.5" y="1.5" width="167" height="43" rx="10" />
            <rect class="trace-beam" x="1.5" y="1.5" width="167" height="43" rx="10" pathLength="100" />
          </svg>
          <div style="display:flex;justify-content:space-between;font-size:11.5px;white-space:nowrap;">
            <span style="font-weight:600;">🛡️ 1. Verify</span>
            <span style="font-family:monospace;">{_node_status(0)}</span>
          </div>
          <div class="ap-muted" style="font-size:11px;font-family:monospace;margin-top:1px;white-space:nowrap;">Cache &amp; channel check</div>
        </div>

        <!-- Cache Node (Right of 1. Verify) -->
        <div class="wf-node {cache_cls}" style="left:190px;top:4px;width:132px;height:44px;padding:6px 9px;">
          <div style="display:flex;justify-content:space-between;align-items:center;font-size:11.5px;white-space:nowrap;gap:4px;">
            <span style="font-weight:600;flex-shrink:0;">⚡ DB Cache</span>
            <span style="font-family:monospace;font-size:10px;flex-shrink:0;">{cache_status}</span>
          </div>
          <div class="ap-muted" style="font-size:10.5px;font-family:monospace;margin-top:1px;white-space:nowrap;">{cache_sub}</div>
        </div>

        <!-- Abort Terminator Node (Right of Huberman Lab? Diamond) -->
        <div class="wf-node {abt_cls}" style="left:190px;top:64px;width:132px;height:48px;border-radius:16px;padding:7px 9px;">
          <div style="display:flex;justify-content:space-between;align-items:center;font-size:11.5px;white-space:nowrap;gap:4px;">
            <span style="font-weight:600;flex-shrink:0;">🛑 Abort</span>
            <span style="font-family:monospace;font-size:10px;flex-shrink:0;color:{"#EF4444" if is_aborted else "inherit"};">{abt_status}</span>
          </div>
          <div class="ap-muted" style="font-size:10.5px;font-family:monospace;margin-top:2px;white-space:nowrap;">{short_reason}</div>
        </div>

        <!-- Step 2: Fetch Captions -->
        <div class="wf-node {_node_cls(1)}" style="left:10px;top:136px;width:168px;height:44px;padding:6px 9px;">
          <svg class="node-trace-svg" viewBox="0 0 170 46">
            <rect class="trace-base" x="1.5" y="1.5" width="167" height="43" rx="10" />
            <rect class="trace-beam" x="1.5" y="1.5" width="167" height="43" rx="10" pathLength="100" />
          </svg>
          <div style="display:flex;justify-content:space-between;font-size:11.5px;white-space:nowrap;">
            <span style="font-weight:600;">📝 2. Captions</span>
            <span style="font-family:monospace;">{_node_status(1)}</span>
          </div>
          <div class="ap-muted" style="font-size:11px;font-family:monospace;margin-top:1px;white-space:nowrap;">YouTube transcript</div>
        </div>

        <!-- Step 3: Window Chunker -->
        <div class="wf-node {_node_cls(2)}" style="left:10px;top:194px;width:168px;height:44px;padding:6px 9px;">
          <svg class="node-trace-svg" viewBox="0 0 170 46">
            <rect class="trace-base" x="1.5" y="1.5" width="167" height="43" rx="10" />
            <rect class="trace-beam" x="1.5" y="1.5" width="167" height="43" rx="10" pathLength="100" />
          </svg>
          <div style="display:flex;justify-content:space-between;font-size:11.5px;white-space:nowrap;">
            <span style="font-weight:600;">✂️ 3. Chunker</span>
            <span style="font-family:monospace;">{_node_status(2)}</span>
          </div>
          <div class="ap-muted" style="font-size:11px;font-family:monospace;margin-top:1px;white-space:nowrap;">400w sliding window</div>
        </div>

        <!-- Step 4: Embed & Analyze -->
        <div class="wf-node {_node_cls(3)}" style="left:10px;top:252px;width:168px;height:44px;padding:6px 9px;">
          <svg class="node-trace-svg" viewBox="0 0 170 46">
            <rect class="trace-base" x="1.5" y="1.5" width="167" height="43" rx="10" />
            <rect class="trace-beam" x="1.5" y="1.5" width="167" height="43" rx="10" pathLength="100" />
          </svg>
          <div style="display:flex;justify-content:space-between;font-size:11.5px;white-space:nowrap;">
            <span style="font-weight:600;">🧬 4. Embed</span>
            <span style="font-family:monospace;">{_node_status(3)}</span>
          </div>
          <div class="ap-muted" style="font-size:11px;font-family:monospace;margin-top:1px;white-space:nowrap;">{embed_sub}</div>
        </div>
      </div>
    </div>
    """


def render_header_brand_html() -> str:
    """Render the top-left PodSeek brand lockup with desktop sidebar toggle."""
    panel_icon_svg = (
        '<svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" '
        'stroke-width="2" stroke-linecap="round" stroke-linejoin="round">'
        '<rect x="3" y="3" width="18" height="18" rx="2" ry="2"/>'
        '<line x1="9" y1="3" x2="9" y2="21"/>'
        "</svg>"
    )
    toggle_btn = (
        '<button id="ap-sidebar-toggle-btn" type="button" title="Toggle Knowledge Base (Cmd+B)" '
        "onclick=\"if (window.togglePodSeekDrawer) { window.togglePodSeekDrawer(false); } else { const col = document.querySelector('.ap-col-left'); if (col) { const isCol = col.classList.toggle('is-collapsed'); try { localStorage.setItem('podseek_sidebar_collapsed', isCol ? '1' : '0'); } catch(e){} } }\">"
        f"{panel_icon_svg}"
        "</button>"
    )
    return (
        '<div class="ap-brand-lockup">'
        f"{toggle_btn}"
        '<div class="ap-brand-badge">PS</div>'
        '<div class="ap-brand-meta">'
        '<h1 class="ap-brand-title">PodSeek</h1>'
        '<div class="ap-muted ap-header-subtitle">Huberman Lab Knowledge Engine</div>'
        "</div>"
        "</div>"
    )


def render_header_controls_html() -> str:
    """Render the right-aligned header controls: Mobile Library Drawer button + Light/Dark Theme Slider."""
    mobile_lib_btn = (
        '<button id="ap-mobile-library-btn" type="button" title="Open Knowledge Base" aria-label="Open Knowledge Base" '
        "onclick=\"if (window.togglePodSeekDrawer) { window.togglePodSeekDrawer(false); } else { const col = document.querySelector('.ap-col-left'); const bd = document.getElementById('ap-mobile-drawer-backdrop'); if (col) { const isOpen = col.classList.toggle('mobile-drawer-open'); if (bd) bd.classList.toggle('is-open', isOpen); document.body.classList.toggle('ap-drawer-open', isOpen); } }\">"
        '<span style="font-size:12px;line-height:1;display:inline-flex;align-items:center;">📚</span>'
        '<span class="ap-lib-btn-label" style="line-height:1;">Library</span>'
        '<svg width="10" height="10" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" style="display:inline-block;vertical-align:middle;"><path d="M19 9l-7 7-7-7"/></svg>'
        "</button>"
    )
    theme_slider = (
        '<button id="ap-theme-slider" type="button" title="Toggle Light / Dark theme" '
        'onclick="(() => {'
        "const isDark = !document.documentElement.classList.contains('ap-dark');"
        "if (window.podSeekApplyTheme) { window.podSeekApplyTheme(isDark); }"
        "try { localStorage.setItem('podseek_theme', isDark ? 'dark' : 'light'); } catch (e) {}"
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
    )
    return f'<div class="ap-slider-wrap">{mobile_lib_btn}{theme_slider}</div>'


def render_episodes_html(items: list[dict]) -> str:
    """Render the scrollable list of indexed episodes for the desktop regular left pane."""
    count = len(items)
    heading_html = (
        '<div class="ap-episodes-heading" '
        'style="border-top:1px solid var(--border-hairline);margin:8px 0 6px;padding-top:8px;'
        f'font-size:12.5px;font-weight:700;color:var(--text-main);">Indexed Episodes ({count})</div>'
    )
    if not items:
        return (
            heading_html + '<div class="ap-muted" style="font-size:12px;font-family:monospace;padding:8px 0;">'
            "No indexed episodes in data/raw/ yet."
            "</div>"
        )
    cards: list[str] = []
    for ep in items:
        ep_id = html.escape(str(ep.get("episode_id", "")))
        raw_title = str(ep.get("episode_title") or "Huberman Lab Episode")
        title = html.escape(raw_title)
        url = html.escape(str(ep.get("url") or f"https://youtu.be/{ep_id}"))
        thumb = f"https://i.ytimg.com/vi/{ep_id}/hqdefault.jpg"
        cards.append(
            f'<a href="{url}" target="_blank" rel="noopener noreferrer" class="ap-subtle" '
            f'style="display:flex;align-items:center;gap:10px;padding:8px 9px;text-decoration:none;margin-bottom:6px;border-radius:10px;">'
            f'<img src="{thumb}" alt="" '
            f'style="width:46px;height:30px;object-fit:cover;border-radius:6px;flex-shrink:0;background:#18181B;" />'
            f'<div style="min-width:0;flex:1;">'
            f'<div style="font-size:12px;font-weight:600;line-height:1.35;color:var(--text-main);'
            f'display:-webkit-box;-webkit-line-clamp:2;-webkit-box-orient:vertical;overflow:hidden;">'
            f"{title}</div>"
            f'<div class="ap-muted" style="font-size:11px;margin-top:2px;">Huberman Lab</div>'
            f"</div></a>"
        )
    cards_html = "".join(cards)
    return (
        heading_html + '<div class="ap-episodes-list modern-scroll" '
        'style="max-height:clamp(180px, calc(100vh - 360px), 480px);overflow-y:auto;padding-right:4px;">'
        + cards_html
        + "</div>"
    )


def render_header_library_html(items: list[dict]) -> str:
    """Render top header bar controls: mobile-only library drawer pill + theme toggle slider."""
    count = len(items)
    btn_label = f"📚 {count} Eps" if count > 0 else "📚 0 Eps"
    if not items:
        cards_html = (
            '<div class="ap-muted" style="font-size:11.5px;font-family:monospace;padding:12px 8px;text-align:center;">'
            "No indexed episodes yet.<br/>Use ✦ Absorb to add one."
            "</div>"
        )
    else:
        cards: list[str] = []
        for ep in items:
            ep_id = html.escape(str(ep.get("episode_id", "")))
            raw_title = str(ep.get("episode_title") or "Huberman Lab Episode")
            title = html.escape(raw_title)
            url = html.escape(str(ep.get("url") or f"https://youtu.be/{ep_id}"))
            thumb = f"https://i.ytimg.com/vi/{ep_id}/hqdefault.jpg"
            cards.append(
                f'<a href="{url}" target="_blank" rel="noopener noreferrer" class="ap-subtle" '
                f'style="display:flex;align-items:center;gap:10px;padding:8px 10px;text-decoration:none;margin-bottom:6px;border-radius:10px;transition:background 0.15s ease;">'
                f'<img src="{thumb}" alt="" '
                f'style="width:44px;height:28px;object-fit:cover;border-radius:5px;flex-shrink:0;background:#18181B;" />'
                f'<div style="min-width:0;flex:1;">'
                f'<div style="font-size:11.5px;font-weight:600;line-height:1.35;color:var(--text-main);'
                f'display:-webkit-box;-webkit-line-clamp:2;-webkit-box-orient:vertical;overflow:hidden;">'
                f"{title}</div>"
                f'<div class="ap-muted" style="font-size:10.5px;margin-top:2px;">Huberman Lab</div>'
                f"</div></a>"
            )
        cards_html = "".join(cards)

    chevron_svg = (
        '<svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" '
        'stroke-width="2" stroke-linecap="round" stroke-linejoin="round" style="opacity:0.65;flex-shrink:0;">'
        '<path d="M19 9l-7 7-7-7" />'
        "</svg>"
    )

    theme_btn_html = (
        '<button id="ap-theme-slider" type="button" title="Toggle Light / Dark theme" '
        'onclick="(() => {'
        "const isDark = !document.documentElement.classList.contains('ap-dark');"
        "if (window.podSeekApplyTheme) { window.podSeekApplyTheme(isDark); }"
        "try { localStorage.setItem('podseek_theme', isDark ? 'dark' : 'light'); } catch (e) {}"
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
    )

    return (
        '<div class="ap-slider-wrap">'
        '<details class="ap-header-episodes-dropdown ap-mobile-only">'
        f'<summary class="ap-header-episodes-btn" title="View Indexed Huberman Lab Episodes">'
        f"<span>{btn_label}</span>{chevron_svg}"
        "</summary>"
        '<div class="ap-header-episodes-menu modern-scroll">'
        '<div style="display:flex;align-items:center;justify-content:space-between;padding:4px 6px 8px;border-bottom:1px solid var(--border-hairline);margin-bottom:6px;">'
        f'<span style="font-size:11.5px;font-weight:700;color:var(--text-main);">Indexed Episodes ({count})</span>'
        '<span class="ap-muted" style="font-size:10px;font-family:monospace;">Huberman Lab</span>'
        "</div>"
        f"{cards_html}"
        "</div>"
        "</details>"
        f"{theme_btn_html}"
        "</div>"
    )


def render_spotlight_workflow_html(
    active_node: str = "retrieve",
    chunks: int = 0,
    relevant: int = 0,
    rewrites: int = 0,
    mode: str = "balanced",
    top_distance: float | None = None,
    done: bool = False,
    aborted: bool = False,
    cached: bool = False,
) -> str:
    """Render the actual full SVG flowchart animation just like desktop, directly inside the active chat turn."""
    flowchart_svg = render_workflow_graph_html(
        active_node=active_node,
        chunks=chunks,
        relevant=relevant,
        rewrites=rewrites,
        done=done,
        aborted=aborted,
        cached=cached,
        mode=mode,
        top_distance=top_distance,
    )
    mode_label = "⚡ Turbo" if mode == "turbo" else ("🎯 Rigorous" if mode == "rigorous" else "⚖️ Balanced")

    if done:
        return (
            '<details class="ap-trace-details">'
            f'<summary><span style="color:var(--done-stroke);">✓</span> CRAG Flowchart · {chunks} chunks · {mode_label} <span style="font-size:10px;opacity:0.7;">▾</span></summary>'
            '<div style="margin-top:6px;max-width:100%;overflow-x:auto;overflow-y:hidden;" class="modern-scroll">'
            + flowchart_svg
            + "</div></details>"
        )

    return (
        '<div class="ap-spotlight-card" style="padding:6px;overflow-x:auto;overflow-y:hidden;margin-bottom:12px;">'
        + flowchart_svg
        + "</div>"
    )


def render_chat_session_html(history: list[dict], episode_count: int = 50, notice: str = "") -> str:
    """Render the ephemeral session chat thread with rendered Markdown, inline pills, and focus-locked spotlight workflow."""
    notice_html = (
        f'<div id="ap-composer-notice" class="ap-composer-notice" role="status" aria-live="polite">{html.escape(notice)}</div>'
        if notice
        else ""
    )
    if not history:
        count_display = str(episode_count if episode_count > 0 else 50)
        onclick_js = (
            "if (window.togglePodSeekDrawer) { "
            "if (window.innerWidth <= 768) { window.togglePodSeekDrawer(true); } "
            "else { window.togglePodSeekDrawer(); } "
            "} else { "
            "const col = document.querySelector('.ap-col-left'); "
            "if (col) { "
            "if (window.innerWidth <= 768) { "
            "col.classList.remove('is-collapsed'); "
            "col.classList.add('mobile-drawer-open'); "
            "document.getElementById('ap-mobile-drawer-backdrop')?.classList.add('is-open'); "
            "document.body.classList.add('ap-drawer-open'); "
            "} else { "
            "col.classList.toggle('is-collapsed'); "
            "} "
            "} "
            "}"
        )
        return (
            '<div class="ap-chat-viewport-wrap">'
            '<div id="ap-chat-scroll" class="modern-scroll ap-chat-scroll ap-chat-empty">'
            '<div class="ap-empty-hero">'
            '<h1 class="ap-empty-title">Find the moment Huberman said it.</h1>'
            '<p class="ap-empty-intro ap-empty-intro-desktop ap-muted">'
            "Andrew Huberman is a Stanford neuroscientist whose Huberman Lab podcast covers sleep, focus, stress, and health in multi-hour episodes. "
            f'PodSeek searches the transcripts of his <button type="button" onclick="{onclick_js}" class="ap-kb-count-link" title="Toggle episode library">{count_display} most viewed episodes</button> '
            "and answers with citations that jump to the exact second on YouTube."
            "</p>"
            '<p class="ap-empty-intro ap-empty-intro-mobile ap-muted">'
            f'Search <button type="button" onclick="{onclick_js}" class="ap-kb-count-link" title="Toggle episode library">{count_display} of Andrew Huberman\'s most viewed episodes</button> '
            "and jump to the exact second he said it."
            "</p>"
            '<div class="ap-empty-steps">'
            '<div class="ap-empty-step">'
            '<span class="ap-step-num">1</span>'
            '<span class="ap-step-text">Pick a topic or ask a question</span>'
            "</div>"
            '<div class="ap-empty-step">'
            '<span class="ap-step-num">2</span>'
            '<span class="ap-step-text">Choose a mode: Turbo is fast, Rigorous checks every source</span>'
            "</div>"
            '<div class="ap-empty-step">'
            '<span class="ap-step-num">3</span>'
            '<span class="ap-step-text">Tap a timestamp to hear it</span>'
            "</div>"
            "</div>"
            '<div class="ap-empty-footnote ap-empty-footnote-desktop ap-muted">'
            "If the episodes don't cover it, PodSeek says so instead of guessing. Independent project, not affiliated with Huberman Lab. Not medical advice."
            "</div>"
            '<div class="ap-empty-footnote ap-empty-footnote-mobile ap-muted">'
            "Says so when episodes don't cover it. Independent project, not medical advice."
            "</div>"
            f"</div></div>{notice_html}"
            "</div>"
        )
    turns: list[str] = []
    last_done = True
    for idx, item in enumerate(history):
        is_last = idx == len(history) - 1
        q = html.escape(str(item.get("question", "")))
        raw_answer = str(item.get("answer", ""))
        cits = list(item.get("citations") or [])
        wf_info = item.get("workflow")
        spotlight_block = ""
        if isinstance(wf_info, dict):
            spotlight_block = render_spotlight_workflow_html(**wf_info)
            if is_last:
                last_done = bool(wf_info.get("done", False))
        elif is_last:
            last_done = raw_answer not in {"Distilling transcripts...", "Distilling grounded response...", ""}

        if raw_answer in {"Distilling transcripts...", "Distilling grounded response...", ""}:
            rendered_answer = (
                '<div class="ap-desktop-streaming ap-muted" style="display:flex;align-items:center;gap:8px;font-size:13.5px;">'
                '<span class="ap-spin">✦</span> Distilling grounded response...</div>'
            )
        else:
            rendered_answer = render_markdown_with_pills(raw_answer, cits)
            if (
                raw_answer.strip()
                == "I could not find any relevant information in the podcast transcripts to answer your question."
            ):
                rendered_answer += (
                    '<div class="ap-muted ap-refusal-note" style="font-size:12.5px;margin-top:6px;">'
                    "Answers come only from indexed episodes."
                    "</div>"
                )

        answer_content = f"{spotlight_block}{rendered_answer}" if spotlight_block else rendered_answer
        turn_cls = "ap-chat-turn ap-chat-turn-last" if is_last else "ap-chat-turn"
        turn_id = ' id="ap-last-turn"' if is_last else ""
        ans_cls = "ap-subtle ap-chat-answer ap-chat-answer-last" if is_last else "ap-subtle ap-chat-answer"
        ans_id = ' id="ap-last-answer"' if is_last else ""
        turns.append(
            f'<div{turn_id} class="{turn_cls}">'
            f'<div style="display:flex;justify-content:flex-end;margin-bottom:12px;">'
            f'<div style="max-width:85%;background:var(--accent);color:#fff;padding:10px 16px;'
            f'border-radius:16px 16px 4px 16px;font-size:14.5px;font-weight:500;line-height:1.45;letter-spacing:-0.01em;">'
            f"{q}</div></div>"
            f'<div{ans_id} class="{ans_cls}" style="padding:16px 18px;margin-bottom:16px;font-size:14.5px;line-height:1.65;letter-spacing:-0.005em;border-radius:16px;">'
            f"{answer_content}</div>"
            f"</div>"
        )
    done_attr = "true" if last_done else "false"
    return (
        '<div class="ap-chat-viewport-wrap">'
        f'<div id="ap-chat-scroll" class="modern-scroll ap-chat-scroll" data-turn-count="{len(history)}" data-turn-done="{done_attr}" '
        'style="overflow-y:auto;padding-right:4px;">' + "".join(turns) + "</div>"
        '<div id="ap-chat-scroll-nav" class="ap-chat-scroll-nav">'
        '<button type="button" id="ap-scroll-top-btn" class="ap-chat-nav-btn" title="Scroll to top" aria-label="Scroll to top" onclick="const c = document.getElementById(\'ap-chat-scroll\'); if (c) c.scrollTo({ top: 0, behavior: \'smooth\' });">'
        '<svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><path d="M18 15l-6-6-6 6"/></svg>'
        "</button>"
        '<button type="button" id="ap-scroll-bottom-btn" class="ap-chat-nav-btn" title="Scroll to bottom" aria-label="Scroll to bottom" onclick="const c = document.getElementById(\'ap-chat-scroll\'); if (c) c.scrollTo({ top: c.scrollHeight, behavior: \'smooth\' });">'
        '<svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><path d="M6 9l6 6 6-6"/></svg>'
        "</button>"
        f"</div>{notice_html}"
        "</div>"
    )


def render_mode_slider_html(active_mode: str = "balanced") -> str:
    """Render the compact in-capsule tap-to-cycle mode button."""
    clean = (active_mode or "balanced").lower()
    if "turbo" in clean:
        mode_cls = "is-turbo"
        icon = "⚡"
        label = "Turbo"
        desc = "skips grading, 0 rewrites"
    elif "rigorous" in clean:
        mode_cls = "is-rigorous"
        icon = "🎯"
        label = "Rigorous"
        desc = "always grades, up to 2 rewrites"
    else:
        mode_cls = "is-balanced"
        icon = "⚖️"
        label = "Balanced"
        desc = "skips grading if dist < 0.35, else grades, up to 1 rewrite"

    return f"""
    <div class="ap-mode-bar">
      <button id="ap-mode-slider" class="ap-mode-cycle-btn {mode_cls}" type="button" title="{label}: {desc} (Click to cycle modes)" onclick="window.podSeekCycleMode && window.podSeekCycleMode()">
        <span class="ms-thumb"></span>
        <span class="cycle-icon-badge">{icon}</span>
        <span class="cycle-label">{label}</span>
      </button>
    </div>
    """


def _render_turbo_workflow_html(
    active_node: str,
    chunks: int,
    done: bool,
    is_cached: bool,
    top_distance: float | None,
) -> str:
    """Spacious 2-node pipeline for Turbo mode: Retrieve directly fused into Generate."""
    ret_cls = (
        "is-running"
        if active_node == "retrieve"
        else ("is-completed" if done or is_cached or active_node == "generate" else "")
    )
    gen_cls = "is-running" if active_node == "generate" else ("is-completed" if (done or is_cached) else "")
    cache_cls = "is-completed" if (is_cached or done) else ("opacity-60" if active_node == "idle" else "")

    ret_status = (
        "⚡ Cached"
        if is_cached
        else ("⟳ Running" if active_node == "retrieve" else ("✓ Done" if ret_cls == "is-completed" else "Idle"))
    )
    ret_sub = f"{chunks} chunks fetched" if chunks > 0 else "Vector similarity"
    cache_status = "⚡ Hit" if is_cached else ("✓ Saved" if done else "Idle")
    cache_sub = "0 LLM calls · 0ms" if is_cached else ("Stored for reuse" if done else "Normalized lookup")

    gen_status = (
        "⚡ Cached" if is_cached else ("⟳ Running" if active_node == "generate" else ("✓ Done" if done else "Queued"))
    )
    gen_sub = "1-call fused synthesis · Citations inlined"

    c_ret_cache = "conn-completed" if (is_cached or done) else "conn-idle"
    c_fused = (
        "conn-completed"
        if (done or is_cached)
        else ("conn-running" if active_node in {"retrieve", "generate"} else "conn-idle")
    )

    top_badge_html = (
        '<span class="ap-subtle" style="font-size:12px;font-family:monospace;padding:2px 8px;color:var(--done-stroke);border-color:var(--done-stroke);white-space:nowrap;flex-shrink:0;">⚡ Cache Hit</span>'
        if is_cached
        else '<span class="ap-subtle" style="font-size:10.5px;font-family:monospace;padding:2px 6px;color:var(--accent);white-space:nowrap;flex-shrink:0;">⚡ Fast · 0 Rewrites</span>'
    )

    return f"""
    <div class="wf-dot-grid">
      <div style="display:flex;align-items:center;justify-content:space-between;margin-bottom:8px;gap:8px;white-space:nowrap;">
        <span style="font-size:12px;font-weight:700;white-space:nowrap;flex-shrink:0;">Workflow · Turbo RAG</span>
        {top_badge_html}
      </div>
      <div class="wf-canvas-wrap" data-orig-height="440" style="position:relative;width:330px;height:440px;">
        <svg width="330" height="440" viewBox="0 0 330 440" style="position:absolute;inset:0;pointer-events:none;">
          <!-- 0. Retrieve <-> QA Cache -->
          <path d="M 178 35 L 192 35" class="{c_ret_cache}" stroke-width="1.5" />

          <!-- 1. Direct Fused Connector: Retrieve (94,62) -> Generate (94,250) -->
          <path d="M 94 62 L 94 250" class="{c_fused}" stroke-width="2" />
          <polygon points="90,245 94,252 98,245" fill="var(--accent)" />

          <!-- Centered Badge on Fused Bypass Path -->
          <rect x="22" y="140" width="286" height="26" rx="13" fill="var(--bg-card)" stroke="var(--accent)" stroke-width="1.25" />
          <text x="165" y="157" text-anchor="middle" fill="var(--accent)" font-size="10.5" font-weight="700" font-family="monospace">⚡ Fused Bypass · Grading &amp; Rewrites Bypassed</text>
        </svg>

        <!-- Process Node 1: Retrieve -->
        <div class="wf-node {ret_cls}" style="left:10px;top:10px;width:168px;height:52px;">
          <svg class="node-trace-svg" viewBox="0 0 170 54">
            <rect class="trace-base" x="1.5" y="1.5" width="167" height="51" rx="10" />
            <rect class="trace-beam" x="1.5" y="1.5" width="167" height="51" rx="10" pathLength="100" />
          </svg>
          <div style="display:flex;justify-content:space-between;font-size:12px;white-space:nowrap;">
            <span style="font-weight:600;">🔍 Retrieve</span>
            <span style="font-family:monospace;">{ret_status}</span>
          </div>
          <div class="ap-muted" style="font-size:11.5px;font-family:monospace;margin-top:2px;white-space:nowrap;">{ret_sub}</div>
        </div>

        <!-- Node 2: QA Cache -->
        <div class="wf-node {cache_cls}" style="left:192px;top:10px;width:134px;height:52px;">
          <svg class="node-trace-svg" viewBox="0 0 136 54">
            <rect class="trace-base" x="1.5" y="1.5" width="133" height="51" rx="10" />
            <rect class="trace-beam" x="1.5" y="1.5" width="133" height="51" rx="10" pathLength="100" />
          </svg>
          <div style="display:flex;justify-content:space-between;font-size:11.5px;white-space:nowrap;">
            <span style="font-weight:600;">⚡ QA Cache</span>
            <span style="font-family:monospace;color:{"var(--done-stroke)" if is_cached else "inherit"};">{cache_status}</span>
          </div>
          <div class="ap-muted" style="font-size:11px;font-family:monospace;margin-top:2px;white-space:nowrap;">{cache_sub}</div>
        </div>

        <!-- Node 3: Fused Generate & Cite (Full-Width Roomy Node) -->
        <div class="wf-node {gen_cls}" style="left:10px;top:250px;width:316px;height:72px;">
          <svg class="node-trace-svg" viewBox="0 0 318 74">
            <rect class="trace-base" x="1.5" y="1.5" width="315" height="71" rx="12" />
            <rect class="trace-beam" x="1.5" y="1.5" width="315" height="71" rx="12" pathLength="100" />
          </svg>
          <div style="display:flex;justify-content:space-between;font-size:12.5px;white-space:nowrap;">
            <span style="font-weight:600;">✨ Fused Generate &amp; Cite</span>
            <span style="font-family:monospace;">{gen_status}</span>
          </div>
          <div class="ap-muted" style="font-size:11.5px;font-family:monospace;margin-top:4px;white-space:nowrap;">{gen_sub}</div>
        </div>
      </div>
    </div>
    """


def _render_balanced_workflow_html(
    active_node: str,
    chunks: int,
    relevant: int,
    rewrites: int,
    done: bool,
    is_aborted: bool,
    is_cached: bool,
    top_distance: float | None,
) -> str:
    """Dedicated Balanced flowchart with fast-path skip, dual decision diamonds, loopback retry, and abort."""
    max_rewrites_display = 1
    aborted_due_to_retries = (
        is_aborted or active_node == "abort" or (done and relevant == 0 and rewrites >= max_rewrites_display)
    )
    is_fast_path = (top_distance is not None and top_distance < 0.35) or (
        done and rewrites == 0 and relevant > 0 and active_node != "grade_documents" and not aborted_due_to_retries
    )
    took_grade = (
        active_node == "grade_documents"
        or (top_distance is not None and top_distance >= 0.35)
        or rewrites > 0
        or aborted_due_to_retries
    )

    ret_cls = (
        "is-running"
        if active_node == "retrieve"
        else (
            "is-completed"
            if done
            or aborted_due_to_retries
            or is_cached
            or active_node in {"grade_documents", "rewrite_query", "generate"}
            else ""
        )
    )
    grd_cls = (
        "is-running"
        if active_node == "grade_documents"
        else (
            "is-completed"
            if (took_grade and (done or aborted_due_to_retries or active_node in {"rewrite_query", "generate"}))
            else ("opacity-60" if is_fast_path else "")
        )
    )
    rew_cls = "is-retrying" if active_node == "rewrite_query" else ("is-completed" if rewrites > 0 else "opacity-60")
    gen_cls = (
        "opacity-60"
        if aborted_due_to_retries
        else ("is-running" if active_node == "generate" else ("is-completed" if (done or is_cached) else ""))
    )
    abt_cls = "is-aborted" if aborted_due_to_retries else "opacity-60"
    cache_cls = (
        "is-completed"
        if (is_cached or (done and not aborted_due_to_retries))
        else ("opacity-60" if active_node == "idle" or aborted_due_to_retries else "")
    )

    ret_status = (
        "⚡ Cached"
        if is_cached
        else ("⟳ Running" if active_node == "retrieve" else ("✓ Done" if ret_cls == "is-completed" else "Idle"))
    )
    ret_sub = f"{chunks} chunks · dist: {top_distance:.2f}" if top_distance is not None else f"{chunks} chunks fetched"

    grd_status = (
        "⚡ Bypassed"
        if is_fast_path
        else (
            "⟳ Running" if active_node == "grade_documents" else ("✓ Done" if grd_cls == "is-completed" else "Queued")
        )
    )
    grd_sub = f"{relevant} / {chunks} relevant" if took_grade else "Fallback if dist ≥ 0.35"

    rew_status = "⟳ Running" if active_node == "rewrite_query" else ("✓ Done" if rewrites > 0 else "Idle")
    rew_sub = f"Retry {rewrites} / 1 max"

    gen_status = (
        "Skipped"
        if aborted_due_to_retries
        else (
            "⚡ Cached"
            if is_cached
            else ("⟳ Running" if active_node == "generate" else ("✓ Done" if done else "Queued"))
        )
    )
    gen_sub = "⚡ Fast-path synthesis" if is_fast_path else "Cited synthesis"

    abt_status = "✕ Max" if aborted_due_to_retries else "Idle"
    abt_sub = "Max retries (1/1)" if aborted_due_to_retries else "Circuit breaker"

    cache_status = "⚡ Hit" if is_cached else ("✓ Saved" if (done and not aborted_due_to_retries) else "Idle")
    cache_sub = (
        "0 LLM calls · 0ms"
        if is_cached
        else ("Stored for reuse" if (done and not aborted_due_to_retries) else "Normalized lookup")
    )

    c_ret_cache = "conn-completed" if (is_cached or (done and not aborted_due_to_retries)) else "conn-idle"
    c_ret_grd = (
        "conn-running"
        if active_node == "grade_documents"
        else ("conn-completed" if grd_cls == "is-completed" and not is_fast_path else "conn-idle")
    )
    c_fastpath = (
        "conn-completed"
        if is_fast_path and (done or is_cached)
        else ("conn-running" if (active_node == "generate" and is_fast_path) else "conn-idle")
    )
    fastpath_arrow = "var(--done-stroke)" if is_fast_path else "var(--border-strong)"
    c_grd_dec = (
        "conn-completed"
        if (done or aborted_due_to_retries or is_cached)
        else (
            "conn-running"
            if active_node in {"rewrite_query", "generate"}
            else ("conn-completed" if grd_cls == "is-completed" else "conn-idle")
        )
    )
    c_dec_gen = (
        "conn-idle"
        if aborted_due_to_retries
        else (
            "conn-running"
            if active_node == "generate" and not is_fast_path
            else ("conn-completed" if (done or is_cached) and not is_fast_path else "conn-idle")
        )
    )
    c_dec1_dec2 = (
        "conn-aborted"
        if aborted_due_to_retries
        else (
            "conn-retrying" if active_node == "rewrite_query" else ("conn-completed" if rewrites > 0 else "conn-idle")
        )
    )
    c_dec2_rew = (
        "conn-retrying" if active_node == "rewrite_query" else ("conn-completed" if rewrites > 0 else "conn-idle")
    )
    c_dec2_abt = "conn-aborted" if aborted_due_to_retries else "conn-idle"
    c_rew_ret = (
        "conn-retrying"
        if (active_node == "retrieve" and rewrites > 0)
        else ("conn-completed" if rewrites > 0 else "conn-idle")
    )

    diamond0_stroke = (
        "var(--done-stroke)" if is_fast_path else ("var(--retry-stroke)" if took_grade else "var(--border-strong)")
    )
    diamond1_stroke = (
        "#EF4444"
        if aborted_due_to_retries
        else (
            "var(--retry-stroke)"
            if active_node == "rewrite_query"
            else (
                "var(--done-stroke)"
                if (done or is_cached or active_node == "generate") and not is_fast_path
                else "var(--border-strong)"
            )
        )
    )
    diamond2_stroke = (
        "#EF4444"
        if aborted_due_to_retries
        else (
            "var(--retry-stroke)"
            if active_node == "rewrite_query"
            else ("var(--done-stroke)" if rewrites > 0 else "var(--border-strong)")
        )
    )

    top_badge_html = (
        '<span class="ap-subtle" style="font-size:11.5px;font-family:monospace;padding:2px 8px;color:var(--done-stroke);border-color:var(--done-stroke);white-space:nowrap;flex-shrink:0;">⚡ Cache Hit</span>'
        if is_cached
        else f'<span class="ap-subtle" style="font-size:10.5px;font-family:monospace;padding:2px 6px;white-space:nowrap;flex-shrink:0;">Rewrites: {rewrites} / 1</span>'
    )

    return f"""
    <div class="wf-dot-grid">
      <div style="display:flex;align-items:center;justify-content:space-between;margin-bottom:8px;gap:8px;white-space:nowrap;">
        <span style="font-size:12px;font-weight:700;white-space:nowrap;flex-shrink:0;">Workflow · Balanced RAG</span>
        {top_badge_html}
      </div>
      <div class="wf-canvas-wrap" data-orig-height="440" style="position:relative;width:330px;height:440px;">
        <svg width="330" height="440" viewBox="0 0 330 440" style="position:absolute;inset:0;pointer-events:none;">
          <!-- 0. Retrieve <-> QA Cache -->
          <path d="M 178 35 L 192 35" class="{c_ret_cache}" stroke-width="1.5" />

          <!-- Retrieve (94,60) -> Diamond 0 Top (94,86) -->
          <path d="M 94 60 L 94 86" class="{c_ret_grd}" stroke-width="1.5" />
          <polygon points="91,82 94,87 97,82" fill="var(--border-strong)" />

          <!-- Diamond 0: Fast-Path Decision: dist < 0.35? (Center: 94, 100) -->
          <polygon points="94,86 142,100 94,114 46,100" fill="var(--bg-card)" stroke="{diamond0_stroke}" stroke-width="1.5" />
          <text x="94" y="103" text-anchor="middle" fill="var(--text-main)" font-size="8.5" font-weight="700" font-family="monospace">dist &lt; 0.35?</text>

          <!-- Fast-Path Left Bypass Line: Diamond 0 Left (46, 100) -> left to 8 -> down to 205 -> right to 36 -> down to 345 (centered through Skip Grading box at x=36) -->
          <path d="M 46 100 L 8 100 L 8 205 L 36 205 L 36 345" class="{c_fastpath}" stroke-width="1.8" stroke-dasharray="4 3" />
          <polygon points="33,341 36,346 39,341" fill="{fastpath_arrow}" />
          <rect x="2" y="225" width="68" height="15" rx="4" fill="var(--bg-card)" stroke="var(--border-hairline)" />
          <text x="36" y="236" text-anchor="middle" fill="var(--done-stroke)" font-size="8.5" font-weight="600" font-family="monospace">Skip Grading</text>

          <!-- Fallback Line: Diamond 0 Bottom (94, 114) -> Grade Top (94, 148) -->
          <path d="M 94 114 L 94 148" class="{c_ret_grd}" stroke-width="1.5" />
          <polygon points="91,144 94,149 97,144" fill="var(--border-strong)" />
          <rect x="80" y="124" width="28" height="15" rx="4" fill="var(--bg-card)" stroke="var(--border-hairline)" />
          <text x="94" y="135" text-anchor="middle" fill="var(--retry-stroke)" font-size="9.5" font-weight="600" font-family="monospace">No</text>

          <!-- Grade Bottom (94, 198) -> Diamond 1 Top (94, 238) -->
          <path d="M 94 198 L 94 238" class="{c_grd_dec}" stroke-width="1.5" />
          <polygon points="91,234 94,239 97,234" fill="var(--border-strong)" />

          <!-- Decision Diamond 1: >=1 relevant? (Center: 94, 265) -->
          <polygon points="94,238 148,265 94,292 40,265" fill="var(--bg-card)" stroke="{diamond1_stroke}" stroke-width="1.75" />
          <text x="94" y="268" text-anchor="middle" fill="var(--text-main)" font-size="9.5" font-weight="600" font-family="monospace">≥1 relevant?</text>

          <!-- Yes Branch: Diamond 1 Bottom (94, 292) -> Generate Top (94, 345) -->
          <path d="M 94 292 L 94 345" class="{c_dec_gen}" stroke-width="1.5" />
          <polygon points="91,341 94,346 97,341" fill="var(--border-strong)" />
          <rect x="76" y="310" width="36" height="15" rx="4" fill="var(--bg-card)" stroke="var(--border-hairline)" />
          <text x="94" y="321" text-anchor="middle" fill="var(--done-stroke)" font-size="10" font-weight="600" font-family="monospace">Yes</text>

          <!-- No Branch: Diamond 1 Right (148, 265) -> Diamond 2 Left (202, 265) -->
          <path d="M 148 265 L 202 265" class="{c_dec1_dec2}" stroke-width="1.5" />
          <polygon points="198,262 203,265 198,268" fill="var(--border-strong)" />
          <rect x="160" y="258" width="28" height="15" rx="4" fill="var(--bg-card)" stroke="var(--border-hairline)" />
          <text x="174" y="269" text-anchor="middle" fill="var(--retry-stroke)" font-size="10" font-weight="600" font-family="monospace">No</text>

          <!-- Decision Diamond 2: Retries < 1? (Center: 256, 265) -->
          <polygon points="256,238 310,265 256,292 202,265" fill="var(--bg-card)" stroke="{diamond2_stroke}" stroke-width="1.75" />
          <text x="256" y="268" text-anchor="middle" fill="var(--text-main)" font-size="9.5" font-weight="600" font-family="monospace">Retries &lt; 1?</text>

          <!-- Yes (Retry): Diamond 2 Top (256, 238) -> Rewrite Bottom (256, 198) -->
          <path d="M 256 238 L 256 198" class="{c_dec2_rew}" stroke-width="1.5" />
          <polygon points="253,202 256,197 259,202" fill="var(--border-strong)" />
          <rect x="238" y="210" width="36" height="14" rx="4" fill="var(--bg-card)" stroke="var(--border-hairline)" />
          <text x="256" y="220" text-anchor="middle" fill="var(--retry-stroke)" font-size="9.5" font-weight="600" font-family="monospace">Yes</text>

          <!-- No (Abort): Diamond 2 Bottom (256, 292) -> Abort Top (256, 345) -->
          <path d="M 256 292 L 256 345" class="{c_dec2_abt}" stroke-width="1.5" />
          <polygon points="253,341 256,346 259,341" fill="var(--border-strong)" />
          <rect x="242" y="310" width="28" height="15" rx="4" fill="var(--bg-card)" stroke="var(--border-hairline)" />
          <text x="256" y="321" text-anchor="middle" fill="#EF4444" font-size="10" font-weight="600" font-family="monospace">No</text>

          <!-- Loopback: Rewrite Top (212, 148) -> Retrieve Right Side (178, 35) -->
          <path d="M 212 148 L 212 70 L 185 70 L 185 35 L 178 35" class="{c_rew_ret}" stroke-width="1.5" />
          <polygon points="182,32 177,35 182,38" fill="var(--border-strong)" />
        </svg>

        <!-- Node 1: Retrieve -->
        <div class="wf-node {ret_cls}" style="left:10px;top:10px;width:168px;height:50px;">
          <svg class="node-trace-svg" viewBox="0 0 170 52">
            <rect class="trace-base" x="1.5" y="1.5" width="167" height="49" rx="10" />
            <rect class="trace-beam" x="1.5" y="1.5" width="167" height="49" rx="10" pathLength="100" />
          </svg>
          <div style="display:flex;justify-content:space-between;font-size:12px;white-space:nowrap;">
            <span style="font-weight:600;">🔍 Retrieve</span>
            <span style="font-family:monospace;">{ret_status}</span>
          </div>
          <div class="ap-muted" style="font-size:11px;font-family:monospace;margin-top:2px;white-space:nowrap;">{ret_sub}</div>
        </div>

        <!-- Node 2: QA Cache -->
        <div class="wf-node {cache_cls}" style="left:190px;top:10px;width:132px;height:50px;">
          <svg class="node-trace-svg" viewBox="0 0 134 52">
            <rect class="trace-base" x="1.5" y="1.5" width="131" height="49" rx="10" />
            <rect class="trace-beam" x="1.5" y="1.5" width="131" height="49" rx="10" pathLength="100" />
          </svg>
          <div style="display:flex;justify-content:space-between;align-items:center;font-size:11.5px;white-space:nowrap;gap:4px;">
            <span style="font-weight:600;flex-shrink:0;">⚡ QA Cache</span>
            <span style="font-family:monospace;font-size:10px;flex-shrink:0;color:{"var(--done-stroke)" if is_cached else "inherit"};">{cache_status}</span>
          </div>
          <div class="ap-muted" style="font-size:10.5px;font-family:monospace;margin-top:2px;white-space:nowrap;">{cache_sub}</div>
        </div>

        <!-- Node 3: Grade (Fallback) -->
        <div class="wf-node {grd_cls}" style="left:10px;top:148px;width:168px;height:50px;">
          <svg class="node-trace-svg" viewBox="0 0 170 52">
            <rect class="trace-base" x="1.5" y="1.5" width="167" height="49" rx="10" />
            <rect class="trace-beam" x="1.5" y="1.5" width="167" height="49" rx="10" pathLength="100" />
          </svg>
          <div style="display:flex;justify-content:space-between;font-size:12px;white-space:nowrap;">
            <span style="font-weight:600;">⚖️ Grade</span>
            <span style="font-family:monospace;">{grd_status}</span>
          </div>
          <div class="ap-muted" style="font-size:11.5px;font-family:monospace;margin-top:2px;white-space:nowrap;">{grd_sub}</div>
        </div>

        <!-- Node 4: Rewrite (Retry 1/1) -->
        <div class="wf-node {rew_cls}" style="left:190px;top:148px;width:132px;height:50px;">
          <svg class="node-trace-svg" viewBox="0 0 134 52">
            <rect class="trace-base" x="1.5" y="1.5" width="131" height="49" rx="10" />
            <rect class="trace-beam" x="1.5" y="1.5" width="131" height="49" rx="10" pathLength="100" />
          </svg>
          <div style="display:flex;justify-content:space-between;align-items:center;font-size:11.5px;white-space:nowrap;gap:4px;">
            <span style="font-weight:600;flex-shrink:0;">✍️ Rewrite</span>
            <span style="font-family:monospace;font-size:10px;flex-shrink:0;">{rew_status}</span>
          </div>
          <div class="ap-muted" style="font-size:10.5px;font-family:monospace;margin-top:2px;white-space:nowrap;">{rew_sub}</div>
        </div>

        <!-- Node 5: Generate (Destination for Fast-Path or Relevant Grade) -->
        <div class="wf-node {gen_cls}" style="left:10px;top:345px;width:168px;height:50px;">
          <svg class="node-trace-svg" viewBox="0 0 170 52">
            <rect class="trace-base" x="1.5" y="1.5" width="167" height="49" rx="10" />
            <rect class="trace-beam" x="1.5" y="1.5" width="167" height="49" rx="10" pathLength="100" />
          </svg>
          <div style="display:flex;justify-content:space-between;font-size:12px;white-space:nowrap;">
            <span style="font-weight:600;">✨ Generate</span>
            <span style="font-family:monospace;">{gen_status}</span>
          </div>
          <div class="ap-muted" style="font-size:11.5px;font-family:monospace;margin-top:2px;white-space:nowrap;">{gen_sub}</div>
        </div>

        <!-- Node 6: Abort (Circuit Breaker Terminator) -->
        <div class="wf-node {abt_cls}" style="left:190px;top:345px;width:132px;height:50px;border-radius:16px;">
          <div style="display:flex;justify-content:space-between;align-items:center;font-size:11.5px;white-space:nowrap;gap:4px;">
            <span style="font-weight:600;flex-shrink:0;">🛑 Abort</span>
            <span style="font-family:monospace;font-size:10px;flex-shrink:0;color:{"#EF4444" if aborted_due_to_retries else "inherit"};">{abt_status}</span>
          </div>
          <div class="ap-muted" style="font-size:10.5px;font-family:monospace;margin-top:2px;white-space:nowrap;">{abt_sub}</div>
        </div>
      </div>
    </div>
    """


def _render_rigorous_workflow_html(
    active_node: str,
    chunks: int,
    relevant: int,
    rewrites: int,
    done: bool,
    is_aborted: bool,
    is_cached: bool,
    top_distance: float | None,
) -> str:
    """Full Corrective RAG cycle for Rigorous mode: dual diamonds, up to 2 rewrites, circuit breaker."""
    ret_cls = (
        "is-running"
        if active_node == "retrieve"
        else (
            "is-completed"
            if done or is_aborted or is_cached or active_node in {"grade_documents", "rewrite_query", "generate"}
            else ""
        )
    )
    grd_cls = (
        "is-running"
        if active_node == "grade_documents"
        else ("is-completed" if done or is_aborted or is_cached or active_node in {"rewrite_query", "generate"} else "")
    )
    rew_cls = "is-retrying" if active_node == "rewrite_query" else ("is-completed" if rewrites > 0 else "opacity-60")
    gen_cls = (
        "opacity-60"
        if is_aborted
        else ("is-running" if active_node == "generate" else ("is-completed" if (done or is_cached) else ""))
    )
    abt_cls = "is-aborted" if is_aborted else "opacity-60"
    cache_cls = (
        "is-completed"
        if (is_cached or (done and not is_aborted))
        else ("opacity-60" if active_node == "idle" or is_aborted else "")
    )

    ret_status = (
        "⚡ Cached"
        if is_cached
        else ("⟳ Running" if active_node == "retrieve" else ("✓ Done" if ret_cls == "is-completed" else "Idle"))
    )
    ret_sub = f"{chunks} chunks fetched"
    grd_status = (
        "⚡ Cached"
        if is_cached
        else (
            "⟳ Running" if active_node == "grade_documents" else ("✓ Done" if grd_cls == "is-completed" else "Queued")
        )
    )
    grd_sub = f"{relevant} / {chunks} relevant"
    rew_status = "⟳ Running" if active_node == "rewrite_query" else ("✓ Done" if rewrites > 0 else "Idle")
    rew_sub = f"Retry {rewrites} / 2"
    gen_status = (
        "Skipped"
        if is_aborted
        else (
            "⚡ Cached"
            if is_cached
            else ("⟳ Running" if active_node == "generate" else ("✓ Done" if done else "Queued"))
        )
    )
    gen_sub = "Cited synthesis"
    abt_status = "✕ Max" if is_aborted else "Idle"
    abt_sub = "Max retries (2/2)" if is_aborted else "Circuit breaker"

    cache_status = "⚡ Hit" if is_cached else ("✓ Saved" if (done and not is_aborted) else "Idle")
    cache_sub = (
        "0 LLM calls · 0ms" if is_cached else ("Stored for reuse" if (done and not is_aborted) else "Normalized lookup")
    )

    c_ret_cache = "conn-completed" if (is_cached or (done and not is_aborted)) else "conn-idle"
    c_ret_grd = (
        "conn-running"
        if active_node == "grade_documents"
        else ("conn-completed" if grd_cls == "is-completed" else "conn-idle")
    )
    c_grd_dec = (
        "conn-completed"
        if (done or is_aborted or is_cached)
        else (
            "conn-running"
            if active_node in {"rewrite_query", "generate"}
            else ("conn-completed" if grd_cls == "is-completed" else "conn-idle")
        )
    )
    c_dec_gen = (
        "conn-idle"
        if is_aborted
        else (
            "conn-running" if active_node == "generate" else ("conn-completed" if (done or is_cached) else "conn-idle")
        )
    )
    c_dec1_dec2 = (
        "conn-aborted"
        if is_aborted
        else (
            "conn-retrying" if active_node == "rewrite_query" else ("conn-completed" if rewrites > 0 else "conn-idle")
        )
    )
    c_dec2_rew = (
        "conn-retrying" if active_node == "rewrite_query" else ("conn-completed" if rewrites > 0 else "conn-idle")
    )
    c_dec2_abt = "conn-aborted" if is_aborted else "conn-idle"
    c_rew_ret = (
        "conn-retrying"
        if (active_node == "retrieve" and rewrites > 0)
        else ("conn-completed" if rewrites > 0 else "conn-idle")
    )

    diamond1_stroke = (
        "#EF4444"
        if is_aborted
        else (
            "var(--retry-stroke)"
            if active_node == "rewrite_query"
            else ("var(--done-stroke)" if (done or is_cached or active_node == "generate") else "var(--border-strong)")
        )
    )
    diamond2_stroke = (
        "#EF4444"
        if is_aborted
        else (
            "var(--retry-stroke)"
            if active_node == "rewrite_query"
            else ("var(--done-stroke)" if rewrites > 0 else "var(--border-strong)")
        )
    )

    top_badge_html = (
        '<span class="ap-subtle" style="font-size:11.5px;font-family:monospace;padding:2px 8px;color:var(--done-stroke);border-color:var(--done-stroke);white-space:nowrap;flex-shrink:0;">⚡ Cache Hit</span>'
        if is_cached
        else f'<span class="ap-subtle" style="font-size:10.5px;font-family:monospace;padding:2px 6px;white-space:nowrap;flex-shrink:0;">Rewrites: {rewrites} / 2</span>'
    )

    return f"""
    <div class="wf-dot-grid">
      <div style="display:flex;align-items:center;justify-content:space-between;margin-bottom:8px;gap:8px;white-space:nowrap;">
        <span style="font-size:12px;font-weight:700;white-space:nowrap;flex-shrink:0;">Workflow · Corrective RAG</span>
        {top_badge_html}
      </div>
      <div class="wf-canvas-wrap" data-orig-height="440" style="position:relative;width:330px;height:440px;">
        <svg width="330" height="440" viewBox="0 0 330 440" style="position:absolute;inset:0;pointer-events:none;">
          <!-- 0. Retrieve <-> QA Cache -->
          <path d="M 178 35 L 192 35" class="{c_ret_cache}" stroke-width="1.5" />

          <!-- 1. Retrieve (94,60) -> Grade (94,148) -->
          <path d="M 94 60 L 94 148" class="{c_ret_grd}" stroke-width="1.5" />
          <polygon points="91,144 94,149 97,144" fill="var(--border-strong)" />

          <!-- 2. Grade (94,198) -> Decision Diamond 1 (94,238) -->
          <path d="M 94 198 L 94 238" class="{c_grd_dec}" stroke-width="1.5" />
          <polygon points="91,234 94,239 97,234" fill="var(--border-strong)" />

          <!-- 3. Decision Diamond 1: ≥1 relevant? (Center: 94, 265) -->
          <polygon points="94,238 148,265 94,292 40,265"
                   fill="var(--bg-card)" stroke="{diamond1_stroke}" stroke-width="1.75" />
          <text x="94" y="268" text-anchor="middle" fill="var(--text-main)"
                font-size="9.5" font-weight="600" font-family="monospace">≥1 relevant?</text>

          <!-- 4. Yes Branch: Diamond 1 Bottom (94,292) -> Generate Top (94,345) -->
          <path d="M 94 292 L 94 345" class="{c_dec_gen}" stroke-width="1.5" />
          <polygon points="91,341 94,346 97,341" fill="var(--border-strong)" />
          <rect x="76" y="310" width="36" height="15" rx="4" fill="var(--bg-card)" stroke="var(--border-hairline)" />
          <text x="94" y="321" text-anchor="middle" fill="var(--done-stroke)" font-size="10" font-weight="600" font-family="monospace">Yes</text>

          <!-- 5. No Branch: Diamond 1 Right (148,265) -> Diamond 2 Left (204,265) -->
          <path d="M 148 265 L 204 265" class="{c_dec1_dec2}" stroke-width="1.5" />
          <polygon points="200,262 205,265 200,268" fill="var(--border-strong)" />
          <rect x="162" y="258" width="28" height="15" rx="4" fill="var(--bg-card)" stroke="var(--border-hairline)" />
          <text x="176" y="269" text-anchor="middle" fill="var(--retry-stroke)" font-size="10" font-weight="600" font-family="monospace">No</text>

          <!-- 6. Decision Diamond 2: Retries < 2? (Center: 259, 265) -->
          <polygon points="259,238 314,265 259,292 204,265"
                   fill="var(--bg-card)" stroke="{diamond2_stroke}" stroke-width="1.75" />
          <text x="259" y="268" text-anchor="middle" fill="var(--text-main)"
                font-size="9.5" font-weight="600" font-family="monospace">Retries &lt; 2?</text>

          <!-- 7. Yes (Retry): Diamond 2 Top (256,238) -> Rewrite Bottom (256,198) -->
          <path d="M 256 238 L 256 198" class="{c_dec2_rew}" stroke-width="1.5" />
          <polygon points="253,202 256,197 259,202" fill="var(--border-strong)" />
          <rect x="238" y="210" width="36" height="14" rx="4" fill="var(--bg-card)" stroke="var(--border-hairline)" />
          <text x="256" y="220" text-anchor="middle" fill="var(--retry-stroke)" font-size="9.5" font-weight="600" font-family="monospace">Yes</text>

          <!-- 8. No (Abort): Diamond 2 Bottom (256,292) -> Abort Top (256,345) -->
          <path d="M 256 292 L 256 345" class="{c_dec2_abt}" stroke-width="1.5" />
          <polygon points="253,341 256,346 259,341" fill="var(--border-strong)" />
          <rect x="242" y="310" width="28" height="15" rx="4" fill="var(--bg-card)" stroke="var(--border-hairline)" />
          <text x="256" y="321" text-anchor="middle" fill="#EF4444" font-size="10" font-weight="600" font-family="monospace">No</text>

          <!-- 9. Loopback: Rewrite Top (212,148) -> Retrieve Right Side (178,35) -->
          <path d="M 212 148 L 212 70 L 185 70 L 185 35 L 178 35" class="{c_rew_ret}" stroke-width="1.5" />
          <polygon points="182,32 177,35 182,38" fill="var(--border-strong)" />
        </svg>

        <!-- Process Node 1: Retrieve -->
        <div class="wf-node {ret_cls}" style="left:10px;top:10px;width:168px;height:50px;">
          <svg class="node-trace-svg" viewBox="0 0 170 52">
            <rect class="trace-base" x="1.5" y="1.5" width="167" height="49" rx="10" />
            <rect class="trace-beam" x="1.5" y="1.5" width="167" height="49" rx="10" pathLength="100" />
          </svg>
          <div style="display:flex;justify-content:space-between;font-size:12px;white-space:nowrap;">
            <span style="font-weight:600;">🔍 Retrieve</span>
            <span style="font-family:monospace;">{ret_status}</span>
          </div>
          <div class="ap-muted" style="font-size:11.5px;font-family:monospace;margin-top:2px;white-space:nowrap;">{ret_sub}</div>
        </div>

        <!-- Node 2: QA Cache -->
        <div class="wf-node {cache_cls}" style="left:190px;top:10px;width:132px;height:50px;">
          <svg class="node-trace-svg" viewBox="0 0 134 52">
            <rect class="trace-base" x="1.5" y="1.5" width="131" height="49" rx="10" />
            <rect class="trace-beam" x="1.5" y="1.5" width="131" height="49" rx="10" pathLength="100" />
          </svg>
          <div style="display:flex;justify-content:space-between;align-items:center;font-size:11.5px;white-space:nowrap;gap:4px;">
            <span style="font-weight:600;flex-shrink:0;">⚡ QA Cache</span>
            <span style="font-family:monospace;font-size:10px;flex-shrink:0;color:{"var(--done-stroke)" if is_cached else "inherit"};">{cache_status}</span>
          </div>
          <div class="ap-muted" style="font-size:10.5px;font-family:monospace;margin-top:2px;white-space:nowrap;">{cache_sub}</div>
        </div>

        <!-- Node 3: Grade -->
        <div class="wf-node {grd_cls}" style="left:10px;top:148px;width:168px;height:50px;">
          <svg class="node-trace-svg" viewBox="0 0 170 52">
            <rect class="trace-base" x="1.5" y="1.5" width="167" height="49" rx="10" />
            <rect class="trace-beam" x="1.5" y="1.5" width="167" height="49" rx="10" pathLength="100" />
          </svg>
          <div style="display:flex;justify-content:space-between;font-size:12px;white-space:nowrap;">
            <span style="font-weight:600;">⚖️ Grade</span>
            <span style="font-family:monospace;">{grd_status}</span>
          </div>
          <div class="ap-muted" style="font-size:11.5px;font-family:monospace;margin-top:2px;white-space:nowrap;">{grd_sub}</div>
        </div>

        <!-- Node 4: Rewrite -->
        <div class="wf-node {rew_cls}" style="left:190px;top:148px;width:132px;height:50px;">
          <svg class="node-trace-svg" viewBox="0 0 134 52">
            <rect class="trace-base" x="1.5" y="1.5" width="131" height="49" rx="10" />
            <rect class="trace-beam" x="1.5" y="1.5" width="131" height="49" rx="10" pathLength="100" />
          </svg>
          <div style="display:flex;justify-content:space-between;align-items:center;font-size:11.5px;white-space:nowrap;gap:4px;">
            <span style="font-weight:600;flex-shrink:0;">✍️ Rewrite</span>
            <span style="font-family:monospace;font-size:10px;flex-shrink:0;">{rew_status}</span>
          </div>
          <div class="ap-muted" style="font-size:10.5px;font-family:monospace;margin-top:2px;white-space:nowrap;">{rew_sub}</div>
        </div>

        <!-- Node 5: Generate -->
        <div class="wf-node {gen_cls}" style="left:10px;top:345px;width:168px;height:50px;">
          <svg class="node-trace-svg" viewBox="0 0 170 52">
            <rect class="trace-base" x="1.5" y="1.5" width="167" height="49" rx="10" />
            <rect class="trace-beam" x="1.5" y="1.5" width="167" height="49" rx="10" pathLength="100" />
          </svg>
          <div style="display:flex;justify-content:space-between;font-size:12px;white-space:nowrap;">
            <span style="font-weight:600;">✨ Generate</span>
            <span style="font-family:monospace;">{gen_status}</span>
          </div>
          <div class="ap-muted" style="font-size:11.5px;font-family:monospace;margin-top:2px;white-space:nowrap;">{gen_sub}</div>
        </div>

        <!-- Node 6: Abort -->
        <div class="wf-node {abt_cls}" style="left:190px;top:345px;width:132px;height:50px;border-radius:16px;">
          <div style="display:flex;justify-content:space-between;align-items:center;font-size:11.5px;white-space:nowrap;gap:4px;">
            <span style="font-weight:600;flex-shrink:0;">🛑 Abort</span>
            <span style="font-family:monospace;font-size:10px;flex-shrink:0;color:{"#EF4444" if is_aborted else "inherit"};">{abt_status}</span>
          </div>
          <div class="ap-muted" style="font-size:11px;font-family:monospace;margin-top:2px;white-space:nowrap;">{abt_sub}</div>
        </div>
      </div>
    </div>
    """


def render_workflow_graph_html(
    active_node: str = "idle",
    chunks: int = 0,
    relevant: int = 0,
    rewrites: int = 0,
    done: bool = False,
    aborted: bool = False,
    cached: bool = False,
    mode: str = "balanced",
    top_distance: float | None = None,
) -> str:
    """Render the active workflow graph dynamically dispatching to dedicated, roomy layouts per mode."""
    clean_mode = (mode or "balanced").lower()
    is_cached = cached or active_node == "cached"
    max_rewrites_display = 0 if "turbo" in clean_mode else (1 if "balanced" in clean_mode else 2)
    is_aborted = aborted or active_node == "abort" or (done and relevant == 0 and rewrites >= max_rewrites_display)

    if "turbo" in clean_mode:
        return _render_turbo_workflow_html(
            active_node=active_node,
            chunks=chunks,
            done=done,
            is_cached=is_cached,
            top_distance=top_distance,
        )
    if "rigorous" in clean_mode:
        return _render_rigorous_workflow_html(
            active_node=active_node,
            chunks=chunks,
            relevant=relevant,
            rewrites=rewrites,
            done=done,
            is_aborted=is_aborted,
            is_cached=is_cached,
            top_distance=top_distance,
        )
    return _render_balanced_workflow_html(
        active_node=active_node,
        chunks=chunks,
        relevant=relevant,
        rewrites=rewrites,
        done=done,
        is_aborted=is_aborted,
        is_cached=is_cached,
        top_distance=top_distance,
    )


def render_sse_log_html(logs: list[tuple[str, str]], endpoint: str = "POST /ask/stream") -> str:
    """Render the color-coded SSE Event Stream log panel."""
    if not logs:
        lines_html = '<div class="ap-muted">Waiting for query...</div>'
    else:
        lines_html = "".join(f'<div style="color:{color};">{html.escape(text)}</div>' for text, color in logs)
    safe_ep = html.escape(endpoint)
    return f"""
    <div class="ap-card ap-sse-card" style="font-family:monospace;font-size:12px;">
      <div style="display:flex;justify-content:space-between;padding-bottom:6px;margin-bottom:6px;border-bottom:1px solid var(--border-hairline);flex-shrink:0;">
        <span style="font-family:sans-serif;font-weight:600;">SSE Event Stream</span>
        <span class="ap-muted">{safe_ep}</span>
      </div>
      <div id="ap-sse-scroll" class="modern-scroll" style="overflow-y:auto;padding-right:4px;display:flex;flex-direction:column;gap:4px;">
        {lines_html}
      </div>
    </div>
    """


def render_stats_for_nerds_html() -> str:
    """Render the Stats for Nerds observability & latency analytics view."""
    return """
    <div style="display:flex;flex-direction:column;gap:14px;">
      <div style="display:grid;grid-template-columns:repeat(auto-fit,minmax(200px,1fr));gap:12px;">
        <div class="ap-card"><div class="ap-muted" style="font-size:12px;">LangSmith Project</div><div style="font-size:16px;font-weight:700;font-family:monospace;margin-top:4px;">podseek</div></div>
        <div class="ap-card"><div class="ap-muted" style="font-size:12px;">Tracing Status</div><div style="font-size:16px;font-weight:700;font-family:monospace;margin-top:4px;">Opt-In Active</div></div>
        <div class="ap-card"><div class="ap-muted" style="font-size:12px;">Max CRAG Rewrites</div><div style="font-size:16px;font-weight:700;font-family:monospace;margin-top:4px;">2 (Circuit Breaker)</div></div>
        <div class="ap-card"><div class="ap-muted" style="font-size:12px;">Eval Suite</div><div style="font-size:16px;font-weight:700;font-family:monospace;margin-top:4px;">scripts/evaluate.py</div></div>
      </div>
      <div class="ap-card">
        <div style="font-size:13px;font-weight:700;margin-bottom:8px;">Stats for Nerds · Trace Explorer & Latency Analytics</div>
        <div class="ap-muted" style="font-size:12px;line-height:1.6;">
          Queries <code>langsmith.Client().list_runs(project_name="podseek")</code> to inspect P50/P95 node latencies
          (<code>retrieve</code> vs <code>grade_documents</code> vs <code>rewrite_query</code> vs <code>generate</code>), token usage, and trace drill-downs.
        </div>
      </div>
    </div>
    """
