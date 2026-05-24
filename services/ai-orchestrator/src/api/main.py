"""ClinicalMind AI Orchestrator — FastAPI application."""

import logging
import uuid
from contextlib import asynccontextmanager

import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from src.config import get_settings

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = get_settings()
    logger.info("Starting ClinicalMind AI Orchestrator")
    yield
    logger.info("Shutting down AI Orchestrator")


def create_app() -> FastAPI:
    app = FastAPI(
        title="ClinicalMind AI Orchestrator",
        description="LangGraph multi-agent orchestration + RAG pipeline for clinical intelligence",
        version="0.1.0",
        lifespan=lifespan,
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["http://localhost:5000", "http://api-gateway:8080"],
        allow_methods=["POST", "GET"],
        allow_headers=["*"],
    )

    from src.api.routes.chat import router as chat_router
    from src.api.routes.health import router as health_router
    from src.api.routes.ingest import router as ingest_router

    app.include_router(health_router)
    app.include_router(chat_router)
    app.include_router(ingest_router)

    return app


app = create_app()

if __name__ == "__main__":
    settings = get_settings()
    uvicorn.run("src.api.main:app", host=settings.host, port=settings.port, reload=False)
