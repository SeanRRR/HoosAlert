from datetime import datetime, timezone

from fastapi import FastAPI, HTTPException, WebSocket
from pydantic import BaseModel
from fastapi.middleware.cors import CORSMiddleware
from src.ml.logic import score_incident
from src.ml.validator import validate_score
from src.socket_manager import manager
from src.database import get_incidents, save_incident

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class Report(BaseModel):
    title: str
    description: str
    location: str


class ReportSubmission(BaseModel):
    incidentType: str
    location: str
    computingId: str
    description: str | None = None


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


@app.get("/health")
async def health():
    return {"status": "ok"}

@app.post("/submit")
async def submit_report(report: Report):
    ai_result = score_incident(report.description)
    severity = validate_score(report.description, ai_result["severity"])
    incident_data = {
        "title": report.title,
        "description": report.description,
        "location": report.location,
        "severity": severity,
        "source": "legacy_submit",
        "created_at": _utc_now_iso(),
    }
    incident_id = await save_incident(incident_data)
    incident_data["id"] = incident_id
    await manager.broadcast(incident_data)
    return {
        "received": report,
        "severity": severity,
        "incident_id": incident_id,
        "message": "Report submitted successfully"
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

    ai_result = score_incident(description)
    severity = validate_score(description, ai_result["severity"])

    incident_data = {
        "title": incident_type,
        "description": description,
        "location": location,
        "severity": severity,
        "reporter_id": reporter_id,
        "source": "user_report",
        "created_at": _utc_now_iso(),
    }

    incident_id = await save_incident(incident_data)
    payload = {**incident_data, "id": incident_id}
    await manager.broadcast(payload)

    return {
        "message": "Report submitted successfully",
        "incident": payload,
    }


@app.get("/api/incidents")
async def list_incidents(limit: int = 100):
    incidents = await get_incidents(limit=limit)
    return {"incidents": incidents}

@app.post("/score")
async def score_endpoint(payload: dict):
    text = payload.get("text", "")
    ai_result = score_incident(text)
    severity = validate_score(text, ai_result["severity"])
    return {"severity": severity, "input": payload}

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        while True:
            await websocket.receive_text()
    except Exception:
        manager.disconnect(websocket)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
