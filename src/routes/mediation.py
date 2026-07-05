"""
Mediation Routes — AI-Mediated Dispute Resolution endpoints.

Flow:
  Party A: POST /mediation/create  → gets dispute_id + invite_code
  Party B: POST /mediation/join    → joins with invite_code
  Both:    POST /mediation/{id}/submit  → each submits statement privately
           GET  /mediation/{id}/status  → poll until status == completed
           GET  /mediation/{id}/result  → see the mediation report
"""

import uuid
import logging
from datetime import datetime
from fastapi import APIRouter, HTTPException, status, Depends, BackgroundTasks
from pydantic import BaseModel

from src.models.mediation_model import (
    CreateDisputeRequest, CreateDisputeResponse,
    JoinDisputeRequest, SubmitStatementRequest,
    MediationFeedbackRequest, DisputeStatusResponse,
    MediationResultResponse, MediationReport, MediationStatus,
    UserDisputeListItem
)
from src.services.mediation_service import get_mediation_service
from src.services.llm_service import get_legal_response
from src.routes.auth_routes import get_current_user
from src.services.auth_service import TokenData

router = APIRouter(prefix="/mediation", tags=["AI Mediation"])
logger = logging.getLogger(__name__)


def _generate_invite_code() -> str:
    """Generate an 8-character uppercase invite code."""
    return str(uuid.uuid4()).replace("-", "")[:8].upper()


# ─── Voice transcript correction ──────────────────────────────────────────────

class VoiceCorrectRequest(BaseModel):
    text: str

class VoiceCorrectResponse(BaseModel):
    corrected: str

@router.post("/voice/correct", response_model=VoiceCorrectResponse)
def correct_voice_transcript(
    request: VoiceCorrectRequest,
    current_user: TokenData = Depends(get_current_user)
):
    """
    Fix speech-to-text transcription errors using the LLM.
    Called from the frontend after the user stops speaking.
    """
    raw = request.text.strip()
    if not raw:
        return VoiceCorrectResponse(corrected="")

    prompt = (
        "You are a transcription corrector for an Indian legal dispute platform. "
        "The text below was produced by a speech-to-text engine and may contain mishearings — "
        "words that sound similar but are wrong in context (e.g. 'length' instead of 'lent', "
        "'bare' instead of 'bear', 'principal' instead of 'principle'). "
        "Fix ONLY clear transcription mistakes. Do NOT rephrase, summarise, or add information. "
        "Preserve all names, amounts, dates, and the speaker's original meaning exactly. "
        "Return ONLY the corrected text — no explanation, no quotes, no prefix.\n\n"
        f"Text: {raw}"
    )

    try:
        corrected = get_legal_response(prompt, language="en").strip()
        # Safety: if LLM returns something much shorter or empty, return original
        if len(corrected) < len(raw) * 0.5:
            return VoiceCorrectResponse(corrected=raw)
        return VoiceCorrectResponse(corrected=corrected)
    except Exception as e:
        logger.error(f"[VoiceCorrect] LLM call failed: {e}")
        return VoiceCorrectResponse(corrected=raw)


# ─── Background task (sync — matches existing codebase pattern) ───────────────

def _run_analysis_background(dispute_id: str, dispute: dict, new_statement_field: str, new_statement: str):
    """
    Runs the full three-layer mediation analysis after both parties submit.
    Executed by FastAPI BackgroundTasks so the HTTP response is returned immediately.
    """
    svc = get_mediation_service()
    try:
        dispute[new_statement_field] = new_statement
        report = svc.run_full_analysis(dispute)

        report_dict = {}
        try:
            import json
            report_dict = json.loads(report.json())
        except Exception:
            report_dict = report.dict()

        svc.update_dispute(dispute_id, {
            "$set": {
                "status": MediationStatus.completed,
                "analysis_result": report_dict,
                "completed_at": datetime.utcnow()
            }
        })
        logger.info(f"[Mediation] Analysis saved for dispute {dispute_id}")

    except Exception as e:
        logger.error(f"[Mediation] Background analysis failed for {dispute_id}: {e}", exc_info=True)
        svc.update_dispute(dispute_id, {
            "$set": {"status": MediationStatus.failed}
        })


