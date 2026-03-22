import json
import math
import os
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from dotenv import load_dotenv

try:
    from google import genai  # google-genai
except ImportError:
    genai = None


_BACKEND_ENV_PATH = Path(__file__).resolve().parents[2] / ".env"
load_dotenv(_BACKEND_ENV_PATH, override=False)

_TIMESTAMP_FIELDS = ("timestamp", "created_at", "scored_at")
_LAT_FIELDS = ("latitude", "lat")
_LON_FIELDS = ("longitude", "lng", "lon")
_TEXT_FIELDS = ("description", "title", "incidentType", "incident_type", "risk_label", "location")


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _confidence_model() -> str:
    return os.getenv("GEMINI_CONFIDENCE_MODEL") or os.getenv("GEMINI_MODEL", "gemini-2.5-flash")


def _confidence_prompt_version() -> str:
    return os.getenv("CONFIDENCE_PROMPT_VERSION", "v1")


def _gemini_api_key() -> str:
    return os.getenv("GEMINI_API_KEY", "")


def _build_genai_client():
    if genai is None:
        raise RuntimeError("google-genai is not installed.")
    api_key = _gemini_api_key()
    if not api_key:
        raise RuntimeError("GEMINI_API_KEY is not configured.")
    return genai.Client(api_key=api_key)


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
    return "".join(getattr(part, "text", "") for part in parts if getattr(part, "text", None))


def _to_float(value: Any) -> float | None:
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _parse_timestamp(value: Any) -> datetime | None:
    if not isinstance(value, str) or not value.strip():
        return None
    try:
        normalized = value.strip().replace("Z", "+00:00")
        parsed = datetime.fromisoformat(normalized)
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=timezone.utc)
        return parsed.astimezone(timezone.utc)
    except ValueError:
        return None


def _incident_timestamp(incident: dict[str, Any]) -> datetime | None:
    for field in _TIMESTAMP_FIELDS:
        parsed = _parse_timestamp(incident.get(field))
        if parsed:
            return parsed
    return None


def _incident_coords(incident: dict[str, Any]) -> tuple[float | None, float | None]:
    lat = next((_to_float(incident.get(field)) for field in _LAT_FIELDS if _to_float(incident.get(field)) is not None), None)
    lon = next((_to_float(incident.get(field)) for field in _LON_FIELDS if _to_float(incident.get(field)) is not None), None)
    return lat, lon


def _tokenize(text: str) -> set[str]:
    return set(re.findall(r"[a-z0-9]+", text.lower()))


def _incident_text(incident: dict[str, Any]) -> str:
    values = []
    for field in _TEXT_FIELDS:
        value = incident.get(field)
        if isinstance(value, str) and value.strip():
            values.append(value.strip())
    return " | ".join(values)


def _jaccard_similarity(left: set[str], right: set[str]) -> float:
    if not left or not right:
        return 0.0
    union = left | right
    if not union:
        return 0.0
    return len(left & right) / len(union)


def _severity_similarity(incident1: dict[str, Any], incident2: dict[str, Any]) -> float | None:
    severity1 = _to_float(incident1.get("severity"))
    severity2 = _to_float(incident2.get("severity"))
    if severity1 is None or severity2 is None:
        return None
    return max(0.0, 1.0 - abs(severity1 - severity2) / 4.0)


def _risk_label_similarity(incident1: dict[str, Any], incident2: dict[str, Any]) -> float | None:
    label1 = incident1.get("risk_label") or incident1.get("incidentType") or incident1.get("incident_type")
    label2 = incident2.get("risk_label") or incident2.get("incidentType") or incident2.get("incident_type")
    if not isinstance(label1, str) or not isinstance(label2, str):
        return None
    tokens1 = _tokenize(label1)
    tokens2 = _tokenize(label2)
    if not tokens1 or not tokens2:
        return None
    if label1.strip().lower() == label2.strip().lower():
        return 1.0
    return _jaccard_similarity(tokens1, tokens2)


def _text_similarity(incident1: dict[str, Any], incident2: dict[str, Any]) -> float:
    return _jaccard_similarity(_tokenize(_incident_text(incident1)), _tokenize(_incident_text(incident2)))


def _haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    radius_km = 6371.0
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    delta_phi = math.radians(lat2 - lat1)
    delta_lambda = math.radians(lon2 - lon1)

    a = (
        math.sin(delta_phi / 2) ** 2
        + math.cos(phi1) * math.cos(phi2) * math.sin(delta_lambda / 2) ** 2
    )
    return 2 * radius_km * math.atan2(math.sqrt(a), math.sqrt(1 - a))


def _distance_similarity(incident1: dict[str, Any], incident2: dict[str, Any]) -> float | None:
    lat1, lon1 = _incident_coords(incident1)
    lat2, lon2 = _incident_coords(incident2)
    if None in (lat1, lon1, lat2, lon2):
        return None
    distance_km = _haversine_km(lat1, lon1, lat2, lon2)
    # Exponential spatial decay with roughly 1 km half-life.
    return math.exp(-distance_km / 1.0)


def _time_similarity(incident1: dict[str, Any], incident2: dict[str, Any]) -> float | None:
    ts1 = _incident_timestamp(incident1)
    ts2 = _incident_timestamp(incident2)
    if ts1 is None or ts2 is None:
        return None
    delta_hours = abs((ts1 - ts2).total_seconds()) / 3600.0
    # Exponential temporal decay with roughly 12 hour half-life.
    return math.exp(-delta_hours / 12.0)


