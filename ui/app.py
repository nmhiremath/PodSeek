"""Gradio UI controller and layout for PodSeek.

The widgets call PodSeekClient. View rendering lives in `ui/components.py`
and stylesheets live in `ui/styles/theme.css`.
"""

import html
import importlib
import json
import os
import random
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

import ui.components as _ui_components  # noqa: E402
from app.agent.nodes import determine_outcome  # noqa: E402
from app.observability import configure_tracing  # noqa: E402
from ui.client import PodSeekClient, make_client  # noqa: E402

importlib.reload(_ui_components)
from ui.components import (  # noqa: E402
    PS_FAVICON_DATA_URI,
    _is_submittable_question,
    format_citations,
    format_event,
    load_theme_css,
    render_chat_session_html,
    render_episodes_html,
    render_head_meta_html,
    render_header_brand_html,
    render_header_controls_html,
    render_ingest_status_html,
    render_ingest_workflow_graph_html,
    render_mode_slider_html,
    render_sse_log_html,
    render_stats_for_nerds_html,
    render_workflow_graph_html,
)

DEFAULT_SHOW = "huberman_lab"
DEFAULT_SPEAKER = "Andrew Huberman"

SAMPLE_PRESETS: list[dict[str, str]] = [
    {
        "topic": "☀️ Morning sunlight protocol",
        "question": "What is the optimal morning sunlight viewing protocol for circadian health?",
    },
    {
        "topic": "⚡ Prevent dopamine crash",
        "question": "How do I prevent a severe dopamine crash and manage baseline motivation?",
    },
    {
        "topic": "🧊 Cold exposure dopamine",
        "question": "How does deliberate cold exposure trigger sustained dopamine release?",
    },
    {
        "topic": "☕ 90-min caffeine delay",
        "question": "How long should I delay morning caffeine intake to avoid an afternoon crash?",
    },
    {
        "topic": "😴 Optimal sleep cocktail",
        "question": "What is the optimal sleep cocktail: magnesium L-threonate, theanine & apigenin?",
    },
    {
        "topic": "🫁 Physiological sigh",
        "question": "How does the physiological sigh rapidly reduce acute stress and heart rate?",
    },
    {
        "topic": "🧠 Focus & ADHD protocols",
        "question": "What neurochemistry protocols help improve focus and manage ADHD?",
    },
    {
        "topic": "🏋️ Hypertrophy & mind-muscle",
        "question": "What is the mind-muscle connection and how does it drive hypertrophy?",
    },
    {
        "topic": "🚫 Off-topic: see a refusal",
        "question": "What are the optimal sauna heat protocols for growth hormone release?",
    },
    {
        "topic": "🏃 Zone 2 cardio volume",
        "question": "How much Zone 2 cardio is recommended for mitochondrial health?",
    },
    {
        "topic": "🍽️ Intermittent fasting clarity",
        "question": "How does intermittent fasting impact mental clarity, autophagy, and insulin?",
    },
    {
        "topic": "💊 Creatine for brain health",
        "question": "What is the ideal creatine monohydrate dosage for cognitive and brain function?",
    },
    {
        "topic": "🍷 Alcohol & REM sleep",
        "question": "How does alcohol consumption disrupt sleep architecture and REM stages?",
    },
    {
        "topic": "💧 Electrolytes & neurons",
        "question": "Why are sodium, potassium, and magnesium critical for brain electrical firing?",
    },
    {
        "topic": "💪 Hormone optimization",
        "question": "What natural behavioral protocols help optimize testosterone and hormone health?",
    },
    {
        "topic": "🧘 NSDR & neuroplasticity",
        "question": "How does Non-Sleep Deep Rest (NSDR) accelerate neuroplasticity and recovery?",
    },
    {
        "topic": "👁️ Panoramic vision & calm",
        "question": "How does panoramic vision down-regulate autonomic stress circuits?",
    },
    {
        "topic": "🦠 Gut-brain axis & mood",
        "question": "How does the gut microbiome communicate with the brain to regulate mood?",
    },
    {
        "topic": "🎯 Visual gaze & alertness",
        "question": "How can visual focus and gaze fixation increase mental alertness?",
    },
    {
        "topic": "🛡️ Cortisol & burnout",
        "question": "How do you prevent burnout by distinguishing acute vs chronic cortisol spikes?",
    },
]


def pick_random_presets(count: int = 5) -> list[dict[str, str]]:
    """Pick distinct random topic/question presets from the Huberman Lab question bank."""
    return random.sample(SAMPLE_PRESETS, min(count, len(SAMPLE_PRESETS)))


QUIRKY_PLACEHOLDERS: list[str] = [
    # Huberman Mannerisms & Catchphrases
    "Zero-cost tool: ask a question...",
    "Thank you for your interest in science...",
    "Did you get your morning sunlight today?...",
    "Take a physiological sigh, then ask...",
    "Overcome your limbic friction...",
    "Lean into your forward center of mass...",
    "I want to emphasize: ask anything...",
    "Waiting 90 minutes for morning caffeine?...",
    "Switch to panoramic vision and ask...",
    "Surfing the dopamine wave pool...",
    "Not medical advice, just pure science...",
    "Costello-approved health protocols...",
    "What does the peer-reviewed data say?...",
    "Visual focus drives cognitive focus...",
    "Engage prefrontal top-down control...",
    "Entering Non-Sleep Deep Rest (NSDR)...",
    "Syncing with your circadian zeitgebers...",
    "Dopamine, acetylcholine, or serotonin?...",
    "Thinking at Zone 2 cardio pace...",
    "Hot sauna or cold plunge curiosity?...",
    # Pop Culture & Lore Mashups
    "May the neuroplasticity be with you...",
    "Speak, friend, and enter the podcast...",
    "One does not simply skip morning sunlight...",
    "Houston, we have a question...",
    "Elementary, my dear Huberman...",
    "Hit me with your best hypothesis...",
    "To sleep or not to sleep? Ask away...",
    "I've got 99 problems but dopamine ain't one...",
    "With great protocols comes great recovery...",
    # Inquisitive, Witty & Philosophical
    "What would Socrates ask Huberman?...",
    "Curiosity didn't kill the cat, lack of sleep did...",
    "Talk neurobiology to me...",
    "Feed me science, Dr. Huberman...",
    "Ask away. Dopamine guaranteed...",
    "What makes your synapses fire?...",
    "Ready when you are, biohacker...",
    "Tell me what protocols you need...",
    "Got a burning biological query?...",
    "Question everything. Especially caffeine timing...",
    "Ask me anything, I've got the transcripts...",
    "Looking for scientific enlightenment?...",
]


def pick_random_placeholder() -> str:
    """Pick a random quirky, funny, or pop-culture placeholder for the ask capsule."""
    return random.choice(QUIRKY_PLACEHOLDERS)


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