# ─── Endpoints ────────────────────────────────────────────────────────────────

@router.post("/create", response_model=CreateDisputeResponse, status_code=status.HTTP_201_CREATED)
def create_dispute(
    request: CreateDisputeRequest,
    current_user: TokenData = Depends(get_current_user)
):
    """
    Create a new dispute room. Party A calls this endpoint.
    Returns an invite_code to share with Party B out-of-band (email, WhatsApp, etc.).
    """
    svc = get_mediation_service()
    dispute_id = str(uuid.uuid4())
    invite_code = _generate_invite_code()
    now = datetime.utcnow()

    prior_context_a = None
    if request.prior_prediction_id:
        pred = svc.db.find_one_doc("case_predictions", {"prediction_id": request.prior_prediction_id})
        if pred:
            prior_context_a = {
                "predicted_verdict": pred.get("predicted_verdict"),
                "confidence": pred.get("confidence"),
                "risk_level": pred.get("risk_level")
            }
            logger.info(f"[Mediation] Loaded prior prediction context for Party A: {request.prior_prediction_id}")

    dispute_doc = {
        "dispute_id": dispute_id,
        "invite_code": invite_code,
        "party_a_user_id": current_user.user_id,
        "party_b_user_id": None,
        "status": MediationStatus.pending_party_b,
        "case_type": request.case_type,
        "case_description": request.case_description,
        "jurisdiction": request.jurisdiction,
        "state": request.state,
        "language": request.language,
        "party_a_statement": request.case_description,
        "party_b_statement": None,
        "prior_context_a": prior_context_a,
        "prior_context_b": None,
        "analysis_result": None,
        "created_at": now,
        "completed_at": None
    }

    saved = svc.save_dispute(dispute_doc)
    if not saved:
        logger.error(f"[Mediation] Failed to save dispute {dispute_id} to DB")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create dispute. Please try again."
        )

    logger.info(f"[Mediation] Dispute created: {dispute_id} by user {current_user.user_id}")

    return CreateDisputeResponse(
        dispute_id=dispute_id,
        status=MediationStatus.pending_party_b,
        invite_code=invite_code,
        message=f"Dispute created. Share invite code '{invite_code}' with the other party so they can join.",
        created_at=now
    )


@router.post("/join")
def join_dispute(
    request: JoinDisputeRequest,
    current_user: TokenData = Depends(get_current_user)
):
    """
    Party B joins an existing dispute using the invite code shared by Party A.
    """
    svc = get_mediation_service()
    dispute = svc.get_dispute_by_invite(request.invite_code)

    if not dispute:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Dispute not found. Please check your invite code."
        )

    if current_user.user_id == dispute["party_a_user_id"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="You cannot join your own dispute as the other party."
        )

    if dispute.get("party_b_user_id"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="This dispute already has both parties. The invite code cannot be reused."
        )

    new_join_status = (
        MediationStatus.pending_party_b_statement
        if dispute.get("party_a_statement")
        else MediationStatus.pending_statements
    )
    svc.update_dispute(dispute["dispute_id"], {
        "$set": {
            "party_b_user_id": current_user.user_id,
            "status": new_join_status
        }
    })

    logger.info(f"[Mediation] Party B ({current_user.user_id}) joined dispute {dispute['dispute_id']}")

    return {
        "dispute_id": dispute["dispute_id"],
        "case_type": dispute["case_type"],
        "jurisdiction": dispute["jurisdiction"],
        "message": "You have joined the dispute. Please submit your statement when ready.",
        "status": MediationStatus.pending_statements
    }


