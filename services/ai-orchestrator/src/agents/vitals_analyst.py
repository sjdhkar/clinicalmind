"""
VitalsAnalystAgent — vital sign time-series analysis.

Calls HF sidecar for Chronos-T5 anomaly detection,
then synthesises a clinical narrative via GPT-4o.
"""

import logging
import httpx

from src.config import Settings
from src.models.clinical_state import ClinicalState, NerEntity, VitalsAnalysis

logger = logging.getLogger(__name__)

VITALS_SYSTEM_PROMPT = """You are a clinical AI assistant analysing vital sign data.
You will be given a vital sign history, a forecast, and an anomaly score.
Write a concise (2-3 sentence) clinical narrative describing what the data shows.
Focus on clinical significance — is this trending toward deterioration?
Use precise clinical language. Do not invent values not provided."""


async def _call_hf_timeseries(
    values: list[float],
    vital_sign: str,
    settings: Settings,
) -> dict:
    """Call the HF sidecar /timeseries endpoint."""
    async with httpx.AsyncClient(timeout=settings.hf_inference_timeout_seconds) as client:
        resp = await client.post(
            f"{settings.hf_inference_url}/timeseries",
            json={"values": values, "prediction_length": 12, "vital_sign": vital_sign},
        )
        resp.raise_for_status()
        return resp.json()


def node_vitals_analyst(state: ClinicalState, settings: Settings) -> dict:
    """
    LangGraph node: analyse vital sign stream for the patient.

    1. Extract recent vital readings from retrieved chunks
    2. Call Chronos-T5 via HF sidecar
    3. Generate clinical narrative with GPT-4o
    """
    import asyncio

    # Extract vitals data from observation chunks
    obs_chunks = [
        c for c in state["retrieved_chunks"]
        if c.source_type == "observation"
    ]

    if not obs_chunks:
        logger.info(f"[{state['trace_id']}] No observation chunks — skipping vitals analysis")
        return {"vitals_analysis": None}

    # Parse SpO2 values from chunks (simplified — full impl parses archetype JSON)
    # In production: deserialise the archetype JSON and extract the specific measurement
    spo2_values = _extract_values_from_chunks(obs_chunks, "spo2")

    if len(spo2_values) < 3:
        return {"vitals_analysis": None}

    # Call HF sidecar (run async in sync context)
    try:
        loop = asyncio.new_event_loop()
        forecast_result = loop.run_until_complete(
            _call_hf_timeseries(spo2_values, "SpO2", settings)
        )
        loop.close()
    except Exception as e:
        logger.warning(f"[{state['trace_id']}] HF timeseries call failed: {e}")
        forecast_result = {
            "mean": [], "low": [], "high": [],
            "anomaly_score": 0.0, "anomaly_detected": False,
        }

    # Generate narrative with LLM
    narrative = _generate_vitals_narrative(
        vital_sign="SpO2",
        history=spo2_values,
        forecast=forecast_result,
        settings=settings,
        trace_id=state["trace_id"],
    )

    return {
        "vitals_analysis": VitalsAnalysis(
            vital_sign="SpO2",
            history=spo2_values,
            forecast_mean=forecast_result.get("mean", []),
            forecast_low=forecast_result.get("low", []),
            forecast_high=forecast_result.get("high", []),
            anomaly_score=forecast_result.get("anomaly_score", 0.0),
            anomaly_detected=forecast_result.get("anomaly_detected", False),
            narrative=narrative,
        )
    }


def _extract_values_from_chunks(chunks: list, field: str) -> list[float]:
    """
    Extract numeric values from observation chunks.
    Full implementation deserialises OpenEHR archetype JSON.
    """
    import json, re
    values = []
    for chunk in chunks:
        try:
            data = json.loads(chunk.content)
            if field in data:
                values.append(float(data[field]))
        except (json.JSONDecodeError, ValueError, KeyError):
            # Fallback: regex extract from plain text
            nums = re.findall(r'\b(\d{2,3}(?:\.\d+)?)\b', chunk.content)
            if nums:
                try:
                    values.append(float(nums[0]))
                except ValueError:
                    pass
    return values


def _generate_vitals_narrative(
    vital_sign: str,
    history: list[float],
    forecast: dict,
    settings: Settings,
    trace_id: str,
) -> str:
    """Call GPT-4o-mini to generate a clinical narrative for the vitals trend."""
    try:
        from langchain_openai import AzureChatOpenAI
        from langchain_core.messages import HumanMessage, SystemMessage

        llm = AzureChatOpenAI(
            azure_deployment=settings.azure_openai_deployment_gpt4o_mini,
            azure_endpoint=settings.azure_openai_endpoint,
            api_key=settings.azure_openai_key,
            api_version=settings.azure_openai_api_version,
            temperature=0.1,
            max_tokens=200,
        )
        user_msg = (
            f"Vital sign: {vital_sign}\n"
            f"Recent history (last {len(history)} readings): {history}\n"
            f"Forecast (next 12 steps): mean={forecast.get('mean', [])[:4]}, "
            f"anomaly_score={forecast.get('anomaly_score', 0):.2f}, "
            f"anomaly_detected={forecast.get('anomaly_detected', False)}\n\n"
            f"Write a 2-3 sentence clinical narrative."
        )
        response = llm.invoke([
            SystemMessage(content=VITALS_SYSTEM_PROMPT),
            HumanMessage(content=user_msg),
        ])
        return str(response.content)
    except Exception as e:
        logger.warning(f"[{trace_id}] Narrative generation failed: {e}")
        anomaly = forecast.get("anomaly_detected", False)
        score = forecast.get("anomaly_score", 0)
        return (
            f"{vital_sign} shows {'concerning' if anomaly else 'stable'} trend "
            f"(anomaly score: {score:.2f}). Recent readings: {history[-3:]}."
        )
