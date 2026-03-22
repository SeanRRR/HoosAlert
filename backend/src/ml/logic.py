# logic.py - Resilient severity scoring with optional Gemini support
import os

import google.generativeai as genai

_GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
if _GEMINI_API_KEY:
    genai.configure(api_key=_GEMINI_API_KEY)


def _fallback_score(text: str) -> dict:
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


def score_incident(text: str) -> dict:
    """
    Score incident severity.
    Falls back to keyword heuristics if Gemini client/model is unavailable.
    """
    if not _GEMINI_API_KEY:
        return _fallback_score(text)
    return _ai_score(text)