@router.post("/{dispute_id}/submit")
def submit_statement(
    dispute_id: str,
    request: SubmitStatementRequest,
    background_tasks: BackgroundTasks,
    current_user: TokenData = Depends(get_current_user)
):
    """
    Submit your private statement about the dispute.
    Neither party can see the other's statement — only the final report is shared.
    When both parties submit, analysis runs automatically in the background.
    """
    svc = get_mediation_service()
    dispute = svc.get_dispute(dispute_id)

    if not dispute:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Dispute not found.")

    user_id = current_user.user_id
    is_party_a = user_id == dispute["party_a_user_id"]
    is_party_b = user_id == dispute.get("party_b_user_id")

    if not is_party_a and not is_party_b:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="You are not a party in this dispute.")

    if dispute["status"] in [MediationStatus.completed, MediationStatus.analysis_running]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="This dispute is already resolved or analysis is running."
        )

    statement_field = "party_a_statement" if is_party_a else "party_b_statement"
    other_field = "party_b_statement" if is_party_a else "party_a_statement"

    if dispute.get(statement_field):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="You have already submitted your statement for this dispute."
        )

    other_submitted = bool(dispute.get(other_field))

    if other_submitted:
        new_status = MediationStatus.analysis_running
    else:
        new_status = (
            MediationStatus.pending_party_b_statement if is_party_a
            else MediationStatus.pending_party_a_statement
        )

    svc.update_dispute(dispute_id, {
        "$set": {
            statement_field: request.statement,
            "status": new_status
        }
    })

    logger.info(f"[Mediation] {'Party A' if is_party_a else 'Party B'} submitted statement for dispute {dispute_id}")

    if other_submitted:
        background_tasks.add_task(
            _run_analysis_background,
            dispute_id,
            dispute,
            statement_field,
            request.statement
        )
        return {
            "dispute_id": dispute_id,
            "status": MediationStatus.analysis_running,
            "message": "Both parties have submitted. AI mediation analysis is now running. Check back in 30–60 seconds."
        }

    return {
        "dispute_id": dispute_id,
        "status": new_status,
        "message": "Statement submitted successfully. Waiting for the other party to submit."
    }


@router.get("/{dispute_id}/status", response_model=DisputeStatusResponse)
def get_dispute_status(
    dispute_id: str,
    current_user: TokenData = Depends(get_current_user)
):
    """
    Poll the status of a dispute. Frontend should poll this every 5–10 seconds
    while status is 'analysis_running'.
    """
    svc = get_mediation_service()
    dispute = svc.get_dispute(dispute_id)

    if not dispute:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Dispute not found.")

    user_id = current_user.user_id
    if user_id not in [dispute["party_a_user_id"], dispute.get("party_b_user_id")]:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied.")

    completed_at = dispute.get("completed_at")
    if isinstance(completed_at, str):
        try:
            completed_at = datetime.fromisoformat(completed_at)
        except Exception:
            completed_at = None

    return DisputeStatusResponse(
        dispute_id=dispute_id,
        status=dispute["status"],
        case_type=dispute["case_type"],
        jurisdiction=dispute.get("jurisdiction", "India"),
        party_a_submitted=bool(dispute.get("party_a_statement")),
        party_b_submitted=bool(dispute.get("party_b_statement")),
        party_b_joined=bool(dispute.get("party_b_user_id")),
        is_party_a=(user_id == dispute["party_a_user_id"]),
        created_at=dispute["created_at"],
        completed_at=completed_at
    )


