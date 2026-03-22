import json
import os
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from google import genai

_GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
_GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")

_DEBUG_AI_SCORING = os.getenv("DEBUG_AI_SCORING", "").lower() in {"1", "true", "yes", "on"}
_PROMPT_VERSION = "v2"

# High-impact keywords for validation
HIGH_IMPACT_KEYWORDS = ["fire", "weapon", "active", "medical", "unconscious", "shooter", "bomb"]
_MAX_HISTORY_ITEMS = 25
_GEMINI_CONTEXT_PATH = Path(__file__).resolve().parents[2] / "data" / "gemini_context.md"


def _debug_ai(message: str) -> None:
    if _DEBUG_AI_SCORING:
        print(f"[ai-score-debug] {message}", file=sys.stderr)


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _load_gemini_context() -> str:
    try:
        return _GEMINI_CONTEXT_PATH.read_text(encoding="utf-8").strip()
    except OSError:
        return (
            "Score campus safety incidents using a 1-5 severity scale. "
            "Use short incident type labels and return only valid JSON."
        )


def _build_genai_client() -> genai.Client:
    if not _GEMINI_API_KEY:
        raise RuntimeError("GEMINI_API_KEY is not configured.")
    return genai.Client(api_key=_GEMINI_API_KEY)


def _response_text(response: Any) -> str:
    text = getattr(response, "text", "") or ""
    if text:
        return text

    candidates = getattr(response, "candidates", None) or []
    if not candidates:
        return ""

    first_candidate = candidates[0]
    content = getattr(first_candidate, "content", None)
    parts = getattr(content, "parts", None) or []
    fragments = []
    for part in parts:
        fragment = getattr(part, "text", None)
        if fragment:
            fragments.append(fragment)
    return "".join(fragments)

def _sanitize_reason_codes(raw_codes: Any, default_code: str) -> list[str]:
    if not isinstance(raw_codes, list):
        return [default_code]

    clean_codes = []
    for item in raw_codes:
        if not isinstance(item, str):
            continue
        normalized = re.sub(r"[^a-z0-9_]+", "_", item.strip().lower()).strip("_")
        if normalized:
            clean_codes.append(normalized)

    return clean_codes or [default_code]


def _context_count(history: list[dict[str, Any]] | None) -> int:
    if not history:
        return 0
    return sum(1 for item in history[:_MAX_HISTORY_ITEMS] if isinstance(item, dict))


def _fallback_score(text: str, history: list[dict[str, Any]] | None = None) -> dict:
    lowered = text.lower()
    context_count = _context_count(history)

    high_risk = ["fire", "weapon", "active shooter", "unconscious", "medical emergency"]
    medium_risk = ["suspicious", "assault", "fight", "theft", "harassment"]
    low_risk = ["traffic", "collision", "accident", "noise", "maintenance"]

    if any(token in lowered for token in high_risk):
        return {
            "severity": 5,
            "risk_label": "high_risk",
            "confidence": 0.35,
            "reason_codes": ["fallback_keyword_high_risk"],
            "model_version": _GEMINI_MODEL,
            "prompt_version": _PROMPT_VERSION,
            "context_count": context_count,
            "fallback_used": True,
            "scored_at": _utc_now_iso(),
        }
    if any(token in lowered for token in medium_risk):
        return {
            "severity": 4,
            "risk_label": "security",
            "confidence": 0.35,
            "reason_codes": ["fallback_keyword_security"],
            "model_version": _GEMINI_MODEL,
            "prompt_version": _PROMPT_VERSION,
            "context_count": context_count,
            "fallback_used": True,
            "scored_at": _utc_now_iso(),
        }
    if any(token in lowered for token in low_risk):
        return {
            "severity": 2,
            "risk_label": "general",
            "confidence": 0.35,
            "reason_codes": ["fallback_keyword_general"],
            "model_version": _GEMINI_MODEL,
            "prompt_version": _PROMPT_VERSION,
            "context_count": context_count,
            "fallback_used": True,
            "scored_at": _utc_now_iso(),
        }
    return {
        "severity": 3,
        "risk_label": "unknown",
        "confidence": 0.25,
        "reason_codes": ["fallback_unknown"],
        "model_version": _GEMINI_MODEL,
        "prompt_version": _PROMPT_VERSION,
        "context_count": context_count,
        "fallback_used": True,
        "scored_at": _utc_now_iso(),
    }

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


