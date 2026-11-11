# Spec Delta

## ADDED Requirements

### Requirement: GoatCounter Page and Outcome Analytics
The system SHALL inject optional cookie-free GoatCounter page tracking and dispatch question outcome events without sensitive question or answer text.

#### Scenario: Script injection with valid code
- **WHEN** `GOATCOUNTER_CODE` is set to a valid string matching `^[a-z0-9-]+$`
- **THEN** `render_head_meta_html()` appends the GoatCounter analytics script tag to the document head.

#### Scenario: Script injection omitted when unset or invalid
- **WHEN** `GOATCOUNTER_CODE` is unset or fails the regex check
- **THEN** `render_head_meta_html()` emits no analytics script tag.

#### Scenario: Outcome event dispatched on question completion
- **WHEN** a question stream or execution finishes in the UI
- **THEN** the UI triggers a GoatCounter event with path `ask/<mode>/<outcome>`
- **AND** the payload contains no question text, answer text, or user IDs.
