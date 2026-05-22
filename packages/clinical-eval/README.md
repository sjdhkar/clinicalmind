# Clinical Evaluation Package

**Responsibility:** RAGAS evaluation pipeline, golden set management, threshold checks

## What's Here

```
clinical-eval/
├── data/
│   └── golden_set_200.json      # 200 clinical Q&A scenarios with expected answers
├── results/
│   └── .gitkeep                 # Eval results committed by nightly CI
├── run_eval.py                  # Main evaluation runner
├── check_thresholds.py          # CI gate — fails if metrics below threshold
├── update_results_index.py      # Updates docs/eval-results/ for dashboard
└── seed_demo_data.py            # Seeds pgvector with sample clinical data for local dev
```

## Evaluation Thresholds (CI gates)

```python
THRESHOLDS = {
    "faithfulness":       0.85,
    "answer_relevancy":   0.80,
    "context_precision":  0.80,
    "context_recall":     0.75,
    "hallucination_rate": 0.05,   # <= 5%
    "news2_agreement":    0.90,   # >= 90%
}
```

PRs that cause any metric to drop below its threshold will **fail the CI check**.

## Running Locally

```bash
cd packages/clinical-eval
uv sync
uv run python run_eval.py --golden-set data/golden_set_200.json --output results/local.json
uv run python check_thresholds.py --results results/local.json
```

## Status: 🚧 In Development
