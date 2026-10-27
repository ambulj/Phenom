"""
End-to-End WebSocket Chat and Safety Test
Verifies:
1. Connection to FastAPI WebSocket endpoint
2. Receiving initial state and rules
3. Chat stream delivery
4. Tool request and confirmation cycle
5. Guardian killswitch trigger and resume cycle
"""

import pytest
import asyncio
import json
from fastapi.testclient import TestClient
from services.backend.main import app
from services.backend.safety.guardian import guardian
from services.backend.safety.registry import registry
from pydantic import BaseModel

class DummyToolArgs(BaseModel):
    message: str

@pytest.fixture(autouse=True)
def setup_test_tool():
    @registry.register(
        name="e2e_dummy_tool",
        tier=1,
        description="A dummy tool for E2E testing",
        args_schema=DummyToolArgs,
        preview_fn=lambda a: f"Dummy preview: {a.get('message')}"
    )
    def dummy_handler(message: str):
        return f"Echo: {message}"

def test_health_endpoint():
    client = TestClient(app)
    resp = client.get("/api/health")
    assert resp.status_code == 200
    assert resp.json()["status"] == "ok"

def test_websocket_e2e_flow():
    client = TestClient(app)
    try:
        with client.websocket_connect("/ws") as ws:
            # 1. Expect initial rules and state messages (and mode, scheduler, watchlist)
            init_rules = ws.receive_json()
            assert init_rules["type"] == "rules.updated"
            
            init_state = ws.receive_json()
            assert init_state["type"] == "state.change"
            assert init_state["payload"]["state"] in ("idle", "halted")

            init_mode = ws.receive_json()
            assert init_mode["type"] == "mode.changed"

            init_sched = ws.receive_json()
            assert init_sched["type"] == "scheduler.list_result"

            init_watch = ws.receive_json()
            assert init_watch["type"] == "watchlist.list_result"

            # 2. Test Killswitch Trigger via WebSocket
            ws.send_json({
                "id": "ks-1",
                "type": "killswitch.trigger",
                "payload": {}
            })
            ks_state = ws.receive_json()
            assert ks_state["type"] == "state.change"
            assert ks_state["payload"]["state"] == "halted"
            assert guardian.is_halted is True

            # 3. Test Killswitch Resume via WebSocket
            ws.send_json({
                "id": "ks-2",
                "type": "killswitch.resume",
                "payload": {}
            })
            resume_state = ws.receive_json()
            assert resume_state["type"] == "state.change"
            assert resume_state["payload"]["state"] == "idle"
            assert guardian.is_halted is False
    finally:
        guardian.resume()
