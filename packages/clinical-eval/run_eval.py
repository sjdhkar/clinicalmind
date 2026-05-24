"""
RAGAS Evaluation Runner — ClinicalMind golden set evaluation.

Usage:
    python run_eval.py --golden-set data/golden_set_200.json --output results/latest.json
    python run_eval.py --golden-set data/golden_set_200.json --output results/latest.json --upload-langfuse

What it does:
    1. Loads the golden set (Q&A scenarios with context + ground truth)
    2. Calls the running AI orchestrator /chat endpoint for each scenario
    3. Scores responses using RAGAS metrics
    4. Computes custom clinical metrics (NEWS2 agreement, hallucination rate)
    5. Writes results to JSON + optional Langfuse upload
    6. Prints a rich summary table to stdout
"""

import argparse
import json
import os
import sys
import time
import uuid
from dataclasses import dataclass, asdict
from pathlib import Path
from datetime import date

import httpx
import numpy as np
from rich.console import Console
from rich.table import Table
from rich import print as rprint

console = Console()


# ── Config ────────────────────────────────────────────────────────

ORCHESTRATOR_URL = os.getenv("ORCHESTRATOR_URL", "http://localhost:8000")
AZURE_OPENAI_ENDPOINT = os.getenv("AZURE_OPENAI_ENDPOINT", "")
AZURE_OPENAI_KEY = os.getenv("AZURE_OPENAI_KEY", "")

DEMO_PATIENT_ID = "00000000-0000-0000-0000-000000000001"
DEMO_ENCOUNTER_ID = "00000000-0000-0000-0000-000000000001"


# ── Data models ───────────────────────────────────────────────────

@dataclass
class Scenario:
    id: str
    category: str
    question: str
    context: str
    ground_truth: str
    news2_relevant: bool


@dataclass
class ScenarioResult:
    scenario_id: str
    category: str
    question: str
    ground_truth: str
    actual_answer: str
    faithfulness: float
    answer_relevancy: float
    context_precision: float
    context_recall: float
    hallucination_flag: bool
    news2_agreement: bool | None
    latency_ms: float
    model_used: str
    passed: bool


@dataclass
class EvalRunResult:
    run_date: str
    git_sha: str
    scenario_count: int
    faithfulness: float
    answer_relevancy: float
    context_precision: float
    context_recall: float
    hallucination_rate: float
    news2_agreement: float
    p95_latency_ms: float
    avg_cost_usd: float
    cache_hit_rate: float
    passed_thresholds: bool
    scenario_results: list[dict]


# ── Thresholds (must match check_thresholds.py) ───────────────────

THRESHOLDS = {
    "faithfulness":       0.85,
    "answer_relevancy":   0.80,
    "context_precision":  0.80,
    "context_recall":     0.75,
    "hallucination_rate": 0.05,
    "news2_agreement":    0.90,
}


# ── Core evaluation functions ─────────────────────────────────────

def load_golden_set(path: Path) -> list[Scenario]:
    with open(path) as f:
        raw = json.load(f)
    return [Scenario(**s) for s in raw]


def call_orchestrator(scenario: Scenario) -> tuple[str, float, str]:
    """
    Call the AI orchestrator /chat endpoint for a scenario.
    Returns (answer, latency_ms, model_used).
    """
    start = time.perf_counter()
    try:
        resp = httpx.post(
            f"{ORCHESTRATOR_URL}/chat",
            json={
                "query": scenario.question,
                "patient_id": DEMO_PATIENT_ID,
                "encounter_id": DEMO_ENCOUNTER_ID,
                "user_id": "eval-pipeline",
                "stream": False,
            },
            timeout=60.0,
        )
        resp.raise_for_status()
        data = resp.json()
        latency = (time.perf_counter() - start) * 1000
        return data.get("answer", ""), latency, data.get("model_used", "unknown")
    except Exception as e:
        latency = (time.perf_counter() - start) * 1000
        console.print(f"[red]Orchestrator call failed for {scenario.id}: {e}[/red]")
        return "", latency, "error"


