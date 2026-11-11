# Architecture Diagrams

This directory contains the source files for PodSeek's architecture diagrams.

## Hero Diagram (`architecture.d2`)

The hero architecture diagram is authored in [D2](https://d2lang.com) (`architecture.d2`) and rendered into light and dark SVG assets embedded in the root `README.md`.

### Prerequisites
Install the D2 CLI (version 0.9.0 or later):
```bash
# macOS via Homebrew
brew install d2

# Linux / curl
curl -fsSL https://d2lang.com/install.sh | sh -s --
```

### Re-render Commands
To re-render both light and dark SVGs using the ELK layout engine:

```bash
# Render light theme (Theme 4: Cool Classics)
d2 --layout=elk --theme=4 docs/diagrams/architecture.d2 docs/assets/architecture-light.svg

# Render dark theme (Theme 200: Dark Mauve)
d2 --layout=elk --theme=200 docs/diagrams/architecture.d2 docs/assets/architecture-dark.svg
```

### In-Doc Mermaid Diagrams
Other structural diagrams (state machines, sequence diagrams, ingestion pipelines) are embedded directly in Markdown files using standard Mermaid syntax with explicit frontmatter theme configuration (`theme: base`). They can be compiled and validated using `@mermaid-js/mermaid-cli`:

```bash
npx @mermaid-js/mermaid-cli -i <input.mmd> -o <output.png>
```
