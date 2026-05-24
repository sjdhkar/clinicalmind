FROM python:3.12-slim AS builder
WORKDIR /build
RUN pip install --no-cache-dir uv
COPY pyproject.toml .
RUN uv venv /opt/venv && \
    uv pip install --python /opt/venv/bin/python \
    fastapi uvicorn[standard] httpx sse-starlette pydantic pydantic-settings \
    langgraph langchain langchain-openai langchain-core \
    llama-index llama-index-vector-stores-postgres \
    asyncpg sqlalchemy pgvector redis langfuse \
    opentelemetry-api opentelemetry-sdk \
    opentelemetry-instrumentation-fastapi \
    numpy tiktoken

FROM python:3.12-slim AS runtime
LABEL maintainer="Srujan Dharkar <github.com/sjdhkar>"
RUN groupadd -r clinicalmind && useradd -r -g clinicalmind -m clinicalmind
WORKDIR /app
COPY --from=builder /opt/venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"
RUN mkdir -p /app && chown -R clinicalmind:clinicalmind /app
COPY --chown=clinicalmind:clinicalmind src/ ./src/
ENV HOST=0.0.0.0 PORT=8000 LOG_LEVEL=info
USER clinicalmind
EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=10s --start-period=30s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/health')"
CMD ["python", "-m", "uvicorn", "src.api.main:app", "--host", "0.0.0.0", "--port", "8000"]
