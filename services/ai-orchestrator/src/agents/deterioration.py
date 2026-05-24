"""
DeteriorationAgent — NEWS2 early warning score calculation + risk narrative.

NEWS2 (National Early Warning Score 2) is the UK NHS standard for detecting
clinical deterioration. It scores 6 physiological parameters.
"""

import logging

from src.config import Settings
from src.models.clinical_state import (
    ClinicalState, DeteriorationAssessment, News2Score, RiskLevel,
)

logger = logging.getLogger(__name__)

DETERIORATION_SYSTEM_PROMPT = """You are a senior clinical AI assistant assessing patient deterioration risk.
You will be given a NEWS2 score breakdown and clinical context.
Provide: (1) a clinical risk narrative (2-3 sentences), and (2) a recommended action.
Be direct and clinically precise. Err on the side of caution."""


def calculate_news2(
    respiratory_rate: int | None = None,
    spo2: float | None = None,
    systolic_bp: int | None = None,
    heart_rate: int | None = None,
    consciousness: str | None = None,
    temperature: float | None = None,
) -> News2Score:
    """
    Calculate NEWS2 score from physiological parameters.

    Scoring per NEWS2 guidelines (Royal College of Physicians, 2017).
    None values are skipped (not scored).
    """
    total = 0

    # Respiratory rate (breaths/min)
    if respiratory_rate is not None:
        if respiratory_rate <= 8:
            total += 3
        elif respiratory_rate <= 11:
            total += 1
        elif respiratory_rate <= 20:
            total += 0
        elif respiratory_rate <= 24:
            total += 2
        else:
            total += 3

    # SpO2 (%)
    if spo2 is not None:
        if spo2 <= 91:
            total += 3
        elif spo2 <= 93:
            total += 2
        elif spo2 <= 95:
            total += 1
        else:
            total += 0

    # Systolic BP (mmHg)
    if systolic_bp is not None:
        if systolic_bp <= 90:
            total += 3
        elif systolic_bp <= 100:
            total += 2
        elif systolic_bp <= 110:
            total += 1
        elif systolic_bp <= 219:
            total += 0
        else:
            total += 3

    # Heart rate (bpm)
    if heart_rate is not None:
        if heart_rate <= 40:
            total += 3
        elif heart_rate <= 50:
            total += 1
        elif heart_rate <= 90:
            total += 0
        elif heart_rate <= 110:
            total += 1
        elif heart_rate <= 130:
            total += 2
        else:
            total += 3

    # Consciousness (ACVPU)
    if consciousness is not None:
        consciousness_upper = consciousness.upper()
        if consciousness_upper == "A":
            total += 0
        elif consciousness_upper in {"C", "V", "P", "U"}:
            total += 3

    # Temperature (°C)
    if temperature is not None:
        if temperature <= 35.0:
            total += 3
        elif temperature <= 36.0:
            total += 1
        elif temperature <= 38.0:
            total += 0
        elif temperature <= 39.0:
            total += 1
        else:
            total += 2

    # Risk level per NEWS2 thresholds
    if total <= 3:
        risk = RiskLevel.LOW
    elif total <= 5:
        risk = RiskLevel.MEDIUM
    elif total <= 7:
        risk = RiskLevel.HIGH
    else:
        risk = RiskLevel.CRITICAL

    return News2Score(
        total_score=total,
        risk_level=risk,
        respiratory_rate=respiratory_rate,
        spo2=spo2,
        systolic_bp=systolic_bp,
        heart_rate=heart_rate,
        consciousness=consciousness,
        temperature=temperature,
    )


