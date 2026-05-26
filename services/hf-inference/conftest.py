"""
conftest.py — Mock all heavy ML dependencies before any test imports.

Unit tests mock the model instances themselves, so they never need
the actual torch/transformers/sentence-transformers packages installed.
This makes CI fast (no 2GB torch download) and dependency-free.
"""
import sys
from unittest.mock import MagicMock

# ── Mock every heavy ML package before any src.* import runs ────
HEAVY_PACKAGES = [
    # PyTorch
    "torch", "torch.nn", "torch.utils", "torch.utils.data",
    "torchvision", "torchaudio",
    # HuggingFace
    "transformers", "transformers.pipelines", "tokenizers",
    # SentenceTransformers
    "sentence_transformers",
    # Chronos
    "chronos",
    # Data science
    "pandas", "scipy", "sklearn", "sklearn.metrics",
    # OpenTelemetry (not needed for unit tests)
    "opentelemetry", "opentelemetry.api", "opentelemetry.sdk",
    "opentelemetry.instrumentation",
    "opentelemetry.instrumentation.fastapi",
    "prometheus_fastapi_instrumentator",
]

for package in HEAVY_PACKAGES:
    if package not in sys.modules:
        sys.modules[package] = MagicMock()

# Ensure torch.bfloat16 and torch.float32 are accessible as attributes
import torch  # now a MagicMock
torch.bfloat16 = "bfloat16"
torch.float32 = "float32"
torch.cuda = MagicMock()
torch.cuda.is_available = lambda: False
torch.backends = MagicMock()
torch.backends.mps = MagicMock()
torch.backends.mps.is_available = lambda: False
torch.tensor = MagicMock(return_value=MagicMock())

# Add project root to path so 'from src.xxx import' works
import os
sys.path.insert(0, os.path.dirname(__file__))
