import json
import math
import os
import re
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from dotenv import load_dotenv

try:
    from google import genai  # google-genai
except ImportError:
    genai = None


class GeminiSimilarityError(RuntimeError):
    def __init__(
        self,
        message: str,
        *,
        reason_codes: list[str] | None = None,
        attempts: int = 0,
        failure_counts: dict[str, int] | None = None,
    ):
        super().__init__(message)
        self.reason_codes = reason_codes or []
        self.attempts = max(0, int(attempts))
        self.failure_counts = failure_counts or {}


_BACKEND_ENV_PATH = Path(__file__).resolve().parents[2] / ".env"
load_dotenv(_BACKEND_ENV_PATH, override=False)

_TIMESTAMP_FIELDS = ("timestamp", "created_at")
_LAT_FIELDS = ("latitude", "lat")
_LON_FIELDS = ("longitude", "lng", "lon")
_TEXT_FIELDS = ("description", "title", "incidentType", "incident_type", "risk_label", "location")
_MIN_CONFIDENCE = 0.02
_MAX_CONFIDENCE = 0.98
_DISTANCE_DECAY_KM = 1.25
_TIME_DECAY_HOURS = 16.0

_GEMINI_PAIR_ATTEMPTS = int(os.getenv("GEMINI_CONFIDENCE_PAIR_ATTEMPTS", "2") or "2")
_GEMINI_PAIR_ATTEMPTS = max(1, min(_GEMINI_PAIR_ATTEMPTS, 3))

_GEMINI_RETRY_PAUSE_MS = int(os.getenv("GEMINI_CONFIDENCE_RETRY_PAUSE_MS", "120") or "120")
_GEMINI_RETRY_PAUSE_MS = max(0, min(_GEMINI_RETRY_PAUSE_MS, 5000))

_GEMINI_COOLDOWN_SEC = int(os.getenv("GEMINI_CONFIDENCE_COOLDOWN_SEC", "60") or "60")
_GEMINI_COOLDOWN_SEC = max(1, min(_GEMINI_COOLDOWN_SEC, 3600))

_GEMINI_INVALID_KEY_COOLDOWN_SEC = int(os.getenv("GEMINI_CONFIDENCE_INVALID_KEY_COOLDOWN_SEC", str(24 * 3600)) or str(24 * 3600))
_GEMINI_INVALID_KEY_COOLDOWN_SEC = max(60, min(_GEMINI_INVALID_KEY_COOLDOWN_SEC, 7 * 24 * 3600))

_PAIR_BLOCK_UNTIL_MONO: dict[tuple[str, str], float] = {}
_CLIENT_BY_KEY: dict[str, Any] = {}


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _confidence_model() -> str:
    return os.getenv("GEMINI_CONFIDENCE_MODEL") or os.getenv("GEMINI_MODEL", "gemini-2.5-flash")


def _confidence_models() -> list[str]:
    pooled_models = os.getenv("GEMINI_CONFIDENCE_MODELS") or os.getenv("GEMINI_MODELS", "")
    parsed = [item.strip() for item in pooled_models.replace("\n", ",").split(",") if item and item.strip()]

    primary_model = _confidence_model().strip()
    if primary_model:
        parsed.append(primary_model)

    defaults = ["gemini-flash-latest", "gemini-2.5-flash-lite", "gemini-flash-lite-latest"]
    parsed.extend(defaults)

    deduped: list[str] = []
    seen: set[str] = set()
    for model_name in parsed:
        if model_name in seen:
            continue
        seen.add(model_name)
        deduped.append(model_name)
    return deduped


def _confidence_prompt_version() -> str:
    return os.getenv("CONFIDENCE_PROMPT_VERSION", "v1")


def _gemini_api_key() -> str:
    return os.getenv("GEMINI_API_KEY", "")


def _gemini_api_keys() -> list[str]:
    pooled_keys = os.getenv("GEMINI_API_KEYS", "")
    parsed = [item.strip() for item in pooled_keys.replace("\n", ",").split(",") if item and item.strip()]

    single_key = _gemini_api_key().strip()
    if single_key:
        parsed.append(single_key)

    deduped: list[str] = []
    seen: set[str] = set()
    for key in parsed:
        if key in seen:
            continue
        seen.add(key)
        deduped.append(key)
    return deduped


