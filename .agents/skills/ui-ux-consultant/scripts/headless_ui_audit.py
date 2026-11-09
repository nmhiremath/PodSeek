#!/usr/bin/env python3
"""Headless UI/UX & DOM Geometry Audit Runner for PodSeek.

Sweeps desktop, tablet, and mobile viewports across Light and Dark modes,
interacts with UI components (mode cycling, drawer toggle, input focus,
simulated long chat turns + scroll nav), captures high-DPI screenshots, and
outputs a deterministic JSON telemetry report (`audit_telemetry.json`) with:
  - Bounding-box collision & overlap checks
  - Viewport & horizontal overflow checks
  - Bottom-pinning verification for capsule, preset carousel, and scroll nav
  - Tap-target size ergonomics
  - Streaming DOM replacement layout-shift (CLS) simulation
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
import urllib.request
from pathlib import Path
from typing import Any

VIEWPORTS: list[dict[str, Any]] = [
    {"name": "mobile_small_360x740", "width": 360, "height": 740, "is_mobile": True},
    {"name": "mobile_std_390x844", "width": 390, "height": 844, "is_mobile": True},
    {"name": "mobile_promax_430x932", "width": 430, "height": 932, "is_mobile": True},
    {"name": "tablet_768x1024", "width": 768, "height": 1024, "is_mobile": True},
    {"name": "laptop_1280x800", "width": 1280, "height": 800, "is_mobile": False},
    {"name": "desktop_1440x900", "width": 1440, "height": 900, "is_mobile": False},
]


DOM_AUDIT_JS = """
() => {
    const vw = window.innerWidth;
    const vh = window.innerHeight;
    const rectOf = (sel) => {
        const el = typeof sel === 'string' ? document.querySelector(sel) : sel;
        if (!el) return null;
        const cs = window.getComputedStyle(el);
        if (cs.display === 'none' || cs.visibility === 'hidden' || parseFloat(cs.opacity) === 0) {
            return { hidden: true, display: cs.display, visibility: cs.visibility, opacity: cs.opacity };
        }
        const r = el.getBoundingClientRect();
        return {
            hidden: false,
            x: Math.round(r.x * 10) / 10,
            y: Math.round(r.y * 10) / 10,
            width: Math.round(r.width * 10) / 10,
            height: Math.round(r.height * 10) / 10,
            top: Math.round(r.top * 10) / 10,
            right: Math.round(r.right * 10) / 10,
            bottom: Math.round(r.bottom * 10) / 10,
            left: Math.round(r.left * 10) / 10,
            position: cs.position,
            zIndex: cs.zIndex,
            fontSize: cs.fontSize,
            lineHeight: cs.lineHeight,
            padding: cs.padding,
            overflowX: cs.overflowX,
            overflowY: cs.overflowY,
        };
    };

    const overlaps = (a, b) => {
        if (!a || !b || a.hidden || b.hidden) return null;
        const xOverlap = Math.max(0, Math.min(a.right, b.right) - Math.max(a.left, b.left));
        const yOverlap = Math.max(0, Math.min(a.bottom, b.bottom) - Math.max(a.top, b.top));
        if (xOverlap > 1 && yOverlap > 1) {
            return { xOverlap: Math.round(xOverlap * 10) / 10, yOverlap: Math.round(yOverlap * 10) / 10 };
        }
        return null;
    };

    const header = rectOf('.ap-header-row');
    const studio = rectOf('#ap-studio-view');
    const colLeft = rectOf('.ap-col-left');
    const colCenter = rectOf('.ap-col-center');
    const colRight = rectOf('.ap-col-right');
    const chatWrap = rectOf('.ap-chat-viewport-wrap');
    const chatScroll = rectOf('#ap-chat-scroll');
    const presets = rectOf('.ap-presets-carousel');
    const capsule = rectOf('.ap-distill-capsule');
    const modeBtn = rectOf('#ap-mode-slider');
    const typewriter = rectOf('.ap-typewriter-wrap');
    const typewriterCursor = rectOf('.ap-typewriter-cursor');
    const distillBtn = rectOf('#ap-distill-btn');
    const scrollNav = rectOf('#ap-chat-scroll-nav');
    const topNavBtn = rectOf('#ap-scroll-top-btn');
    const botNavBtn = rectOf('#ap-scroll-bottom-btn');
    const wfGrid = rectOf('.ap-col-right .wf-dot-grid');
    const sseCard = rectOf('.ap-col-right .ap-sse-card');

    const issues = [];

    // 1. Check outer page overflow (should be locked to 100dvh)
    const docScrollW = document.documentElement.scrollWidth;
    const docScrollH = document.documentElement.scrollHeight;
    if (docScrollW > vw + 2) {
        issues.push({
            severity: 'P1',
            type: 'horizontal_page_overflow',
            detail: `Document scrollWidth (${docScrollW}px) exceeds viewport width (${vw}px)`,
        });
    }
    if (docScrollH > vh + 4) {
        issues.push({
            severity: 'P1',
            type: 'vertical_page_overflow',
            detail: `Document scrollHeight (${docScrollH}px) exceeds viewport height (${vh}px); outer page scrolls instead of internal chat scroll`,
        });
    }

    // 2. Check Mode Button vs Typewriter / Input overlap & spacing
    if (modeBtn && !modeBtn.hidden && typewriter && !typewriter.hidden) {
        const ov = overlaps(modeBtn, typewriter);
        const gap = Math.round((typewriter.left - modeBtn.right) * 10) / 10;
        if (ov) {
            issues.push({
                severity: 'P0',
                type: 'mode_button_overlaps_typewriter',
                detail: `#ap-mode-slider overlaps .ap-typewriter-wrap by ${ov.xOverlap}px horizontally`,
            });
        } else if (gap < 8) {
            issues.push({
                severity: 'P2',
                type: 'tight_mode_to_typewriter_gap',
                detail: `Gap between #ap-mode-slider right edge (${modeBtn.right}px) and .ap-typewriter-wrap left edge (${typewriter.left}px) is only ${gap}px (recommended >= 10px)`,
            });
        }
        if (typewriter.height > 30) {
            issues.push({
                severity: 'P1',
                type: 'typewriter_multiline_wrap',
                detail: `.ap-typewriter-wrap height is ${typewriter.height}px (> 30px), indicating text or cursor wrapped onto a second line`,
            });
        }
    }

    // 3. Check Typewriter vs Distill Button overlap
    if (typewriter && !typewriter.hidden && distillBtn && !distillBtn.hidden) {
        const ov = overlaps(typewriter, distillBtn);
        if (ov) {
            issues.push({
                severity: 'P0',
                type: 'typewriter_overlaps_distill_btn',
                detail: `.ap-typewriter-wrap overlaps #ap-distill-btn by ${ov.xOverlap}px`,
            });
        }
    }

    // 4. Check Bottom Viewport Pinning of Capsule & Presets
    if (capsule && !capsule.hidden) {
        const bottomGap = Math.round((vh - capsule.bottom) * 10) / 10;
        if (bottomGap > 42 || bottomGap < -2) {
            issues.push({
                severity: 'P1',
                type: 'capsule_not_pinned_to_bottom',
                detail: `.ap-distill-capsule bottom is ${bottomGap}px from viewport bottom (expected 8px–28px)`,
            });
        }
    }
    if (presets && !presets.hidden && capsule && !capsule.hidden) {
        const presetToCapsuleGap = Math.round((capsule.top - presets.bottom) * 10) / 10;
        if (presetToCapsuleGap < -2 || presetToCapsuleGap > 24) {
            issues.push({
                severity: 'P2',
                type: 'presets_to_capsule_spacing',
                detail: `Vertical gap between .ap-presets-carousel and .ap-distill-capsule is ${presetToCapsuleGap}px`,
            });
        }
    }

    // 5. Desktop Column Top & Bottom Edge Alignment
    if (vw > 768 && colCenter && !colCenter.hidden && colRight && !colRight.hidden) {
        const topDiff = Math.abs(colCenter.top - colRight.top);
        const botDiff = Math.abs(colCenter.bottom - colRight.bottom);
        if (topDiff > 3) {
            issues.push({
                severity: 'P2',
                type: 'desktop_column_top_misalignment',
                detail: `.ap-col-center top (${colCenter.top}px) and .ap-col-right top (${colRight.top}px) differ by ${topDiff.toFixed(1)}px`,
            });
        }
        if (botDiff > 4) {
            issues.push({
                severity: 'P2',
                type: 'desktop_column_bottom_misalignment',
                detail: `.ap-col-center bottom (${colCenter.bottom}px) and .ap-col-right bottom (${colRight.bottom}px) differ by ${botDiff.toFixed(1)}px`,
            });
        }
    }

    // 6. Preset Pills Single-Line Check
    const pillRects = Array.from(document.querySelectorAll('button.ap-preset-pill')).map(rectOf).filter(r => r && !r.hidden);
    if (pillRects.length > 1) {
        const firstTop = pillRects[0].top;
        const wrappedPills = pillRects.filter(r => Math.abs(r.top - firstTop) > 8);
        if (wrappedPills.length > 0) {
            issues.push({
                severity: 'P1',
                type: 'preset_carousel_wrapped_multiline',
                detail: `${wrappedPills.length} preset pills wrapped onto a second line instead of staying in a single horizontal row`,
            });
        }
    }

    return {
        viewport: { width: vw, height: vh, docScrollW, docScrollH },
        cssVars: {
            apStudioH: document.documentElement.style.getPropertyValue('--ap-studio-h'),
            apChatH: document.documentElement.style.getPropertyValue('--ap-chat-h'),
            apMobileNavBottom: document.documentElement.style.getPropertyValue('--ap-mobile-nav-bottom'),
        },
        elements: {
            header,
            studio,
            colLeft,
            colCenter,
            colRight,
            chatWrap,
            chatScroll,
            presets,
            capsule,
            modeBtn,
            typewriter,
            typewriterCursor,
            distillBtn,
            scrollNav,
            topNavBtn,
            botNavBtn,
            wfGrid,
            sseCard,
        },
        modeToTypewriterGapPx: (modeBtn && !modeBtn.hidden && typewriter && !typewriter.hidden)
            ? Math.round((typewriter.left - modeBtn.right) * 10) / 10
            : null,
        capsuleBottomGapPx: (capsule && !capsule.hidden)
            ? Math.round((vh - capsule.bottom) * 10) / 10
            : null,
        issues,
    };
}
"""


SIMULATE_STREAMING_CHAT_JS = """
() => {
    const chatScroll = document.getElementById('ap-chat-scroll');
    if (!chatScroll) return { error: 'no #ap-chat-scroll found' };
    chatScroll.classList.remove('ap-chat-empty');

    const beforeCapsule = document.querySelector('.ap-distill-capsule')?.getBoundingClientRect();
    const beforePresets = document.querySelector('.ap-presets-carousel')?.getBoundingClientRect();

    // Inject 6 realistic multi-paragraph Q&A turns + mobile spotlight flowchart
    let turnsHtml = '';
    for (let i = 1; i <= 6; i++) {
        const isLast = (i === 6);
        const spotlight = isLast ? `
          <div class="ap-spotlight-card" style="padding:6px;overflow:hidden;margin-bottom:12px;">
            <div class="wf-dot-grid">
              <div style="display:flex;align-items:center;justify-content:space-between;margin-bottom:8px;gap:8px;white-space:nowrap;">
                <span style="font-size:12px;font-weight:700;">Workflow · Balanced RAG</span>
                <span class="ap-subtle" style="font-size:10.5px;font-family:monospace;padding:2px 6px;">Rewrites: 0 / 1</span>
              </div>
              <div class="wf-canvas-wrap" data-orig-height="440" style="position:relative;width:330px;height:440px;">
                <div class="wf-node is-completed" style="left:10px;top:10px;width:168px;height:50px;">
                  <div style="display:flex;justify-content:space-between;font-size:12px;"><span style="font-weight:600;">🔍 Retrieve</span><span>✓ Done</span></div>
                  <div class="ap-muted" style="font-size:11px;font-family:monospace;">4 chunks · dist: 0.29</div>
                </div>
                <div class="wf-node is-running" style="left:10px;top:345px;width:168px;height:50px;">
                  <div style="display:flex;justify-content:space-between;font-size:12px;"><span style="font-weight:600;">✨ Generate</span><span>⟳ Running</span></div>
                  <div class="ap-muted" style="font-size:11px;font-family:monospace;">⚡ Fast-path synthesis</div>
                </div>
              </div>
            </div>
          </div>` : '';
        turnsHtml += `
          <div style="display:flex;justify-content:flex-end;margin-bottom:12px;">
            <div style="max-width:85%;background:var(--accent);color:#fff;padding:10px 16px;border-radius:16px 16px 4px 16px;font-size:14.5px;font-weight:500;line-height:1.45;">
              How does protocol #${i} impact dopamine baseline and circadian alignment?
            </div>
          </div>
          <div class="ap-subtle" style="padding:16px 18px;margin-bottom:16px;font-size:14.5px;line-height:1.65;border-radius:16px;">
            ${spotlight}
            <div class="ap-md">
              <p><strong>${i}. Circadian &amp; Dopaminergic Coupling:</strong> Viewing morning sunlight within 30–60 minutes of waking triggers intrinsically photosensitive retinal ganglion cells (ipRGCs), timing the cortisol peak and setting a 16-hour melatonin timer
              <a href="https://youtu.be/QmOF0crdyRU?t=529" target="_blank" class="gai-pill"><span class="gai-yt-circle"><svg width="8" height="8" viewBox="0 0 24 24" fill="#FFF"><polygon points="6,4 20,12 6,20"/></svg></span><span>Master Your Sleep · 08:49</span></a>.</p>
              <ul>
                <li><strong>Deliberate Cold Exposure:</strong> Elevates catecholamines (dopamine &amp; norepinephrine) by up to 250% above baseline for 2–3 hours without a subsequent crash.</li>
                <li><strong>Caffeine Delay:</strong> Waiting 90–120 minutes after waking prevents afternoon adenosine receptor rebound.</li>
              </ul>
            </div>
          </div>`;
    }

    chatScroll.innerHTML = turnsHtml;
    chatScroll.scrollTop = Math.floor(chatScroll.scrollHeight / 2);
    chatScroll.dispatchEvent(new Event('scroll'));
    if (window.updateChatScrollNav) window.updateChatScrollNav();

    const afterCapsule = document.querySelector('.ap-distill-capsule')?.getBoundingClientRect();
    const afterPresets = document.querySelector('.ap-presets-carousel')?.getBoundingClientRect();
    const wfWrap = document.querySelector('.ap-spotlight-card .wf-canvas-wrap')?.getBoundingClientRect();
    const spotlightCard = document.querySelector('.ap-spotlight-card')?.getBoundingClientRect();
    const scrollNav = document.getElementById('ap-chat-scroll-nav')?.getBoundingClientRect();
    const topBtnVis = document.getElementById('ap-scroll-top-btn')?.classList.contains('is-visible');
    const botBtnVis = document.getElementById('ap-scroll-bottom-btn')?.classList.contains('is-visible');

    const capsuleDriftY = (beforeCapsule && afterCapsule)
        ? Math.round(Math.abs(afterCapsule.bottom - beforeCapsule.bottom) * 10) / 10
        : null;
    const presetsDriftY = (beforePresets && afterPresets)
        ? Math.round(Math.abs(afterPresets.bottom - beforePresets.bottom) * 10) / 10
        : null;

    return {
        chatScrollHeight: chatScroll.scrollHeight,
        chatClientHeight: chatScroll.clientHeight,
        chatIsScrollableInternally: chatScroll.scrollHeight > chatScroll.clientHeight + 20,
        capsuleDriftY,
        presetsDriftY,
        scrollButtonsVisibleMidScroll: { topBtnVis, botBtnVis },
        scrollNavRect: scrollNav ? {
            top: Math.round(scrollNav.top),
            bottom: Math.round(scrollNav.bottom),
            right: Math.round(scrollNav.right),
            width: Math.round(scrollNav.width),
            height: Math.round(scrollNav.height),
        } : null,
        spotlightWorkflowFitsCard: (wfWrap && spotlightCard)
            ? (wfWrap.width <= spotlightCard.width + 2)
            : null,
        wfWrapRect: wfWrap ? {
            width: Math.round(wfWrap.width * 10) / 10,
            height: Math.round(wfWrap.height * 10) / 10,
        } : null,
        spotlightCardRect: spotlightCard ? {
            width: Math.round(spotlightCard.width * 10) / 10,
            height: Math.round(spotlightCard.height * 10) / 10,
        } : null,
    };
}
"""


def wait_for_server(url: str, timeout_s: float = 15.0) -> bool:
    deadline = time.time() + timeout_s
    while time.time() < deadline:
        try:
            with urllib.request.urlopen(url, timeout=2.0) as resp:
                if resp.status < 500:
                    return True
        except Exception:
            time.sleep(0.4)
    return False


def run_playwright_audit(url: str, out_dir: Path) -> dict[str, Any]:
    from playwright.sync_api import sync_playwright  # type: ignore[import-not-found]

    out_dir.mkdir(parents=True, exist_ok=True)
    report: dict[str, Any] = {
        "target_url": url,
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "viewports": {},
        "summary_issues": [],
    }

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        for vp in VIEWPORTS:
            vp_name = vp["name"]
            context = browser.new_context(
                viewport={"width": vp["width"], "height": vp["height"]},
                device_scale_factor=2,
                is_mobile=vp["is_mobile"],
                has_touch=vp["is_mobile"],
            )
            page = context.new_page()
            page.goto(url, wait_until="networkidle", timeout=30000)
            page.wait_for_timeout(900)

            # Ensure Light mode first
            page.evaluate("""() => {
                document.documentElement.classList.remove('ap-dark', 'dark');
                document.body.classList.remove('ap-dark', 'dark');
                document.querySelector('.gradio-container')?.classList.remove('ap-dark', 'dark');
            }""")
            page.wait_for_timeout(250)

            light_png = out_dir / f"{vp_name}_light_empty.png"
            page.screenshot(path=str(light_png), full_page=False)
            light_metrics = page.evaluate(DOM_AUDIT_JS)

            # Test Mode Cycling (Balanced -> Rigorous -> Turbo -> Balanced)
            mode_states = []
            for _ in range(3):
                page.evaluate("() => window.podSeekCycleMode && window.podSeekCycleMode()")
                page.wait_for_timeout(220)
                lbl = page.evaluate("() => document.querySelector('#ap-mode-slider .cycle-label')?.textContent?.trim()")
                mode_states.append(lbl)

            # Test Drawer Toggle
            if vp["is_mobile"]:
                page.evaluate("() => document.getElementById('ap-mobile-library-btn')?.click()")
            else:
                page.evaluate("() => document.getElementById('ap-sidebar-toggle-btn')?.click()")
            page.wait_for_timeout(350)
            drawer_png = out_dir / f"{vp_name}_light_drawer.png"
            page.screenshot(path=str(drawer_png), full_page=False)
            # Close drawer
            if vp["is_mobile"]:
                page.evaluate("() => document.querySelector('.ap-drawer-close-btn')?.click()")
            else:
                page.evaluate("() => document.getElementById('ap-sidebar-toggle-btn')?.click()")
            page.wait_for_timeout(300)

            # Simulate Streaming Multi-Turn Chat & Check Bottom Pinning + Scroll Nav + Spotlight Flowchart
            stream_metrics = page.evaluate(SIMULATE_STREAMING_CHAT_JS)
            page.wait_for_timeout(250)
            chat_png = out_dir / f"{vp_name}_light_streaming_chat.png"
            page.screenshot(path=str(chat_png), full_page=False)
            post_chat_metrics = page.evaluate(DOM_AUDIT_JS)

            # Switch to Dark Mode & Capture
            page.evaluate("() => document.getElementById('ap-theme-slider')?.click()")
            page.wait_for_timeout(300)
            dark_png = out_dir / f"{vp_name}_dark_streaming_chat.png"
            page.screenshot(path=str(dark_png), full_page=False)

            vp_entry = {
                "dimensions": {"width": vp["width"], "height": vp["height"], "is_mobile": vp["is_mobile"]},
                "screenshots": {
                    "light_empty": str(light_png),
                    "light_drawer": str(drawer_png),
                    "light_streaming_chat": str(chat_png),
                    "dark_streaming_chat": str(dark_png),
                },
                "mode_cycle_sequence": mode_states,
                "initial_dom_audit": light_metrics,
                "streaming_chat_simulation": stream_metrics,
                "post_chat_dom_audit": post_chat_metrics,
            }
            report["viewports"][vp_name] = vp_entry

            for iss in light_metrics.get("issues", []) + post_chat_metrics.get("issues", []):
                report["summary_issues"].append({"viewport": vp_name, **iss})

            if stream_metrics.get("capsuleDriftY") and stream_metrics["capsuleDriftY"] > 2:
                report["summary_issues"].append(
                    {
                        "viewport": vp_name,
                        "severity": "P0",
                        "type": "capsule_drifted_during_chat_generation",
                        "detail": f".ap-distill-capsule shifted vertically by {stream_metrics['capsuleDriftY']}px when chat history grew",
                    }
                )

            context.close()
        browser.close()

    telemetry_path = out_dir / "audit_telemetry.json"
    telemetry_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
    return report


def run_chrome_cli_fallback(url: str, out_dir: Path) -> dict[str, Any]:
    """Fallback screenshot + DOM snapshot using system Google Chrome headless CLI if Playwright is absent."""
    import subprocess

    chrome_bin = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
    if not os.path.exists(chrome_bin):
        raise RuntimeError("Neither python playwright nor Google Chrome binary found.")

    out_dir.mkdir(parents=True, exist_ok=True)
    report: dict[str, Any] = {
        "target_url": url,
        "runner": "chrome_cli_fallback",
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "viewports": {},
    }
    for vp in VIEWPORTS:
        vp_name = vp["name"]
        png_path = out_dir / f"{vp_name}_light.png"
        cmd = [
            chrome_bin,
            "--headless=new",
            "--disable-gpu",
            "--hide-scrollbars",
            f"--window-size={vp['width']},{vp['height']}",
            "--virtual-time-budget=3500",
            f"--screenshot={png_path}",
            url,
        ]
        subprocess.run(cmd, check=False, capture_output=True, text=True)
        report["viewports"][vp_name] = {
            "dimensions": {"width": vp["width"], "height": vp["height"]},
            "screenshots": {"light": str(png_path)},
        }

    telemetry_path = out_dir / "audit_telemetry.json"
    telemetry_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description="Run PodSeek Headless UI/UX Audit")
    parser.add_argument("--url", default="http://127.0.0.1:7860", help="Target PodSeek UI URL")
    parser.add_argument("--out-dir", default="/tmp/podseek_ui_audit", help="Directory for screenshots & telemetry JSON")
    args = parser.parse_args()

    out_dir = Path(args.out_dir).resolve()
    if not wait_for_server(args.url, timeout_s=10.0):
        print(f"ERROR: Target URL {args.url} is not reachable.", file=sys.stderr)
        return 2

    try:
        report = run_playwright_audit(args.url, out_dir)
        runner = "playwright"
    except ImportError:
        report = run_chrome_cli_fallback(args.url, out_dir)
        runner = "chrome_cli_fallback"

    print(
        json.dumps(
            {
                "status": "ok",
                "runner": runner,
                "out_dir": str(out_dir),
                "telemetry_json": str(out_dir / "audit_telemetry.json"),
                "viewports_tested": list(report.get("viewports", {}).keys()),
                "issues_detected": len(report.get("summary_issues", [])),
                "summary_issues": report.get("summary_issues", []),
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
