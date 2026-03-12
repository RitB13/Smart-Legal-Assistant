import json

def parse_llm_output(raw_output: str):
    try:
        return json.loads(raw_output)
    except Exception:
        return {"summary": raw_output, "laws": [], "suggestions": []}
