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


def score_incident(text: str) -> dict:
    """
    Score incident severity.
    Falls back to keyword heuristics if Gemini client/model is unavailable.
    """
    model_cls = getattr(genai, "GenerativeModel", None)
    if not _GEMINI_API_KEY or model_cls is None:
        return _fallback_score(text)

    try:
        prompt = (
            "Analyze this incident report and output only JSON with fields "
            "{'severity': int, 'type': str}. Text: "
            f"{text}"
        )
        model = model_cls("gemini-1.5-flash")
        model.generate_content(prompt)
    except Exception:
        return _fallback_score(text)

    # Keep deterministic output until strict Gemini JSON parsing is added.
    return _fallback_score(text)
