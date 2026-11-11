# 7. In-Repo Provider Factory vs Proxy Gateway

> Recorded retroactively on 2026-11-10; decision originally made in commit `56aaa0b`.

## Status
Accepted

## Context
Deployments need flexibility to run against Google GenAI (default), OpenAI, Anthropic, xAI (Grok), or local open-weights models via Ollama without changing application code. In enterprise settings, this is often handled by deploying an external API proxy gateway (e.g. LiteLLM Proxy, Portkey, Kong AI Gateway). However, for a single-service free-tier deployment, introducing an external proxy service adds operational overhead, failure points, and deployment cost.

## Decision
Implement an in-repository factory module (`app/factory.py`) with LRU-cached builder functions (`_build_chat_model`, `_build_embedding_model`). Model selection is driven purely by environment variables (`LLM_PROVIDER`, `CHAT_MODEL`, `EMBEDDING_PROVIDER`, `EMBEDDING_MODEL`). Additionally, ChromaDB collection names are dynamically derived from the active embedding model (`get_collection_name()`), isolating vectors across embedding switches.

## Alternatives Considered
1. **External Gateway (LiteLLM Proxy / Portkey):** Deploy a separate proxy container to unify LLM APIs under OpenAI-compatible endpoints. Rejected because running a secondary proxy container exceeds Render free-tier RAM limits and complicates local setups.
2. **Direct Hardcoded SDK Calls:** Hardcode `ChatGoogleGenerativeAI`. Rejected because local offline developers and enterprise evaluators require the ability to run against local Ollama or OpenAI without modifying source code.

## Consequences
### Good
- Zero external runtime infrastructure required: runs inside the application process with zero network hops.
- Cache efficiency: `@lru_cache` ensures model wrapper instances are reused without redundant allocations.
- Vector dimension safety: switching from Gemini (`dim=3072`) to OpenAI (`dim=1536`) automatically shifts to an isolated collection name (`podcast_chunks_text_embedding_3_small`), preventing Chroma dimension mismatch crashes.

### Bad
- Does not provide gateway-level features like cross-provider automatic retry fallbacks, centralized token rate-limiting, or cross-tenant virtual keys.
- Requires SDK client packages (`langchain-google-genai`, `langchain-openai`, `langchain-anthropic`, `langchain-ollama`) to be listed in `requirements.txt`.

## Evidence
- `app/factory.py`: `get_chat_model()`, `get_embedding_model()`, `get_collection_name()`.
- Git commit: `56aaa0b`.
