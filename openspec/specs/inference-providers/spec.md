# Capability Specification: Inference Providers

## Purpose
The inference providers capability provides an isolated abstraction layer and factory pattern for instantiating chat and embedding models across Google GenAI, OpenAI, Anthropic, xAI (Grok), and local Ollama instances, while ensuring vector dimension safety across model switches.

## Requirements

### Requirement: Pluggable Chat Model Factory
The system SHALL instantiate the configured chat model based on the `LLM_PROVIDER` and `CHAT_MODEL` environment variables with LRU caching.

#### Scenario: Google GenAI chat model instantiation
- **WHEN** `LLM_PROVIDER` is `"google_genai"` (or `"google"`, `"gemini"`)
- **THEN** `get_chat_model()` instantiates `ChatGoogleGenerativeAI` with the specified `CHAT_MODEL` (default: `gemini-3.8-flash`) and temperature.

#### Scenario: OpenAI, Anthropic, xAI, or Ollama chat model instantiation
- **WHEN** `LLM_PROVIDER` is set to `"openai"`, `"anthropic"`, `"xai"` / `"grok"`, or `"ollama"`
- **THEN** `get_chat_model()` instantiates the corresponding LangChain chat model wrapper with appropriate credentials and endpoint configuration.

#### Scenario: Unsupported LLM provider error
- **WHEN** an unrecognized `LLM_PROVIDER` string is provided
- **THEN** `get_chat_model()` raises a `ValueError` listing the supported providers.

### Requirement: Pluggable Embedding Model Factory
The system SHALL instantiate the configured text embedding provider based on `EMBEDDING_PROVIDER` and `EMBEDDING_MODEL` with LRU caching.

#### Scenario: Default Gemini embedding model instantiation
- **WHEN** `EMBEDDING_PROVIDER` is `"google_genai"`
- **THEN** `get_embedding_model()` instantiates `GoogleGenerativeAIEmbeddings` with `EMBEDDING_MODEL` (default: `models/gemini-embedding-2`).

### Requirement: Safe Dynamic Collection Naming
The system SHALL derive ChromaDB collection names dynamically from the active embedding model name to avoid vector dimension mismatches.

#### Scenario: Embedding model switch
- **WHEN** `get_collection_name()` is called
- **THEN** it reads `EMBEDDING_MODEL` (default: `models/gemini-embedding-2`)
- **AND** strips `models/` and replaces non-alphanumeric characters with underscores
- **AND** returns the collection name formatted as `podcast_chunks_<clean_name>` (e.g. `podcast_chunks_gemini-embedding-2`).
