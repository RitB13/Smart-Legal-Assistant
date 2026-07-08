import json
import requests
import logging
from config import GROQ_API_KEY, GROQ_MODEL, LLM_TIMEOUT, LLM_MAX_TOKENS, LLM_TEMPERATURE
from tenacity import retry, stop_after_attempt, wait_exponential

logger = logging.getLogger(__name__)

BASE_URL = "https://api.groq.com/openai/v1/chat/completions"

# Base system prompt (language-agnostic guidance)
BASE_SYSTEM_PROMPT = """You are a legal assistant specialized in providing accurate and helpful legal information on Indian law and international legal principles.
You have expertise in various areas of law including civil, criminal, employment, property, constitutional, and contract law.

CRITICAL INSTRUCTION: You must respond ONLY in the SAME LANGUAGE as the user's query. If the user writes in Hindi, respond entirely in Hindi. If in English, respond in English. And so on for other languages.

Always structure your responses in this JSON format:
{
    "summary": "<detailed explanation of the legal issue>",
    "laws": ["<relevant law or statute 1>", "<relevant law or statute 2>"],
    "suggestions": ["<actionable suggestion 1>", "<actionable suggestion 2>"],
    "follow_up_questions": ["<natural follow-up question the user is likely to ask next 1>", "<follow-up question 2>", "<follow-up question 3>"]
}

Guidelines:
- The "summary" field MUST be in the same language as the user's query
- The "suggestions" field MUST be in the same language as the user's query
- Law names or legal sections can remain in English if they are proper names (e.g., "Indian Penal Code")
- Ensure all JSON is valid and properly formatted
- Provide clear, concise, and accurate legal guidance
- The "follow_up_questions" should be 2-3 natural follow-up questions in the SAME LANGUAGE as the user's query
- Do not include any text outside the JSON structure"""


def create_language_aware_prompt(language_code: str) -> str:
    """
    Create a language-aware system prompt for multilingual support.
    
    Args:
        language_code: ISO language code (e.g., 'en', 'hi', 'bn')
        
    Returns:
        System prompt string with language-specific instructions
    """
    language_names = {
        'en': 'English',
        'hi': 'Hindi (हिन्दी)',
        'bn': 'Bengali (বাংলা)',
        'ta': 'Tamil (தமிழ்)',
        'te': 'Telugu (తెలుగు)',
        'mr': 'Marathi (मराठी)',
        'gu': 'Gujarati (ગુજરાતી)',
        'kn': 'Kannada (ಕನ್ನಡ)',
        'ml': 'Malayalam (മലയാളം)',
        'pa': 'Punjabi (ਪੰਜਾਬੀ)'
    }
    
    language_name = language_names.get(language_code, language_code)
    
    prompt = BASE_SYSTEM_PROMPT + f"\n\nIMPORTANT: The user is communicating in {language_name}. Your response MUST be entirely in {language_name}."
    
    return prompt