def _weighted_average(components: dict[str, float | None], weights: dict[str, float]) -> float:
    total_weight = 0.0
    weighted_sum = 0.0
    for name, value in components.items():
        if value is None:
            continue
        weight = weights.get(name, 0.0)
        weighted_sum += value * weight
        total_weight += weight
    if total_weight == 0:
        return 0.0
    return weighted_sum / total_weight


def _calibrate_probability(raw_score: float) -> float:
    centered = raw_score - 0.55
    return 1.0 / (1.0 + math.exp(-6.0 * centered))


def _top_reason_codes(components: dict[str, float | None]) -> list[str]:
    pairs = [(name, value) for name, value in components.items() if value is not None]
    pairs.sort(key=lambda item: item[1], reverse=True)
    return [f"feature_{name}" for name, _ in pairs[:3]]


def _deterministic_similarity(
    incident1: dict[str, Any],
    incident2: dict[str, Any],
    weights: dict[str, float] | None = None,
) -> dict[str, Any]:
    effective_weights = weights or {
        "text": 0.3,
        "distance": 0.25,
        "time": 0.2,
        "severity": 0.15,
        "risk_label": 0.1,
    }

    components = {
        "text": _text_similarity(incident1, incident2),
        "distance": _distance_similarity(incident1, incident2),
        "time": _time_similarity(incident1, incident2),
        "severity": _severity_similarity(incident1, incident2),
        "risk_label": _risk_label_similarity(incident1, incident2),
    }
    weighted_score = _weighted_average(components, effective_weights)
    calibrated = _calibrate_probability(weighted_score)

    return {
        "components": components,
        "weights": effective_weights,
        "raw_score": weighted_score,
        "calibrated_score": calibrated,
        "reason_codes": _top_reason_codes(components),
    }


def _gemini_similarity(
    incident1: dict[str, Any],
    incident2: dict[str, Any],
    deterministic_summary: dict[str, Any],
) -> dict[str, Any]:
    client = _build_genai_client()
    prompt = (
        "You are estimating whether two campus safety incidents refer to the same event, "
        "a related event cluster, or unrelated events. Use the structured incident fields, "
        "the descriptions, timestamps, coordinates, and the deterministic feature summary. "
        "Return ONLY valid JSON with this shape: "
        "{\"semantic_similarity\": <float 0-1>, "
        "\"match_confidence\": <float 0-1>, "
        "\"reason_codes\": [\"<snake_case_reason>\"]}.\n\n"
        f"Incident 1:\n{json.dumps(incident1, indent=2, sort_keys=True)}\n\n"
        f"Incident 2:\n{json.dumps(incident2, indent=2, sort_keys=True)}\n\n"
        f"Deterministic feature summary:\n{json.dumps(deterministic_summary, indent=2, sort_keys=True)}"
    )
    response = client.models.generate_content(model=_confidence_model(), contents=prompt)
    payload = _extract_json_dict(_response_text(response))
    if payload is None:
        raise RuntimeError("Gemini similarity response was not valid JSON.")

    try:
        semantic_similarity = float(payload.get("semantic_similarity"))
    except (TypeError, ValueError):
        semantic_similarity = deterministic_summary["calibrated_score"]

    try:
        match_confidence = float(payload.get("match_confidence"))
    except (TypeError, ValueError):
        match_confidence = semantic_similarity

    semantic_similarity = max(0.0, min(semantic_similarity, 1.0))
    match_confidence = max(0.0, min(match_confidence, 1.0))
    raw_reason_codes = payload.get("reason_codes")
    reason_codes = [code for code in raw_reason_codes if isinstance(code, str) and code.strip()] if isinstance(raw_reason_codes, list) else []
    if not reason_codes:
        reason_codes = ["gemini_similarity_default"]

    return {
        "semantic_similarity": semantic_similarity,
        "match_confidence": match_confidence,
        "reason_codes": reason_codes,
    }


def incident_match_confidence(
    incident1: dict[str, Any],
    incident2: dict[str, Any],
    *,
    weights: dict[str, float] | None = None,
    use_gemini: bool = True,
) -> dict[str, Any]:
    deterministic = _deterministic_similarity(incident1, incident2, weights=weights)
    reason_codes = list(deterministic["reason_codes"])
    fallback_used = True
    semantic_similarity = None

    final_confidence = deterministic["calibrated_score"]
    if use_gemini:
        try:
            gemini_result = _gemini_similarity(incident1, incident2, deterministic)
            semantic_similarity = gemini_result["semantic_similarity"]
            final_confidence = 0.55 * deterministic["calibrated_score"] + 0.45 * gemini_result["match_confidence"]
            reason_codes.extend(gemini_result["reason_codes"])
            fallback_used = False
        except Exception:
            reason_codes.append("gemini_similarity_unavailable")

    deduped_reason_codes = list(dict.fromkeys(reason_codes))
    return {
        "incident_1": incident1,
        "incident_2": incident2,
        "confidence": round(max(0.0, min(final_confidence, 1.0)), 6),
        "deterministic_score": round(deterministic["calibrated_score"], 6),
        "semantic_similarity": None if semantic_similarity is None else round(semantic_similarity, 6),
        "components": deterministic["components"],
        "weights": deterministic["weights"],
        "reason_codes": deduped_reason_codes,
        "model_version": _confidence_model(),
        "prompt_version": _confidence_prompt_version(),
        "fallback_used": fallback_used,
        "scored_at": _utc_now_iso(),
    }