_INIT_UI_JS_TEMPLATE = """() => {
    window.podSeekSelectMode = (modeVal) => {
        const btn = document.getElementById('ap-mode-slider');
        if (btn) {
            btn.classList.remove('is-turbo', 'is-balanced', 'is-rigorous');
            const iconBadge = btn.querySelector('.cycle-icon-badge');
            const labelSpan = btn.querySelector('.cycle-label');
            if (modeVal.includes('Turbo')) {
                btn.classList.add('is-turbo');
                if (iconBadge) iconBadge.textContent = '⚡';
                if (labelSpan) labelSpan.textContent = 'Turbo';
            } else if (modeVal.includes('Rigorous')) {
                btn.classList.add('is-rigorous');
                if (iconBadge) iconBadge.textContent = '🎯';
                if (labelSpan) labelSpan.textContent = 'Rigorous';
            } else {
                btn.classList.add('is-balanced');
                if (iconBadge) iconBadge.textContent = '⚖️';
                if (labelSpan) labelSpan.textContent = 'Balanced';
            }
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
    window.podSeekCycleMode = () => {
        const btn = document.getElementById('ap-mode-slider');
        let current = 'balanced';
        if (btn) {
            if (btn.classList.contains('is-turbo')) current = 'turbo';
            else if (btn.classList.contains('is-rigorous')) current = 'rigorous';
        }
        let nextMode = '⚖️ Balanced';
        if (current === 'balanced') nextMode = '🎯 Rigorous';
        else if (current === 'rigorous') nextMode = '⚡ Turbo';
        else nextMode = '⚖️ Balanced';

        window.podSeekSelectMode(nextMode);
    };
    const setupPodSeekUI = () => {
        let isDark = false;
        try {
            isDark = localStorage.getItem('podseek_theme') === 'dark';
        } catch (e) {}

        if (isDark) {
            document.documentElement.classList.add('ap-dark');
            document.body.classList.add('ap-dark');
            document.querySelector('.gradio-container')?.classList.add('ap-dark');
            document.querySelector('gradio-app')?.classList.add('ap-dark');
        } else {
            document.documentElement.classList.remove('ap-dark', 'dark');
            document.body.classList.remove('ap-dark', 'dark');
            document.querySelector('.gradio-container')?.classList.remove('ap-dark', 'dark');
            document.querySelector('gradio-app')?.classList.remove('ap-dark', 'dark');
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

        const headerRow = document.querySelector('.ap-header-row');
        if (headerRow) {
            headerRow.style.setProperty('margin-bottom', '0px', 'important');
            headerRow.style.setProperty('margin-top', '0px', 'important');
        }
        const studioView = document.getElementById('ap-studio-view');
        if (studioView) {
            studioView.style.setProperty('margin-top', '0px', 'important');
        }
        const backdropWrap = document.querySelector('.ap-mobile-drawer-backdrop-wrap');
        if (backdropWrap && window.innerWidth > 768) {
            backdropWrap.style.setProperty('display', 'none', 'important');
            backdropWrap.style.setProperty('height', '0px', 'important');
            backdropWrap.style.setProperty('margin', '0px', 'important');
            backdropWrap.style.setProperty('padding', '0px', 'important');
        }

        const colRight = document.querySelector('.ap-col-right');
        if (colRight) {
            colRight.style.setProperty('padding-top', '0px', 'important');
            colRight.style.setProperty('margin-top', '0px', 'important');
            const wf = colRight.querySelector('.wf-dot-grid');
            if (wf) {
                wf.style.setProperty('margin-top', '0px', 'important');
                let parent = wf.parentElement;
                while (parent && parent !== colRight) {
                    parent.style.setProperty('padding-top', '0px', 'important');
                    parent.style.setProperty('margin-top', '0px', 'important');
                    parent.style.setProperty('border-top-width', '0px', 'important');
                    parent = parent.parentElement;
                }
            }
        }

        const syncDesktopViewport = () => {
            const studio = document.getElementById('ap-studio-view');
            if (!studio || studio.classList.contains('ap-view-hidden')) return;
            const colCenter = document.querySelector('.ap-col-center');
            const presets = colCenter ? colCenter.querySelector('.ap-presets-carousel') : null;
            const presetsVisible = Boolean(presets && presets.offsetParent !== null);

            if (window.innerWidth <= 768) {
                // Mobile: Clear any desktop inline height overrides and compute dynamic chat viewport height
                studio.style.removeProperty('height');
                studio.style.removeProperty('min-height');
                studio.style.removeProperty('max-height');
                if (colRight) {
                    colRight.style.removeProperty('height');
                    colRight.style.removeProperty('min-height');
                    colRight.style.removeProperty('max-height');
                }
                const colLeftEl = document.querySelector('.ap-col-left');
                if (colLeftEl) {
                    colLeftEl.style.removeProperty('height');
                    colLeftEl.style.removeProperty('min-height');
                    colLeftEl.style.removeProperty('max-height');
                }
                if (colCenter) {
                    colCenter.style.removeProperty('height');
                    colCenter.style.removeProperty('min-height');
                    colCenter.style.removeProperty('max-height');
                    const hRect = headerRow ? headerRow.getBoundingClientRect() : { bottom: 54 };
                    const vvH = window.visualViewport ? window.visualViewport.height : window.innerHeight;
                    const mobileChatH = Math.max(180, Math.floor(vvH - hRect.bottom - 6));
                    document.documentElement.style.setProperty('--ap-chat-h', `${mobileChatH}px`);
                }
                const navBottom = 'calc(108px + env(safe-area-inset-bottom, 0px))';
                document.documentElement.style.setProperty('--ap-mobile-nav-bottom', navBottom);
                return;
            }

            const rect = studio.getBoundingClientRect();
            const availH = Math.max(460, Math.floor(window.innerHeight - rect.top - 14));
            document.documentElement.style.setProperty('--ap-studio-h', `${availH}px`);
            studio.style.setProperty('height', `${availH}px`, 'important');
            studio.style.setProperty('min-height', `${availH}px`, 'important');
            studio.style.setProperty('max-height', `${availH}px`, 'important');

            if (colCenter) {
                colCenter.style.setProperty('height', `${availH}px`, 'important');
                colCenter.style.setProperty('min-height', `${availH}px`, 'important');
                colCenter.style.setProperty('max-height', `${availH}px`, 'important');
                colCenter.style.setProperty('display', 'flex', 'important');
                colCenter.style.setProperty('flex-direction', 'column', 'important');

                const presetsH = presets ? presets.offsetHeight + 10 : 40;
                const capsuleEl = colCenter.querySelector('.ap-distill-capsule');
                const capsuleH = capsuleEl ? capsuleEl.offsetHeight + 6 : 58;
                const desktopChatH = Math.max(160, Math.floor(availH - presetsH - capsuleH - 24));
                document.documentElement.style.setProperty('--ap-chat-h', `${desktopChatH}px`);

                const chatScroll = document.getElementById('ap-chat-scroll');
                if (chatScroll) {
                    chatScroll.style.setProperty('flex', '1 1 0%', 'important');
                    chatScroll.style.setProperty('min-height', '0px', 'important');
                    chatScroll.style.setProperty('height', `${desktopChatH}px`, 'important');
                    chatScroll.style.setProperty('max-height', `${desktopChatH}px`, 'important');
                    let p = chatScroll.parentElement;
                    while (p && p !== colCenter) {
                        p.style.setProperty('display', 'flex', 'important');
                        p.style.setProperty('flex-direction', 'column', 'important');
                        p.style.setProperty('flex', '1 1 0%', 'important');
                        p.style.setProperty('min-height', '0px', 'important');
                        p.style.setProperty('height', `${desktopChatH}px`, 'important');
                        p.style.setProperty('max-height', `${desktopChatH}px`, 'important');
                        p.style.setProperty('overflow', 'hidden', 'important');
                        p = p.parentElement;
                    }
                }
                if (presets) {
                    presets.style.setProperty('flex', '0 0 auto', 'important');
                    presets.style.setProperty('margin-top', 'auto', 'important');
                }
                if (capsuleEl) {
                    capsuleEl.style.setProperty('flex', '0 0 auto', 'important');
                    if (!presetsVisible) {
                        capsuleEl.style.setProperty('margin-top', 'auto', 'important');
                    } else {
                        capsuleEl.style.setProperty('margin-top', '2px', 'important');
                    }
                }
            }

            if (colRight) {
                colRight.style.setProperty('height', `${availH}px`, 'important');
                colRight.style.setProperty('min-height', `${availH}px`, 'important');
                colRight.style.setProperty('max-height', `${availH}px`, 'important');
                const sseScroll = document.getElementById('ap-sse-scroll');
                if (sseScroll) {
                    sseScroll.style.setProperty('flex', '1 1 0%', 'important');
                    sseScroll.style.setProperty('min-height', '0px', 'important');
                    sseScroll.style.setProperty('height', '100%', 'important');
                    sseScroll.style.setProperty('max-height', 'none', 'important');
                    let p = sseScroll.parentElement;
                    while (p && p !== colRight) {
                        p.style.setProperty('display', 'flex', 'important');
                        p.style.setProperty('flex-direction', 'column', 'important');
                        p.style.setProperty('flex', '1 1 0%', 'important');
                        p.style.setProperty('min-height', '0px', 'important');
                        p.style.setProperty('height', '100%', 'important');
                        p = p.parentElement;
                    }
                }
            }

            const colLeftEl = document.querySelector('.ap-col-left');
            if (colLeftEl && !colLeftEl.classList.contains('is-collapsed')) {
                colLeftEl.style.setProperty('height', `${availH}px`, 'important');
                colLeftEl.style.setProperty('min-height', `${availH}px`, 'important');
                colLeftEl.style.setProperty('max-height', `${availH}px`, 'important');
            }
        };
        syncDesktopViewport();
        if (!window.__podseekResizeBound) {
            window.__podseekResizeBound = true;
            window.addEventListener('resize', syncDesktopViewport);
        }

        window.togglePodSeekDrawer = (openOnly = false) => {
            const col = document.querySelector('.ap-col-left');
            const bd = document.getElementById('ap-mobile-drawer-backdrop');
            if (!col) return;
            if (window.innerWidth <= 768) {
                const willOpen = openOnly ? true : !col.classList.contains('mobile-drawer-open');
                col.classList.toggle('mobile-drawer-open', willOpen);
                if (bd) bd.classList.toggle('is-open', willOpen);
                document.body.classList.toggle('ap-drawer-open', willOpen);
            } else {
                const willOpen = openOnly ? true : col.classList.contains('is-collapsed');
                if (willOpen) {
                    col.classList.remove('is-collapsed');
                    try { localStorage.setItem('podseek_sidebar_collapsed', '0'); } catch(e){}
                    col.classList.add('ap-drawer-pulse');
                    setTimeout(() => col.classList.remove('ap-drawer-pulse'), 1400);
                } else {
                    col.classList.add('is-collapsed');
                    try { localStorage.setItem('podseek_sidebar_collapsed', '1'); } catch(e){}
                }
                syncDesktopViewport();
            }
        };

        const colLeft = document.querySelector('.ap-col-left');
        if (window.innerWidth <= 768 && !window.__podseekMobileDrawerInit) {
            window.__podseekMobileDrawerInit = true;
            if (colLeft) colLeft.classList.remove('mobile-drawer-open');
            document.getElementById('ap-mobile-drawer-backdrop')?.classList.remove('is-open');
            document.body.classList.remove('ap-drawer-open');
        }
        if (colLeft && window.innerWidth > 768) {
            try {
                if (localStorage.getItem('podseek_sidebar_collapsed') !== '0') {
                    colLeft.classList.add('is-collapsed');
                }
            } catch (e) {
                colLeft.classList.add('is-collapsed');
            }
        }

        const drawer = document.querySelector('.ap-col-left');
        if (drawer && !drawer.dataset.psSwipeBound) {
            drawer.dataset.psSwipeBound = '1';
            let startY = 0;
            let currentY = 0;
            let isDragging = false;

            const onTouchStart = (e) => {
                if (window.innerWidth > 768) return;
                if (drawer.classList.contains('mobile-drawer-open')) {
                    if (drawer.scrollTop <= 5 || e.target.closest('.ap-mobile-drawer-header')) {
                        startY = e.touches[0].clientY;
                        isDragging = true;
                        drawer.style.transition = 'none';
                    }
                }
            };

            const onTouchMove = (e) => {
                if (!isDragging) return;
                currentY = e.touches[0].clientY;
                const deltaY = currentY - startY;
                if (deltaY > 0) {
                    if (e.cancelable) e.preventDefault();
                    drawer.style.transform = `translateY(${deltaY}px)`;
                }
            };

            const onTouchEnd = () => {
                if (!isDragging) return;
                isDragging = false;
                drawer.style.transition = 'transform 0.28s cubic-bezier(0.32, 0.72, 0, 1)';
                const deltaY = currentY - startY;
                if (deltaY > 60) {
                    drawer.classList.remove('mobile-drawer-open');
                    document.getElementById('ap-mobile-drawer-backdrop')?.classList.remove('is-open');
                    document.body.classList.remove('ap-drawer-open');
                    drawer.style.transform = '';
                } else {
                    drawer.style.transform = '';
                }
                startY = 0;
                currentY = 0;
            };

            drawer.addEventListener('touchstart', onTouchStart, { passive: true });
            drawer.addEventListener('touchmove', onTouchMove, { passive: false });
            drawer.addEventListener('touchend', onTouchEnd, { passive: true });
        }

        if (!window.__podseekKeyBound) {
            window.__podseekKeyBound = true;
            window.addEventListener('keydown', (e) => {
                if ((e.metaKey || e.ctrlKey) && e.key.toLowerCase() === 'b') {
                    e.preventDefault();
                    document.getElementById('ap-sidebar-toggle-btn')?.click();
                }
            });
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
        let vp = document.querySelector('meta[name="viewport"]');
        if (vp && (!vp.content.includes('interactive-widget') || vp.content.includes('maximum-scale'))) {
            vp.content = "width=device-width, initial-scale=1, interactive-widget=resizes-content, viewport-fit=cover";
        }
        document.querySelectorAll('meta[name="twitter:creator"], meta[property="og:url"][content*="gradio"], meta[name="twitter:site"][content*="gradio"]').forEach((m) => m.remove());
        document.querySelectorAll('link[rel="icon"], link[rel="shortcut icon"]').forEach((lnk) => {
            if (!lnk.href || !lnk.href.startsWith('data:image/svg+xml')) {
                lnk.type = 'image/svg+xml';
                lnk.href = __PS_FAVICON_URI__;
            }
        });

        if (window.visualViewport && !window.__podseekViewportBound) {
            window.__podseekViewportBound = true;
            const handleViewportResize = () => {
                if (window.innerWidth > 768) return;
                const capsule = document.querySelector('.ap-distill-capsule');
                const modeRow = document.querySelector('.ap-mode-row');
                const vv = window.visualViewport;
                const keyboardHeight = Math.max(0, window.innerHeight - (vv.height + vv.offsetTop));
                if (keyboardHeight > 50) {
                    if (capsule) {
                        capsule.style.setProperty('bottom', `${keyboardHeight + 8}px`, 'important');
                    }
                    document.documentElement.style.setProperty('--ap-mobile-nav-bottom', `${keyboardHeight + 68}px`);
                    if (modeRow) {
                        modeRow.style.setProperty('display', 'none', 'important');
                    }
                } else {
                    if (capsule) {
                        capsule.style.removeProperty('bottom');
                    }
                    syncDesktopViewport();
                    if (modeRow) {
                        modeRow.style.removeProperty('display');
                    }
                }
            };
            window.visualViewport.addEventListener('resize', handleViewportResize);
            window.visualViewport.addEventListener('scroll', handleViewportResize);
        }

        const ta = document.querySelector('#ap-distill-input textarea, #ap-distill-input input');
        const distillBtn = document.getElementById('ap-distill-btn');
        const syncTextareaAutoGrow = (el) => {
            if (!el) return;
            el.style.height = 'auto';
            const h = Math.min(120, Math.max(24, el.scrollHeight));
            el.style.height = `${h}px`;
            el.style.overflowY = el.scrollHeight > 120 ? 'auto' : 'hidden';
            if (window.syncDesktopViewport) {
                window.syncDesktopViewport();
            }
        };
        const syncDistillBtnState = () => {
            const btn = document.getElementById('ap-distill-btn');
            const inputEl = document.querySelector('#ap-distill-input textarea, #ap-distill-input input');
            const canSubmit = Boolean(inputEl && inputEl.value && inputEl.value.trim().length >= 3);
            if (btn) {
                btn.disabled = !canSubmit;
                btn.setAttribute('aria-disabled', canSubmit ? 'false' : 'true');
            }
            if (canSubmit) {
                document.getElementById('ap-composer-notice')?.remove();
            }
            if (inputEl) {
                syncTextareaAutoGrow(inputEl);
            }
        };
        if (distillBtn && !ta) {
            distillBtn.disabled = true;
            distillBtn.setAttribute('aria-disabled', 'true');
        }
        if (ta) {
            ta.placeholder = '';
            ta.removeAttribute('placeholder');
            ta.setAttribute('data-placeholder-disabled', 'true');
            ta.setAttribute('aria-label', 'Ask a question about Huberman Lab episodes');
            syncDistillBtnState();
            syncTextareaAutoGrow(ta);
        }
        const capsule = document.querySelector('.ap-distill-capsule');
        if (capsule) {
            // Remove any orphan or duplicate wraps across the entire document
            const existingWraps = document.querySelectorAll('.ap-typewriter-wrap');
            if (existingWraps.length > 0) {
                const firstWrap = existingWraps[0];
                if (firstWrap.parentElement !== capsule) {
                    capsule.appendChild(firstWrap);
                }
                for (let i = 1; i < existingWraps.length; i++) {
                    existingWraps[i].remove();
                }
            } else {
                const wrap = document.createElement('div');
                wrap.className = 'ap-typewriter-wrap';
                wrap.setAttribute('aria-hidden', 'true');
                wrap.innerHTML = '<span class="ap-typewriter-text"></span><span class="ap-typewriter-cursor"></span>';
                capsule.appendChild(wrap);
            }

            if (!capsule.dataset.psClickBound) {
                capsule.dataset.psClickBound = '1';
                capsule.addEventListener('click', (e) => {
                    if (e.target && (
                        e.target.id === 'ap-distill-btn' ||
                        e.target.closest('#ap-distill-btn') ||
                        e.target.id === 'ap-mode-slider' ||
                        e.target.closest('#ap-mode-slider') ||
                        e.target.closest('.ap-mode-capsule-slot')
                    )) return;
                    const taInput = capsule.querySelector('textarea, input');
                    if (taInput && document.activeElement !== taInput) {
                        taInput.focus();
                    }
                });
            }
        }
        if (ta && !ta.dataset.psInputBound) {
            ta.dataset.psInputBound = '1';
            ta.addEventListener('input', () => {
                syncDistillBtnState();
                const wrap = document.querySelector('.ap-typewriter-wrap');
                if (wrap) {
                    if (ta.value && ta.value.trim().length > 0) {
                        wrap.style.setProperty('display', 'none', 'important');
                        wrap.style.setProperty('visibility', 'hidden', 'important');
                    } else {
                        wrap.style.removeProperty('display');
                        wrap.style.removeProperty('visibility');
                    }
                }
            });
        }
        if (ta && !ta.dataset.psBound) {
            ta.dataset.psBound = '1';
            ta.addEventListener('keydown', (e) => {
                if (e.key === 'Enter' && !e.shiftKey) {
                    e.preventDefault();
                    if (ta.value && ta.value.trim().length >= 3) {
                        document.getElementById('ap-distill-btn')?.click();
                    }
                }
            });
            ta.addEventListener('focus', () => {
                const wrap = document.querySelector('.ap-typewriter-wrap');
                if (wrap) {
                    wrap.style.setProperty('display', 'none', 'important');
                    wrap.style.setProperty('visibility', 'hidden', 'important');
                }
                if (window.innerWidth <= 768) {
                    setTimeout(() => {
                        if (window.visualViewport) {
                            const vv = window.visualViewport;
                            const keyboardHeight = Math.max(0, window.innerHeight - (vv.height + vv.offsetTop));
                            const capsule = document.querySelector('.ap-distill-capsule');
                            const modeRow = document.querySelector('.ap-mode-row');
                            if (capsule && keyboardHeight > 50) {
                                capsule.style.setProperty('bottom', `${keyboardHeight + 8}px`, 'important');
                                document.documentElement.style.setProperty('--ap-mobile-nav-bottom', `${keyboardHeight + 68}px`);
                            }
                            if (modeRow) {
                                modeRow.style.setProperty('display', 'none', 'important');
                            }
                        }
                        const chatEl = document.getElementById('ap-chat-scroll');
                        if (chatEl && !chatEl.classList.contains('ap-chat-empty')) {
                            chatEl.scrollTop = chatEl.scrollHeight;
                        }
                    }, 120);
                }
            });
            ta.addEventListener('blur', () => {
                const wrap = document.querySelector('.ap-typewriter-wrap');
                if (wrap && (!ta.value || ta.value.trim().length === 0)) {
                    wrap.style.removeProperty('display');
                    wrap.style.removeProperty('visibility');
                }
                if (window.innerWidth <= 768) {
                    setTimeout(() => {
                        const capsule = document.querySelector('.ap-distill-capsule');
                        const modeRow = document.querySelector('.ap-mode-row');
                        if (capsule) capsule.style.removeProperty('bottom');
                        syncDesktopViewport();
                        if (modeRow) modeRow.style.removeProperty('display');
                    }, 120);
                }
            });
        }

        // Clean up any old scroll nav attached directly to centerCol
        const strayNav = document.querySelector('.ap-col-center > #ap-chat-scroll-nav');
        if (strayNav) strayNav.remove();

        const getEffectiveScroll = () => {
            const chat = document.getElementById('ap-chat-scroll');
            if (!chat) return { top: 0, max: 0, target: null };
            if (chat.scrollHeight > chat.clientHeight + 15) {
                return { top: chat.scrollTop, max: chat.scrollHeight - chat.clientHeight, target: chat };
            }
            let p = chat.parentElement;
            while (p && p !== document.body) {
                if (p.scrollHeight > p.clientHeight + 15) {
                    return { top: p.scrollTop, max: p.scrollHeight - p.clientHeight, target: p };
                }
                p = p.parentElement;
            }
            const docEl = document.documentElement || document.body;
            if (docEl.scrollHeight > docEl.clientHeight + 15) {
                return { top: window.scrollY || docEl.scrollTop, max: docEl.scrollHeight - docEl.clientHeight, target: window };
            }
            return { top: chat.scrollTop, max: chat.scrollHeight - chat.clientHeight, target: chat };
        };

        const topBtn = document.getElementById('ap-scroll-top-btn');
        const bottomBtn = document.getElementById('ap-scroll-bottom-btn');

        if (topBtn && !topBtn.dataset.psBound) {
            topBtn.dataset.psBound = '1';
            topBtn.addEventListener('click', (e) => {
                e.preventDefault();
                e.stopPropagation();
                const { target } = getEffectiveScroll();
                if (target === window) {
                    window.scrollTo({ top: 0, behavior: 'smooth' });
                } else if (target) {
                    target.scrollTo({ top: 0, behavior: 'smooth' });
                }
            });
        }

        if (bottomBtn && !bottomBtn.dataset.psBound) {
            bottomBtn.dataset.psBound = '1';
            bottomBtn.addEventListener('click', (e) => {
                e.preventDefault();
                e.stopPropagation();
                const { target } = getEffectiveScroll();
                if (target === window) {
                    window.scrollTo({ top: document.body.scrollHeight, behavior: 'smooth' });
                } else if (target) {
                    target.scrollTo({ top: target.scrollHeight, behavior: 'smooth' });
                }
            });
        }

        const updateScrollNav = () => {
            const chat = document.getElementById('ap-chat-scroll');
            const tb = document.getElementById('ap-scroll-top-btn');
            const bb = document.getElementById('ap-scroll-bottom-btn');
            if (!chat || chat.classList.contains('ap-chat-empty')) {
                if (tb) tb.classList.remove('is-visible');
                if (bb) bb.classList.remove('is-visible');
                return;
            }

            const { top, max } = getEffectiveScroll();
            if (max <= 15) {
                if (tb) tb.classList.remove('is-visible');
                if (bb) bb.classList.remove('is-visible');
                return;
            }

            if (top > 30) {
                tb?.classList.add('is-visible');
            } else {
                tb?.classList.remove('is-visible');
            }

            if (top < max - 30) {
                bb?.classList.add('is-visible');
            } else {
                bb?.classList.remove('is-visible');
            }
        };
        window.updateChatScrollNav = updateScrollNav;

        const chatEl = document.getElementById('ap-chat-scroll');
        if (chatEl && !chatEl.dataset.psScrollBound) {
            chatEl.dataset.psScrollBound = '1';
            chatEl.addEventListener('scroll', () => {
                if (!window.__podseekProgrammaticScroll) {
                    const dist = chatEl.scrollHeight - chatEl.scrollTop - chatEl.clientHeight;
                    window.__podseekFollowBottom = dist <= 120;
                    window.__podseekSavedScrollTop = chatEl.scrollTop;
                }
                updateScrollNav();
            }, { passive: true });
        }

        const handleWheel = (e) => {
            const { target } = getEffectiveScroll();
            if (!target) return;
            if (target === window) {
                window.scrollBy({ top: e.deltaY });
            } else {
                target.scrollTop += e.deltaY;
            }
            if (window.updateChatScrollNav) window.updateChatScrollNav();
        };

        if (chatEl && !chatEl.dataset.psWheelBound) {
            chatEl.dataset.psWheelBound = '1';
            chatEl.addEventListener('wheel', handleWheel, { passive: true });
        }

        const centerCol = document.querySelector('.ap-col-center');
        if (centerCol && !centerCol.dataset.psWheelBound) {
            centerCol.dataset.psWheelBound = '1';
            centerCol.addEventListener('wheel', handleWheel, { passive: true });
        }

        if (!window.__podseekScrollBound) {
            window.__podseekScrollBound = true;
            window.addEventListener('scroll', updateScrollNav, { passive: true });
            window.addEventListener('resize', () => {
                updateScrollNav();
            }, { passive: true });
            document.querySelector('.ap-col-center')?.addEventListener('scroll', updateScrollNav, { passive: true });
        }

        updateScrollNav();
    };
    setupPodSeekUI();

    // Animated Typewriter Engine: types character by character, holds for 2 seconds, backspaces, and picks next
    if (!window.__podseekTypewriterStarted) {
        window.__podseekTypewriterStarted = true;
        const phrases = __TYPEWRITER_PHRASES__;
        let phraseIdx = Math.floor(Math.random() * phrases.length);
        let charIdx = 0;
        let isDeleting = false;

        const runStep = () => {
            const taInput = document.querySelector('#ap-distill-input textarea, #ap-distill-input input');
            if (taInput && (taInput.placeholder || taInput.hasAttribute('placeholder'))) {
                taInput.placeholder = '';
                taInput.removeAttribute('placeholder');
            }

            // Ensure only one typewriter wrap is active and remove any duplicates
            const allWraps = document.querySelectorAll('.ap-typewriter-wrap');
            if (allWraps.length > 1) {
                for (let i = 1; i < allWraps.length; i++) allWraps[i].remove();
            }
            const wrapEl = allWraps[0] || null;
            const textEl = wrapEl ? wrapEl.querySelector('.ap-typewriter-text') : null;

            const isFocused = (document.activeElement === taInput);
            const hasText = Boolean(taInput && taInput.value && taInput.value.trim().length > 0);

            if (isFocused || hasText) {
                if (wrapEl) {
                    wrapEl.style.setProperty('display', 'none', 'important');
                    wrapEl.style.setProperty('visibility', 'hidden', 'important');
                }
                setTimeout(runStep, 150);
                return;
            }

            if (wrapEl) {
                wrapEl.style.removeProperty('display');
                wrapEl.style.removeProperty('visibility');
                wrapEl.style.setProperty('opacity', '0.35', 'important');
            }

            const currentPhrase = phrases[phraseIdx] || "Ask across episodes...";

            if (!isDeleting) {
                charIdx++;
                if (textEl) textEl.textContent = currentPhrase.substring(0, charIdx);

                if (charIdx >= currentPhrase.length) {
                    isDeleting = true;
                    // Exactly 2 seconds pause when text is fully typed
                    setTimeout(runStep, 2000);
                    return;
                }
                const typeSpeed = Math.floor(Math.random() * 12) + 32;
                setTimeout(runStep, typeSpeed);
            } else {
                charIdx--;
                if (textEl) textEl.textContent = currentPhrase.substring(0, charIdx);

                if (charIdx <= 0) {
                    isDeleting = false;
                    let nextIdx;
                    do {
                        nextIdx = Math.floor(Math.random() * phrases.length);
                    } while (nextIdx === phraseIdx && phrases.length > 1);
                    phraseIdx = nextIdx;
                    charIdx = 0;
                    setTimeout(runStep, 350);
                    return;
                }
                setTimeout(runStep, 18);
            }
        };

        setTimeout(runStep, 80);
    }

    let setupDebounce;
    const obs = new MutationObserver((mutations) => {
        // Skip mutations caused solely by the typewriter text/cursor
        const onlyTypewriter = mutations.every(m => {
            const t = m.target;
            return t && (
                (t.classList && (t.classList.contains('ap-typewriter-text') || t.classList.contains('ap-typewriter-cursor'))) ||
                (t.parentElement && t.parentElement.classList && t.parentElement.classList.contains('ap-typewriter-wrap'))
            );
        });
        if (onlyTypewriter) return;

        clearTimeout(setupDebounce);
        setupDebounce = setTimeout(() => {
            setupPodSeekUI();
        }, 50);

        const evtEl = document.getElementById('ap-analytics-event');
        if (evtEl && !evtEl.dataset.counted) {
            evtEl.dataset.counted = 'true';
            const m = evtEl.dataset.mode;
            const o = evtEl.dataset.outcome;
            if (m && o) {
                window.goatcounter?.count({
                    path: 'ask/' + m + '/' + o,
                    title: 'Question ' + o,
                    event: true
                });
            }
        }

        // Scroll latest answer into view when content is replaced or a turn finishes; stay pinned while streaming if following
        const chatEl = document.getElementById('ap-chat-scroll');
        const hasChatMutation = Boolean(chatEl) && mutations.some(m => {
            const t = m.target;
            return t && (chatEl.contains(t) || (t.contains && t.contains(chatEl)));
        });
        if (hasChatMutation && chatEl) {
            if (chatEl.classList.contains('ap-chat-empty')) {
                window.__podseekLastTurnCount = 0;
                window.__podseekLastTurnDone = true;
                window.__podseekFollowBottom = true;
                window.__podseekSavedScrollTop = 0;
            } else {
                const turnCount = parseInt(chatEl.dataset.turnCount || '0', 10);
                const turnDone = chatEl.dataset.turnDone === 'true';
                const prevCount = window.__podseekLastTurnCount || 0;
                const prevDone = window.__podseekLastTurnDone !== false;
                if (typeof window.__podseekFollowBottom === 'undefined') {
                    window.__podseekFollowBottom = true;
                }
                if (turnCount > prevCount) {
                    window.__podseekFollowBottom = true;
                }
                const turnJustFinished = turnDone && (!prevDone || turnCount > prevCount);
                window.__podseekProgrammaticScroll = true;
                if (turnJustFinished) {
                    const lastAns = document.getElementById('ap-last-answer') || document.getElementById('ap-last-turn');
                    if (lastAns && lastAns.offsetHeight > chatEl.clientHeight * 0.85) {
                        chatEl.scrollTop = Math.max(0, lastAns.offsetTop - 12);
                    } else {
                        chatEl.scrollTop = chatEl.scrollHeight;
                    }
                    window.__podseekSavedScrollTop = chatEl.scrollTop;
                } else if (window.__podseekFollowBottom) {
                    chatEl.scrollTop = chatEl.scrollHeight;
                    window.__podseekSavedScrollTop = chatEl.scrollTop;
                } else if (typeof window.__podseekSavedScrollTop === 'number') {
                    chatEl.scrollTop = window.__podseekSavedScrollTop;
                }
                window.__podseekLastTurnCount = turnCount;
                window.__podseekLastTurnDone = turnDone;
                requestAnimationFrame(() => {
                    window.__podseekProgrammaticScroll = false;
                });
            }
            if (window.updateChatScrollNav) {
                window.updateChatScrollNav();
            }
        }

        const curTa = document.querySelector('#ap-distill-input textarea, #ap-distill-input input');
        if (curTa) {
            syncTextareaAutoGrow(curTa);
        }

        const sseEl = document.getElementById('ap-sse-scroll');
        if (sseEl) sseEl.scrollTop = sseEl.scrollHeight;
    });
    obs.observe(document.body, { childList: true, subtree: true });
}"""