def _normalize_ai_result(
    payload: dict[str, Any],
    fallback_text: str,
    history: list[dict[str, Any]] | None = None,
) -> dict:
    fallback = _fallback_score(fallback_text, history=history)

    try:
        severity = int(payload.get("severity", fallback["severity"]))
    except (TypeError, ValueError):
        severity = fallback["severity"]

    severity = max(1, min(severity, 5))
    risk_label = payload.get("risk_label") or payload.get("type") or fallback["risk_label"]
    if not isinstance(risk_label, str) or not risk_label.strip():
        risk_label = fallback["risk_label"]
    risk_label = risk_label.strip()

    try:
        confidence = float(payload.get("confidence", fallback["confidence"]))
    except (TypeError, ValueError):
        confidence = fallback["confidence"]
    confidence = max(0.0, min(confidence, 1.0))

    reason_codes = _sanitize_reason_codes(
        payload.get("reason_codes"),
        default_code="model_generated",
    )

    return {
        "severity": severity,
        "risk_label": risk_label,
        "confidence": confidence,
        "reason_codes": reason_codes,
        "model_version": _GEMINI_MODEL,
        "prompt_version": _PROMPT_VERSION,
        "context_count": _context_count(history),
        "fallback_used": False,
        "scored_at": _utc_now_iso(),
    }


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
        guidance_text = _load_gemini_context()
        prompt = (
            "You are scoring campus safety incident reports. "
            "Use the scoring guidance, the current report, and the recent incident "
            "history for context. Return ONLY valid JSON with this shape: "
            "{\"severity\": <integer 1-5>, "
            "\"risk_label\": \"<short label>\", "
            "\"confidence\": <float 0-1>, "
            "\"reason_codes\": [\"<snake_case_reason>\"]}.\n\n"
            f"Scoring guidance:\n{guidance_text}\n\n"
            f"Current report:\n{text}\n\n"
            f"Recent incident history (most recent first):\n{history_text}"
        )
        client = _build_genai_client()
        response = client.models.generate_content(model=_GEMINI_MODEL, contents=prompt)
        response_text = _response_text(response)
        _debug_ai(f"Gemini raw response: {response_text!r}")
        payload = _extract_json_dict(response_text)
        if payload is None:
            _debug_ai("Gemini response could not be parsed as JSON; using fallback score.")
            return _fallback_score(text, history=history)
        _debug_ai(f"Gemini parsed payload: {payload}")
        return _normalize_ai_result(payload, text, history=history)
    except Exception as exc:
        _debug_ai(f"Gemini request failed: {exc!r}; using fallback score.")
        return _fallback_score(text, history=history)

def validate_score(text: str, ai_score: int) -> int:
    """
    Override AI score if high-impact keywords are present but the score is low.
    """
    if any(keyword in text.lower() for keyword in HIGH_IMPACT_KEYWORDS) and ai_score < 4:
        return 5
    return ai_score

def _normalize_incident(data: str | dict) -> dict[str, Any]:
    if isinstance(data, dict):
        return dict(data)
    if isinstance(data, str):
        return {"description": data}
    return {"description": str(data)}


def _incident_to_text(incident: dict[str, Any]) -> str:
    incident_type = incident.get("incident_type") or incident.get("incidentType") or incident.get("title") or ""
    location = incident.get("location") or ""
    reporter = incident.get("computingID") or incident.get("computingId") or incident.get("reporter_id") or ""
    timestamp = incident.get("timestamp") or incident.get("created_at") or ""
    description = incident.get("description") or incident.get("text") or ""

    return (
        f"Incident Type: {incident_type}, "
        f"Description: {description}, "
        f"Location: {location}, "
        f"Reporter: {reporter}, "
        f"Timestamp: {timestamp}"
    )


def _apply_score_validation(text: str, score: dict[str, Any]) -> dict[str, Any]:
    validated = dict(score)
    original_severity = validated["severity"]
    validated_severity = validate_score(text, original_severity)
    validated["severity"] = validated_severity
    if validated_severity != original_severity:
        reason_codes = list(validated.get("reason_codes", []))
        if "validator_high_impact_keyword" not in reason_codes:
            reason_codes.append("validator_high_impact_keyword")
        validated["reason_codes"] = reason_codes
    return validated


def score_incident(data: str | dict, history: list[dict[str, Any]] | None = None) -> dict:
    """
    Score incident severity.
    Accepts structured input (dictionary) and combines fields into a single text string.
    Falls back to keyword heuristics if Gemini client/model is unavailable.
    """
    incident = _normalize_incident(data)
    text = _incident_to_text(incident)
    if not _GEMINI_API_KEY:
        score = _fallback_score(text, history=history)
        return {"incident": incident, "score": _apply_score_validation(text, score)}
    
    score = _ai_score(text, history=history)
    return {"incident": incident, "score": _apply_score_validation(text, score)}
