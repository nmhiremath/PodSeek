# Pillar 9: Reliability & Failure Modes

## 1. What This Pillar Means in Production AI Systems
Reliability in production AI systems requires engineering resilient systems that anticipate non-deterministic model behavior, third-party API outages, rate limits, corrupt inputs, and infrastructure limits. Systems must fail gracefully and predictably, maintaining service availability through defensive defaults, retries, circuit breakers, and clear user-facing error surfaces rather than crashing with unhandled exceptions.

## 2. What PodSeek Does
PodSeek implements defensive programming across all pipeline stages, prioritizing graceful degradation:
- **Batch Grading Fallback (`app/agent/nodes.py:grade_documents`):** If the LLM structured output call throws an exception or parsing fails, the node logs a warning (`logger.warning(...)`) and automatically retains all retrieved documents (`relevant_documents = list(documents)`), ensuring the request proceeds to synthesis rather than failing.
- **Streaming Fallback (`app/agent/nodes.py:generate`):** Token streaming is wrapped in a `try...except` block; if token streaming fails, the node logs a warning and falls back to synchronous `chain.invoke()`.
- **Empty Retrieval Circuit Breaker (`app/agent/graph.py`, `app/agent/nodes.py`):** If retrieval returns zero relevant documents and rewrites reach the ceiling (`rewrite_count >= max_retries`), execution routes to `generate` which safely returns a clean refusal message without spurious citations.
- **Clean API Error Mapping (`ui/client.py:_raise_clean_api_error`):** Intercepts HTTP client errors from FastAPI and extracts the `detail` message, displaying human-readable text to the user rather than raw internal `httpx` stack traces.
- **Defensive YouTube Ingestion (`app/ingestion/youtube.py`):** Channel metadata resolution and caption extraction try manual creator captions first, auto-generated captions second, and direct language fetch third, catching network errors cleanly.

### Summary Table: Failure -> Detection -> Behavior

| Failure Mode | Detection Mechanism | System Behavior |
| :--- | :--- | :--- |
| **Model Rate Limit (HTTP 429)** | Provider client raises exception | FastAPI catches exception; client logs error and surfaces rate-limit message to user. |
| **Grading Structured Output Parse Error** | `try...except Exception` in `grade_documents()` | Logs warning; falls back to treating all retrieved chunks as relevant to preserve continuity. |
| **Token Streaming Interruption** | `try...except Exception` during token iteration | Logs warning; falls back to synchronous `chain.invoke()` and emits full generation. |
| **Empty Semantic Retrieval** | `relevant_documents == []` after max retries | Router breaks loop; `generate` outputs standardized refusal without citations. |
| **Non-Huberman Ingestion Attempt** | `is_huberman_channel()` evaluates to `False` | Ingestion endpoint rejects with HTTP 400 and clear error message before downloading. |
| **Render Free-Tier Cold Start** | Initial request latency spike (> 30s) | In-process client and committed ChromaDB ensure fast initialization once container wakes. |
| **Empty or Short User Input** | Input length $< 3$ non-whitespace characters | Gradio UI disables Distill button; client validation prevents submitting query. |
| **Missing LangSmith Credentials** | `configure_tracing()` checks env vars | Automatically forces `LANGCHAIN_TRACING_V2="false"`, preventing telemetry crashes. |

## 3. Enterprise Approach
At enterprise scale, organizations deploy:
- **Resilience Engineering Middleware:** Tenacity or Resilience4j circuit breakers, exponential backoff jittered retries, and dead-letter queues.
- **Cross-Region Multi-Provider Redundancy:** Automatically switching traffic between US and EU cloud regions or from Google GenAI to Azure OpenAI on persistent 5xx errors.
- **Synthetic Canary Probes:** Scheduled automated probes making end-to-end synthetic requests every 60 seconds to detect API degradation before users do.

## 4. Why We Didn't Need It Here, and How PodSeek Achieves the Same Intent
For a focused podcast question-answering assistant running on single-container hosting:
- Defensive fallbacks inside LangGraph nodes (grading fallback to all-chunks, streaming fallback to invoke) prevent fatal request crashes without requiring distributed queueing.
- The circuit-breaker ceiling (`MAX_REWRITES = 2`) mathematically bounds worst-case execution time and token usage.
- Clean error surface mapping prevents internal framework details or API keys from being exposed in frontend error banners.

## 5. Where Our Approach Breaks Down
PodSeek's reliability architecture breaks down under the following triggers:
- **Extended Provider Outages:** If the primary LLM provider (Google AI Studio) experiences an extended regional outage, PodSeek has no automated failover to alternate cloud providers unless manually configured in `.env`.
- **YouTube Caption IP Blocking:** If YouTube aggressively rate-limits or blocks the host IP address (common on public cloud providers like Render), caption ingestion fails until fresh session cookies are mounted in `cookies.txt`.

## 6. Trade-Offs Accepted
- **Optimistic Grading Fallback vs Strict Abort:** Accepted passing all chunks to generation if grading fails, prioritizing availability over strict filtering.
- **In-Memory Fault Tolerance vs Durable Queues:** Accepted that in-flight requests during container restarts are dropped rather than replayed from a persistent queue.
- **Manual Cookie Management for Ingestion:** Accepted mounting `cookies.txt` when cloud IPs are throttled rather than maintaining a rotating residential proxy pool.

## 7. Pitfalls Encountered
- **Bare `except Exception` in Handlers:** Early code used bare exception handlers that swallowed unexpected bugs. Fixed in commit `d4c0068` by replacing bare exceptions with specific error types or contextual logging across grading, generation, and cache paths.
- **Mobile Drawer Freezing:** The mobile drawer UI occasionally initialized in an open state, blocking interaction. Fixed in commit `d4c0068` by enforcing a closed state on initial load (`c6c175a`).

## 8. Next Steps (Candidate OpenSpec Changes)
- `exponential-backoff-model-retries`: Wrap LLM provider calls in jittered exponential backoff retries using Tenacity.
- `caption-fetch-proxy-support`: Add optional HTTP proxy configuration for `app/ingestion/youtube.py` to bypass public cloud IP throttles on YouTube.
