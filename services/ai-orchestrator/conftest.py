"""
conftest.py — Mock all heavy dependencies before any test imports.
AI orchestrator unit tests need no LLM, no database, no Redis.
"""
import sys
from unittest.mock import MagicMock

HEAVY_PACKAGES = [
    # LangChain / LangGraph
    "langgraph", "langgraph.graph", "langgraph.graph.message",
    "langchain", "langchain.schema", "langchain_core",
    "langchain_core.messages", "langchain_core.output_parsers",
    "langchain_openai",
    # LlamaIndex
    "llama_index", "llama_index.core", "llama_index.vector_stores",
    "llama_index.embeddings",
    # Database
    "asyncpg", "sqlalchemy", "sqlalchemy.ext.asyncio",
    "sqlalchemy.orm", "sqlalchemy",
    "pgvector",
    # Redis
    "redis",
    # LLMOps
    "langfuse",
    # OpenTelemetry
    "opentelemetry", "opentelemetry.api", "opentelemetry.sdk",
    "opentelemetry.instrumentation",
    "opentelemetry.instrumentation.fastapi",
    # SSE
    "sse_starlette",
    # Tiktoken
    "tiktoken",
]

for package in HEAVY_PACKAGES:
    if package not in sys.modules:
        sys.modules[package] = MagicMock()

# Add project root to path
import os
sys.path.insert(0, os.path.dirname(__file__))

# LangGraph StateGraph needs special treatment since it's used as a decorator
from unittest.mock import MagicMock
langgraph_mock = sys.modules["langgraph"]
langgraph_mock.graph = MagicMock()

# Make TypedDict work (it's from typing, not mocked)
from typing import TypedDict  # noqa: F401
