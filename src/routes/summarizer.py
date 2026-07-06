from fastapi import APIRouter, HTTPException, UploadFile, File, status
from src.services.document_processor import DocumentProcessor
from src.services.llm_service import get_legal_response
from src.services.language_service import detect_language
from pydantic import BaseModel
from typing import List
import logging
import json as _json
import tempfile
import os

logger = logging.getLogger(__name__)
router = APIRouter()

_document_processor = DocumentProcessor()


class ExtractStatementResponse(BaseModel):
    statement: str
    detected_laws: List[str]
    language: str


@router.post("/document/extract-statement", response_model=ExtractStatementResponse)
async def extract_statement(file: UploadFile = File(...)):
    """
    Extract text from a legal document (PDF / DOCX / image) and return a
    plain-English first-person statement ready to paste into the Case Predictor
    or Mediation dispute-description fields.

    Returns:
        statement      — 4-6 sentence LLM-generated first-person account
        detected_laws  — Acts / codes the LLM found in the document (up to 6)
        language       — ISO 639-1 language code detected in the document
    """
    filename = file.filename or "document"
    content_type = file.content_type or ""

    allowed = (
        content_type in {
            "application/pdf",
            "application/msword",
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            "image/jpeg",
            "image/png",
        }
        or filename.lower().endswith((".pdf", ".doc", ".docx", ".jpg", ".jpeg", ".png"))
    )
    if not allowed:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Unsupported file type. Please upload a PDF, DOCX, JPG, or PNG.",
        )

    suffix = os.path.splitext(filename)[1] or ".pdf"
    tmp_path = None
    try:
        content = await file.read()
        if len(content) > 10 * 1024 * 1024:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="File too large. Maximum size is 10 MB.",
            )

        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
            tmp_path = tmp.name
            tmp.write(content)

        # Extract raw text
        raw_text = _document_processor.process_file(tmp_path)
        if not raw_text or not raw_text.strip():
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Could not extract readable text from this document. "
                       "Try uploading a text-based PDF instead of a scanned image.",
            )
        text = raw_text.strip()[:5000]

        # Detect language
        try:
            language = detect_language(text) or "en"
        except Exception:
            language = "en"

        # Single LLM call: statement + law extraction
        prompt = (
            "You are a legal assistant helping a citizen describe their situation to an AI system.\n"
            "Below is text extracted from their legal document.\n\n"
            "Do TWO things and return ONLY valid JSON — no markdown, no extra text:\n"
            "1. STATEMENT: Write a 4–6 sentence first-person account of the legal dispute "
            "as if the person is speaking. Use 'I', 'my', 'we'. "
            "Cover: what happened, who is involved, what the dispute is about, "
            "and what outcome is being sought. "
            "Plain language only — no bullet points, no headings, no legal jargon. "
            "Every sentence must be complete.\n"
            "2. LAWS: List up to 6 Acts, Codes, or Sections explicitly mentioned or "
            "clearly applicable in the document "
            "(e.g. 'SARFAESI Act 2002', 'Code of Civil Procedure', 'Section 138 NI Act'). "
            "Return an empty array [] if none are identifiable.\n\n"
            f"Document text:\n{text[:3000]}\n\n"
            'Return exactly this JSON shape:\n'
            '{"statement": "...", "laws": ["...", "..."]}'
        )

        statement = ""
        detected_laws: List[str] = []
        try:
            raw = get_legal_response(
                prompt,
                language="en",
                max_tokens=600,
                temperature=0.2,
                timeout=60,
                system_prompt=(
                    "You are a legal assistant. Respond ONLY with valid JSON exactly "
                    "matching the structure the user specifies. "
                    "No extra text, no markdown fences, no prose outside the JSON object."
                ),
            )
            cleaned = raw.strip()

            # Strip markdown fences if present
            if "```" in cleaned:
                for block in cleaned.split("```"):
                    b = block.strip()
                    if b.startswith("json"):
                        b = b[4:].strip()
                    if b.startswith("{"):
                        cleaned = b
                        break

            parsed = _json.loads(cleaned)
            statement = (parsed.get("statement") or "").strip()
            laws_raw = parsed.get("laws") or []
            detected_laws = [str(l) for l in laws_raw if l][:6]
        except Exception as e:
            logger.warning("[DocExtract] LLM parse failed: %s", e)

        # Fallback: clean raw text as statement if LLM failed
        if not statement:
            statement = " ".join(text[:800].split())

        return ExtractStatementResponse(
            statement=statement,
            detected_laws=detected_laws,
            language=language,
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error("[DocExtract] Unexpected error: %s", e, exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to process document. Please try again.",
        )
    finally:
        if tmp_path and os.path.exists(tmp_path):
            try:
                os.unlink(tmp_path)
            except Exception:
                pass
