"""
ClinicalMind Demo API
=====================
Lightweight FastAPI service for the live demo deployment.

This is NOT the full production orchestrator — it's a demo-grade backend that:
  - Accepts the same API contracts as the full orchestrator
  - Calls Azure OpenAI with pre-seeded clinical context
  - Streams responses via SSE (same format as production)
  - Returns realistic RAGAS eval metrics
  - Requires NO database, NO Redis, NO HuggingFace models

Deploy this on Render (free tier) alongside the Angular frontend.
The full production stack uses the services/ai-orchestrator/ service.
"""

import json
import os
import uuid
from datetime import datetime

import httpx
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

app = FastAPI(title="ClinicalMind Demo API", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],   # demo only — restrict in production
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Config ────────────────────────────────────────────────────────
AZURE_OPENAI_ENDPOINT = os.getenv("AZURE_OPENAI_ENDPOINT", "")
AZURE_OPENAI_KEY = os.getenv("AZURE_OPENAI_KEY", "")
AZURE_OPENAI_DEPLOYMENT = os.getenv("AZURE_OPENAI_DEPLOYMENT", "gpt-4o-mini")
AZURE_OPENAI_API_VERSION = os.getenv("AZURE_OPENAI_API_VERSION", "2024-08-01-preview")

# ── Demo patient data (pre-seeded, no DB needed) ─────────────────
DEMO_PATIENTS = {
    "p001": {
        "name": "J. Smith",
        "bed": "A-12",
        "news2": 7,
        "risk": "high",
        "vitals": "SpO2 91-93%, HR 112 bpm, RR 24/min, BP 105/68 mmHg, Temp 38.2°C",
        "notes": "Patient admitted with shortness of breath. SpO2 declining despite 2L/min O2. "
                 "Blood cultures taken. Dr Ahmed notified. Paracetamol 1g IV given at 08:15.",
    },
    "p002": {
        "name": "M. Patel",
        "bed": "A-14",
        "news2": 2,
        "risk": "low",
        "vitals": "SpO2 97%, HR 78 bpm, RR 16/min, BP 122/80 mmHg, Temp 37.0°C",
        "notes": "Patient stable overnight. Metformin 500mg given with breakfast. Mobilising independently.",
    },
    "p003": {
        "name": "R. Kumar",
        "bed": "B-03",
        "news2": 4,
        "risk": "medium",
        "vitals": "SpO2 95%, HR 92 bpm, RR 19/min, BP 110/72 mmHg, Temp 37.8°C",
        "notes": "Post-appendectomy day 2. Wound site clean. Pain 3/10 on oral analgesia. "
                 "Tolerating light diet. Physiotherapy reviewed.",
    },
    "p004": {
        "name": "S. Jones",
        "bed": "B-07",
        "news2": 9,
        "risk": "critical",
        "vitals": "SpO2 92%, HR 118 bpm, RR 26/min, BP 88/54 mmHg, Temp 39.1°C",
        "notes": "Suspected sepsis. Sepsis 6 commenced: high-flow O2, blood cultures x2, "
                 "IV Tazocin 4.5g, 500ml fluid bolus. Lactate 3.2 mmol/L. ICU reviewing.",
    },
}

CLINICAL_PROTOCOLS = """
NEWS2 Escalation: Score 0-4 = low risk (12h monitoring). Score 5-6 = medium (4h monitoring, 
medical review). Score 7+ = high risk (continuous monitoring, urgent medical review).

Sepsis 6 Bundle (within 1 hour): High-flow oxygen, blood cultures x2, IV broad-spectrum 
antibiotics, IV fluid challenge 500ml crystalloid, serum lactate, urine output monitoring.

SpO2 targets: 94-98% for most patients. 88-92% for COPD patients (hypercapnic risk).
"""


# ── Request models ────────────────────────────────────────────────

class ChatRequest(BaseModel):
    query: str
    patient_id: str = "p001"
    encounter_id: str = "enc-001"
    user_id: str = "demo-user"
    stream: bool = True


# ── Endpoints ─────────────────────────────────────────────────────

@app.get("/health")
def health():
    return {"status": "ok", "service": "clinicalmind-demo-api", "timestamp": datetime.utcnow().isoformat()}


@app.get("/api/patients")
def get_patients():
    return [
        {
            "patientId": pid,
            "patientName": data["name"],
            "wardBed": data["bed"],
            "news2Score": data["news2"],
            "riskLevel": data["risk"],
            "lastUpdated": datetime.utcnow().isoformat(),
            "anomalyDetected": data["news2"] >= 7,
        }
        for pid, data in DEMO_PATIENTS.items()
    ]


@app.get("/api/eval/metrics")
def get_eval_metrics():
    return [
        {"date": "2025-05-24", "faithfulness": 0.91, "answerRelevancy": 0.88,
         "contextPrecision": 0.87, "hallucination_rate": 0.028, "p95LatencyMs": 3400, "costPerQuery": 0.0021},
        {"date": "2025-05-23", "faithfulness": 0.91, "answerRelevancy": 0.88,
         "contextPrecision": 0.86, "hallucination_rate": 0.029, "p95LatencyMs": 3450, "costPerQuery": 0.0022},
        {"date": "2025-05-22", "faithfulness": 0.90, "answerRelevancy": 0.87,
         "contextPrecision": 0.85, "hallucination_rate": 0.031, "p95LatencyMs": 3600, "costPerQuery": 0.0023},
        {"date": "2025-05-21", "faithfulness": 0.89, "answerRelevancy": 0.86,
         "contextPrecision": 0.84, "hallucination_rate": 0.034, "p95LatencyMs": 3700, "costPerQuery": 0.0024},
        {"date": "2025-05-20", "faithfulness": 0.87, "answerRelevancy": 0.84,
         "contextPrecision": 0.83, "hallucination_rate": 0.041, "p95LatencyMs": 4100, "costPerQuery": 0.0027},
    ]


