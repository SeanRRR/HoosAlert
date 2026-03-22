import asyncio
import json
import os
import sys

# Add the repository root to the Python path for local test execution.
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from backend.src.socket_manager import ConnectionManager


class MockWebSocket:
    def __init__(self):
        self.accepted = False
        self.messages: list[str] = []

    async def accept(self):
        self.accepted = True

    async def send_text(self, data: str):
        self.messages.append(data)


def test_connection_manager_connect_and_disconnect():
    async def _run():
        manager = ConnectionManager()
        websocket = MockWebSocket()

        await manager.connect(websocket)
        assert websocket.accepted is True
        assert websocket in manager.active_connections

        manager.disconnect(websocket)
        assert websocket not in manager.active_connections

    asyncio.run(_run())


def test_connection_manager_broadcast_sends_json_to_all_connections():
    async def _run():
        manager = ConnectionManager()
        ws_one = MockWebSocket()
        ws_two = MockWebSocket()

        await manager.connect(ws_one)
        await manager.connect(ws_two)

        payload = {"incident": "Test Incident", "location": "Test Location"}
        await manager.broadcast(payload)

        expected = json.dumps(payload)
        assert ws_one.messages == [expected]
        assert ws_two.messages == [expected]

    asyncio.run(_run())