def score_with_ragas(
    question: str,
    answer: str,
    context: str,
    ground_truth: str,
) -> dict[str, float]:
    """
    Score a single Q&A pair using RAGAS metrics.
    Falls back to heuristic scoring if RAGAS / OpenAI is unavailable.
    """
    try:
        from ragas import evaluate
        from ragas.metrics import (
            faithfulness, answer_relevancy,
            context_precision, context_recall,
        )
        from datasets import Dataset
        from langchain_openai import AzureChatOpenAI, AzureOpenAIEmbeddings

        dataset = Dataset.from_dict({
            "question": [question],
            "answer": [answer],
            "contexts": [[context]],
            "ground_truth": [ground_truth],
        })

        llm = AzureChatOpenAI(
            azure_deployment=os.getenv("AZURE_OPENAI_DEPLOYMENT_GPT4O_MINI", "gpt-4o-mini"),
            azure_endpoint=AZURE_OPENAI_ENDPOINT,
            api_key=AZURE_OPENAI_KEY,
            api_version="2024-08-01-preview",
            temperature=0,
        )
        embeddings = AzureOpenAIEmbeddings(
            azure_deployment=os.getenv("AZURE_OPENAI_EMBEDDING_DEPLOYMENT", "text-embedding-3-small"),
            azure_endpoint=AZURE_OPENAI_ENDPOINT,
            api_key=AZURE_OPENAI_KEY,
            api_version="2024-08-01-preview",
        )

        result = evaluate(
            dataset,
            metrics=[faithfulness, answer_relevancy, context_precision, context_recall],
            llm=llm,
            embeddings=embeddings,
        )
        return {
            "faithfulness": float(result["faithfulness"]),
            "answer_relevancy": float(result["answer_relevancy"]),
            "context_precision": float(result["context_precision"]),
            "context_recall": float(result["context_recall"]),
        }
    except Exception as e:
        console.print(f"[yellow]RAGAS unavailable ({e}), using heuristic scoring[/yellow]")
        return _heuristic_scores(answer, context, ground_truth)


def _heuristic_scores(answer: str, context: str, ground_truth: str) -> dict[str, float]:
    """
    Simple heuristic scoring when RAGAS / OpenAI is unavailable.
    Used in offline CI runs and local development.
    Based on word overlap (Jaccard similarity).
    """
    def jaccard(a: str, b: str) -> float:
        a_words = set(a.lower().split())
        b_words = set(b.lower().split())
        if not a_words or not b_words:
            return 0.0
        return len(a_words & b_words) / len(a_words | b_words)

    if not answer.strip():
        return {"faithfulness": 0.0, "answer_relevancy": 0.0,
                "context_precision": 0.0, "context_recall": 0.0}

    faithfulness_score = jaccard(answer, context)
    relevancy_score = jaccard(answer, ground_truth)
    precision_score = min(faithfulness_score + 0.1, 1.0)
    recall_score = min(relevancy_score + 0.05, 1.0)

    return {
        "faithfulness": round(faithfulness_score, 4),
        "answer_relevancy": round(relevancy_score, 4),
        "context_precision": round(precision_score, 4),
        "context_recall": round(recall_score, 4),
    }


def check_hallucination(answer: str, context: str) -> bool:
    """
    Simple hallucination check: flag if answer contains numbers
    not present in context (fabricated values).
    """
    import re
    answer_nums = set(re.findall(r'\b\d+(?:\.\d+)?\b', answer))
    context_nums = set(re.findall(r'\b\d+(?:\.\d+)?\b', context))
    fabricated = answer_nums - context_nums
    # Allow small numbers (1-10) as they could be scores, rankings, etc.
    significant_fabricated = {n for n in fabricated if float(n) > 10}
    return len(significant_fabricated) > 0


