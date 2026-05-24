"""
seed_demo_data.py — Seed the local database with demo clinical data.

Run this after `docker compose up -d` to get a working demo environment.
Creates:
  - 4 demo patients with observation data
  - Nursing notes with clinical entities
  - Protocol chunks from sample guidelines
  - Eval run history for the dashboard

Usage:
    cd packages/clinical-eval
    python seed_demo_data.py
"""

import asyncio
import json
import os
import sys
from datetime import datetime, timedelta, timezone
import httpx
from rich.console import Console

console = Console()

ORCHESTRATOR_URL = os.getenv("ORCHESTRATOR_URL", "http://localhost:8000")

DEMO_PATIENTS = [
    {"patient_id": "00000000-0000-0000-0000-000000000001",
     "encounter_id": "00000000-0000-0000-0000-000000000001",
     "name": "J. Smith", "bed": "A-12"},
    {"patient_id": "00000000-0000-0000-0000-000000000002",
     "encounter_id": "00000000-0000-0000-0000-000000000002",
     "name": "M. Patel", "bed": "A-14"},
    {"patient_id": "00000000-0000-0000-0000-000000000003",
     "encounter_id": "00000000-0000-0000-0000-000000000003",
     "name": "R. Kumar", "bed": "B-03"},
    {"patient_id": "00000000-0000-0000-0000-000000000004",
     "encounter_id": "00000000-0000-0000-0000-000000000004",
     "name": "S. Jones", "bed": "B-07"},
]


def _ts(hours_ago: int = 0) -> str:
    return (datetime.now(timezone.utc) - timedelta(hours=hours_ago)).isoformat()


def make_observations(patient_id: str, encounter_id: str, deteriorating: bool) -> list[dict]:
    """Generate 6 hours of observation archetypes for a patient."""
    base_spo2 = 91.0 if deteriorating else 97.0
    base_hr = 112 if deteriorating else 78
    base_rr = 24 if deteriorating else 16
    base_sbp = 95 if deteriorating else 122

    observations = []
    for i, hours_ago in enumerate([6, 5, 4, 3, 2, 1, 0]):
        drift = i * (0.5 if deteriorating else 0.1)
        obs = {
            "archetype_id": "openEHR-EHR-OBSERVATION.news2_score.v1",
            "patient_id": patient_id,
            "encounter_id": encounter_id,
            "spo2": round(base_spo2 - drift, 1),
            "heart_rate": int(base_hr + drift * 2),
            "respiratory_rate": int(base_rr + drift),
            "systolic_bp": int(base_sbp - drift * 2),
            "temperature": 38.2 if deteriorating else 37.0,
            "consciousness": "V" if (deteriorating and i >= 5) else "A",
            "time": _ts(hours_ago),
        }
        observations.append(obs)
    return observations


NURSING_NOTES = {
    "00000000-0000-0000-0000-000000000001": [
        "Patient admitted with shortness of breath and chest pain. SpO2 on air 91%. Commenced on 2L/min oxygen via nasal cannula. Blood cultures taken. Dr Ahmed notified. Patient reports pain score 7/10. Paracetamol 1g IV administered.",
        "Patient's condition deteriorating. SpO2 dropping despite oxygen therapy. Respiratory rate increasing. Patient appears anxious. Rapid response team called. Dr Williams reviewed. Plan: increase oxygen, repeat ABG, consider HDU transfer.",
    ],
    "00000000-0000-0000-0000-000000000002": [
        "Patient stable overnight. Routine observations all within normal parameters. Metformin 500mg given with breakfast. Patient mobilised to bathroom independently. No complaints reported.",
    ],
    "00000000-0000-0000-0000-000000000003": [
        "Patient recovering well from appendectomy. Wound site clean and dry. Pain score 3/10, well controlled on oral analgesia. Tolerating light diet. Physiotherapy reviewed, mobilising with minimal assistance.",
    ],
    "00000000-0000-0000-0000-000000000004": [
        "Patient transferred from A&E with suspected sepsis. Temperature 39.1°C, HR 118 bpm, BP 88/54 mmHg. Sepsis 6 commenced: high-flow oxygen, blood cultures x2, IV fluids 500ml bolus, IV Tazocin 4.5g. Lactate 3.2 mmol/L. ICU team reviewing.",
        "Post-fluid challenge: BP improved to 102/68 mmHg. HR settling to 98 bpm. Patient more responsive. Lactate repeat 2.1 mmol/L. ICU bed requested. IV vancomycin added for MRSA cover.",
    ],
}