@app.post("/api/chat/stream")
async def chat_stream(request: ChatRequest):
    """Stream an AI response via SSE."""
    patient = DEMO_PATIENTS.get(request.patient_id, DEMO_PATIENTS["p001"])
    trace_id = str(uuid.uuid4())

    return StreamingResponse(
        _stream_response(request.query, patient, trace_id),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        }
    )


async def _stream_response(query: str, patient: dict, trace_id: str):
    """Generate SSE events from Azure OpenAI."""
    # Start event
    yield f"event: start\ndata: {json.dumps({'trace_id': trace_id})}\n\n"

    # Build grounded prompt
    system_prompt = f"""You are ClinicalMind, an AI clinical decision support assistant.
Answer ONLY from the patient context below. Cite sources as [OBS-1], [NOTE-1], or [PROTOCOL-1].
If you cannot answer from context, say "Insufficient data in the available records."
Be concise and clinically precise."""

    user_prompt = f"""PATIENT CONTEXT:
[OBS-1] Current vitals: {patient['vitals']}
[NOTE-1] Nursing notes: {patient['notes']}
[PROTOCOL-1] Clinical protocols: {CLINICAL_PROTOCOLS}

QUESTION: {query}

Answer concisely (2-3 sentences). Include relevant NEWS2 scoring if applicable."""

    # Call Azure OpenAI (streaming)
    if AZURE_OPENAI_KEY and AZURE_OPENAI_ENDPOINT:
        url = (f"{AZURE_OPENAI_ENDPOINT}openai/deployments/{AZURE_OPENAI_DEPLOYMENT}"
               f"/chat/completions?api-version={AZURE_OPENAI_API_VERSION}")

        async with httpx.AsyncClient(timeout=60) as client:
            async with client.stream("POST", url,
                headers={"api-key": AZURE_OPENAI_KEY, "Content-Type": "application/json"},
                json={
                    "messages": [
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_prompt},
                    ],
                    "stream": True,
                    "max_tokens": 300,
                    "temperature": 0.1,
                }
            ) as response:
                async for line in response.aiter_lines():
                    if line.startswith("data: ") and line != "data: [DONE]":
                        try:
                            chunk = json.loads(line[6:])
                            token = chunk["choices"][0]["delta"].get("content", "")
                            if token:
                                yield f"event: token\ndata: {token}\n\n"
                        except (json.JSONDecodeError, KeyError):
                            pass
    else:
        # Fallback: pre-written demo response (no Azure key needed)
        demo_response = _get_demo_response(query, patient)
        for word in demo_response.split():
            yield f"event: token\ndata: {word} \n\n"

    # Citation event
    yield f"event: citation\ndata: {json.dumps({'chunk_id': 'obs-001', 'source_type': 'observation', 'timestamp': '2025-05-24T14:32:00Z', 'score': 0.91})}\n\n"
    yield f"event: citation\ndata: {json.dumps({'chunk_id': 'note-001', 'source_type': 'nursing_note', 'timestamp': '2025-05-24T08:15:00Z', 'score': 0.87})}\n\n"

    # Metadata event
    yield f"event: metadata\ndata: {json.dumps({'agents_used': ['vitals_analyst', 'evidence_retrieval'], 'model_used': 'gpt-4o-mini', 'prompt_version': 'v1.2.0', 'insufficient_data': False, 'citation_count': 2})}\n\n"

    yield "event: done\ndata: \n\n"


def _get_demo_response(query: str, patient: dict) -> str:
    """Pre-written responses when no Azure OpenAI key is configured."""
    q = query.lower()
    vitals = patient["vitals"]
    news2 = patient["news2"]

    if any(w in q for w in ["spo2", "oxygen", "saturation"]):
        return (f"Based on [OBS-1], the patient's current SpO2 is within the documented vital signs: {vitals}. "
                f"The NEWS2 score of {news2} reflects the current clinical picture and warrants appropriate monitoring.")

    if any(w in q for w in ["news2", "risk", "deteriorat", "escalat"]):
        risk_map = {0: "low", 1: "low", 2: "low", 3: "medium", 4: "medium",
                    5: "medium", 6: "medium", 7: "high", 8: "high", 9: "critical", 10: "critical"}
        risk = risk_map.get(news2, "high")
        action = "Continuous monitoring and urgent medical review" if news2 >= 7 else "Increase monitoring frequency"
        return (f"The current NEWS2 score is {news2}, indicating {risk} clinical risk [OBS-1]. "
                f"{action} is indicated per escalation protocol [PROTOCOL-1].")

    if any(w in q for w in ["note", "nursing", "summary", "handover"]):
        return f"Per [NOTE-1]: {patient['notes']}"

    if any(w in q for w in ["sepsis", "infection", "antibiotic"]):
        return ("The Sepsis 6 bundle should be completed within 1 hour of recognition: "
                "high-flow oxygen, blood cultures x2, IV antibiotics, 500ml fluid challenge, "
                "serum lactate, and urine output monitoring [PROTOCOL-1].")

    return (f"Based on the available clinical records [OBS-1][NOTE-1], the patient's current status is: "
            f"{vitals}. NEWS2 score is {news2}. {patient['notes'][:100]}...")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
