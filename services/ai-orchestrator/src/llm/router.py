"""
Model Router — dynamic LLM selection based on query complexity.

Tier 1: phi-3-mini  — simple lookups, < 500 tokens  (~$0.00/query local)
Tier 2: gpt-4o-mini — summarisation, analysis       (~$0.0004/query)
Tier 3: gpt-4o      — complex reasoning, synthesis  (~$0.005/query)

Expected distribution: 38% / 41% / 21% → ~76% cost saving vs all-GPT-4o.
"""

import logging
from src.config import Settings
from src.models.clinical_state import QueryType

logger = logging.getLogger(__name__)

SIMPLE_QUERY_TYPES = {QueryType.EVIDENCE_LOOKUP}
COMPLEX_QUERY_TYPES = {QueryType.DETERIORATION_RISK}


class ModelRouter:
    def __init__(self, settings: Settings):
        self.settings = settings

    def route(self, estimated_tokens: int, query_type: QueryType) -> str:
        """
        Select the appropriate model for this query.

        Decision logic:
        1. DETERIORATION_RISK always gets GPT-4o (clinical safety)
        2. Below phi3 threshold AND simple type → phi-3-mini
        3. Below gpt4o-mini threshold → gpt-4o-mini
        4. Default → gpt-4o
        """
        s = self.settings

        if query_type in COMPLEX_QUERY_TYPES:
            model = "gpt-4o"
        elif (
            estimated_tokens < s.router_phi3_max_tokens
            and query_type in SIMPLE_QUERY_TYPES
        ):
            model = "phi-3-mini"
        elif estimated_tokens < s.router_gpt4o_mini_max_tokens:
            model = "gpt-4o-mini"
        else:
            model = "gpt-4o"

        logger.debug(
            f"Model routing: tokens={estimated_tokens} "
            f"query_type={query_type} → {model}"
        )
        return model

    def estimate_cost_usd(self, model: str, prompt_tokens: int, completion_tokens: int) -> float:
        """Estimate cost in USD for a single call. Used for cost tracking."""
        pricing = {
            # Per 1M tokens (input / output)
            "gpt-4o":      (5.00, 15.00),
            "gpt-4o-mini": (0.15, 0.60),
            "phi-3-mini":  (0.00, 0.00),  # local inference
        }
        input_price, output_price = pricing.get(model, (5.00, 15.00))
        return (
            (prompt_tokens / 1_000_000) * input_price
            + (completion_tokens / 1_000_000) * output_price
        )
