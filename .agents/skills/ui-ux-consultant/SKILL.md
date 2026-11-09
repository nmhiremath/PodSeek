---
name: ui-ux-consultant
description: >-
  Autonomous UI/UX Testing Consultant & Design Critic that runs in its own
  dedicated subagent with a headless browser (Playwright) and Chrome DevTools.
  Sweeps mobile, tablet, and desktop viewports in Light and Dark modes,
  interacts with all UI components, runs deterministic DOM geometry/overlap/WCAG
  telemetry, visually inspects screenshots with multimodal vision, and produces
  a comprehensive UI/UX bug, modernity, and design improvement report. Use when
  the user asks to audit, critique, test, or review the UI/UX design or layout.
---

# UI/UX Testing Consultant & Design Critic Skill

This skill launches an isolated **UI/UX Testing Consultant Subagent** (`ui-ux-consultant-agent`) that drives a real headless browser against the live application, tests every interactive component across 6 screen sizes in both Light and Dark themes, combines pixel-exact DOM geometry checks with multimodal visual critique, and delivers an actionable UI/UX report.

---

## Architecture & Workflow

```
Main Agent
  └─► define_subagent + invoke_subagent ("ui-ux-consultant-agent")
        ├─► Step 1: Verify or launch target web app URL (default: http://127.0.0.1:7860)
        ├─► Step 2: Run `.agents/skills/ui-ux-consultant/scripts/headless_ui_audit.py`
        │     • Sweeps 6 viewports: 360×740, 390×844, 430×932, 768×1024, 1280×800, 1440×900
        │     • Tests Light & Dark themes, Drawer open/close, Mode cycling, Preset carousel,
        │       Input focus/typewriter concealment, and Long-form chat scroll + nav buttons
        │     • Computes bounding-box overlaps, viewport overflow, bottom-pinning drift,
        │       tap-target ergonomics, contrast ratios, and streaming layout stability (CLS)
        │     • Captures full-viewport & component PNG screenshots + `audit_telemetry.json`
        ├─► Step 3: Multimodal Visual Inspection (`read_file` on captured PNGs)
        │     • Evaluates visual hierarchy, typography, alignment, negative space, and modern craft
        │       against `.agents/skills/ui-ux-consultant/references/design_rubric.md`
        └─► Step 4: Write `ui_ux_audit_report.md` artifact & return executive summary
```

---

## Step-by-Step Instructions for the Main Agent

When this skill is triggered:

### 1. Define the Specialist Subagent
Call `define_subagent` with:
- **`Name`**: `"ui-ux-consultant-agent"`
- **`Description`**: `"Principal UI/UX Testing Consultant & Design Critic with headless browser automation and multimodal visual inspection."`
- **`EnableWriteTools`**: `true` (so it can run the Playwright audit script and write the report artifact)
- **`EnableMCPTools`**: `true` (so it can also use `chrome-devtools` / `a11y-debugging` if needed)
- **`EnableSubagentTools`**: `false`
- **`SystemPrompt`**:
  Use the instructions below so the subagent acts as a Principal Product Designer (Apple HIG / Linear / Vercel / Perplexity caliber) and Staff Frontend QA Engineer:
  1. Read `.agents/skills/ui-ux-consultant/references/design_rubric.md`.
  2. Run `.venv/bin/python .agents/skills/ui-ux-consultant/scripts/headless_ui_audit.py --url <TARGET_URL> --out-dir <ARTIFACT_DIR>/ui_audit` using `run_command`.
     - If Playwright is not installed in `.venv`, either use the Chrome CLI headless screenshot/DOM dump fallback built into `headless_ui_audit.py` or install Playwright (`pip install playwright && playwright install chromium`).
     - If no server is listening on `<TARGET_URL>`, start `python -m ui.app` as a background daemon first and wait until `http://127.0.0.1:7860` responds.
  3. Read `<ARTIFACT_DIR>/ui_audit/audit_telemetry.json` and call `read_file` on the generated PNG screenshots in `<ARTIFACT_DIR>/ui_audit/` to visually inspect mobile, tablet, and desktop layouts in both Light and Dark modes.
  4. Cross-reference every visual observation with the actual CSS/HTML source in `ui/styles/theme.css`, `ui/components.py`, and `ui/app.py` (read-only—do not modify application code during an audit unless explicitly instructed).
  5. Write a comprehensive markdown artifact at `<ARTIFACT_DIR>/ui_ux_audit_report.md` (with `UserFacing: true`) and return a concise summary to the parent agent.

### 2. Invoke the Subagent
Call `invoke_subagent` with:
- **`TypeName`**: `"ui-ux-consultant-agent"`
- **`Role`**: `"UI/UX Testing Consultant"`
- **`Model`**: `"inherit"`
- **`Prompt`**: Specify the target URL (default `http://127.0.0.1:7860`), the current conversation's artifact directory path, and any specific flows or components the user wants emphasized.

---

## Resources in This Skill
- **Headless Browser & DOM Geometry Script**: [headless_ui_audit.py](./scripts/headless_ui_audit.py)
- **UI/UX Design & Modernity Evaluation Rubric**: [design_rubric.md](./references/design_rubric.md)