def check_news2_agreement(answer: str, scenario: Scenario) -> bool | None:
    """
    For NEWS2-relevant scenarios: check if the answer's risk assessment
    directionally agrees with the ground truth.
    """
    if not scenario.news2_relevant:
        return None

    risk_keywords = {
        "high": ["high risk", "urgent", "escalat", "immediate", "critical", "concerning"],
        "low": ["low risk", "normal", "stable", "routine", "within normal"],
    }

    ground_truth_lower = scenario.ground_truth.lower()
    answer_lower = answer.lower()

    gt_risk = None
    for level, keywords in risk_keywords.items():
        if any(kw in ground_truth_lower for kw in keywords):
            gt_risk = level
            break

    if gt_risk is None:
        return None

    answer_matches = any(kw in answer_lower for kw in risk_keywords[gt_risk])
    return answer_matches


# ── Main runner ───────────────────────────────────────────────────

def run_evaluation(
    golden_set_path: Path,
    output_path: Path,
    upload_langfuse: bool = False,
    limit: int | None = None,
) -> EvalRunResult:
    scenarios = load_golden_set(golden_set_path)
    if limit:
        scenarios = scenarios[:limit]

    console.print(f"\n[bold]ClinicalMind RAGAS Evaluation[/bold]")
    console.print(f"Scenarios: {len(scenarios)} | Orchestrator: {ORCHESTRATOR_URL}\n")

    results: list[ScenarioResult] = []

    for i, scenario in enumerate(scenarios, 1):
        console.print(f"  [{i}/{len(scenarios)}] {scenario.id} ({scenario.category})")

        # 1. Call AI orchestrator
        answer, latency_ms, model_used = call_orchestrator(scenario)

        # 2. Score with RAGAS
        scores = score_with_ragas(
            scenario.question, answer, scenario.context, scenario.ground_truth
        )

        # 3. Clinical-specific checks
        hallucination = check_hallucination(answer, scenario.context)
        news2_ok = check_news2_agreement(answer, scenario)

        passed = (
            scores["faithfulness"] >= THRESHOLDS["faithfulness"]
            and scores["answer_relevancy"] >= THRESHOLDS["answer_relevancy"]
            and not hallucination
        )

        results.append(ScenarioResult(
            scenario_id=scenario.id,
            category=scenario.category,
            question=scenario.question,
            ground_truth=scenario.ground_truth,
            actual_answer=answer,
            faithfulness=scores["faithfulness"],
            answer_relevancy=scores["answer_relevancy"],
            context_precision=scores["context_precision"],
            context_recall=scores["context_recall"],
            hallucination_flag=hallucination,
            news2_agreement=news2_ok,
            latency_ms=round(latency_ms, 1),
            model_used=model_used,
            passed=passed,
        ))

    # Aggregate metrics
    def avg(field: str) -> float:
        vals = [getattr(r, field) for r in results if isinstance(getattr(r, field), float)]
        return round(float(np.mean(vals)), 4) if vals else 0.0

    latencies = [r.latency_ms for r in results]
    p95_latency = round(float(np.percentile(latencies, 95)), 1) if latencies else 0.0

    hallucination_rate = round(
        sum(1 for r in results if r.hallucination_flag) / max(len(results), 1), 4
    )

    news2_results = [r.news2_agreement for r in results if r.news2_agreement is not None]
    news2_agreement = round(
        sum(1 for x in news2_results if x) / max(len(news2_results), 1), 4
    ) if news2_results else 0.0

    faithfulness = avg("faithfulness")
    answer_relevancy = avg("answer_relevancy")
    context_precision = avg("context_precision")
    context_recall = avg("context_recall")

    passed_thresholds = (
        faithfulness >= THRESHOLDS["faithfulness"]
        and answer_relevancy >= THRESHOLDS["answer_relevancy"]
        and context_precision >= THRESHOLDS["context_precision"]
        and context_recall >= THRESHOLDS["context_recall"]
        and hallucination_rate <= THRESHOLDS["hallucination_rate"]
        and news2_agreement >= THRESHOLDS["news2_agreement"]
    )

    import subprocess
    try:
        git_sha = subprocess.check_output(["git", "rev-parse", "--short", "HEAD"],
                                           text=True).strip()
    except Exception:
        git_sha = "unknown"

    run_result = EvalRunResult(
        run_date=str(date.today()),
        git_sha=git_sha,
        scenario_count=len(results),
        faithfulness=faithfulness,
        answer_relevancy=answer_relevancy,
        context_precision=context_precision,
        context_recall=context_recall,
        hallucination_rate=hallucination_rate,
        news2_agreement=news2_agreement,
        p95_latency_ms=p95_latency,
        avg_cost_usd=0.0,  # populated from Langfuse in production
        cache_hit_rate=0.0,
        passed_thresholds=passed_thresholds,
        scenario_results=[asdict(r) for r in results],
    )

    # Write results
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w") as f:
        json.dump(asdict(run_result), f, indent=2, default=str)

    _print_summary(run_result)

    if upload_langfuse and os.getenv("LANGFUSE_SECRET_KEY"):
        _upload_to_langfuse(run_result)

    return run_result


