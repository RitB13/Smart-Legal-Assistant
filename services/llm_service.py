import requests
from config import GROQ_API_KEY, GROQ_MODEL

BASE_URL = "https://api.groq.com/openai/v1/chat/completions"

def get_legal_response(user_query: str):
    headers = {"Authorization": f"Bearer {GROQ_API_KEY}"}
    payload = {
        "model": GROQ_MODEL,
        "messages": [
            {"role": "system", "content": "You are a legal assistant. Always structure responses in this JSON format: { 'summary': '...', 'laws': ['law1', 'law2'], 'suggestions': ['...'] }"},
            {"role": "user", "content": user_query}
        ],
        "temperature": 0.3
    }

    response = requests.post(BASE_URL, headers=headers, json=payload)
    response.raise_for_status()
    return response.json()["choices"][0]["message"]["content"]
