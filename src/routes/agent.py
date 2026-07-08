"""
Legal Triage Agent Routes
=========================
Public endpoint — no authentication required.
Routes a user's plain-language description to the right tool.

Endpoints:
  POST /agent/triage  — classify situation and return tool routing
"""

import logging
from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field

from src.services.agent_triage_service import triage

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/agent", tags=["Legal Triage Agent"])


class TriageRequest(BaseModel):
    text: str = Field(
        ...,
        min_length=5,
        max_length=2000,
        description="User's plain-language description of their legal situation.",
        examples=["I've been charged with IPC 302 murder and want to apply for bail."],
    )


class TriageResponse(BaseModel):
    tool:         str  # "chat" | "predict" | "mediation"
    reason:       str  # one-sentence explanation shown to user
    prefill_text: str  # original text, passed through to pre-fill the target tool


@router.post(
    "/triage",
    response_model=TriageResponse,
    summary="Route legal situation to the right tool",
    description=(
        "Classifies the user's plain-language description into one of three tools: "
        "Legal Assistant chatbot (chat), Case Outcome Predictor (predict), or "
        "AI-Mediated Dispute Resolution (mediation). "
        "Never answers the legal question — only routes. No authentication required."
    ),
)
async def agent_triage(request: TriageRequest) -> TriageResponse:
    try:
        result = triage(request.text)
        return TriageResponse(**result)
    except Exception as exc:
        logger.error("[AgentTriage] /triage endpoint failed: %s", exc, exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Triage failed. Please try again.",
        )
