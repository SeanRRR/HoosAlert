from fastapi import FastAPI, WebSocket
from pydantic import BaseModel
from fastapi.middleware.cors import CORSMiddleware
from src.ml.logic import score_incident
from src.ml.validator import validate_score
from src.socket_manager import manager

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

@app.get("/health")
async def health():
    return {"status": "ok"}

@app.post("/submit")
async def submit_report(report: Report):
    # Call internal scoring logic
    ai_result = score_incident(report.description)
    severity = validate_score(report.description, ai_result["severity"])
    incident_data = {
        "title": report.title,
        "description": report.description,
        "location": report.location,
        "severity": severity
    }
    # Broadcast to WebSocket clients
    await manager.broadcast(incident_data)
    return {
        "received": report,
        "severity": severity,
        "message": "Report submitted successfully"
    }

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
            data = await websocket.receive_text()
            # Handle incoming messages if needed
    except:
        manager.disconnect(websocket)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