_INIT_UI_JS = _INIT_UI_JS_TEMPLATE.replace("__TYPEWRITER_PHRASES__", json.dumps(QUIRKY_PLACEHOLDERS)).replace(
    "__PS_FAVICON_URI__", json.dumps(PS_FAVICON_DATA_URI)
)

__all__ = ["build_demo", "format_citations", "format_event"]

_FIRE_GOATCOUNTER_JS = """() => {
    const el = document.getElementById('ap-analytics-event');
    if (el && !el.dataset.counted) {
        el.dataset.counted = 'true';
        const m = el.dataset.mode;
        const o = el.dataset.outcome;
        if (m && o) {
            window.goatcounter?.count({
                path: 'ask/' + m + '/' + o,
                title: 'Question ' + o,
                event: true
            });
        }
    }
}"""


def _demo_fallback_enabled() -> bool:
    val = os.getenv("PODSEEK_DEMO_FALLBACK") or os.getenv("ASKPODCAST_DEMO_FALLBACK", "false")
    return val.strip().lower() in {"1", "true", "yes"}


def build_demo(client: PodSeekClient | None = None, stylesheet: str = "theme.css") -> Any:
    configure_tracing()
    if client is None:
        client = make_client()

    def load_episodes_html() -> str:
        try:
            return render_episodes_html(client.episodes())
        except Exception:
            return render_episodes_html([])

    def get_episode_count() -> int:
        try:
            items = client.episodes()
            return len(items) if items else 23
        except Exception:
            return 23

    init_ep_count = get_episode_count()

    def on_ingest(video_url_or_id: str):
        cleaned = video_url_or_id.strip()
        current_eps = load_episodes_html()
        if not cleaned:
            err_box = render_ingest_status_html(
                "error", "Missing episode link", "Paste a Huberman Lab YouTube URL or video ID."
            )
            err_logs = [("✕ [ingest] Missing episode link", "#EF4444")]
            yield (
                gr.update(value=err_box, visible=True),
                current_eps,
                render_ingest_workflow_graph_html(active_step="abort", error=True, abort_reason="Empty link"),
                render_sse_log_html(err_logs, endpoint="POST /ingest"),
                "",
            )
            time.sleep(3.2)
            yield (
                gr.update(value="", visible=False),
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
            gr.update(value=render_ingest_status_html("loading", stages[0][1], stages[0][2]), visible=True),
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
                    gr.update(value=render_ingest_status_html("loading", title_txt, detail_txt), visible=True),
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
                    gr.update(value=render_ingest_status_html("success", banner_title, title), visible=True),
                    updated_eps,
                    render_ingest_workflow_graph_html(active_step="done", chunks_indexed=chunks_n, cached=is_cached),
                    render_sse_log_html(ingest_logs, endpoint="POST /ingest"),
                    "",
                )
                time.sleep(3.2)
                yield (
                    gr.update(value="", visible=False),
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
                    gr.update(value=status_box, visible=True),
                    current_eps,
                    render_ingest_workflow_graph_html(active_step="abort", error=True, abort_reason=reason),
                    render_sse_log_html(ingest_logs, endpoint="POST /ingest"),
                    "",
                )
                time.sleep(4.0)
                yield (
                    gr.update(value="", visible=False),
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

    def on_ask(question: Any, history: list[dict] | Any = None, mode_label: str = "⚖️ Balanced"):
        if not isinstance(question, str):
            question = str(getattr(question, "value", question or ""))
        cleaned = question.strip()
        if not isinstance(history, list):
            history = []
        current_history = list(history or [])
        mode_val = (
            "turbo"
            if "turbo" in (mode_label or "").lower()
            else ("rigorous" if "rigorous" in (mode_label or "").lower() else "balanced")
        )
        if not _is_submittable_question(cleaned):
            short_msg = "Enter a question of at least 3 characters."
            yield (
                render_chat_session_html(current_history, episode_count=init_ep_count, notice=short_msg),
                current_history,
                render_workflow_graph_html(mode=mode_val),
                render_sse_log_html([(short_msg, "var(--retry-stroke)")]),
                question,
                gr.update(visible=True),
                "",
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

        # Clear input immediately while keeping preset questions always visible
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
            gr.update(visible=True),
            "",
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
                    no_change = getattr(gr, "skip", lambda: gr.update())()
                    yield (
                        render_chat_session_html(preview_history),
                        current_history,
                        no_change,
                        no_change,
                        "",
                        gr.update(visible=True),
                        "",
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
                    gr.update(visible=True),
                    "",
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
                    gr.update(visible=True),
                    "",
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
                gr.update(visible=True),
                "",
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
        outcome = determine_outcome(answer, cached=is_cached, aborted=aborted)
        tracker_html = f'<div id="ap-analytics-event" data-mode="{html.escape(mode_val)}" data-outcome="{html.escape(outcome)}" style="display:none;"></div>'
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
            gr.update(visible=True),
            tracker_html,
        )

    viewport_meta = render_head_meta_html()
    with gr.Blocks(
        title="PodSeek",
        fill_width=True,
        analytics_enabled=False,
        css=load_theme_css(stylesheet),
        head=viewport_meta,
    ) as demo:
        chat_state = gr.State([])
        analytics_tracker = gr.HTML("", visible=True, elem_id="ap-analytics-tracker")
        p1, p2, p3, p4, p5 = pick_random_presets(5)
        preset_1_state = gr.State(p1["question"])
        preset_2_state = gr.State(p2["question"])
        preset_3_state = gr.State(p3["question"])
        preset_4_state = gr.State(p4["question"])
        preset_5_state = gr.State(p5["question"])

        # Top Header Bar: Brand on Left + Controls (Library Drawer on Mobile + Theme Toggle) Flush Right
        with gr.Row(elem_classes=["ap-card", "ap-header-row"]):
            gr.HTML(
                f'<div class="ap-header-inner-row">'
                f'<div class="ap-header-brand">{render_header_brand_html()}</div>'
                f'<div class="ap-header-controls">{render_header_controls_html()}</div>'
                f"</div>",
                elem_classes=["ap-header-wrap"],
            )

        # Backdrop for Mobile Slide-Over Drawer
        gr.HTML(
            '<div id="ap-mobile-drawer-backdrop" '
            "onclick=\"document.querySelector('.ap-col-left')?.classList.remove('mobile-drawer-open'); "
            "document.body.classList.remove('ap-drawer-open'); "
            "this.classList.remove('is-open');\"></div>",
            elem_classes=["ap-mobile-drawer-backdrop-wrap"],
        )

        # PAGE 1: 3-Column Studio View
        with gr.Row(visible=True, elem_id="ap-studio-view"):
            # ENTITY 1 (Left): Collapsible Sidebar on Desktop / Slide-Over Sheet on Mobile (hidden by default)
            with gr.Column(scale=2, elem_classes=["ap-card", "ap-col-left", "is-collapsed"]):
                with gr.Column(
                    elem_id="ap-bento-accordion",
                    elem_classes=["ap-bento-accordion"],
                ):
                    gr.HTML(
                        '<div class="ap-mobile-drawer-header">'
                        '<div style="width:100%;display:flex;flex-direction:column;align-items:center;gap:6px;">'
                        '<div style="width:36px;height:4px;border-radius:9999px;background:var(--border-strong);opacity:0.6;"></div>'
                        '<div style="width:100%;display:flex;align-items:center;justify-content:space-between;padding-top:2px;">'
                        '<div style="display:flex;align-items:center;gap:6px;">'
                        '<span style="font-size:14px;">📚</span>'
                        '<span style="font-weight:700;font-size:13.5px;color:var(--text-main);">Knowledge Base</span>'
                        "</div>"
                        '<button type="button" class="ap-drawer-close-btn" '
                        "onclick=\"document.querySelector('.ap-col-left')?.classList.remove('mobile-drawer-open'); "
                        "document.body.classList.remove('ap-drawer-open'); "
                        "document.getElementById('ap-mobile-drawer-backdrop')?.classList.remove('is-open');\">"
                        "<span>Hide</span>"
                        '<svg width="10" height="10" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><path d="M19 9l-7 7-7-7"/></svg>'
                        "</button>"
                        "</div>"
                        "</div>"
                        "</div>"
                        '<div class="ap-ingest-title" style="font-size:12.5px;font-weight:700;margin:8px 0 6px;">Ingest Episode</div>',
                        elem_classes=["ap-sidebar-header-wrap"],
                    )
                    with gr.Row(elem_classes=["ap-ingest-capsule"]):
                        video_input = gr.Textbox(
                            label="",
                            show_label=False,
                            container=False,
                            placeholder="Paste YouTube link...",
                            lines=1,
                            max_lines=1,
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
                    ingest_status = gr.HTML("", visible=False, elem_id="ap-ingest-status-wrap")
                    episodes_html = gr.HTML(load_episodes_html(), elem_classes=["ap-episodes-list-block"])

            # ENTITY 2 (Center): Hero Session Chat + Always-Visible Presets + Multiline Capsule ("Distill ->")
            with gr.Column(scale=8, elem_classes=["ap-card", "ap-col-center"]):
                chat_html = gr.HTML(render_chat_session_html([], episode_count=init_ep_count))

                with gr.Row(elem_classes=["ap-presets-carousel"], visible=True) as presets_row:
                    preset_1 = gr.Button(p1["topic"], size="sm", elem_classes=["ap-preset-pill"])
                    preset_2 = gr.Button(p2["topic"], size="sm", elem_classes=["ap-preset-pill"])
                    preset_3 = gr.Button(p3["topic"], size="sm", elem_classes=["ap-preset-pill"])
                    preset_4 = gr.Button(p4["topic"], size="sm", elem_classes=["ap-preset-pill"])
                    preset_5 = gr.Button(p5["topic"], size="sm", elem_classes=["ap-preset-pill"])

                with gr.Group(elem_id="ap-mode-radio-wrap", elem_classes=["ap-hidden-bridge"]):
                    mode_radio = gr.Radio(
                        choices=["⚡ Turbo", "⚖️ Balanced", "🎯 Rigorous"],
                        value="⚖️ Balanced",
                        show_label=False,
                        container=False,
                        elem_id="ap-mode-radio",
                        elem_classes=["ap-view-hidden"],
                    )

                with gr.Row(elem_classes=["ap-distill-capsule"]):
                    mode_slider_html = gr.HTML(
                        render_mode_slider_html("balanced"), elem_classes=["ap-mode-capsule-slot"]
                    )
                    question_input = gr.Textbox(
                        label="Ask a question about Huberman Lab episodes",
                        show_label=False,
                        container=False,
                        placeholder="",
                        lines=1,
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

            # ENTITY 3 (Right): Cyclic Workflow Graph + Color-Coded SSE Stream
            with gr.Column(scale=3, elem_classes=["ap-col-right"]):
                graph_html = gr.HTML(render_workflow_graph_html(mode="balanced"), elem_classes=["ap-workflow-block"])
                sse_html = gr.HTML(render_sse_log_html([]), elem_classes=["ap-sse-block"])

        # PAGE 2: Stats for Nerds View
        with gr.Row(visible=True, elem_id="ap-nerds-view", elem_classes=["ap-view-hidden"]):
            with gr.Column(scale=12):
                gr.HTML(render_stats_for_nerds_html())

        def load_initial_view() -> tuple[str, str, str, Any, Any, Any, Any, Any, Any, str, str, str, str, str]:
            p1_n, p2_n, p3_n, p4_n, p5_n = pick_random_presets(5)
            try:
                ep_items = client.episodes()
            except Exception:
                ep_items = []
            count = len(ep_items) if ep_items else 23
            return (
                render_episodes_html(ep_items),
                render_workflow_graph_html(mode="balanced"),
                render_chat_session_html([], episode_count=count),
                "",
                gr.update(value=p1_n["topic"]),
                gr.update(value=p2_n["topic"]),
                gr.update(value=p3_n["topic"]),
                gr.update(value=p4_n["topic"]),
                gr.update(value=p5_n["topic"]),
                p1_n["question"],
                p2_n["question"],
                p3_n["question"],
                p4_n["question"],
                p5_n["question"],
            )

        demo.load(
            load_initial_view,
            outputs=[
                episodes_html,
                graph_html,
                chat_html,
                question_input,
                preset_1,
                preset_2,
                preset_3,
                preset_4,
                preset_5,
                preset_1_state,
                preset_2_state,
                preset_3_state,
                preset_4_state,
                preset_5_state,
            ],
            show_progress="hidden",
            js=_INIT_UI_JS,
        )
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

        ask_outputs = [chat_html, chat_state, graph_html, sse_html, question_input, presets_row, analytics_tracker]
        ask_ev = ask_btn.click(
            on_ask,
            inputs=[question_input, chat_state, mode_radio],
            outputs=ask_outputs,
            show_progress="hidden",
        )
        ask_ev.then(None, inputs=[analytics_tracker], js=_FIRE_GOATCOUNTER_JS)

        sub_ev = question_input.submit(
            on_ask,
            inputs=[question_input, chat_state, mode_radio],
            outputs=ask_outputs,
            show_progress="hidden",
        )
        sub_ev.then(None, inputs=[analytics_tracker], js=_FIRE_GOATCOUNTER_JS)

        for p_btn, p_st in [
            (preset_1, preset_1_state),
            (preset_2, preset_2_state),
            (preset_3, preset_3_state),
            (preset_4, preset_4_state),
            (preset_5, preset_5_state),
        ]:
            p_ev = p_btn.click(
                on_ask,
                inputs=[p_st, chat_state, mode_radio],
                outputs=ask_outputs,
                show_progress="hidden",
            )
            p_ev.then(None, inputs=[analytics_tracker], js=_FIRE_GOATCOUNTER_JS)

    return demo


if __name__ == "__main__":
    import socket

    port = int(os.environ.get("PORT", "7860"))

    def get_wifi_ip() -> str:
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect(("8.8.8.8", 80))
            ip = s.getsockname()[0]
            s.close()
            return ip
        except Exception:
            return "127.0.0.1"

    wifi_ip = get_wifi_ip()
    print("=" * 64)
    print(f"📱 Phone & Wi-Fi Devices:  http://{wifi_ip}:{port}")
    print(f"💻 This Mac:              http://localhost:{port}")
    print("=" * 64)

    # Launch bound to 0.0.0.0 for LAN visibility, with share link fallback
    favicon_file = Path(__file__).resolve().parent / "styles" / "favicon.svg"
    app = build_demo()
    try:
        app.launch(server_name="0.0.0.0", server_port=port, share=True, show_api=False, favicon_path=favicon_file)
    except Exception:
        app.launch(server_name="0.0.0.0", server_port=port, share=False, show_api=False, favicon_path=favicon_file)
