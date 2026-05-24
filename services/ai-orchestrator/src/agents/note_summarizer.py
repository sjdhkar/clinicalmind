"""
NoteSummarizerAgent — nursing note NER + summarisation.

Calls HF sidecar for Bio_ClinicalBERT NER,
then summarises with GPT-4o-mini.
"""

import logging
import httpx

from src.config import Settings
from src.models.clinical_state import ClinicalState, NerEntity, NoteSummary

logger = logging.getLogger(__name__)

SUMMARISE_SYSTEM_PROMPT = """You are a clinical AI assistant summarising nursing notes.
Write a structured clinical handover summary from the notes provided.
Format: 1 paragraph covering key events, medications administered, patient status, and concerns.
Be precise and concise. Use clinical terminology. Do not invent information."""


async def _call_hf_ner(text: str, settings: Settings) -> dict:
    """Call HF sidecar /ner endpoint."""
    async with httpx.AsyncClient(timeout=settings.hf_inference_timeout_seconds) as client:
        resp = await client.post(
            f"{settings.hf_inference_url}/ner",
            json={"text": text[:4000], "min_score": 0.80},
        )
        resp.raise_for_status()
        return resp.json()


def node_note_summarizer(state: ClinicalState, settings: Settings) -> dict:
    """
    LangGraph node: summarise nursing notes for the patient.

    1. Collect nursing note chunks from retrieved context
    2. Run Bio_ClinicalBERT NER via HF sidecar
    3. Summarise with GPT-4o-mini
    """
    import asyncio

    note_chunks = [
        c for c in state["retrieved_chunks"]
        if c.source_type == "nursing_note"
    ]

    if not note_chunks:
        logger.info(f"[{state['trace_id']}] No nursing note chunks — skipping summariser")
        return {"note_summary": None}

    # Concatenate note content for NER + summarisation
    combined_text = "\n\n".join(
        f"[{c.timestamp or 'unknown time'}] {c.content}"
        for c in note_chunks
    )

    # Infer time window from chunk timestamps
    time_window_hours = 24  # default; full impl calculates from timestamps

    # Run NER
    entities: list[NerEntity] = []
    try:
        loop = asyncio.new_event_loop()
        ner_result = loop.run_until_complete(_call_hf_ner(combined_text, settings))
        loop.close()
        entities = [
            NerEntity(
                text=e["text"],
                label=e["label"],
                score=e["score"],
            )
            for e in ner_result.get("entities", [])
        ]
    except Exception as e:
        logger.warning(f"[{state['trace_id']}] NER call failed: {e}")

    # Summarise with LLM
    summary = _summarise_notes(combined_text, entities, settings, state["trace_id"])

    return {
        "note_summary": NoteSummary(
            summary=summary,
            key_entities=entities,
            time_window_hours=time_window_hours,
        )
    }


def _summarise_notes(
    text: str,
    entities: list[NerEntity],
    settings: Settings,
    trace_id: str,
) -> str:
    """Call GPT-4o-mini to summarise nursing notes."""
    try:
        from langchain_openai import AzureChatOpenAI
        from langchain_core.messages import HumanMessage, SystemMessage

        llm = AzureChatOpenAI(
            azure_deployment=settings.azure_openai_deployment_gpt4o_mini,
            azure_endpoint=settings.azure_openai_endpoint,
            api_key=settings.azure_openai_key,
            api_version=settings.azure_openai_api_version,
            temperature=0.1,
            max_tokens=400,
        )

        entity_hint = ""
        if entities:
            top_entities = [f"{e.text} ({e.label})" for e in entities[:8]]
            entity_hint = f"\nKey entities identified: {', '.join(top_entities)}"

        response = llm.invoke([
            SystemMessage(content=SUMMARISE_SYSTEM_PROMPT),
            HumanMessage(content=f"NURSING NOTES:\n{text[:3000]}{entity_hint}"),
        ])
        return str(response.content)
    except Exception as e:
        logger.warning(f"[{trace_id}] Note summarisation failed: {e}")
        # Fallback: return truncated raw text
        return f"[Summary unavailable — raw notes excerpt]: {text[:500]}..."
