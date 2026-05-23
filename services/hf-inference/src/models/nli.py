"""
Natural Language Inference for hallucination verification.

Model: cross-encoder/nli-deberta-v3-small
Task: Natural Language Inference (entailment / neutral / contradiction)
Use in ClinicalMind: Verify that each claim in an LLM response is supported
                     by the retrieved chunk it cites.

Labels:
  entailment   — the passage logically supports the claim
  neutral      — the passage is related but does not directly support the claim
  contradiction — the passage contradicts the claim

Threshold in ClinicalMind:
  entailment_score >= 0.70 → PASS (green badge in UI)
  entailment_score 0.40–0.69 → WARN (yellow badge — show with ⚠)
  entailment_score < 0.40 → FAIL (block response, trigger fallback)
"""

import logging
from dataclasses import dataclass
from enum import Enum

from sentence_transformers import CrossEncoder

from src.config import Settings

logger = logging.getLogger(__name__)

LABELS = ["contradiction", "entailment", "neutral"]


class NliVerdict(str, Enum):
    PASS = "pass"
    WARN = "warn"
    FAIL = "fail"


@dataclass
class NliModel:
    model: CrossEncoder
    model_id: str


@dataclass
class NliResult:
    entailment_score: float
    neutral_score: float
    contradiction_score: float
    verdict: NliVerdict
    predicted_label: str


def load_nli_model(settings: Settings, device: str) -> NliModel:
    """Load NLI cross-encoder. Called once by the registry."""
    model = CrossEncoder(
        settings.nli_model_id,
        device=device,
        cache_folder=settings.model_cache_dir,
    )
    return NliModel(model=model, model_id=settings.nli_model_id)


def verify_claim(
    model: NliModel,
    claim: str,
    passage: str,
    pass_threshold: float = 0.70,
    warn_threshold: float = 0.40,
) -> NliResult:
    """
    Verify that a claim is entailed by (supported by) a passage.

    Args:
        model: Loaded NliModel from registry
        claim: A single factual claim from the LLM response
               e.g. "Patient's SpO2 was 91% at 14:32"
        passage: The retrieved chunk that was cited for this claim
        pass_threshold: Entailment score above this → PASS
        warn_threshold: Entailment score above this (but below pass) → WARN

    Returns:
        NliResult with all three label scores and a verdict

    Note:
        The cross-encoder/nli-deberta-v3-small model expects the passage as the
        *premise* and the claim as the *hypothesis* — i.e. the pair is (passage, claim).
        This is the standard NLI direction: does the premise entail the hypothesis?
    """
    if not claim or not claim.strip():
        raise ValueError("Claim must not be empty")
    if not passage or not passage.strip():
        raise ValueError("Passage must not be empty")

    # NLI direction: premise = passage (evidence), hypothesis = claim
    scores = model.model.predict(
        [(passage, claim)],
        show_progress_bar=False,
    )[0]

    # Softmax to get probabilities
    import numpy as np
    exp_scores = np.exp(scores - np.max(scores))
    probs = exp_scores / exp_scores.sum()

    label_scores = dict(zip(LABELS, probs.tolist()))
    entailment = label_scores["entailment"]
    neutral = label_scores["neutral"]
    contradiction = label_scores["contradiction"]

    predicted_label = max(label_scores, key=label_scores.get)

    if entailment >= pass_threshold:
        verdict = NliVerdict.PASS
    elif entailment >= warn_threshold:
        verdict = NliVerdict.WARN
    else:
        verdict = NliVerdict.FAIL

    return NliResult(
        entailment_score=round(entailment, 4),
        neutral_score=round(neutral, 4),
        contradiction_score=round(contradiction, 4),
        verdict=verdict,
        predicted_label=predicted_label,
    )


def verify_claims_batch(
    model: NliModel,
    claims_and_passages: list[tuple[str, str]],
    pass_threshold: float = 0.70,
    warn_threshold: float = 0.40,
) -> list[NliResult]:
    """
    Verify multiple (claim, passage) pairs in a single batch inference call.

    More efficient than calling verify_claim() in a loop when a response
    has multiple cited claims.
    """
    if not claims_and_passages:
        return []

    import numpy as np

    # NLI direction: (passage, claim) for each pair
    pairs = [(passage, claim) for claim, passage in claims_and_passages]
    raw_scores = model.model.predict(pairs, show_progress_bar=False)

    results = []
    for scores in raw_scores:
        exp_scores = np.exp(scores - np.max(scores))
        probs = exp_scores / exp_scores.sum()
        label_scores = dict(zip(LABELS, probs.tolist()))

        entailment = label_scores["entailment"]
        neutral = label_scores["neutral"]
        contradiction = label_scores["contradiction"]
        predicted_label = max(label_scores, key=label_scores.get)

        if entailment >= pass_threshold:
            verdict = NliVerdict.PASS
        elif entailment >= warn_threshold:
            verdict = NliVerdict.WARN
        else:
            verdict = NliVerdict.FAIL

        results.append(
            NliResult(
                entailment_score=round(entailment, 4),
                neutral_score=round(neutral, 4),
                contradiction_score=round(contradiction, 4),
                verdict=verdict,
                predicted_label=predicted_label,
            )
        )

    return results