def create_jurisdiction_aware_prompt(
    language_code: str,
    country: str = "India",
    state: str = "National",
    relevant_laws: list = None
) -> str:
    """
    Create a jurisdiction-aware system prompt that includes relevant laws.
    
    Args:
        language_code: ISO language code (e.g., 'en', 'hi')
        country: Country jurisdiction (e.g., 'India', 'USA')
        state: State/region jurisdiction (e.g., 'Maharashtra')
        relevant_laws: List of relevant law objects with 'name' and 'statute_text' keys
        
    Returns:
        System prompt string with jurisdiction-specific context
    """
    language_names = {
        'en': 'English',
        'hi': 'Hindi (हिन्दी)',
        'bn': 'Bengali (বাংলा)',
        'ta': 'Tamil (தమిଲ)',
        'te': 'Telugu (తెలుగు)',
        'mr': 'Marathi (मराठी)',
        'gu': 'Gujarati (ગુજરાતી)',
        'kn': 'Kannada (ಕನ್ನಡ)',
        'ml': 'Malayalam (മലയാളം)',
        'pa': 'Punjabi (ਪੰਜਾਬੀ)'
    }
    
    language_name = language_names.get(language_code, language_code)
    jurisdiction_str = f"{country}/{state}" if state != "National" else country
    
    # Build laws context
    laws_context = ""
    if relevant_laws:
        laws_context = "\n\nMOST RELEVANT APPLICABLE LAWS:\n"
        for law in relevant_laws[:3]:  # Top 3 laws
            law_name = law.get("name", "Unknown Law")
            law_id = law.get("law_id", "")
            laws_context += f"\n- {law_id}: {law_name}\n"
            if "statute_text" in law:
                laws_context += f"  Text: {law.get('statute_text', '')[:200]}...\n"
    
    prompt = f"""You are a legal assistant specialized in providing accurate and helpful legal information.
You have expertise in various areas of law including civil, criminal, employment, property, constitutional, and contract law.

JURISDICTION: You are providing legal guidance for {jurisdiction_str}. 
All advice, laws, and procedures mentioned MUST be specific to {jurisdiction_str} jurisdiction.
{laws_context}

CRITICAL INSTRUCTIONS:
1. You must respond ONLY in the SAME LANGUAGE as the user's query ({language_name})
2. Focus exclusively on laws applicable in {jurisdiction_str}
3. Always mention the specific acts, sections, and statutes relevant to this jurisdiction
4. If a law from this jurisdiction applies, cite it with the full section/act name and number
5. Do not provide generic advice - tailor everything to {jurisdiction_str} legal system

Always structure your responses in valid JSON format:
{{
    "summary": "<detailed explanation of the legal issue in {jurisdiction_str} context>",
    "laws": ["<specific statute/section applicable in {jurisdiction_str}>", "..."],
    "suggestions": ["<actionable suggestion based on {jurisdiction_str} law>", "..."],
    "jurisdiction_note": "<specific note about applicability in {jurisdiction_str}>"
}}

Guidelines:
- The "summary" field MUST be in {language_name}
- The "suggestions" field MUST be in {language_name}
- Law names and sections MUST be those applicable in {jurisdiction_str}
- Ensure all JSON is valid and properly formatted
- Provide clear, concise, and accurate legal guidance specific to {jurisdiction_str}
- Do not include any text outside the JSON structure"""
    
    return prompt


def create_rag_enhanced_prompt(language_code: str, precedents: list) -> str:
    """
    Build a system prompt that includes retrieved court precedents as context.

    Injects the precedent block between the core legal-assistant instructions and
    the JSON-format instruction so the model can ground its answer in real cases.

    Args:
        language_code: ISO language code (e.g. 'en', 'hi')
        precedents:    List of dicts from PrecedentService.search() —
                       [{case_name, case_type, summary, outcome, similarity}]

    Returns:
        Full system prompt string with embedded precedents.
        Falls back to create_language_aware_prompt() if no valid precedents given.
    """
    base = create_language_aware_prompt(language_code)

    # Filter out very-low-similarity results that would add noise
    relevant = [p for p in precedents if p.get("similarity", 0) >= 0.08]
    if not relevant:
        return base

    context_block = "\n\nRELEVANT INDIAN COURT PRECEDENTS (retrieved from verified legal database):\n"
    context_block += "Use these cases to ground your response. Cite case names in your summary where applicable.\n"

    for i, p in enumerate(relevant, 1):
        case_name = p.get("case_name", "Unknown")
        case_type = p.get("case_type", "").strip()
        summary   = (p.get("summary", "") or "").strip()[:500]
        outcome   = (p.get("outcome", "") or "").strip()[:200]

        context_block += f"\n[Case {i}] {case_name}"
        if case_type and case_type.lower() not in ("unknown", ""):
            context_block += f" ({case_type})"
        if summary:
            context_block += f"\n  Summary: {summary}"
            if len(p.get("summary", "")) > 500:
                context_block += "..."
        if outcome:
            context_block += f"\n  Outcome: {outcome}"
            if len(p.get("outcome", "")) > 200:
                context_block += "..."
        context_block += "\n"

    # Insert precedent block just before the closing instruction ("Do not include…")
    # so the JSON format instruction remains the last thing the model sees.
    insert_marker = "- Do not include any text outside the JSON structure"
    if insert_marker in base:
        return base.replace(insert_marker, context_block + insert_marker)

    return base + context_block