def node_deterioration(state: ClinicalState, settings: Settings) -> dict:
    """
    LangGraph node: calculate NEWS2 and generate risk narrative.

    1. Extract vital parameters from observation chunks + vitals analysis
    2. Calculate NEWS2 score
    3. Generate clinical risk narrative + action via GPT-4o-mini
    """
    # Extract vitals from observation chunks
    params = _extract_vital_params(state)

    news2 = calculate_news2(**params)

    logger.info(
        f"[{state['trace_id']}] NEWS2={news2.total_score} "
        f"risk={news2.risk_level.value} patient={state['patient_id']}"
    )

    narrative, action = _generate_risk_narrative(news2, state, settings)

    return {
        "deterioration_assessment": DeteriorationAssessment(
            news2=news2,
            risk_narrative=narrative,
            recommended_action=action,
            confidence=0.85 if len(params) >= 3 else 0.5,
        )
    }


def _extract_vital_params(state: ClinicalState) -> dict:
    """Extract NEWS2 parameters from the clinical state."""
    import json, re
    params = {}

    obs_chunks = [c for c in state["retrieved_chunks"] if c.source_type == "observation"]

    for chunk in obs_chunks:
        try:
            data = json.loads(chunk.content)
            if "spo2" in data and "spo2" not in params:
                params["spo2"] = float(data["spo2"])
            if "heart_rate" in data and "heart_rate" not in params:
                params["heart_rate"] = int(data["heart_rate"])
            if "systolic_bp" in data and "systolic_bp" not in params:
                params["systolic_bp"] = int(data["systolic_bp"])
            if "respiratory_rate" in data and "respiratory_rate" not in params:
                params["respiratory_rate"] = int(data["respiratory_rate"])
            if "temperature" in data and "temperature" not in params:
                params["temperature"] = float(data["temperature"])
            if "consciousness" in data and "consciousness" not in params:
                params["consciousness"] = str(data["consciousness"])
        except (json.JSONDecodeError, ValueError, KeyError):
            pass

    # Supplement from vitals analysis if available
    if state.get("vitals_analysis") and "spo2" not in params:
        va = state["vitals_analysis"]
        if va.history:
            params["spo2"] = va.history[-1]

    return params


def _generate_risk_narrative(
    news2: News2Score,
    state: ClinicalState,
    settings: Settings,
) -> tuple[str, str]:
    """Generate clinical risk narrative and recommended action using LLM."""
    try:
        from langchain_openai import AzureChatOpenAI
        from langchain_core.messages import HumanMessage, SystemMessage
        import json

        llm = AzureChatOpenAI(
            azure_deployment=settings.azure_openai_deployment_gpt4o_mini,
            azure_endpoint=settings.azure_openai_endpoint,
            api_key=settings.azure_openai_key,
            api_version=settings.azure_openai_api_version,
            temperature=0.1,
            max_tokens=300,
        )

        context = (
            f"NEWS2 total score: {news2.total_score} ({news2.risk_level.value} risk)\n"
            f"SpO2: {news2.spo2}%\n"
            f"Heart rate: {news2.heart_rate} bpm\n"
            f"Systolic BP: {news2.systolic_bp} mmHg\n"
            f"Respiratory rate: {news2.respiratory_rate} /min\n"
            f"Temperature: {news2.temperature}°C\n"
            f"Consciousness: {news2.consciousness}"
        )

        response = llm.invoke([
            SystemMessage(content=DETERIORATION_SYSTEM_PROMPT),
            HumanMessage(
                content=f"{context}\n\n"
                        f'Respond in JSON: {{"narrative": "...", "action": "..."}}'
            ),
        ])

        parsed = json.loads(str(response.content))
        return parsed.get("narrative", ""), parsed.get("action", "")

    except Exception as e:
        logger.warning(f"[{state['trace_id']}] Risk narrative generation failed: {e}")
        action_map = {
            RiskLevel.LOW: "Continue routine monitoring. Reassess in 12 hours.",
            RiskLevel.MEDIUM: "Increase monitoring frequency. Notify shift coordinator.",
            RiskLevel.HIGH: "Urgent medical review required within 1 hour.",
            RiskLevel.CRITICAL: "IMMEDIATE medical emergency response required.",
        }
        return (
            f"NEWS2 score {news2.total_score} indicates {news2.risk_level.value} risk.",
            action_map[news2.risk_level],
        )
