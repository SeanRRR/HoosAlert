from fastapi.testclient import TestClient
import asyncio
import websockets
import json
from backend.src.socket_manager import app

client = TestClient(app)

async def test_websocket_and_post():
    # Start a WebSocket connection
    uri = "ws://localhost:8000/ws"
    async with websockets.connect(uri) as websocket:
        # Send a POST request to the /api/report endpoint
        report_data = {"incident": "Test Incident", "location": "Test Location"}
        response = client.post("/api/report", json=report_data)
        assert response.status_code == 200
        assert response.json() == {"message": "Report received and broadcasted"}

        # Receive the broadcasted message from the WebSocket
        received_message = await websocket.recv()
        assert json.loads(received_message) == report_data

# Run the test
if __name__ == "__main__":
    asyncio.run(test_websocket_and_post())

