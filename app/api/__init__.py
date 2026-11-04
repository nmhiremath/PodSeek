"""FastAPI application initialization for PodSeek."""

from fastapi import FastAPI

from app.api.routes import router
from app.observability import configure_tracing

app = FastAPI(
    title="PodSeek API",
    description="Corrective RAG Chatbot indexing podcast transcripts with clickable timestamp citations.",
    version="0.1.0",
)

app.include_router(router)

# Dotenv has already been loaded by the vector store import inside the router.
# Tracing stays off unless LANGCHAIN_TRACING_V2 and LANGCHAIN_API_KEY are both set.
configure_tracing()

__all__ = ["app"]
