import asyncio
import os
from contextlib import suppress
from datetime import datetime, timedelta, timezone
from typing import Any


from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from src.database import (
    get_due_incidents_for_rescoring,
    get_incidents,
    get_incidents_for_scoring,
    save_incident,
    update_incident_fields,
)
from src.ml.logic import score_incident
from src.ml.validator import validate_score
from src.schemas.report_submission import ReportSubmission
from src.socket_manager import manager


app = FastAPI(title="HoosAlert Backend")

class TweetPayload(BaseModel):
    text: str

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Open for hackathon speed; restrict later for production.
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class Report(BaseModel):
    title: str
    description: str
    location: str


_TWEET_LOCATION_ALIASES: dict[str, str] = {
    "alderman library": "alderman-library",
    "alderman": "alderman-library",
    "clemons library": "clemons-library",
    "clemons": "clemons-library",
    "shannon library": "shannon-library",
    "shannon": "shannon-library",
    "newcomb hall": "newcomb-hall",
    "newcomb": "newcomb-hall",
    "rotunda": "rotunda",
    "lawn": "lawn",
    "scott stadium": "scott-stadium",
    "uva hospital": "uva-medical-center",
    "student health": "student-health",
}

_TWEET_LOCATION_META: dict[str, dict[str, Any]] = {
    "alderman-library": {"label": "Alderman Library", "latitude": 38.036811, "longitude": -78.505393},
    "clemons-library": {"label": "Clemons Library", "latitude": 38.036316, "longitude": -78.506207},
    "shannon-library": {"label": "Shannon Library", "latitude": 38.036506, "longitude": -78.50531},
    "newcomb-hall": {"label": "Newcomb Hall", "latitude": 38.0370, "longitude": -78.5050},
    "rotunda": {"label": "The Rotunda", "latitude": 38.0365, "longitude": -78.5034},
    "lawn": {"label": "The Lawn", "latitude": 38.0360, "longitude": -78.5030},
    "scott-stadium": {"label": "Scott Stadium", "latitude": 38.031203, "longitude": -78.513774},
    "uva-medical-center": {"label": "UVA Medical Center", "latitude": 38.031244, "longitude": -78.498455},
    "student-health": {"label": "Student Health", "latitude": 38.030351, "longitude": -78.503761},
}


def _resolve_tweet_location(text: str) -> tuple[str | None, str, float | None, float | None]:
    normalized = text.lower()

    matched_key: str | None = None
    for phrase, key in _TWEET_LOCATION_ALIASES.items():
        if phrase in normalized:
            matched_key = key
            break

    if matched_key is None:
        return None, "UVA Campus", None, None

    location_meta = _TWEET_LOCATION_META.get(matched_key)
    if not location_meta:
        return matched_key, "UVA Campus", None, None

    return (
        matched_key,
        str(location_meta.get("label", "UVA Campus")),
        location_meta.get("latitude"),
        location_meta.get("longitude"),
    )


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _clamp_int(value: Any, minimum: int, maximum: int, default: int) -> int:
    try:
        parsed = int(value)
    except (TypeError, ValueError):
        parsed = default
    return max(minimum, min(parsed, maximum))


def _clamp_float(value: Any, minimum: float, maximum: float, default: float) -> float:
    try:
        parsed = float(value)
    except (TypeError, ValueError):
        parsed = default
    return max(minimum, min(parsed, maximum))


def _extract_score_result(scored_report: Any) -> tuple[dict[str, Any], dict[str, Any]]:
    if isinstance(scored_report, dict):
        raw_score = scored_report.get("score")
        if isinstance(raw_score, dict):
            incident = scored_report.get("incident")
            return (incident if isinstance(incident, dict) else {}, raw_score)
        return ({}, scored_report)
    return ({}, {})


