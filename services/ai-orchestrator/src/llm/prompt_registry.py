"""
Prompt Registry — versioned clinical prompts via Langfuse.

Every prompt used in ClinicalMind is:
  - Versioned (semantic version string)
  - Stored in Langfuse (when enabled) for tracing + A/B testing
  - Falls back to hardcoded defaults when Langfuse is unavailable

This means prompt changes are tracked, rollback-able, and tied to eval scores.
"""

import logging
from src.config import Settings

logger = logging.getLogger(__name__)

# ── Hardcoded prompt defaults ─────────────────────────────────────
# These are the production prompts. Langfuse overrides these when enabled.

PROMPTS: dict[str, tuple[str, str]] = {
    # (version, system_prompt)
    "clinical-synthesis": (
        "v1.2.0",
        """You are ClinicalMind, an AI clinical decision support assistant.
You help clinicians by answering questions about their patients using only
the clinical records provided to you.

STRICT RULES:
1. Answer ONLY from the context provided. Never use prior knowledge about specific patients.
2. Cite the source of every factual claim using [CHUNK-N] notation.
3. If the answer cannot be determined from the provided context, respond:
   "Insufficient data in the available records to answer this question."
4. Never invent, estimate, or extrapolate clinical values.
5. Use clear clinical language appropriate for a qualified nurse or doctor.
6. Format responses in plain prose — no markdown headers or bullet lists.

Your response must be in JSON:
{"answer": "...", "citations": ["CHUNK-1", "CHUNK-3"], "insufficient_data": false}""",
    ),
    "vitals-analysis": (
        "v1.0.1",
        """You are a clinical AI assistant specialising in vital sign analysis.
Analyse the provided vital sign data and forecast to produce a concise clinical narrative.
Focus on: trend direction, rate of change, clinical significance, and deterioration risk.
Do not invent values. Use only the numbers provided.""",
    ),
    "deterioration-risk": (
        "v1.1.0",
        """You are a senior clinical AI assistant assessing patient deterioration risk.
Given a NEWS2 score and clinical context, provide:
1. A 2-3 sentence clinical risk narrative
2. A specific recommended action (monitoring frequency, escalation, etc.)
Be direct, precise, and err on the side of caution for patient safety.""",
    ),
}


class PromptRegistry:
    def __init__(self, settings: Settings):
        self.settings = settings
        self._langfuse_client = None

        if settings.langfuse_enabled and settings.langfuse_secret_key:
            self._init_langfuse()

    def _init_langfuse(self) -> None:
        try:
            from langfuse import Langfuse
            self._langfuse_client = Langfuse(
                secret_key=self.settings.langfuse_secret_key,
                public_key=self.settings.langfuse_public_key,
                host=self.settings.langfuse_host,
            )
            logger.info("Langfuse prompt registry connected")
        except Exception as e:
            logger.warning(f"Langfuse init failed, using local prompts: {e}")

    def get_prompt(self, name: str) -> tuple[str, str]:
        """
        Get a prompt by name.

        Returns (version, system_prompt).
        Tries Langfuse first, falls back to local defaults.
        """
        if self._langfuse_client:
            try:
                prompt = self._langfuse_client.get_prompt(name)
                return prompt.version, prompt.compile()
            except Exception as e:
                logger.debug(f"Langfuse prompt fetch failed for '{name}': {e}")

        if name in PROMPTS:
            return PROMPTS[name]

        logger.warning(f"Prompt '{name}' not found, using clinical-synthesis default")
        return PROMPTS["clinical-synthesis"]

    def list_prompts(self) -> list[str]:
        return list(PROMPTS.keys())