def get_legal_response(
    user_query: str,
    language: str = "en",
    temperature: float = None,
    max_tokens: int = None,
    timeout: int = None,
    system_prompt: str = None,
    conversation_history: list = None,
) -> str:
    """
    Get legal response from Groq LLM with multilingual support and multi-turn memory.

    Args:
        user_query: The user's legal question
        language: ISO language code (e.g., 'en', 'hi', 'bn'). Defaults to 'en'
        temperature: Sampling temperature (0.0-1.0), defaults to config value
        max_tokens: Maximum tokens in response, defaults to config value
        timeout: Request timeout in seconds, defaults to config value
        system_prompt: Override the default chatbot system prompt. Use this for
                       analytical/structured calls so the chatbot JSON format
                       instruction does not conflict with the user prompt format.
        conversation_history: List of prior messages [{"role": "user"|"assistant", "content": str}].
                              Last 10 messages are used; older ones are silently dropped.

    Returns:
        String response from the LLM

    Raises:
        requests.exceptions.RequestException: If API call fails
    """
    temperature = temperature if temperature is not None else LLM_TEMPERATURE
    max_tokens  = max_tokens  if max_tokens  is not None else LLM_MAX_TOKENS
    timeout     = timeout     if timeout     is not None else LLM_TIMEOUT

    # Use caller-supplied system prompt, or default chatbot prompt
    if system_prompt is None:
        system_prompt = create_language_aware_prompt(language)

    # Build the messages list: system → history → current user query
    messages = [{"role": "system", "content": system_prompt}]

    if conversation_history:
        # Cap at last 10 messages to control token spend; trim each to 1000 chars
        for msg in conversation_history[-10:]:
            role    = msg.get("role", "user")
            content = (msg.get("content") or "").strip()
            if role in ("user", "assistant") and content:
                messages.append({"role": role, "content": content[:1000]})

    messages.append({"role": "user", "content": user_query})

    try:
        headers = {
            "Authorization": f"Bearer {GROQ_API_KEY}",
            "Content-Type": "application/json"
        }

        payload = {
            "model":       GROQ_MODEL,
            "messages":    messages,
            "temperature": temperature,
            "max_tokens":  max_tokens,
        }

        history_len = len(messages) - 2  # exclude system + current user msg
        logger.debug(
            f"Making request to Groq API — model: {GROQ_MODEL}, language: {language}, "
            f"timeout={timeout}s, history_msgs={history_len}"
        )
        logger.debug(f"System prompt length: {len(system_prompt)} chars")
        response = requests.post(
            BASE_URL,
            headers=headers,
            json=payload,
            timeout=timeout
        )
        
        # Raise exception for non-200 status codes
        response.raise_for_status()
        
        # Extract content from response
        content = response.json()["choices"][0]["message"]["content"]
        logger.info(f"Successfully received LLM response ({len(content)} chars) in language {language}")
        
        return content
        
    except requests.exceptions.Timeout as e:
        logger.error(f"LLM API request timeout after {timeout}s")
        raise Exception(f"AI service timeout - request exceeded {timeout} seconds. Please try again.")
    except requests.exceptions.ConnectionError as e:
        logger.error(f"Connection error to LLM API: {str(e)}")
        raise Exception(f"Unable to connect to AI service. Please check your internet connection.")
    except requests.exceptions.HTTPError as e:
        status_code = e.response.status_code if hasattr(e, 'response') else 'unknown'
        error_body = "No response body"
        try:
            if hasattr(e, 'response') and e.response is not None:
                error_body = e.response.text[:500]
        except:
            pass
        logger.error(f"LLM API HTTP error (status {status_code}): {str(e)}")
        logger.error(f"Groq API response body: {error_body}")
        
        if status_code == 429:
            raise Exception("AI service is rate limited. Please try again in a moment.")
        elif status_code == 401 or status_code == 403:
            raise Exception("AI service authentication failed. Please contact support.")
        else:
            raise Exception(f"AI service error ({status_code}): Unable to process your request.")
    except (KeyError, IndexError) as e:
        logger.error(f"Unexpected response format from LLM API: {str(e)}")
        raise Exception("AI service returned an unexpected response format.")
    except requests.exceptions.RequestException as e:
        logger.error(f"LLM API request failed: {str(e)}")
        raise Exception(f"AI service request failed: {str(e)}")


