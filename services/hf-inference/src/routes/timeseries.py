"""Time-series forecasting endpoint — vital sign anomaly detection."""

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from src.config import Settings, get_settings
from src.models.registry import get_model
from src.models.timeseries import load_timeseries_model, run_forecast

router = APIRouter(prefix="/timeseries", tags=["timeseries"])


class TimeseriesRequest(BaseModel):
    values: list[float] = Field(
        ...,
        min_length=3,
        max_length=1000,
        description="Historical vital sign readings in chronological order",
        examples=[[98.2, 97.8, 97.5, 96.9, 96.1, 95.8, 95.2, 94.8]],
    )
    prediction_length: int = Field(
        default=12,
        ge=1,
        le=64,
        description="Number of future steps to forecast",
    )
    vital_sign: str = Field(
        default="unknown",
        description="Label for the vital sign (SpO2, HR, BP_sys, etc.) — used for logging",
    )


class TimeseriesResponse(BaseModel):
    mean: list[float]
    low: list[float]
    high: list[float]
    anomaly_score: float
    anomaly_detected: bool
    prediction_length: int
    model_id: str


@router.post("", response_model=TimeseriesResponse, summary="Vital sign forecasting + anomaly")
async def forecast_vitals(
    request: TimeseriesRequest,
    settings: Settings = Depends(get_settings),
) -> TimeseriesResponse:
    """
    Forecast future vital sign values using Amazon Chronos-T5.

    Returns a point forecast (mean) and 80% confidence interval (low/high),
    plus an anomaly score indicating how unusual the predicted trajectory is
    relative to the patient's recent baseline.
    """
    try:
        model = get_model("timeseries", load_timeseries_model, settings)
        result = run_forecast(
            model,
            request.values,
            request.prediction_length,
        )
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e)) from e
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Forecasting failed: {str(e)}") from e

    return TimeseriesResponse(
        mean=result.mean,
        low=result.low,
        high=result.high,
        anomaly_score=result.anomaly_score,
        anomaly_detected=result.anomaly_detected,
        prediction_length=result.prediction_length,
        model_id=model.model_id,
    )
