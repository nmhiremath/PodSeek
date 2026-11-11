# Capability Specification: Studio UI

## Purpose
The Studio UI capability provides an interactive, responsive 3-column Bento Studio web interface built with Gradio 5, supporting real-time streaming, interactive SVG workflow flowcharts, Google AI Overview-style inline timestamp citation pills, and in-process execution.

## Requirements

### Requirement: 3-Column Bento Studio Layout
The system SHALL present a 3-column responsive layout comprising an Ingest/Library column, a Chat/Distill column, and a Workflow Observability column.

#### Scenario: Desktop layout organization
- **WHEN** the UI loads on desktop viewports
- **THEN** column 1 (`scale=3`) displays the ingestion command capsule and indexed episodes list
- **AND** column 2 (`scale=5`) displays the chat history, preset question chips, and the multiline `Distill →` composer capsule
- **AND** column 3 (`scale=4`) displays the live SVG workflow flowchart and SSE telemetry stream.

### Requirement: Input Validation and Composer Behavior
The system SHALL guard input submission against empty or short inputs and support multiline keyboard ergonomics.

#### Scenario: Input validation under 3 characters
- **WHEN** the question input is empty or fewer than 3 non-whitespace characters
- **THEN** the `Distill` button is disabled
- **AND** pressing Enter does not trigger query execution.

#### Scenario: Keyboard submission
- **WHEN** the user presses Enter in the composer without Shift
- **THEN** the question is submitted
- **AND** Shift+Enter inserts a newline.

### Requirement: Google AI Overview Inline Stadium Citations
The system SHALL format raw timestamp citations in generated answers into styled inline stadium chips.

#### Scenario: Rendering inline citation pills
- **WHEN** the answer text contains citations like `[00:57:54]` or `[Episode Title @ 00:57:54]`
- **THEN** `render_inline_citations()` transforms them into clickable `a.gai-pill` stadium chips
- **AND** each chip includes a circular YouTube play icon and links directly to `https://youtu.be/<id>?t=<sec>`
- **AND** chips are constrained with CSS ellipsis to stay within the answer card width.

### Requirement: In-Process vs Remote Client Adapter
The system SHALL support both decoupled HTTP/SSE remote client mode and single-process in-process client mode.

#### Scenario: In-process execution mode
- **WHEN** `PODSEEK_UI_MODE` is set to `"inprocess"` (or default when no remote URL is configured)
- **THEN** `make_client()` instantiates `InProcessClient`
- **AND** UI calls invoke FastAPI route handlers and LangGraph event generators directly without HTTP socket roundtrips.