def _print_summary(result: EvalRunResult) -> None:
    table = Table(title=f"Eval Results — {result.run_date} | SHA: {result.git_sha}")
    table.add_column("Metric", style="cyan")
    table.add_column("Score", style="bold")
    table.add_column("Threshold")
    table.add_column("Status")

    def status(val: float, threshold: float, invert: bool = False) -> str:
        ok = val <= threshold if invert else val >= threshold
        return "[green]PASS ✓[/green]" if ok else "[red]FAIL ✗[/red]"

    table.add_row("Faithfulness",       f"{result.faithfulness:.4f}",     "≥ 0.85", status(result.faithfulness, 0.85))
    table.add_row("Answer Relevancy",   f"{result.answer_relevancy:.4f}", "≥ 0.80", status(result.answer_relevancy, 0.80))
    table.add_row("Context Precision",  f"{result.context_precision:.4f}","≥ 0.80", status(result.context_precision, 0.80))
    table.add_row("Context Recall",     f"{result.context_recall:.4f}",   "≥ 0.75", status(result.context_recall, 0.75))
    table.add_row("Hallucination Rate", f"{result.hallucination_rate:.1%}","≤ 5%",  status(result.hallucination_rate, 0.05, invert=True))
    table.add_row("NEWS2 Agreement",    f"{result.news2_agreement:.1%}",   "≥ 90%", status(result.news2_agreement, 0.90))
    table.add_row("P95 Latency",        f"{result.p95_latency_ms:.0f}ms", "—",     "—")

    console.print(table)
    overall = "[green bold]PASSED[/green bold]" if result.passed_thresholds else "[red bold]FAILED[/red bold]"
    console.print(f"\nOverall: {overall} ({result.scenario_count} scenarios)\n")


def _upload_to_langfuse(result: EvalRunResult) -> None:
    try:
        from langfuse import Langfuse
        lf = Langfuse(
            secret_key=os.getenv("LANGFUSE_SECRET_KEY", ""),
            public_key=os.getenv("LANGFUSE_PUBLIC_KEY", ""),
        )
        lf.score(
            name="eval_run",
            value=1.0 if result.passed_thresholds else 0.0,
            comment=f"faithfulness={result.faithfulness} news2={result.news2_agreement}",
        )
        console.print("[green]Langfuse upload complete[/green]")
    except Exception as e:
        console.print(f"[yellow]Langfuse upload failed: {e}[/yellow]")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run ClinicalMind RAGAS evaluation")
    parser.add_argument("--golden-set", type=Path, default=Path("data/golden_set_200.json"))
    parser.add_argument("--output", type=Path, default=Path("results/latest.json"))
    parser.add_argument("--upload-langfuse", action="store_true")
    parser.add_argument("--limit", type=int, help="Limit number of scenarios (for quick runs)")
    args = parser.parse_args()

    result = run_evaluation(
        golden_set_path=args.golden_set,
        output_path=args.output,
        upload_langfuse=args.upload_langfuse,
        limit=args.limit,
    )

    sys.exit(0 if result.passed_thresholds else 1)
