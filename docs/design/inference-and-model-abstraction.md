# Pillar 4: Inference & Model Abstraction

## 1. What This Pillar Means in Production AI Systems
Inference and model abstraction provides an isolated boundary between application business logic and underlying foundation model providers. In production AI systems, this pillar insulates the codebase from provider API breaking changes, manages API authentication securely, enables straightforward switching between cloud and self-hosted models, and prevents vector dimension mismatches across embedding model switches.

## 2. What PodSeek Does
PodSeek consolidates all LLM and embedding instantiation into a centralized factory module (`app/factory.py`):
- **Provider Resolution (`app/factory.py:get_chat_model`):** Reads `LLM_PROVIDER` (default: `google_genai`) and `CHAT_MODEL` (default: `gemini-3.8-flash`). Supports Google GenAI, OpenAI, Anthropic, xAI (Grok), and local Ollama instances.
- **Embedding Resolution (`app/factory.py:get_embedding_model`):** Reads `EMBEDDING_PROVIDER` (default: `google_genai`) and `EMBEDDING_MODEL` (default: `models/gemini-embedding-2`, 3072 dimensions).
- **Instance Caching (`app/factory.py:_build_chat_model`):** Decorated with `@lru_cache(maxsize=16)` for chat models and `@lru_cache(maxsize=8)` for embeddings to prevent redundant client instantiation.
- **Dynamic Collection Isolation (`app/factory.py:get_collection_name`):** Computes ChromaDB collection names dynamically: `f"podcast_chunks_{clean_name}"` where `clean_name` strips `models/` and replaces non-alphanumeric characters with underscores. This ensures switching embedding models creates a separate isolated vector collection, preventing dimension mismatch errors.

## 3. Enterprise Approach
At enterprise scale, organizations typically deploy:
- **Centralized LLM Gateways:** LiteLLM Proxy, Portkey, Kong AI Gateway, or Cloudflare AI Gateway.
- **Dynamic Cross-Provider Failover:** Automatically routing requests to OpenAI if Google GenAI returns 429 (rate limit) or 503 (overloaded).
- **Virtual Keys and Tenant Quotas:** Enforcing per-user or per-department token spend limits and rate limits at the gateway layer.
- **Semantic Caching Layer:** Global Redis semantic caching across all enterprise applications.

## 4. Why We Didn't Need It Here, and How PodSeek Achieves the Same Intent
For a single-service free-tier deployment:
- Running an external proxy gateway container would double memory consumption and exceed Render's 512 MB container RAM limit.
- An in-repo factory pattern with `@lru_cache` achieves identical code decoupling: not a single line of agent graph code references a specific provider or model string.
- Setting `LLM_PROVIDER=ollama` or `LLM_PROVIDER=openai` in `.env` immediately shifts the entire pipeline without restarting an external proxy.

## 5. Where Our Approach Breaks Down
PodSeek's model abstraction breaks down under the following triggers:
- **Automated Fallback During 429s:** If Google GenAI encounters a rate limit (HTTP 429), the factory does not automatically retry the call against an OpenAI or Anthropic fallback key in real time.
- **Streaming Protocol Variations:** Ollama or local model providers occasionally buffer streaming chunks differently than Google GenAI, affecting frontend token delta delivery.
- **Token Usage Accounting:** The factory does not track cumulative token costs or enforce per-IP dollar caps.

## 6. Trade-Offs Accepted
- **In-Process Factory vs Dedicated Gateway:** Accepted lack of cross-provider automated failover in exchange for zero infrastructure cost and zero network proxy latency.
- **Static Configuration per Instance:** Accepted that switching models requires restarting the process with new environment variables rather than dynamic runtime request routing.
- **Provider SDK Dependencies:** Accepted bundling optional LangChain client libraries (`langchain-openai`, `langchain-anthropic`, etc.) in `requirements.txt`.

## 7. Pitfalls Encountered
- **ChromaDB Vector Dimension Crash:** In early testing, switching from Gemini embeddings (`dim=3072`) to OpenAI embeddings (`dim=1536`) caused ChromaDB to throw a fatal dimension mismatch error because both used collection name `"podcast_chunks"`. Fixed in commit `56aaa0b` by deriving the collection name from `EMBEDDING_MODEL` via `get_collection_name()`.
- **Grok / xAI Authentication:** xAI's API is OpenAI-compatible but requires a custom `base_url="https://api.x.ai/v1"` and explicit `api_key` handling. Fixed in commit `56aaa0b` by adding custom provider resolution in `_build_chat_model()`.

## 8. Next Steps (Candidate OpenSpec Changes)
- **`automatic-provider-failover`**: Add runtime try/except logic in `get_chat_model` to failover to a secondary provider when HTTP 429 or 503 is returned.
- **`token-cost-telemetry`**: Record input and output token counts in `AgentState` and surface cumulative query costs in `AskResponse`.