def _build_score_payload(
    ai_result: dict[str, Any],
    report_text: str,
    scored_at: str,
    context_count: int,
) -> dict[str, Any]:
    raw_severity = _clamp_int(ai_result.get("severity"), minimum=1, maximum=5, default=3)
    validated_severity = validate_score(report_text, raw_severity)

    risk_label = ai_result.get("risk_label") or ai_result.get("type") or "unknown"
    if not isinstance(risk_label, str) or not risk_label.strip():
        risk_label = "unknown"

    fallback_used = bool(ai_result.get("fallback_used", False))
    raw_confidence = _clamp_float(
        ai_result.get("confidence"),
        minimum=0.0,
        maximum=1.0,
        default=CONFIDENCE_BASELINE,
    )
    confidence, context_scale = _calibrate_confidence(
        raw_confidence=raw_confidence,
        context_count=context_count,
        fallback_used=fallback_used,
    )

    raw_reason_codes = ai_result.get("reason_codes")
    if isinstance(raw_reason_codes, list):
        reason_codes = [code for code in raw_reason_codes if isinstance(code, str) and code.strip()]
    else:
        reason_codes = []
    if not reason_codes:
        reason_codes = ["model_no_reason_code"]

    if validated_severity != raw_severity:
        reason_codes.append("validator_keyword_override")

    if context_count > 0:
        reason_codes.append("recent_context_used")
    else:
        reason_codes.append("low_context_available")
    if abs(confidence - raw_confidence) > 1e-9:
        reason_codes.append("confidence_calibrated_from_baseline")
    if context_scale < 1.0:
        reason_codes.append("confidence_limited_by_context")
    if fallback_used and "fallback_rule_based" not in reason_codes:
        reason_codes.append("fallback_rule_based")

    deduped_reason_codes = list(dict.fromkeys(reason_codes))

    return {
        "severity": validated_severity,
        "risk_label": risk_label,
        "confidence": confidence,
        "reason_codes": deduped_reason_codes,
        "model_version": str(ai_result.get("model_version", "unknown")),
        "prompt_version": str(ai_result.get("prompt_version", "unknown")),
        "context_count": max(0, context_count),
        "fallback_used": fallback_used,
        "scored_at": scored_at,
    }


def _env_int(name: str, default: int, minimum: int, maximum: int) -> int:
    raw = os.getenv(name)
    if raw is None:
        return default

    try:
        value = int(raw)
    except ValueError:
        return default

    return max(minimum, min(value, maximum))


def _env_float(name: str, default: float, minimum: float, maximum: float) -> float:
    raw = os.getenv(name)
    if raw is None:
        return default

    try:
        value = float(raw)
    except ValueError:
        return default

    return max(minimum, min(value, maximum))


LLM_CONTEXT_HOURS = _env_int("LLM_CONTEXT_HOURS", default=24, minimum=1, maximum=24 * 30)
LLM_CONTEXT_LIMIT = _env_int("LLM_CONTEXT_LIMIT", default=100, minimum=1, maximum=1000)

CONFIDENCE_BASELINE = _env_float("CONFIDENCE_BASELINE", default=0.5, minimum=0.0, maximum=1.0)
CONFIDENCE_FULL_CONTEXT_COUNT = _env_int("CONFIDENCE_FULL_CONTEXT_COUNT", default=10, minimum=1, maximum=1000)
CONFIDENCE_FALLBACK_DELTA_SCALE = _env_float(
    "CONFIDENCE_FALLBACK_DELTA_SCALE",
    default=0.25,
    minimum=0.0,
    maximum=1.0,
)

RESCORE_ENABLED = os.getenv("RESCORE_ENABLED", "1").lower() in {"1", "true", "yes", "on"}
RESCORE_LOOP_SLEEP_SEC = _env_int("RESCORE_LOOP_SLEEP_SEC", default=5, minimum=1, maximum=300)
RESCORE_BATCH_SIZE = _env_int("RESCORE_BATCH_SIZE", default=20, minimum=1, maximum=200)
_RESCORE_INTERVAL_BY_SEVERITY = {
    1: _env_int("RESCORE_INTERVAL_SEVERITY_1_SEC", default=1800, minimum=30, maximum=24 * 3600),
    2: _env_int("RESCORE_INTERVAL_SEVERITY_2_SEC", default=900, minimum=30, maximum=24 * 3600),
    3: _env_int("RESCORE_INTERVAL_SEVERITY_3_SEC", default=300, minimum=30, maximum=24 * 3600),
    4: _env_int("RESCORE_INTERVAL_SEVERITY_4_SEC", default=120, minimum=30, maximum=24 * 3600),
    5: _env_int("RESCORE_INTERVAL_SEVERITY_5_SEC", default=60, minimum=5, maximum=24 * 3600),
}

_rescore_worker_task: asyncio.Task | None = None


def _calibrate_confidence(raw_confidence: float, context_count: int, fallback_used: bool) -> tuple[float, float]:
    safe_context_count = max(0, context_count)
    context_scale = min(1.0, safe_context_count / float(CONFIDENCE_FULL_CONTEXT_COUNT))

    delta = raw_confidence - CONFIDENCE_BASELINE
    if fallback_used:
        delta *= CONFIDENCE_FALLBACK_DELTA_SCALE

    calibrated_confidence = CONFIDENCE_BASELINE + (delta * context_scale)
    return (
        _clamp_float(
            calibrated_confidence,
            minimum=0.0,
            maximum=1.0,
            default=CONFIDENCE_BASELINE,
        ),
        context_scale,
    )


def _parse_iso_utc(value: Any) -> datetime:
    if isinstance(value, str):
        try:
            parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
            if parsed.tzinfo is None:
                parsed = parsed.replace(tzinfo=timezone.utc)
            return parsed.astimezone(timezone.utc)
        except ValueError:
            pass
    return datetime.now(timezone.utc)