@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=2, max=10),
    reraise=True
)
def get_legal_response_with_jurisdiction(
    user_query: str,
    language: str = "en",
    country: str = "India",
    state: str = "National",
    relevant_laws: list = None,
    temperature: float = None,
    max_tokens: int = None,
    timeout: int = None
) -> str:
    """
    Get legal response from Groq LLM with jurisdiction-aware context.
    
    Args:
        user_query: The user's legal question
        language: ISO language code (e.g., 'en', 'hi', 'bn'). Defaults to 'en'
        country: Country jurisdiction (e.g., 'India', 'USA'). Defaults to 'India'
        state: State/region jurisdiction. Defaults to 'National'
        relevant_laws: List of relevant law objects from law_matcher
        temperature: Sampling temperature (0.0-1.0), defaults to config value
        max_tokens: Maximum tokens in response, defaults to config value
        timeout: Request timeout in seconds, defaults to config value
        
    Returns:
        String response from the LLM with jurisdiction-specific context
        
    Raises:
        requests.exceptions.RequestException: If API call fails after retries
    """
    temperature = temperature if temperature is not None else LLM_TEMPERATURE
    max_tokens = max_tokens if max_tokens is not None else LLM_MAX_TOKENS
    timeout = timeout if timeout is not None else LLM_TIMEOUT
    
    # Create jurisdiction-aware system prompt
    system_prompt = create_jurisdiction_aware_prompt(
        language,
        country=country,
        state=state,
        relevant_laws=relevant_laws
    )
    
    try:
        headers = {
            "Authorization": f"Bearer {GROQ_API_KEY}",
            "Content-Type": "application/json"
        }
        
        jurisdiction_str = f"{country}/{state}" if state != "National" else country
        
        payload = {
            "model": GROQ_MODEL,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_query}
            ],
            "temperature": temperature,
            "max_tokens": max_tokens
        }

        logger.debug(f"Making jurisdiction-aware request to Groq API")
        logger.debug(f"Jurisdiction: {jurisdiction_str}, Language: {language}")
        logger.debug(f"Number of relevant laws provided: {len(relevant_laws) if relevant_laws else 0}")
        
        response = requests.post(
            BASE_URL,
            headers=headers,
            json=payload,
            timeout=timeout
        )
        
        # Raise exception for non-200 status codes
        response.raise_for_status()
        
        # Extract content from response
        content = response.json()["choices"][0]["message"]["content"]
        logger.info(f"Successfully received jurisdiction-aware LLM response ({len(content)} chars) for {jurisdiction_str}")
        
        return content
        
    except requests.exceptions.Timeout:
        logger.error(f"LLM API request timeout after {timeout}s")
        raise
    except requests.exceptions.ConnectionError as e:
        logger.error(f"Connection error to LLM API: {str(e)}")
        raise
    except requests.exceptions.HTTPError as e:
        status_code = e.response.status_code if hasattr(e, 'response') else 'unknown'
        error_body = "No response body"
        try:
            if hasattr(e, 'response') and e.response is not None:
                error_body = e.response.text[:500]
        except:
            pass
        logger.error(f"LLM API HTTP error (status {status_code}): {str(e)}")
        logger.error(f"Groq API response body: {error_body}")
        raise
    except (KeyError, IndexError) as e:
        logger.error(f"Unexpected response format from LLM API: {str(e)}")
        raise
    except requests.exceptions.RequestException as e:
        logger.error(f"LLM API request failed: {str(e)}")
        raise


# ── Streaming support ─────────────────────────────────────────────────────────