def _build_genai_client(api_key: str | None = None):
    if genai is None:
        raise RuntimeError("google-genai is not installed.")

    resolved_api_key = (api_key or _gemini_api_key()).strip()
    if not resolved_api_key:
        raise RuntimeError("GEMINI_API_KEY is not configured.")

    cached = _CLIENT_BY_KEY.get(resolved_api_key)
    if cached is not None:
        return cached

    client = genai.Client(api_key=resolved_api_key)
    _CLIENT_BY_KEY[resolved_api_key] = client
    return client


def _sanitize_reason_codes(raw_codes: Any, default_code: str) -> list[str]:
    if not isinstance(raw_codes, list):
        return [default_code]

    clean_codes: list[str] = []
    for item in raw_codes:
        if not isinstance(item, str):
            continue
        normalized = re.sub(r"[^a-z0-9_]+", "_", item.strip().lower()).strip("_")
        if normalized:
            clean_codes.append(normalized)

    deduped = list(dict.fromkeys(clean_codes))
    return deduped or [default_code]


def _extract_first_json_object(raw_text: str) -> str | None:
    start = raw_text.find("{")
    if start < 0:
        return None

    depth = 0
    in_string = False
    escaped = False
    for index in range(start, len(raw_text)):
        ch = raw_text[index]

        if in_string:
            if escaped:
                escaped = False
            elif ch == "\\":
                escaped = True
            elif ch == '"':
                in_string = False
            continue

        if ch == '"':
            in_string = True
            continue

        if ch == "{":
            depth += 1
            continue

        if ch == "}":
            depth -= 1
            if depth == 0:
                return raw_text[start : index + 1]

    return None


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

    candidate = _extract_first_json_object(raw)
    if not candidate:
        return None

    try:
        payload = json.loads(candidate)
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


def _first_float_for_fields(incident: dict[str, Any], fields: tuple[str, ...]) -> float | None:
    for field in fields:
        parsed = _to_float(incident.get(field))
        if parsed is not None:
            return parsed
    return None


def _incident_coords(incident: dict[str, Any]) -> tuple[float | None, float | None]:
    lat = _first_float_for_fields(incident, _LAT_FIELDS)
    lon = _first_float_for_fields(incident, _LON_FIELDS)
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
    return math.exp(-distance_km / _DISTANCE_DECAY_KM)


def _time_similarity(incident1: dict[str, Any], incident2: dict[str, Any]) -> float | None:
    ts1 = _incident_timestamp(incident1)
    ts2 = _incident_timestamp(incident2)
    if ts1 is None or ts2 is None:
        return None
    delta_hours = abs((ts1 - ts2).total_seconds()) / 3600.0
    return math.exp(-delta_hours / _TIME_DECAY_HOURS)


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


def _information_coverage(components: dict[str, float | None], weights: dict[str, float]) -> float:
    total_weight = sum(max(0.0, weight) for weight in weights.values())
    if total_weight == 0:
        return 0.0
    present_weight = sum(
        max(0.0, weights.get(name, 0.0))
        for name, value in components.items()
        if value is not None
    )
    return max(0.0, min(present_weight / total_weight, 1.0))


def _calibrate_probability(raw_score: float) -> float:
    centered = raw_score - 0.55
    return 1.0 / (1.0 + math.exp(-6.0 * centered))


def _apply_information_decay(score: float, coverage: float) -> float:
    decay_factor = 0.85 + 0.15 * max(0.0, min(coverage, 1.0))
    return score * decay_factor


def _allow_extreme_confidence(incident1: dict[str, Any], incident2: dict[str, Any]) -> bool:
    return bool(incident1.get("official_report")) or bool(incident2.get("official_report"))


def _bound_confidence(score: float, *, allow_extremes: bool) -> float:
    lower = 0.0 if allow_extremes else _MIN_CONFIDENCE
    upper = 1.0 if allow_extremes else _MAX_CONFIDENCE
    return max(lower, min(score, upper))


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
    information_coverage = _information_coverage(components, effective_weights)
    calibrated = _apply_information_decay(_calibrate_probability(weighted_score), information_coverage)

    reason_codes = _top_reason_codes(components)
    if information_coverage < 1.0:
        reason_codes.append("information_decay_applied")

    return {
        "components": components,
        "weights": effective_weights,
        "information_coverage": information_coverage,
        "raw_score": weighted_score,
        "calibrated_score": calibrated,
        "reason_codes": reason_codes,
    }