def _rescore_interval_seconds(severity: Any) -> int:
    safe_severity = _clamp_int(severity, minimum=1, maximum=5, default=3)
    return _RESCORE_INTERVAL_BY_SEVERITY[safe_severity]


def _next_rescore_at_iso(scored_at: str, severity: Any) -> tuple[int, str]:
    interval_sec = _rescore_interval_seconds(severity)
    scored_dt = _parse_iso_utc(scored_at)
    next_dt = scored_dt + timedelta(seconds=interval_sec)
    return interval_sec, next_dt.isoformat()


def _score_storage_fields(score_data: dict[str, Any], existing_incident: dict[str, Any] | None = None) -> dict[str, Any]:
    scored_at = str(score_data.get("scored_at", _utc_now_iso()))
    interval_sec, next_rescore_at = _next_rescore_at_iso(scored_at, score_data.get("severity"))
    risk_label = score_data.get("risk_label")
    if not isinstance(risk_label, str) or not risk_label.strip():
        risk_label = "unknown"

    raw_reason_codes = score_data.get("reason_codes")
    if isinstance(raw_reason_codes, list):
        reason_codes = [code for code in raw_reason_codes if isinstance(code, str) and code.strip()]
    else:
        reason_codes = []
    if not reason_codes:
        reason_codes = ["model_no_reason_code"]

    existing_version = _clamp_int(
        (existing_incident or {}).get("score_version", 0),
        minimum=0,
        maximum=1_000_000_000,
        default=0,
    )
    score_version = existing_version + 1 if existing_incident else 1

    return {
        "severity": _clamp_int(score_data.get("severity"), minimum=1, maximum=5, default=3),
        "risk_label": risk_label,
        "score_confidence": _clamp_float(score_data.get("confidence"), minimum=0.0, maximum=1.0, default=0.5),
        "score_reason_codes": reason_codes,
        "score_model_version": str(score_data.get("model_version", "unknown")),
        "score_prompt_version": str(score_data.get("prompt_version", "unknown")),
        "score_context_count": _clamp_int(score_data.get("context_count"), minimum=0, maximum=1000, default=0),
        "score_fallback_used": bool(score_data.get("fallback_used", False)),
        "score_scored_at": scored_at,
        "last_scored_at": scored_at,
        "update_interval_sec": interval_sec,
        "next_rescore_at": next_rescore_at,
        "score_version": score_version,
    }


async def _rescore_incident_and_broadcast(incident: dict[str, Any]) -> None:
    incident_id = incident.get("id")
    if incident_id is None:
        return

    description = str(incident.get("description") or incident.get("title") or "")
    history = await get_incidents_for_scoring(
        hours=LLM_CONTEXT_HOURS,
        limit=LLM_CONTEXT_LIMIT,
    )

    raw_result = score_incident(
        {
            "title": incident.get("title"),
            "description": description,
            "location": incident.get("location"),
            "reporter_id": incident.get("reporter_id"),
            "created_at": incident.get("created_at") or incident.get("timestamp"),
            "latitude": incident.get("latitude"),
            "longitude": incident.get("longitude"),
        },
        history=history,
    )
    _, raw_score = _extract_score_result(raw_result)

    scored_at = str(raw_score.get("scored_at", _utc_now_iso()))
    score_data = _build_score_payload(
        ai_result=raw_score,
        report_text=description,
        scored_at=scored_at,
        context_count=len(history),
    )
    update_fields = _score_storage_fields(score_data, existing_incident=incident)

    updated = await update_incident_fields(str(incident_id), update_fields)
    if not updated:
        return

    incident_payload = {**incident, **update_fields, "id": str(incident_id)}
    await manager.broadcast(
        {
            "event_type": "incident_rescored",
            "incident": incident_payload,
            "score": score_data,
        }
    )


async def _rescore_worker_loop() -> None:
    while True:
        try:
            due_incidents = await get_due_incidents_for_rescoring(
                now_iso=_utc_now_iso(),
                limit=RESCORE_BATCH_SIZE,
            )
            for incident in due_incidents:
                await _rescore_incident_and_broadcast(incident)
        except asyncio.CancelledError:
            raise
        except Exception:
            # Keep worker running even when one iteration fails.
            pass

        await asyncio.sleep(RESCORE_LOOP_SLEEP_SEC)


@app.on_event("startup")
async def _start_rescore_worker() -> None:
    global _rescore_worker_task

    if not RESCORE_ENABLED:
        return
    if _rescore_worker_task and not _rescore_worker_task.done():
        return

    _rescore_worker_task = asyncio.create_task(_rescore_worker_loop())


@app.on_event("shutdown")
async def _stop_rescore_worker() -> None:
    global _rescore_worker_task

    if _rescore_worker_task is None:
        return

    _rescore_worker_task.cancel()
    with suppress(asyncio.CancelledError):
        await _rescore_worker_task
    _rescore_worker_task = None