@router.get("/{dispute_id}/result", response_model=MediationResultResponse)
def get_dispute_result(
    dispute_id: str,
    current_user: TokenData = Depends(get_current_user)
):
    """
    Get the final mediation report. Both parties see the same report simultaneously.
    Returns 200 with status field indicating whether analysis is done.
    """
    svc = get_mediation_service()
    dispute = svc.get_dispute(dispute_id)

    if not dispute:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Dispute not found.")

    user_id = current_user.user_id
    if user_id not in [dispute["party_a_user_id"], dispute.get("party_b_user_id")]:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied.")

    dispute_status = dispute["status"]

    if dispute_status == MediationStatus.failed:
        return MediationResultResponse(
            dispute_id=dispute_id,
            status=MediationStatus.failed,
            report=None,
            message="Analysis failed. Please contact support or try resubmitting."
        )

    if dispute_status != MediationStatus.completed:
        status_messages = {
            MediationStatus.pending_party_b: "Waiting for the other party to join.",
            MediationStatus.pending_statements: "Both parties joined. Waiting for statements.",
            MediationStatus.pending_party_b_statement: "Your statement received. Waiting for the other party.",
            MediationStatus.pending_party_a_statement: "Waiting for the other party's statement.",
            MediationStatus.analysis_running: "Both statements received. AI analysis is running — check back in 30–60 seconds."
        }
        return MediationResultResponse(
            dispute_id=dispute_id,
            status=dispute_status,
            report=None,
            message=status_messages.get(dispute_status, "Processing...")
        )

    raw_report = dispute.get("analysis_result")
    if not raw_report:
        return MediationResultResponse(
            dispute_id=dispute_id,
            status=MediationStatus.failed,
            report=None,
            message="Report data is missing. Please contact support."
        )

    try:
        report = MediationReport(**raw_report)
    except Exception as e:
        logger.error(f"[Mediation] Failed to deserialize report for {dispute_id}: {e}")
        return MediationResultResponse(
            dispute_id=dispute_id,
            status=MediationStatus.failed,
            report=None,
            message="Report could not be loaded. Please contact support."
        )

    return MediationResultResponse(
        dispute_id=dispute_id,
        status=MediationStatus.completed,
        report=report,
        message="Mediation complete. Both parties can now view the report."
    )


@router.post("/{dispute_id}/feedback")
def submit_feedback(
    dispute_id: str,
    feedback: MediationFeedbackRequest,
    current_user: TokenData = Depends(get_current_user)
):
    """
    Submit feedback on the mediation report. Used for research and model improvement.
    """
    svc = get_mediation_service()
    dispute = svc.get_dispute(dispute_id)

    if not dispute:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Dispute not found.")

    user_id = current_user.user_id
    if user_id not in [dispute["party_a_user_id"], dispute.get("party_b_user_id")]:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied.")

    feedback_doc = {
        "feedback_id": str(uuid.uuid4()),
        "dispute_id": dispute_id,
        "user_id": user_id,
        "role": "party_a" if user_id == dispute["party_a_user_id"] else "party_b",
        "rating": feedback.rating,
        "accepted_settlement": feedback.accepted_settlement,
        "comment": feedback.comment,
        "timestamp": datetime.utcnow()
    }

    svc.save_feedback(feedback_doc)
    logger.info(f"[Mediation] Feedback saved for dispute {dispute_id} by user {user_id}")

    return {"message": "Feedback recorded. Thank you — this helps us improve the system."}


@router.get("/my/disputes")
def list_my_disputes(current_user: TokenData = Depends(get_current_user)):
    """
    List all disputes the current user is a party in (as Party A or Party B).
    """
    svc = get_mediation_service()
    disputes = svc.get_user_disputes(current_user.user_id)

    result = []
    for d in disputes:
        try:
            completed_at = d.get("completed_at")
            if isinstance(completed_at, str):
                try:
                    completed_at = datetime.fromisoformat(completed_at)
                except Exception:
                    completed_at = None

            result.append(UserDisputeListItem(
                dispute_id=d["dispute_id"],
                invite_code=d["invite_code"],
                status=d["status"],
                case_type=d["case_type"],
                role="party_a" if current_user.user_id == d["party_a_user_id"] else "party_b",
                created_at=d["created_at"],
                completed_at=completed_at
            ))
        except Exception as e:
            logger.warning(f"[Mediation] Skipping malformed dispute in list: {e}")

    return {"disputes": [item.dict() for item in result], "total": len(result)}
