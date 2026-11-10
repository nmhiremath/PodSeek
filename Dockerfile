# Container image for the standalone FastAPI API server (`uvicorn app.api:app`).
# Note: The Render cloud deployment runs the Gradio Studio UI in-process via `python -m ui.app` (see render.yaml).
FROM python:3.13-slim

# Prevent Python from writing bytecode and buffer stdout/stderr
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PORT=8000

WORKDIR /app

# Install dependencies in a separate layer for Docker cache reuse
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Copy application code and directories
COPY app/ ./app/
COPY scripts/ ./scripts/
COPY pyproject.toml .

# Create non-root user for security and set directory permissions
RUN useradd -m -u 1000 appuser && \
    mkdir -p /app/chroma_db /app/data && \
    chown -R appuser:appuser /app

USER appuser

EXPOSE 8000

# Container health probe checking /health endpoint
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/health')" || exit 1

# Launch production server bound to all interfaces
CMD ["uvicorn", "app.api:app", "--host", "0.0.0.0", "--port", "8000"]
