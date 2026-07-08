"""
Agent Triage Service
====================
Classifies a user's free-text legal situation into one of three tools
using Groq LLM with JSON-mode output.

Returns a routing decision only — never answers the legal question itself.
"""

import json
import logging
import requests

from config import GROQ_API_KEY, GROQ_MODEL

logger = logging.getLogger(__name__)

GROQ_URL = "https://api.groq.com/openai/v1/chat/completions"

TRIAGE_SYSTEM_PROMPT = """You are a legal routing agent for Smart Legal Assistant, an AI platform for Indian law.

Your ONLY job is to read the user's description of their legal situation and decide which of the three tools below is the best match. You must NEVER answer the legal question, give legal advice, or provide any analysis whatsoever.

AVAILABLE TOOLS:

1. "chat" — Legal Assistant chatbot.
   Use when the user wants legal advice, wants to understand their rights, wants to know what steps to take, or has a general legal question.
   Examples: "My employer fired me without notice", "I received a legal notice", "Police filed an FIR, what do I do?", "What are my rights as a tenant?"

2. "predict" — Case Outcome Predictor.
   Use when the user wants to know the likely outcome, probability of winning, or chances of getting bail.
   Examples: "Will I get bail?", "What are my chances of winning?", "Will the court rule in my favor?", "What will happen to my case?"

3. "mediation" — AI-Mediated Dispute Resolution.
   Use when there are TWO parties in a dispute and the user wants to resolve it without going to court.
   Examples: "My landlord won't return my deposit and we want to settle", "My business partner and I disagree on profit sharing", "My neighbor and I have a property dispute we want to resolve"

ROUTING RULES:
- "what should I do" / "what are my rights" / "how do I" → "chat"
- "will I win" / "chances" / "bail" / "outcome" / "verdict" / "predict" → "predict"
- two parties + dispute + settlement/resolution → "mediation"
- ambiguous → always default to "chat"

Respond with ONLY valid JSON, no other text:
{"tool": "chat" | "predict" | "mediation", "reason": "one sentence explaining why this tool fits"}"""


def triage(text: str) -> dict:
    """
    Route a user's situation description to the appropriate tool.

    Args:
        text: Free-text description of the user's legal situation (max 1500 chars used).

    Returns:
        Dict with keys:
          tool         — "chat" | "predict" | "mediation"
          reason       — one sentence explaining the routing
          prefill_text — original text passed through unchanged
    """
    text = (text or "").strip()
    if not text:
        return {
            "tool": "chat",
            "reason": "Our Legal Assistant can help you with your situation.",
            "prefill_text": text,
        }

    try:
        response = requests.post(
            GROQ_URL,
            headers={
                "Authorization": f"Bearer {GROQ_API_KEY}",
                "Content-Type": "application/json",
            },
            json={
                "model": GROQ_MODEL,
                "messages": [
                    {"role": "system", "content": TRIAGE_SYSTEM_PROMPT},
                    {"role": "user",   "content": text[:1500]},
                ],
                "temperature": 0.0,
                "max_tokens": 120,
                "response_format": {"type": "json_object"},
            },
            timeout=15,
        )
        response.raise_for_status()

        content = response.json()["choices"][0]["message"]["content"]
        parsed  = json.loads(content)

        tool = parsed.get("tool", "chat")
        if tool not in ("chat", "predict", "mediation"):
            logger.warning("[AgentTriage] Unexpected tool value '%s' — falling back to chat", tool)
            tool = "chat"

        reason = (parsed.get("reason") or "").strip()
        if not reason:
            reason = "Our Legal Assistant can help you with this."

        return {"tool": tool, "reason": reason, "prefill_text": text}

    except requests.exceptions.Timeout:
        logger.warning("[AgentTriage] Groq call timed out — defaulting to chat")
    except requests.exceptions.RequestException as exc:
        logger.error("[AgentTriage] Groq request failed: %s", exc)
    except (json.JSONDecodeError, KeyError) as exc:
        logger.error("[AgentTriage] Failed to parse Groq response: %s", exc)
    except Exception as exc:
        logger.error("[AgentTriage] Unexpected error: %s", exc, exc_info=True)

    return {
        "tool": "chat",
        "reason": "Our Legal Assistant can help you with your situation.",
        "prefill_text": text,
    }
