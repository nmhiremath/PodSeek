# Architecture Diagrams

This directory documents the visual architecture diagrams for PodSeek.

## System Context Flowchart
The system context diagram is authored in Mermaid (`flowchart LR`) and embedded directly in `README.md` and `docs/design/README.md`. It illustrates component boundaries across the web service (Gradio Studio UI, FastAPI, QA cache, LangGraph agent), committed data (ChromaDB, raw transcripts), and external services (Google GenAI, YouTube, LangSmith).

## Animated Corrective Loop (`docs/assets/crag-loop-dark.svg` / `docs/assets/crag-loop-light.svg`)
The hand-authored SMIL animated SVG visualizes the 4-node Corrective RAG loop (`Retrieve` -> `Grade` -> `Rewrite` -> `Generate`), including the Balanced distance fast-path and circuit-breaker refusal routing directly to `Generate`.

### Demo Screen Recording (`docs/assets/demo.gif`)
> TODO(record): Screen recording of the live Gradio Studio UI flowchart spotlighting node transitions during live query execution is not yet included.

### In-Doc Mermaid Diagrams
Other structural diagrams (state machines, sequence diagrams, ingestion pipelines) are embedded directly in Markdown files using standard Mermaid syntax with explicit frontmatter theme configuration (`theme: base`). They can be compiled and validated using `@mermaid-js/mermaid-cli`:

```bash
npx @mermaid-js/mermaid-cli -i <input.mmd> -o <output.png>
```
