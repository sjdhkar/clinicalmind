"""
Vital sign time-series forecasting using Amazon Chronos-T5.

Model: amazon/chronos-t5-small
Task: Time Series Forecasting
Use in ClinicalMind: Predict next N steps of a vital sign stream, flag deterioration.

Chronos is a zero-shot time-series foundation model — no fine-tuning required.
It takes a context window of past values and returns a forecast distribution.
"""

import logging
from dataclasses import dataclass, field

import numpy as np
import torch

from src.config import Settings

logger = logging.getLogger(__name__)


@dataclass
class TimeseriesModel:
    pipeline: object  # chronos.ChronosPipeline
    model_id: str
    device: str


@dataclass
class ForecastResult:
    mean: list[float]           # point forecast (mean of distribution)
    low: list[float]            # 10th percentile (lower bound)
    high: list[float]           # 90th percentile (upper bound)
    anomaly_score: float        # 0.0–1.0; high = likely anomaly
    anomaly_detected: bool
    prediction_length: int


def load_timeseries_model(settings: Settings, device: str) -> TimeseriesModel:
    """Load Chronos pipeline. Called once by the registry."""
    try:
        from chronos import ChronosPipeline
    except ImportError as e:
        raise ImportError(
            "chronos-forecasting is not installed. "
            "Run: pip install chronos-forecasting"
        ) from e

    torch_dtype = torch.bfloat16 if device != "cpu" else torch.float32

    pipe = ChronosPipeline.from_pretrained(
        settings.timeseries_model_id,
        device_map=device,
        torch_dtype=torch_dtype,
        cache_dir=settings.model_cache_dir,
    )
    return TimeseriesModel(pipeline=pipe, model_id=settings.timeseries_model_id, device=device)


def run_forecast(
    model: TimeseriesModel,
    values: list[float],
    prediction_length: int,
    num_samples: int = 20,
    anomaly_threshold: float = 0.8,
) -> ForecastResult:
    """
    Forecast future vital sign values and compute an anomaly score.

    Args:
        model: Loaded TimeseriesModel from registry
        values: Historical vital sign readings (e.g. last 24h of SpO2 readings)
        prediction_length: Number of future steps to predict
        num_samples: Samples to draw from the forecast distribution (higher = better CI)
        anomaly_threshold: Anomaly score above this triggers anomaly_detected=True

    Returns:
        ForecastResult with point forecast, confidence interval, and anomaly score
    """
    if len(values) < 3:
        raise ValueError("At least 3 historical values required for forecasting")

    context = torch.tensor(values, dtype=torch.float32).unsqueeze(0)  # shape: (1, T)

    forecast = model.pipeline.predict(
        context=context,
        prediction_length=prediction_length,
        num_samples=num_samples,
    )
    # forecast shape: (1, num_samples, prediction_length)
    samples = forecast[0].numpy()  # (num_samples, prediction_length)

    mean_forecast = samples.mean(axis=0).tolist()
    low_forecast = np.percentile(samples, 10, axis=0).tolist()
    high_forecast = np.percentile(samples, 90, axis=0).tolist()

    anomaly_score = _compute_anomaly_score(values, mean_forecast, low_forecast, high_forecast)

    return ForecastResult(
        mean=[round(v, 2) for v in mean_forecast],
        low=[round(v, 2) for v in low_forecast],
        high=[round(v, 2) for v in high_forecast],
        anomaly_score=round(anomaly_score, 4),
        anomaly_detected=anomaly_score > anomaly_threshold,
        prediction_length=prediction_length,
    )


def _compute_anomaly_score(
    history: list[float],
    mean_forecast: list[float],
    low_forecast: list[float],
    high_forecast: list[float],
) -> float:
    """
    Compute a 0–1 anomaly score based on:
    1. How far the forecast deviates from the historical baseline
    2. Uncertainty width (wide CI = model is unsure = potential anomaly)

    This is a heuristic — in production you'd compare against NEWS2 clinical ranges.
    """
    history_arr = np.array(history)
    baseline_mean = history_arr.mean()
    baseline_std = history_arr.std() + 1e-8  # avoid division by zero

    forecast_mean = np.mean(mean_forecast)
    deviation = abs(forecast_mean - baseline_mean) / baseline_std

    ci_width = np.mean(np.array(high_forecast) - np.array(low_forecast))
    normalised_ci = ci_width / (baseline_std * 4 + 1e-8)

    # Weighted combination: 60% deviation, 40% uncertainty
    score = 0.6 * min(deviation / 3.0, 1.0) + 0.4 * min(normalised_ci, 1.0)
    return float(np.clip(score, 0.0, 1.0))
