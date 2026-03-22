from datetime import datetime, timezone
import os
from typing import Any

from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from src.database import get_incidents, get_incidents_for_scoring, save_incident
from src.ml.logic import score_incident
from src.ml.validator import validate_score
from src.schemas.report_submission import ReportSubmission
from src.socket_manager import manager

app = FastAPI(title="HoosAlert Backend")

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


def _build_score_payload(
    ai_result: dict[str, Any],
    report_text: str,
    scored_at: str,
    context_count: int,
) -> dict[str, Any]:
    raw_severity = _clamp_int(ai_result.get("severity"), minimum=1, maximum=5, default=3)
    validated_severity = validate_score(report_text, raw_severity)

    risk_label = ai_result.get("type", "unknown")
    if not isinstance(risk_label, str) or not risk_label.strip():
        risk_label = "unknown"

    confidence = _clamp_float(ai_result.get("confidence"), minimum=0.0, maximum=1.0, default=0.5)

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

    fallback_used = bool(ai_result.get("fallback_used", False))
    if fallback_used and "fallback_rule_based" not in reason_codes:
        reason_codes.append("fallback_rule_based")

    # Preserve order while removing duplicates.
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


LLM_CONTEXT_HOURS = _env_int("LLM_CONTEXT_HOURS", default=24, minimum=1, maximum=24 * 30)
LLM_CONTEXT_LIMIT = _env_int("LLM_CONTEXT_LIMIT", default=100, minimum=1, maximum=1000)


@app.get("/")
async def root_health():
    return {"status": "HoosAlert API is online"}


@app.get("/health")
async def health():
    return {"status": "ok"}


@app.post("/submit")
async def submit_report(report: Report):
    scored_at = _utc_now_iso()
    ai_result = score_incident(report.description)
    score_data = _build_score_payload(
        ai_result=ai_result,
        report_text=report.description,
        scored_at=scored_at,
        context_count=0,
    )

    incident_data = {
        "title": report.title,
        "description": report.description,
        "location": report.location,
        "severity": score_data["severity"],
        "risk_label": score_data["risk_label"],
        "score_confidence": score_data["confidence"],
        "score_reason_codes": score_data["reason_codes"],
        "score_model_version": score_data["model_version"],
        "score_prompt_version": score_data["prompt_version"],
        "score_context_count": score_data["context_count"],
        "score_fallback_used": score_data["fallback_used"],
        "score_scored_at": score_data["scored_at"],
        "source": "legacy_submit",
        "created_at": scored_at,
    }
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

    ai_result = score_incident(
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
    score_data = _build_score_payload(
        ai_result=ai_result,
        report_text=description,
        scored_at=timestamp,
        context_count=len(history),
    )

    incident_data = {
        "title": incident_type,
        "description": description,
        "location": location,
        "latitude": report.latitude,
        "longitude": report.longitude,
        "severity": score_data["severity"],
        "risk_label": score_data["risk_label"],
        "score_confidence": score_data["confidence"],
        "score_reason_codes": score_data["reason_codes"],
        "score_model_version": score_data["model_version"],
        "score_prompt_version": score_data["prompt_version"],
        "score_context_count": score_data["context_count"],
        "score_fallback_used": score_data["fallback_used"],
        "score_scored_at": score_data["scored_at"],
        "reporter_id": reporter_id,
        "source": "user_report",
        "created_at": timestamp,
    }

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
    ai_result = score_incident(text)
    score_data = _build_score_payload(
        ai_result=ai_result,
        report_text=text,
        scored_at=_utc_now_iso(),
        context_count=0,
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


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("src.main:app", host="0.0.0.0", port=8000, reload=True)