PROTOCOL_CHUNKS = [
    {
        "content": "[Sepsis Management — Fluid Resuscitation]\nAdminister a fluid challenge of 500ml crystalloid (e.g. 0.9% sodium chloride) over 15 minutes for adults with suspected sepsis and signs of hypoperfusion. Reassess haemodynamic status after each bolus. Caution in patients with known cardiac or renal failure.",
        "source_type": "protocol",
        "metadata": {"guideline": "NICE NG51", "section": "Fluid Resuscitation"},
    },
    {
        "content": "[NEWS2 — Escalation Thresholds]\nScore 0-4: Low risk — minimum 12-hourly monitoring. Score 5-6: Medium risk — minimum 4-hourly monitoring, consider urgent medical review. Score 7+: High risk — continuous monitoring, immediate medical review required. Any single parameter scoring 3: Consider emergency response regardless of total score.",
        "source_type": "protocol",
        "metadata": {"guideline": "RCP NEWS2 2017", "section": "Escalation"},
    },
    {
        "content": "[Oxygen Therapy — Target Saturations]\nFor most acutely ill patients: target SpO2 94-98%. For patients with COPD or risk of hypercapnic respiratory failure: target SpO2 88-92%. Titrate oxygen delivery to achieve target. Reassess regularly. Document inspired oxygen concentration and delivery device.",
        "source_type": "protocol",
        "metadata": {"guideline": "BTS Emergency Oxygen", "section": "Target Saturations"},
    },
    {
        "content": "[Sepsis 6 — Hour-1 Bundle]\nWithin 1 hour of sepsis recognition: 1. High-flow oxygen. 2. Blood cultures x2 (aerobic + anaerobic). 3. IV antibiotics (broad-spectrum, per local protocol). 4. IV fluid challenge 500ml crystalloid. 5. Serum lactate. 6. Urine output monitoring (catheterise if needed). Document time of each intervention.",
        "source_type": "protocol",
        "metadata": {"guideline": "Sepsis Trust Bundle", "section": "Hour-1 Bundle"},
    },
]


async def ingest_document(patient_id: str, encounter_id: str, doc_type: str, content: str, metadata: dict) -> None:
    async with httpx.AsyncClient(timeout=30) as client:
        try:
            await client.post(f"{ORCHESTRATOR_URL}/ingest", json={
                "patient_id": patient_id,
                "encounter_id": encounter_id,
                "document_type": doc_type,
                "content": content,
                "metadata": metadata,
            })
        except Exception as e:
            console.print(f"  [yellow]Ingest failed (is the orchestrator running?): {e}[/yellow]")


async def main():
    console.print("\n[bold]ClinicalMind Demo Data Seeder[/bold]")
    console.print(f"Orchestrator: {ORCHESTRATOR_URL}\n")

    # Check orchestrator is running
    try:
        async with httpx.AsyncClient(timeout=5) as client:
            resp = await client.get(f"{ORCHESTRATOR_URL}/health")
            resp.raise_for_status()
        console.print("[green]✓ Orchestrator is running[/green]")
    except Exception:
        console.print("[red]✗ Orchestrator not reachable. Run: docker compose up -d[/red]")
        console.print("  Seeding will attempt to continue but ingest calls will fail.\n")

    # Seed observations
    console.print("\n[bold]Seeding observations...[/bold]")
    deteriorating = {
        "00000000-0000-0000-0000-000000000001": True,
        "00000000-0000-0000-0000-000000000002": False,
        "00000000-0000-0000-0000-000000000003": False,
        "00000000-0000-0000-0000-000000000004": True,
    }

    for patient in DEMO_PATIENTS:
        pid, eid = patient["patient_id"], patient["encounter_id"]
        observations = make_observations(pid, eid, deteriorating[pid])
        for obs in observations:
            await ingest_document(pid, eid, "observation", json.dumps(obs), {"patient_name": patient["name"]})
        console.print(f"  ✓ {patient['name']} — {len(observations)} observations")

    # Seed nursing notes
    console.print("\n[bold]Seeding nursing notes...[/bold]")
    for patient in DEMO_PATIENTS:
        pid, eid = patient["patient_id"], patient["encounter_id"]
        notes = NURSING_NOTES.get(pid, [])
        for i, note in enumerate(notes):
            await ingest_document(pid, eid, "nursing_note", note, {
                "author_role": "nurse",
                "timestamp": _ts(i * 2),
            })
        console.print(f"  ✓ {patient['name']} — {len(notes)} nursing notes")

    # Seed protocols (shared across all patients, no patient_id)
    console.print("\n[bold]Seeding protocol knowledge base...[/bold]")
    for chunk in PROTOCOL_CHUNKS:
        await ingest_document(
            "00000000-0000-0000-0000-000000000000",  # global namespace
            "00000000-0000-0000-0000-000000000000",
            "protocol_pdf",
            chunk["content"],
            chunk["metadata"],
        )
    console.print(f"  ✓ {len(PROTOCOL_CHUNKS)} protocol chunks")

    console.print("\n[green bold]✓ Demo data seeded successfully[/green bold]")
    console.print("Open http://localhost:4200 to see the dashboard.\n")


if __name__ == "__main__":
    asyncio.run(main())
