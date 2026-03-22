import os
import google.generativeai as genai

# Configure Gemini API key
_GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
if _GEMINI_API_KEY:
    genai.configure(api_key=_GEMINI_API_KEY)

# High-impact keywords for validation
HIGH_IMPACT_KEYWORDS = ["fire", "weapon", "active", "medical", "unconscious", "shooter", "bomb"]

def _fallback_score(text: str) -> dict:
    """
    Fallback scoring based on keyword heuristics.
    """
    lowered = text.lower()

    high_risk = ["fire", "weapon", "active shooter", "unconscious", "medical emergency"]
    medium_risk = ["suspicious", "assault", "fight", "theft", "harassment"]
    low_risk = ["traffic", "collision", "accident", "noise", "maintenance"]

    if any(token in lowered for token in high_risk):
        return {"severity": 5, "type": "high_risk"}
    if any(token in lowered for token in medium_risk):
        return {"severity": 4, "type": "security"}
    if any(token in lowered for token in low_risk):
        return {"severity": 2, "type": "general"}
    return {"severity": 3, "type": "unknown"}

def _ai_score(text: str) -> dict:
    """
    Use Gemini AI to score the incident severity.
    Returns a fallback score in case of errors or unavailability.
    """
    try:
        prompt = (
            "Analyze this incident report and output only JSON with fields "
            "{'severity': int, 'type': str}. Text: "
            f"{text}"
        )
        model_cls = getattr(genai, "GenerativeModel", None)
        if not model_cls:
            raise RuntimeError("GenerativeModel class not found in genai module.")
        model = model_cls("gemini-1.5-flash")
        response = model.generate_content(prompt)
        # Assuming the response contains a JSON-like structure
        return response.get("data", _fallback_score(text))
    except Exception:
        return _fallback_score(text)

def validate_score(text: str, ai_score: int) -> int:
    """
    Override AI score if high-impact keywords are present but the score is low.
    """
    if any(keyword in text.lower() for keyword in HIGH_IMPACT_KEYWORDS) and ai_score < 4:
        return 5
    return ai_score

def score_incident(data: dict) -> dict:
    """
    Score incident severity.
    Accepts structured input (dictionary) and combines fields into a single text string.
    Falls back to keyword heuristics if Gemini client/model is unavailable.
    """
    # Combine the fields into a single string for processing
    text = (
        f"Incident Type: {data['incident_type']}, "
        f"Location: {data['location']}, "
        f"Computing ID: {data['computingID']}, "
        f"Timestamp: {data['timestamp']}"
    )
    if not _GEMINI_API_KEY:
        return _fallback_score(text)
    
    # Get AI score and validate it
    ai_result = _ai_score(text)
    ai_result["severity"] = validate_score(text, ai_result["severity"])
    return ai_result