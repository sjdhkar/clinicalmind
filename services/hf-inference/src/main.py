"""
ClinicalMind HuggingFace Inference Sidecar
FastAPI application entry point.
"""

import logging
from contextlib import asynccontextmanager

import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from src.config import get_settings
from src.models.registry import preload_all
from src.routes import embed, health, nli, rerank, table_qa, timeseries
from src.routes import ner as ner_router

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup / shutdown lifecycle handler."""
    settings = get_settings()
    logger.info(f"Starting ClinicalMind HF Inference Sidecar on device='{settings.device}'")

    if settings.preload_models:
        logger.info("Preloading all models (preload_models=True) ...")
        preload_all(settings)
    else:
        logger.info("Lazy loading enabled — models will load on first request")

    yield  # --- app is running ---

    logger.info("Shutting down HF Inference Sidecar")


def create_app() -> FastAPI:
    settings = get_settings()

    app = FastAPI(
        title="ClinicalMind HF Inference",
        description=(
            "Private HuggingFace inference sidecar for ClinicalMind. "
            "Serves 6 clinical AI models locally — no PHI leaves the Azure tenant."
        ),
        version="0.1.0",
        lifespan=lifespan,
        docs_url="/docs",
        redoc_url="/redoc",
    )

    # ── CORS ──────────────────────────────────────────────────
    # Only allow the API gateway (internal traffic only in production)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["http://localhost:8000", "http://api-gateway:8080"],
        allow_methods=["POST", "GET"],
        allow_headers=["*"],
    )

    # ── Routers ───────────────────────────────────────────────
    app.include_router(health.router)
    app.include_router(ner_router.router)
    app.include_router(timeseries.router)
    app.include_router(table_qa.router)
    app.include_router(rerank.router)
    app.include_router(nli.router)
    app.include_router(embed.router)

    # ── Root ─────────────────────────────────────────────────
    @app.get("/", include_in_schema=False)
    async def root():
        return JSONResponse({"service": "clinicalmind-hf-inference", "docs": "/docs"})

    return app


app = create_app()

if __name__ == "__main__":
    settings = get_settings()
    uvicorn.run(
        "src.main:app",
        host=settings.host,
        port=settings.port,
        log_level=settings.log_level,
        reload=False,  # never reload in production — reloading drops model cache
        workers=settings.workers,
    )
