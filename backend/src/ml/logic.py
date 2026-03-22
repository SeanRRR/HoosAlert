import json
import os
import re
from typing import Any

import google.generativeai as genai

# Configure Gemini API key
_GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
if _GEMINI_API_KEY:
    genai.configure(api_key=_GEMINI_API_KEY)

# High-impact keywords for validation
HIGH_IMPACT_KEYWORDS = ["fire", "weapon", "active", "medical", "unconscious", "shooter", "bomb"]
_MAX_HISTORY_ITEMS = 25

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

def _extract_json_dict(raw_text: str) -> dict[str, Any] | None:
    if not raw_text:
        return None

    raw = raw_text.strip()
    if raw.startswith("```"):
        raw = re.sub(r"^```(?:json)?\s*", "", raw)
        raw = re.sub(r"\s*```$", "", raw)

    try:
        payload = json.loads(raw)
        if isinstance(payload, dict):
            return payload
    except json.JSONDecodeError:
        pass

    match = re.search(r"\{.*\}", raw, flags=re.DOTALL)
    if not match:
        return None

    try:
        payload = json.loads(match.group(0))
        if isinstance(payload, dict):
            return payload
    except json.JSONDecodeError:
        return None
    return None


def _normalize_ai_result(payload: dict[str, Any], fallback_text: str) -> dict:
    fallback = _fallback_score(fallback_text)

    try:
        severity = int(payload.get("severity", fallback["severity"]))
    except (TypeError, ValueError):
        severity = fallback["severity"]

    severity = max(1, min(severity, 5))
    incident_type = payload.get("type", fallback["type"])
    if not isinstance(incident_type, str) or not incident_type.strip():
        incident_type = fallback["type"]

    return {"severity": severity, "type": incident_type}


def _summarize_history(history: list[dict[str, Any]] | None) -> str:
    if not history:
        return "No recent incident context available."

    lines = []
    for item in history[:_MAX_HISTORY_ITEMS]:
        if not isinstance(item, dict):
            continue

        title = item.get("title") or item.get("incidentType") or item.get("incident_type") or "Unknown"
        location = item.get("location") or "Unknown"
        severity = item.get("severity", "unknown")
        when = item.get("created_at") or item.get("timestamp") or "unknown"
        source = item.get("source", "unknown")
        description = item.get("description") or ""
        lines.append(
            f"- title={title}; location={location}; severity={severity}; "
            f"source={source}; time={when}; description={description}"
        )

    if not lines:
        return "No recent incident context available."

    return "\n".join(lines)


def _ai_score(text: str, history: list[dict[str, Any]] | None = None) -> dict:
    """
    Use Gemini AI to score the incident severity.
    Returns a fallback score in case of errors or unavailability.
    """
    try:
        history_text = _summarize_history(history)
        prompt = (
            "You are scoring campus safety incident reports. "
            "Use the current report and the recent incident history for context. "
            "Return ONLY valid JSON with this shape: "
            "{\"severity\": <integer 1-5>, \"type\": \"<short label>\"}.\n\n"
            f"Current report:\n{text}\n\n"
            f"Recent incident history (most recent first):\n{history_text}"
        )
        model_cls = getattr(genai, "GenerativeModel", None)
        if not model_cls:
            raise RuntimeError("GenerativeModel class not found in genai module.")
        model = model_cls("gemini-1.5-flash")
        response = model.generate_content(prompt)
        response_text = getattr(response, "text", "") or ""
        payload = _extract_json_dict(response_text)
        if payload is None:
            return _fallback_score(text)
        return _normalize_ai_result(payload, text)
    except Exception:
        return _fallback_score(text)

def validate_score(text: str, ai_score: int) -> int:
    """
    Override AI score if high-impact keywords are present but the score is low.
    """
    if any(keyword in text.lower() for keyword in HIGH_IMPACT_KEYWORDS) and ai_score < 4:
        return 5
    return ai_score

def _normalize_input(data: str | dict) -> str:
    """
    Normalize either raw text or a structured report dict into a single text blob.
    """
    if isinstance(data, str):
        return data

    if isinstance(data, dict):
        incident_type = data.get("incident_type") or data.get("incidentType") or data.get("title") or ""
        location = data.get("location") or ""
        reporter = data.get("computingID") or data.get("computingId") or data.get("reporter_id") or ""
        timestamp = data.get("timestamp") or data.get("created_at") or ""
        description = data.get("description") or ""

        return (
            f"Incident Type: {incident_type}, "
            f"Description: {description}, "
            f"Location: {location}, "
            f"Reporter: {reporter}, "
            f"Timestamp: {timestamp}"
        )

    return str(data)


def score_incident(data: str | dict, history: list[dict[str, Any]] | None = None) -> dict:
    """
    Score incident severity.
    Accepts structured input (dictionary) and combines fields into a single text string.
    Falls back to keyword heuristics if Gemini client/model is unavailable.
    """
    text = _normalize_input(data)
    if not _GEMINI_API_KEY:
        return _fallback_score(text)
    
    # Get AI score and validate it
    ai_result = _ai_score(text, history=history)
    ai_result["severity"] = validate_score(text, ai_result["severity"])
    return ai_result
