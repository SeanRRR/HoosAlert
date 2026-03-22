import uvicorn
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from schemas.report import ReportSubmission

# Import your sub-modules
from socket_manager import manager
import ai_logic 

app = FastAPI(title="HoosAlert Backend")

# --- CORS SETUP ---
# Allows Reed's frontend (localhost:3000) to talk to this API
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Open for hackathon speed; restrict to ["http://localhost:3000"] later
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- ROUTES ---

@app.get("/")
async def health_check():
    return {"status": "HoosAlert API is online"}

@app.post("/api/report")
async def handle_report(report: ReportSubmission):
    """
    The Core Pipeline:
    1. Receive raw text from Reed's UI.
    2. Pass it to the Gemini 'Brain'.
    3. Broadcast the resulting JSON to all live map users.
    """
    raw_text = report.text
    
    # Send to Gemini (ai_logic.py)
    processed_incident = ai_logic.process_with_gemini(raw_text)
    
    # Broadcast to WebSockets (socket_manager.py)
    await manager.broadcast(processed_incident)
    
    return {
        "status": "Incident Processed",
        "incident": processed_incident
    }

# --- WEBSOCKET ENDPOINT ---

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        while True:
            # Keep the connection open
            await websocket.receive_text() 
    except WebSocketDisconnect:
        manager.disconnect(websocket)

if __name__ == "__main__":
    # Runs the server on http://localhost:8000
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)