def _extract_retry_delay_seconds(message: str) -> int | None:
    patterns = [
        r"retry in\s+([0-9]+(?:\.[0-9]+)?)s",
        r"retrydelay\W*([0-9]+)s",
    ]
    lowered = message.lower()
    for pattern in patterns:
        match = re.search(pattern, lowered, flags=re.IGNORECASE)
        if not match:
            continue
        try:
            return max(1, math.ceil(float(match.group(1))))
        except ValueError:
            continue
    return None


def _classify_gemini_error(exc: Exception) -> str:
    message = str(exc).lower()

    if "api_key_invalid" in message or "api key not valid" in message:
        return "invalid_key"
    if "resource_exhausted" in message or "quota exceeded" in message or "429" in message:
        return "quota_exhausted"
    if "not_found" in message or "is not found" in message:
        return "model_not_found"
    if "timeout" in message or "timed out" in message or "deadline" in message:
        return "timeout"
    if "service unavailable" in message or "503" in message or "unavailable" in message:
        return "service_unavailable"
    if "permission" in message or "forbidden" in message or "403" in message:
        return "permission_denied"
    if "connection" in message or "network" in message or "dns" in message:
        return "network_error"
    return "request_error"


def _cooldown_seconds_for_error(error_kind: str, exc: Exception) -> int:
    retry_delay = _extract_retry_delay_seconds(str(exc))
    if retry_delay is not None:
        return retry_delay

    if error_kind == "invalid_key":
        return _GEMINI_INVALID_KEY_COOLDOWN_SEC
    if error_kind == "model_not_found":
        return 6 * 3600
    if error_kind in {"quota_exhausted", "timeout", "service_unavailable", "network_error", "request_error"}:
        return _GEMINI_COOLDOWN_SEC
    return _GEMINI_COOLDOWN_SEC


def _should_retry_error(error_kind: str) -> bool:
    return error_kind in {
        "quota_exhausted",
        "timeout",
        "service_unavailable",
        "network_error",
        "request_error",
        "invalid_json",
    }


def _prune_pair_block_cache(now_mono: float) -> None:
    stale_pairs = [pair for pair, blocked_until in _PAIR_BLOCK_UNTIL_MONO.items() if blocked_until <= now_mono]
    for pair in stale_pairs:
        _PAIR_BLOCK_UNTIL_MONO.pop(pair, None)


