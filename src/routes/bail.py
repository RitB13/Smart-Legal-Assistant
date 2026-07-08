"""
Bail Prediction Routes
======================
Exposes the classical LinearSVC bail predictor as a REST endpoint.

Endpoints:
  POST /bail/predict   — predict bail outcome for a petition text
  GET  /bail/health    — check whether the model is loaded
"""

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field
from typing import Dict, Any
import logging

from src.services.bail_predictor_service import get_bail_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/bail", tags=["Bail Prediction"])


# ── Request / Response models ──────────────────────────────────────────────

class BailPredictRequest(BaseModel):
    text: str = Field(
        ...,
        min_length=10,
        description="Bail petition text or case description (up to 2000 chars used).",
        examples=["The accused is charged with IPC 302 murder and has prior criminal record."],
    )


class BailProbabilities(BaseModel):
    bail_granted: float
    bail_denied: float


class BailPredictResponse(BaseModel):
    prediction:    str            # "Bail Granted" or "Bail Denied"
    label:         str            # "0" or "1"
    confidence:    float          # 0–100
    risk_level:    str            # "low" | "medium" | "high" | "uncertain"
    probabilities: BailProbabilities


class BailHealthResponse(BaseModel):
    model_loaded:       bool
    model_type:         str
    test_accuracy:      float
    test_f1_weighted:   float
    training_samples:   int


# ── Endpoints ──────────────────────────────────────────────────────────────

@router.post(
    "/predict",
    response_model=BailPredictResponse,
    summary="Predict bail outcome",
    description=(
        "Predict whether bail is likely to be granted or denied for the given petition text. "
        "Returns a prediction, confidence score, risk level, and class probabilities. "
        "Model: LinearSVC + TF-IDF, trained on 123,742 Indian bail cases (85.8% accuracy)."
    ),
)
async def predict_bail(request: BailPredictRequest) -> BailPredictResponse:
    svc = get_bail_service()

    if not svc.available:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=(
                "Bail prediction model is not loaded. "
                "Ensure src/data/models/classical/bail/ contains the model artifacts."
            ),
        )

    try:
        result = svc.predict(request.text)
        return BailPredictResponse(
            prediction=result["prediction"],
            label=result["label"],
            confidence=result["confidence"],
            risk_level=result["risk_level"],
            probabilities=BailProbabilities(**result["probabilities"]),
        )
    except Exception as e:
        logger.error("[Bail] /predict failed: %s", e, exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Bail prediction failed. Check server logs for details.",
        )


@router.get(
    "/health",
    response_model=BailHealthResponse,
    summary="Bail model health check",
)
async def bail_health() -> BailHealthResponse:
    svc = get_bail_service()
    info = svc.get_model_info()
    return BailHealthResponse(
        model_loaded=info["model_loaded"],
        model_type=info["model_type"],
        test_accuracy=info["test_accuracy"],
        test_f1_weighted=info["test_f1_weighted"],
        training_samples=info["training_samples"],
    )
