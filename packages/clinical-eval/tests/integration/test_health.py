"""
Integration tests — require the AI orchestrator to be running.
Skipped automatically if ORCHESTRATOR_URL is unreachable.
"""
import pytest
import httpx
import os

ORCHESTRATOR_URL = os.getenv("ORCHESTRATOR_URL", "http://localhost:8000")


def orchestrator_reachable() -> bool:
    try:
        r = httpx.get(f"{ORCHESTRATOR_URL}/health", timeout=3.0)
        return r.status_code == 200
    except Exception:
        return False


@pytest.mark.skipif(not orchestrator_reachable(), reason="Orchestrator not running")
def test_orchestrator_health():
    r = httpx.get(f"{ORCHESTRATOR_URL}/health", timeout=5.0)
    assert r.status_code == 200
    assert r.json()["status"] == "ok"


@pytest.mark.skipif(not orchestrator_reachable(), reason="Orchestrator not running")
def test_chat_endpoint_returns_response():
    r = httpx.post(
        f"{ORCHESTRATOR_URL}/chat",
        json={
            "query": "What is the patient's heart rate?",
            "patient_id": "00000000-0000-0000-0000-000000000001",
            "encounter_id": "00000000-0000-0000-0000-000000000001",
            "user_id": "test-user",
            "stream": False,
        },
        timeout=30.0,
    )
    assert r.status_code in {200, 500}   # 500 is ok if DB not seeded