def _gemini_similarity(
    incident1: dict[str, Any],
    incident2: dict[str, Any],
    deterministic_summary: dict[str, Any],
) -> dict[str, Any]:
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

    api_keys = _gemini_api_keys()
    if not api_keys:
        raise GeminiSimilarityError(
            "No Gemini API keys configured.",
            reason_codes=["gemini_error_no_api_keys"],
        )

    model_candidates = _confidence_models()
    if not model_candidates:
        raise GeminiSimilarityError(
            "No Gemini models configured.",
            reason_codes=["gemini_error_no_models"],
        )

    now_mono = time.monotonic()
    _prune_pair_block_cache(now_mono)

    last_error: Exception | None = None
    failure_counts: dict[str, int] = {}
    technical_reason_codes: list[str] = []
    attempts = 0
    skipped_pairs = 0
    total_pairs = len(api_keys) * len(model_candidates)

    for model_name in model_candidates:
        for api_key in api_keys:
            pair_key = (model_name, api_key)
            blocked_until = _PAIR_BLOCK_UNTIL_MONO.get(pair_key, 0.0)
            if blocked_until > time.monotonic():
                skipped_pairs += 1
                technical_reason_codes.append("gemini_pair_temporarily_skipped")
                continue

            for attempt_index in range(1, _GEMINI_PAIR_ATTEMPTS + 1):
                attempts += 1
                try:
                    client = _build_genai_client(api_key=api_key)
                    response = client.models.generate_content(model=model_name, contents=prompt)
                    payload = _extract_json_dict(_response_text(response))
                    if payload is None:
                        error_kind = "invalid_json"
                        failure_counts[error_kind] = failure_counts.get(error_kind, 0) + 1
                        technical_reason_codes.append(f"gemini_error_{error_kind}")
                        if attempt_index < _GEMINI_PAIR_ATTEMPTS and _should_retry_error(error_kind):
                            if _GEMINI_RETRY_PAUSE_MS > 0:
                                time.sleep(_GEMINI_RETRY_PAUSE_MS / 1000.0)
                            continue
                        break

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
                    reason_codes = _sanitize_reason_codes(payload.get("reason_codes"), "gemini_similarity_default")

                    return {
                        "semantic_similarity": semantic_similarity,
                        "match_confidence": match_confidence,
                        "reason_codes": reason_codes,
                        "model_version": model_name,
                        "attempts": attempts,
                        "failure_counts": failure_counts,
                    }
                except Exception as exc:
                    last_error = exc
                    error_kind = _classify_gemini_error(exc)
                    failure_counts[error_kind] = failure_counts.get(error_kind, 0) + 1
                    technical_reason_codes.append(f"gemini_error_{error_kind}")

                    cooldown_seconds = _cooldown_seconds_for_error(error_kind, exc)
                    if cooldown_seconds > 0:
                        _PAIR_BLOCK_UNTIL_MONO[pair_key] = max(
                            _PAIR_BLOCK_UNTIL_MONO.get(pair_key, 0.0),
                            time.monotonic() + cooldown_seconds,
                        )

                    if attempt_index < _GEMINI_PAIR_ATTEMPTS and _should_retry_error(error_kind):
                        if _GEMINI_RETRY_PAUSE_MS > 0:
                            time.sleep(_GEMINI_RETRY_PAUSE_MS / 1000.0)
                        continue
                    break

    if skipped_pairs >= total_pairs and attempts == 0:
        technical_reason_codes.append("gemini_all_pairs_temporarily_blocked")

    error_codes = _sanitize_reason_codes(
        list(dict.fromkeys(technical_reason_codes)),
        default_code="gemini_similarity_unavailable",
    )

    raise GeminiSimilarityError(
        (
            "All Gemini model/key attempts failed or were skipped. "
            f"attempts={attempts}, skipped_pairs={skipped_pairs}, total_pairs={total_pairs}, "
            f"last_error={last_error!r}"
        ),
        reason_codes=error_codes,
        attempts=attempts,
        failure_counts=failure_counts,
    )


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
    model_version = _confidence_model()
    gemini_attempts = 0
    gemini_failure_counts: dict[str, int] = {}

    if use_gemini:
        try:
            gemini_result = _gemini_similarity(incident1, incident2, deterministic)
            semantic_similarity = gemini_result["semantic_similarity"]
            final_confidence = 0.55 * deterministic["calibrated_score"] + 0.45 * gemini_result["match_confidence"]
            reason_codes.extend(gemini_result["reason_codes"])
            model_version = str(gemini_result.get("model_version", model_version))
            gemini_attempts = int(gemini_result.get("attempts", 0))
            gemini_failure_counts = {
                key: int(value)
                for key, value in (gemini_result.get("failure_counts") or {}).items()
                if isinstance(key, str)
            }
            fallback_used = False
        except GeminiSimilarityError as exc:
            reason_codes.append("gemini_similarity_unavailable")
            reason_codes.extend(exc.reason_codes)
            gemini_attempts = exc.attempts
            gemini_failure_counts = exc.failure_counts
        except Exception:
            reason_codes.append("gemini_similarity_unavailable")
    else:
        reason_codes.append("gemini_similarity_disabled")

    allow_extremes = _allow_extreme_confidence(incident1, incident2)
    deduped_reason_codes = _sanitize_reason_codes(list(dict.fromkeys(reason_codes)), "confidence_computed")
    return {
        "incident_1": incident1,
        "incident_2": incident2,
        "confidence": round(_bound_confidence(final_confidence, allow_extremes=allow_extremes), 6),
        "deterministic_score": round(deterministic["calibrated_score"], 6),
        "semantic_similarity": None if semantic_similarity is None else round(semantic_similarity, 6),
        "components": deterministic["components"],
        "weights": deterministic["weights"],
        "information_coverage": round(deterministic["information_coverage"], 6),
        "reason_codes": deduped_reason_codes,
        "model_version": model_version,
        "prompt_version": _confidence_prompt_version(),
        "fallback_used": fallback_used,
        "allow_extreme_confidence": allow_extremes,
        "gemini_attempts": gemini_attempts,
        "gemini_failure_counts": gemini_failure_counts,
        "scored_at": _utc_now_iso(),
    }