@app.get("/")
async def root_health():
    return {"status": "HoosAlert API is online"}


@app.get("/health")
async def health():
    return {"status": "ok"}


@app.post("/submit")
async def submit_report(report: Report):
    raw_result = score_incident(
        {
            "title": report.title,
            "description": report.description,
            "location": report.location,
        }
    )
    _, raw_score = _extract_score_result(raw_result)

    scored_at = str(raw_score.get("scored_at", _utc_now_iso()))
    context_count = _clamp_int(raw_score.get("context_count", 0), minimum=0, maximum=1000, default=0)
    score_data = _build_score_payload(
        ai_result=raw_score,
        report_text=report.description,
        scored_at=scored_at,
        context_count=context_count,
    )

    incident_data = {
        "title": report.title,
        "description": report.description,
        "location": report.location,
        "source": "legacy_submit",
        "created_at": scored_at,
    }
    incident_data.update(_score_storage_fields(score_data))

    incident_id = await save_incident(incident_data)
    incident_payload = {**incident_data, "id": incident_id}
    event_payload = {"incident": incident_payload, "score": score_data}
    await manager.broadcast(event_payload)

    return {
        "message": "Report submitted successfully",
        "received": report,
        "severity": score_data["severity"],
        "incident_id": incident_id,
        "incident": incident_payload,
        "score": score_data,
    }


@app.post("/api/report")
async def create_report(report: ReportSubmission):
    incident_type = report.incidentType.strip()
    location = report.location.strip()
    reporter_id = report.computingId.strip()

    if not incident_type or not location or not reporter_id:
        raise HTTPException(
            status_code=422,
            detail="incidentType, location, and computingId are required",
        )

    description = (report.description or incident_type).strip()
    timestamp = _utc_now_iso()

    history = await get_incidents_for_scoring(
        hours=LLM_CONTEXT_HOURS,
        limit=LLM_CONTEXT_LIMIT,
    )

    raw_result = score_incident(
        {
            "incidentType": incident_type,
            "description": description,
            "location": location,
            "computingId": reporter_id,
            "timestamp": timestamp,
            "latitude": report.latitude,
            "longitude": report.longitude,
        },
        history=history,
    )
    _, raw_score = _extract_score_result(raw_result)

    scored_at = str(raw_score.get("scored_at", timestamp))
    score_data = _build_score_payload(
        ai_result=raw_score,
        report_text=description,
        scored_at=scored_at,
        context_count=len(history),
    )

    incident_data = {
        "title": incident_type,
        "description": description,
        "location": location,
        "latitude": report.latitude,
        "longitude": report.longitude,
        "reporter_id": reporter_id,
        "source": "user_report",
        "created_at": timestamp,
    }
    incident_data.update(_score_storage_fields(score_data))

    incident_id = await save_incident(incident_data)
    incident_payload = {**incident_data, "id": incident_id}
    event_payload = {"incident": incident_payload, "score": score_data}
    await manager.broadcast(event_payload)

    return {
        "message": "Report submitted successfully",
        "incident": incident_payload,
        "score": score_data,
    }


@app.get("/api/incidents")
async def list_incidents(limit: int = 100):
    incidents = await get_incidents(limit=limit)
    return {"incidents": incidents}


@app.post("/score")
async def score_endpoint(payload: dict):
    text = payload.get("text", "")
    raw_result = score_incident({"text": text})
    _, raw_score = _extract_score_result(raw_result)

    scored_at = str(raw_score.get("scored_at", _utc_now_iso()))
    context_count = _clamp_int(raw_score.get("context_count", 0), minimum=0, maximum=1000, default=0)
    score_data = _build_score_payload(
        ai_result=raw_score,
        report_text=text,
        scored_at=scored_at,
        context_count=context_count,
    )
    return {"score": score_data, "input": payload}


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(websocket)
    except Exception:
        manager.disconnect(websocket)

@app.post("/inject_tweet")
async def inject_tweet(payload: TweetPayload):
    text = payload.text.strip()
    severity = 5 if "shooter" in text.lower() or "attack" in text.lower() else 3
    location_key, location_label, latitude, longitude = _resolve_tweet_location(text)

    event_payload = {
        "event_type": "tweet_injected",
        "incident": {
            "id": f"tweet-{datetime.now(timezone.utc).timestamp()}",
            "title": text or "UVA Alert",
            "location": location_label,
            "location_key": location_key,
            "latitude": latitude,
            "longitude": longitude,
            "severity": severity,
            "risk_label": "critical" if severity == 5 else "medium",
            "source": "tweet_injected",
            "created_at": _utc_now_iso(),
        },
    }

    await manager.broadcast(event_payload)
    return {"ok": True}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("src.main:app", host="0.0.0.0", port=8000, reload=True)
