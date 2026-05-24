"""
check_thresholds.py — CI gate for RAGAS evaluation results.

Called by GitHub Actions after run_eval.py.
Exits 0 if all thresholds pass, exits 1 (fails the build) if any fail.

Usage:
    python check_thresholds.py --results results/latest.json
"""

import argparse
import json
import sys
from pathlib import Path
from rich.console import Console
from rich.table import Table

console = Console()

THRESHOLDS = {
    "faithfulness":       (">=", 0.85),
    "answer_relevancy":   (">=", 0.80),
    "context_precision":  (">=", 0.80),
    "context_recall":     (">=", 0.75),
    "hallucination_rate": ("<=", 0.05),
    "news2_agreement":    (">=", 0.90),
}


def check(results_path: Path) -> bool:
    with open(results_path) as f:
        data = json.load(f)

    console.print(f"\n[bold]Threshold Check — {data.get('run_date', 'unknown')}[/bold]")
    console.print(f"Git SHA: {data.get('git_sha', 'unknown')} | Scenarios: {data.get('scenario_count', 0)}\n")

    table = Table()
    table.add_column("Metric")
    table.add_column("Value", style="bold")
    table.add_column("Threshold")
    table.add_column("Result")

    all_pass = True

    for metric, (op, threshold) in THRESHOLDS.items():
        value = data.get(metric, 0.0)
        if op == ">=":
            passed = float(value) >= threshold
            display_threshold = f"≥ {threshold}"
        else:
            passed = float(value) <= threshold
            display_threshold = f"≤ {threshold}"

        if not passed:
            all_pass = False

        display_value = f"{float(value):.1%}" if "rate" in metric or "agreement" in metric else f"{float(value):.4f}"
        result_str = "[green]PASS ✓[/green]" if passed else "[red bold]FAIL ✗[/red bold]"
        table.add_row(metric, display_value, display_threshold, result_str)

    console.print(table)

    if all_pass:
        console.print("\n[green bold]All thresholds passed — PR is safe to merge.[/green bold]\n")
    else:
        console.print("\n[red bold]Threshold check FAILED — this PR cannot be merged.[/red bold]")
        console.print("[red]Fix the failing metrics before requesting review.[/red]\n")

    return all_pass


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--results", type=Path, default=Path("results/latest.json"))
    args = parser.parse_args()

    passed = check(args.results)
    sys.exit(0 if passed else 1)