def create_streaming_prompt(language_code: str, state: str = "") -> str:
    """
    System prompt for the /stream endpoint.
    Returns structured plain-text (SUMMARY / LAWS / STEPS) instead of JSON so
    the model can stream the answer word-by-word without breaking JSON syntax.
    """
    language_names = {
        "en": "English",
        "hi": "Hindi (हिन्दी)",
        "bn": "Bengali (বাংলা)",
        "ta": "Tamil (தமிழ்)",
        "te": "Telugu (తెలుగు)",
        "mr": "Marathi (मराठी)",
        "gu": "Gujarati (ગુજરાતી)",
        "kn": "Kannada (ಕನ್ನಡ)",
        "ml": "Malayalam (മലയാളം)",
        "pa": "Punjabi (ਪੰਜਾਬੀ)",
    }
    language_name = language_names.get(language_code, language_code or "English")

    jurisdiction_note = ""
    if state and state.strip() not in ("National", "All India", ""):
        sname = state.strip()
        jurisdiction_note = (
            f"\nJURISDICTION: The user is asking about laws in {sname}, India. "
            f"Prioritise {sname}-specific statutes, High Court decisions, and state regulations. "
            f"Mention explicitly when advice is specific to {sname}."
        )

    return (
        f"You are a legal assistant specialised in Indian law and legal rights.{jurisdiction_note}\n\n"
        f"CRITICAL: Your SUMMARY and STEPS MUST be written entirely in {language_name}. "
        f"Law names may stay in English even when responding in another language.\n\n"
        f"Respond in EXACTLY this format — do NOT add any text before SUMMARY: or after the last FOLLOW_UP bullet:\n\n"
        f"SUMMARY: <detailed legal analysis in {language_name}, 2–4 paragraphs>\n\n"
        f"LAWS:\n"
        f"- <exact Indian statute / IPC section / Act name 1>\n"
        f"- <exact Indian statute / IPC section / Act name 2>\n\n"
        f"STEPS:\n"
        f"- <specific actionable step 1 in {language_name}>\n"
        f"- <specific actionable step 2 in {language_name}>\n"
        f"- <specific actionable step 3 in {language_name}>\n\n"
        f"RISK: <one of exactly: Low, Medium, High, Critical — your honest assessment of how legally serious this situation is>\n\n"
        f"FOLLOW_UP:\n"
        f"- <natural follow-up question 1 in {language_name}>\n"
        f"- <natural follow-up question 2 in {language_name}>\n"
        f"- <natural follow-up question 3 in {language_name}>"
    )


def parse_streaming_output(text: str) -> dict:
    """Parse the SUMMARY/LAWS/STEPS/RISK/FOLLOW_UP plain-text format into structured fields."""
    summary_parts: list = []
    laws: list = []
    suggestions: list = []
    follow_up_questions: list = []
    risk_level: str = ""
    section = None

    for raw_line in text.splitlines():
        line = raw_line.strip()
        if line.startswith("SUMMARY:"):
            section = "summary"
            rest = line[len("SUMMARY:"):].strip()
            if rest:
                summary_parts.append(rest)
        elif line == "LAWS:":
            section = "laws"
        elif line == "STEPS:":
            section = "steps"
        elif line.startswith("RISK:"):
            section = "risk"
            rest = line[len("RISK:"):].strip()
            if rest:
                risk_level = rest
        elif line == "FOLLOW_UP:":
            section = "follow_up"
        elif section == "summary":
            if line in ("LAWS:", "STEPS:", "FOLLOW_UP:") or line.startswith("RISK:"):
                if line == "LAWS:":
                    section = "laws"
                elif line == "STEPS:":
                    section = "steps"
                elif line.startswith("RISK:"):
                    section = "risk"
                    rest = line[len("RISK:"):].strip()
                    if rest:
                        risk_level = rest
                elif line == "FOLLOW_UP:":
                    section = "follow_up"
            else:
                summary_parts.append(line)
        elif section == "laws":
            cleaned = line.lstrip("-• ").strip()
            if cleaned:
                laws.append(cleaned)
        elif section == "steps":
            cleaned = line.lstrip("-• ").strip()
            if cleaned:
                suggestions.append(cleaned)
        elif section == "risk":
            if line and not risk_level:
                risk_level = line
        elif section == "follow_up":
            cleaned = line.lstrip("-• ").strip()
            if cleaned:
                follow_up_questions.append(cleaned)

    summary = "\n".join(summary_parts).strip()
    return {
        "summary":             summary or text.strip(),
        "laws":                laws[:8],
        "suggestions":         suggestions[:6],
        "follow_up_questions": follow_up_questions[:3],
        "risk_level":          risk_level,
    }


