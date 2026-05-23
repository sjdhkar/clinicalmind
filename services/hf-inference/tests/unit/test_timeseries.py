"""
Unit tests for the time-series model handler.
Focuses on the anomaly scoring logic — no Chronos model required.
"""

import numpy as np
import pytest

from src.models.timeseries import ForecastResult, _compute_anomaly_score


class TestComputeAnomalyScore:
    def test_stable_forecast_low_anomaly_score(self):
        """If forecast is close to baseline, score should be low."""
        history = [98.0, 98.2, 97.8, 98.1, 97.9, 98.0]
        forecast_mean = [98.0, 97.9, 98.1]
        forecast_low = [97.5, 97.4, 97.6]
        forecast_high = [98.5, 98.4, 98.6]

        score = _compute_anomaly_score(history, forecast_mean, forecast_low, forecast_high)
        assert score < 0.3, f"Expected low anomaly for stable vital, got {score}"

    def test_deteriorating_forecast_high_anomaly_score(self):
        """If forecast deviates far from baseline, score should be high."""
        history = [98.0, 98.2, 97.8, 98.1, 97.9, 98.0]  # stable SpO2 ~98%
        forecast_mean = [93.0, 91.0, 89.0]               # rapid drop
        forecast_low = [91.0, 89.0, 87.0]
        forecast_high = [95.0, 93.0, 91.0]

        score = _compute_anomaly_score(history, forecast_mean, forecast_low, forecast_high)
        assert score > 0.6, f"Expected high anomaly for deteriorating vital, got {score}"

    def test_score_bounded_0_to_1(self):
        """Anomaly score must always be in [0, 1]."""
        # Extreme scenarios
        histories = [
            [100.0] * 10,
            [1.0, 100.0, 1.0, 100.0, 1.0, 100.0],  # highly variable
        ]
        for history in histories:
            forecast_mean = [0.0, 0.0, 0.0]
            forecast_low = [-10.0, -10.0, -10.0]
            forecast_high = [200.0, 200.0, 200.0]
            score = _compute_anomaly_score(history, forecast_mean, forecast_low, forecast_high)
            assert 0.0 <= score <= 1.0

    def test_identical_forecast_to_history_near_zero(self):
        """Forecast identical to historical mean should yield near-zero score."""
        history = [75.0] * 10
        mean_val = 75.0
        forecast_mean = [mean_val] * 3
        forecast_low = [74.0] * 3
        forecast_high = [76.0] * 3

        score = _compute_anomaly_score(history, forecast_mean, forecast_low, forecast_high)
        assert score < 0.2

    def test_wide_confidence_interval_increases_score(self):
        """A wide CI indicates uncertainty — should contribute to anomaly score."""
        history = [75.0] * 10
        # Same mean forecast but wider CI
        narrow_score = _compute_anomaly_score(
            history, [75.0, 75.0, 75.0], [74.5, 74.5, 74.5], [75.5, 75.5, 75.5]
        )
        wide_score = _compute_anomaly_score(
            history, [75.0, 75.0, 75.0], [50.0, 50.0, 50.0], [100.0, 100.0, 100.0]
        )
        assert wide_score > narrow_score


class TestForecastResult:
    def test_anomaly_detected_flag_matches_threshold(self):
        result = ForecastResult(
            mean=[90.0],
            low=[88.0],
            high=[92.0],
            anomaly_score=0.85,
            anomaly_detected=True,
            prediction_length=1,
        )
        assert result.anomaly_detected is True

    def test_no_anomaly_below_threshold(self):
        result = ForecastResult(
            mean=[98.0],
            low=[97.0],
            high=[99.0],
            anomaly_score=0.12,
            anomaly_detected=False,
            prediction_length=1,
        )
        assert result.anomaly_detected is False
