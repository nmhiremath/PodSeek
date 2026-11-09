# UI/UX Design, Ergonomics & Modernity Rubric

Use this rubric when inspecting screenshots and DOM telemetry in the `ui-ux-consultant` subagent. Every critique must be concrete, tied to measurable visual/DOM evidence, and paired with an actionable code-level recommendation.

---

## 1. Visual Hierarchy & Spatial Rhythm (20 pts)
- **Focal Point Clarity:** On initial load, does the eye immediately land on the primary value proposition (hero prompt) and primary action (`.ap-distill-capsule`)?
- **Bento Card & Column Alignment:** On desktop (`1280px+`), do top and bottom edges of `.ap-col-left` (when open), `.ap-col-center`, and `.ap-col-right` align to the exact pixel (`±1px`)? Are inter-column gaps equal to the header-to-studio vertical gap (`12px`)?
- **Breathing Room & Padding Symmetry:** Inside `.ap-distill-capsule` and `.ap-ingest-capsule`, is there balanced horizontal clearance (`≥10px–14px`) between the left mode pill (`#ap-mode-slider`), the text/typewriter prompt (`.ap-typewriter-wrap`), and the right submit button (`#ap-distill-btn`)?
- **De-cluttering:** Are redundant headers, double borders, nested scrollbars, or dead whitespace zones eliminated?

---

## 2. Responsive & Viewport Ergonomics (25 pts)
- **Zero-Scroll App Shell (`100dvh`):** Does `document.documentElement.scrollHeight <= window.innerHeight` hold true so the outer browser page never scrolls while `#ap-chat-scroll` and `#ap-sse-scroll` scroll internally?
- **Bottom Viewport Pinning:** Are `.ap-presets-carousel`, `.ap-distill-capsule`, and `#ap-chat-scroll-nav` permanently anchored to the bottom of the viewport across all screen sizes—even when long multi-paragraph answers stream in?
- **Touch Target Sizing (Mobile `≤768px`):**
  - Primary interactive buttons (`#ap-distill-btn`, `#ap-mode-slider`, `#ap-mobile-library-btn`, `#ap-theme-slider`, `.ap-chat-nav-btn`) must have a minimum hit height of `30px–44px` and `≥6px` separation from adjacent targets.
  - Horizontal topic carousel (`.ap-presets-carousel`) must scroll smoothly on a single row (`flex-wrap: nowrap`) without wrapping or clipping pill text.
- **Small-Screen Flowchart Scaling (`360px`, `390px`, `430px`):** Does `.wf-canvas-wrap` fit cleanly inside `.ap-spotlight-card` without horizontal clipping or excessive bottom dead space?

---

## 3. Interaction & Streaming Stability (20 pts)
- **Zero Layout Shift (CLS = 0) During Token Streaming:**
  - Does `#ap-chat-scroll` maintain a locked pixel height (`var(--ap-chat-h)`) when `innerHTML` is replaced on token deltas?
  - Does `.wf-canvas-wrap` maintain a locked `transform: scale(...)` with `transition: none` so it never zooms or jumps during streaming?
- **Typewriter Prompt Lifecycle:**
  - Does `.ap-typewriter-wrap` stay on a single line (`height <= 24px`) with its blinking cursor `|` inline next to the last character?
  - Does it immediately hide (`display: none`) on input focus or when text is entered, and restore cleanly on blur when empty?
- **Drawer & Modal Choreography:**
  - On mobile, does the Knowledge Base slide-over drawer (`#ap-bento-accordion` / `.ap-col-left`) open with a smooth backdrop blur and close cleanly via the `Hide` button, backdrop tap, or downward swipe?
  - On desktop, does `Cmd+B` or clicking `#ap-sidebar-toggle-btn` smoothly collapse/expand `.ap-col-left` while recalculating the center column width?

---

## 4. Typography, Color & Dark/Light Mode Craft (20 pts)
- **Contrast & Legibility (WCAG AA):**
  - Body copy (`--text-main` on `--bg-card` / `--bg-subtle`): contrast ratio `≥ 7:1`.
  - Muted metadata (`--text-muted`): contrast ratio `≥ 4.5:1` (except intentionally ghosted placeholder typewriter text at `0.35` opacity).
  - Mode pill states (`Balanced` blue, `Turbo` amber, `Rigorous` crimson): distinct, legible, and harmonious in both Light (`#F8F9FA`) and Dark (`#111113`) themes.
- **Citation Pill Craft (`a.gai-pill`):**
  - Do inline YouTube timestamp citations render as compact stadium pills with the circular red play badge, never breaking line rhythm or leaving orphaned punctuation (`).`, `],`)?

---

## 5. Modern AI Product Benchmarks (15 pts)
Compare the interface against best-in-class modern AI & developer tools (**Linear, Perplexity, Raycast, Claude, Vercel Geist**):
- **Perceived Speed & Feedback:** Does every user action (mode cycle, topic pill click, absorb click, theme toggle) provide immediate `<16ms` visual feedback?
- **Information Architecture:** Can a first-time visitor understand what the app does, see how many episodes are indexed, test a curated topic in one tap, and inspect the Corrective RAG reasoning graph without feeling overwhelmed?
- **Delight & Polish:** Identify 3–5 high-leverage micro-improvements (e.g., subtle gradient fade masks on scroll containers, keyboard shortcut hints, active pill states, empty-state polish) that elevate the UI from "good" to "signature portfolio piece."

---

## Required Report Template (`ui_ux_audit_report.md`)

Structure your final artifact as follows:
1. **Executive Summary & Design Scorecard** (Overall score `/100` + breakdown table across the 5 categories above).
2. **Multi-Viewport Visual Gallery** (Embedded screenshots from `<ARTIFACT_DIR>/ui_audit/` using markdown image carousels across Desktop Light/Dark and Mobile Light/Dark).
3. **Confirmed Bugs & Geometry Violations (`P0` / `P1`)** (Exact element selectors, measured bounding boxes from `audit_telemetry.json`, root cause in `ui/styles/theme.css` or `ui/components.py`, and exact fix).
4. **UX Friction & Ergonomic Pain Points (`P2`)** (User journey bottlenecks on mobile and desktop).
5. **Modernity & Aesthetic Elevations (`P3`)** (Prioritized list of high-impact design upgrades with ready-to-apply CSS/HTML snippets).