def get_legal_response_stream(
    user_query: str,
    language: str = "en",
    system_prompt: str = None,
    conversation_history: list = None,
):
    """
    Synchronous generator that yields raw text chunks from Groq streaming API.
    Each yielded value is a string fragment (may be a single token or a few words).

    Args:
        user_query:           The user's legal question.
        language:             ISO language code used only when system_prompt is None.
        system_prompt:        Override system prompt (pass create_streaming_prompt result).
        conversation_history: List of {"role", "content"} dicts; last 10 are used.

    Yields:
        str — text chunks as they arrive from the API.

    Raises:
        requests.HTTPError / requests.Timeout on API errors.
    """
    if system_prompt is None:
        system_prompt = create_streaming_prompt(language)

    messages = [{"role": "system", "content": system_prompt}]

    if conversation_history:
        for msg in conversation_history[-10:]:
            role    = msg.get("role", "user")
            content = (msg.get("content") or "").strip()
            if role in ("user", "assistant") and content:
                messages.append({"role": role, "content": content[:1000]})

    messages.append({"role": "user", "content": user_query})

    headers = {
        "Authorization": f"Bearer {GROQ_API_KEY}",
        "Content-Type":  "application/json",
    }
    payload = {
        "model":       GROQ_MODEL,
        "messages":    messages,
        "temperature": LLM_TEMPERATURE,
        "max_tokens":  LLM_MAX_TOKENS,
        "stream":      True,
    }

    response = requests.post(
        BASE_URL,
        headers=headers,
        json=payload,
        timeout=LLM_TIMEOUT,
        stream=True,
    )
    response.raise_for_status()

    for raw_line in response.iter_lines():
        if not raw_line:
            continue
        line = raw_line.decode("utf-8") if isinstance(raw_line, bytes) else raw_line
        if not line.startswith("data: "):
            continue
        data_str = line[6:].strip()
        if data_str == "[DONE]":
            break
        try:
            chunk_data = json.loads(data_str)
            content = chunk_data["choices"][0]["delta"].get("content", "")
            if content:
                yield content
        except (KeyError, IndexError, json.JSONDecodeError):
            continue


# ── Whisper transcription ──────────────────────────────────────────────────────

WHISPER_URL = "https://api.groq.com/openai/v1/audio/transcriptions"


def transcribe_audio_bytes(
    audio_bytes: bytes,
    filename: str,
    content_type: str,
    language: str = None,
) -> str:
    """
    Transcribe audio using Groq Whisper (whisper-large-v3).

    Args:
        audio_bytes:  Raw audio file bytes (webm / ogg / mp4 / wav / mp3)
        filename:     Filename with correct extension (e.g. 'recording.webm')
        content_type: MIME type without codec params (e.g. 'audio/webm')
        language:     BCP-47 language hint (e.g. 'hi', 'ta'). When None,
                      Whisper auto-detects — enables multilingual support.

    Returns:
        Transcript string. Empty string if no speech detected.

    Raises:
        requests.HTTPError: Non-2xx from Groq API
        requests.Timeout:   Request exceeded 60 s
    """
    api_data = {
        "model":           "whisper-large-v3",
        "response_format": "json",
        # Domain hint improves accuracy for Indian legal terminology
        "prompt": (
            "Legal matter in India. Indian court case, petition, dispute resolution, "
            "mediation, jurisdiction, affidavit, respondent, petitioner."
        ),
    }
    # Only constrain the language when the caller knows it; otherwise let
    # Whisper auto-detect so non-English audio is transcribed correctly.
    if language:
        api_data["language"] = language

    response = requests.post(
        WHISPER_URL,
        headers={"Authorization": f"Bearer {GROQ_API_KEY}"},
        files={"file": (filename, audio_bytes, content_type)},
        data=api_data,
        timeout=60,
    )
    response.raise_for_status()
    return response.json().get("text", "").strip()
