import os
import re
from functools import lru_cache

from langchain_core.embeddings import Embeddings
from langchain_core.language_models.chat_models import BaseChatModel

DEFAULT_LLM_PROVIDER = "google_genai"
DEFAULT_CHAT_MODEL = "gemini-3.8-flash"
DEFAULT_EMBEDDING_PROVIDER = "google_genai"
DEFAULT_EMBEDDING_MODEL = "models/gemini-embedding-2"
DEFAULT_TEMPERATURE = 0.2


def get_collection_name() -> str:
    """Derive a safe, provider-specific ChromaDB collection name from the active embedding model.

    If the embedding model changes, a new isolated collection is automatically created
    to prevent vector dimension mismatch errors.
    """
    embedding_model = os.getenv("EMBEDDING_MODEL", DEFAULT_EMBEDDING_MODEL)
    clean_name = re.sub(r"[^a-zA-Z0-9_-]", "_", embedding_model.replace("models/", ""))
    return f"podcast_chunks_{clean_name}"


@lru_cache(maxsize=16)
def _build_chat_model(provider: str, model: str, temperature: float) -> BaseChatModel:
    if provider in ("google", "google_genai", "gemini"):
        from langchain_google_genai import ChatGoogleGenerativeAI

        return ChatGoogleGenerativeAI(model=model, temperature=temperature)
    elif provider == "openai":
        from langchain_openai import ChatOpenAI

        return ChatOpenAI(model=model, temperature=temperature)
    elif provider == "anthropic":
        from langchain_anthropic import ChatAnthropic

        return ChatAnthropic(model_name=model, temperature=temperature)  # type: ignore[call-arg]
    elif provider in ("xai", "grok"):
        from langchain_openai import ChatOpenAI
        from pydantic import SecretStr

        xai_api_key = os.getenv("XAI_API_KEY")
        return ChatOpenAI(
            model=model if model != DEFAULT_CHAT_MODEL else "grok-2-latest",
            api_key=SecretStr(xai_api_key) if xai_api_key else None,
            base_url="https://api.x.ai/v1",
            temperature=temperature,
        )
    elif provider == "ollama":
        from langchain_ollama import ChatOllama

        base_url = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
        return ChatOllama(model=model, base_url=base_url, temperature=temperature)
    else:
        raise ValueError(
            f"Unsupported LLM_PROVIDER: '{provider}'. "
            "Supported providers: google_genai, openai, anthropic, xai (grok), ollama."
        )


def get_chat_model(temperature: float | None = None) -> BaseChatModel:
    """Instantiate or reuse a cached chat model based on LLM_PROVIDER and CHAT_MODEL env vars."""
    provider = os.getenv("LLM_PROVIDER", DEFAULT_LLM_PROVIDER).lower()
    model = os.getenv("CHAT_MODEL", DEFAULT_CHAT_MODEL)
    if temperature is None:
        temperature = float(os.getenv("TEMPERATURE", str(DEFAULT_TEMPERATURE)))
    return _build_chat_model(provider, model, float(temperature))


@lru_cache(maxsize=8)
def _build_embedding_model(provider: str, model: str) -> Embeddings:
    if provider in ("google", "google_genai", "gemini"):
        from langchain_google_genai import GoogleGenerativeAIEmbeddings

        return GoogleGenerativeAIEmbeddings(model=model)
    elif provider == "openai":
        from langchain_openai import OpenAIEmbeddings

        return OpenAIEmbeddings(model=model)
    elif provider == "ollama":
        from langchain_ollama import OllamaEmbeddings

        base_url = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
        return OllamaEmbeddings(model=model, base_url=base_url)
    else:
        raise ValueError(
            f"Unsupported EMBEDDING_PROVIDER: '{provider}'. "
            "Supported embedding providers: google_genai, openai, ollama."
        )


def get_embedding_model() -> Embeddings:
    """Instantiate or reuse a cached embedding model based on EMBEDDING_PROVIDER and EMBEDDING_MODEL."""
    provider = os.getenv("EMBEDDING_PROVIDER", os.getenv("LLM_PROVIDER", DEFAULT_EMBEDDING_PROVIDER)).lower()
    model = os.getenv("EMBEDDING_MODEL", DEFAULT_EMBEDDING_MODEL)
    return _build_embedding_model(provider, model)
