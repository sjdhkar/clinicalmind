# ── Stage 1: dependency builder ─────────────────────────────────
FROM python:3.12-slim AS builder

WORKDIR /build

# Install uv for fast dependency resolution
RUN pip install --no-cache-dir uv

# Copy dependency spec only — layer is cached until pyproject.toml changes
COPY pyproject.toml .

# Install all deps into a local venv
RUN uv venv /opt/venv && \
    uv pip install --python /opt/venv/bin/python \
    fastapi uvicorn[standard] httpx pydantic pydantic-settings \
    transformers tokenizers torch sentence-transformers \
    chronos-forecasting numpy pandas \
    opentelemetry-api opentelemetry-sdk \
    opentelemetry-instrumentation-fastapi \
    prometheus-fastapi-instrumentator

# ── Stage 2: runtime image ───────────────────────────────────────
FROM python:3.12-slim AS runtime

LABEL maintainer="Srujan Dharkar <github.com/sjdhkar>"
LABEL description="ClinicalMind HF Inference Sidecar — private clinical AI models"

# Non-root user for security
RUN groupadd -r clinicalmind && useradd -r -g clinicalmind -m clinicalmind

WORKDIR /app

# Copy virtualenv from builder stage
COPY --from=builder /opt/venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Model cache directories — mounted as persistent volume in production
RUN mkdir -p /app/.cache/models && chown -R clinicalmind:clinicalmind /app

# Copy application source
COPY --chown=clinicalmind:clinicalmind src/ ./src/

# HuggingFace cache config
ENV HF_HOME=/app/.cache
ENV TRANSFORMERS_CACHE=/app/.cache/models
ENV HF_HUB_DISABLE_TELEMETRY=1
ENV TOKENIZERS_PARALLELISM=false  

# App config
ENV HOST=0.0.0.0
ENV PORT=8001
ENV LOG_LEVEL=info
ENV WORKERS=1

USER clinicalmind

EXPOSE 8001

HEALTHCHECK --interval=30s --timeout=10s --start-period=120s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8001/health')"

CMD ["python", "-m", "uvicorn", "src.main:app", \
    "--host", "0.0.0.0", \
    "--port", "8001", \
    "--workers", "1", \
    "--log-level", "info"]
