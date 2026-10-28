import os
import pytest
from starlette.websockets import WebSocketDisconnect
from fastapi.testclient import TestClient
from services.backend.main import app, failed_handshakes

VALID_TOKEN = "a" * 64

@pytest.fixture(autouse=True)
def setup_env():
    old_token = os.environ.get("PHENOM_SESSION_TOKEN")
    old_dev = os.environ.get("PHENOM_DEV")
    
    os.environ["PHENOM_SESSION_TOKEN"] = VALID_TOKEN
    os.environ["PHENOM_DEV"] = "1"
    failed_handshakes.clear()
    
    yield
    
    if old_token is not None:
        os.environ["PHENOM_SESSION_TOKEN"] = old_token
    else:
        os.environ.pop("PHENOM_SESSION_TOKEN", None)
        
    if old_dev is not None:
        os.environ["PHENOM_DEV"] = old_dev
    else:
        os.environ.pop("PHENOM_DEV", None)
    failed_handshakes.clear()


def test_ws_no_token_rejected():
    """Connecting without any token must be rejected with close code 4401."""
    client = TestClient(app)
    with pytest.raises(WebSocketDisconnect) as exc_info:
        with client.websocket_connect("/ws"):
            pass
    assert exc_info.value.code == 4401


def test_ws_wrong_token_rejected():
    """Connecting with an invalid token must be rejected with close code 4401."""
    client = TestClient(app)
    with pytest.raises(WebSocketDisconnect) as exc_info:
        with client.websocket_connect("/ws", subprotocols=["phenom.wrong_token_value"]):
            pass
    assert exc_info.value.code == 4401


def test_ws_bad_origin_rejected():
    """Connecting with a valid token but disallowed Origin header must be rejected with code 4401."""
    client = TestClient(app)
    with pytest.raises(WebSocketDisconnect) as exc_info:
        with client.websocket_connect(
            "/ws",
            subprotocols=[f"phenom.{VALID_TOKEN}"],
            headers={"origin": "http://malicious-website.com"}
        ):
            pass
    assert exc_info.value.code == 4401


def test_ws_good_token_and_good_origin_succeeds():
    """Valid token and allowed Origin must connect and receive initial setup frames."""
    client = TestClient(app)
    with client.websocket_connect(
        "/ws",
        subprotocols=[f"phenom.{VALID_TOKEN}"],
        headers={"origin": "http://localhost:5173"}
    ) as ws:
        msg1 = ws.receive_json()
        assert msg1["type"] == "rules.updated"
        msg2 = ws.receive_json()
        assert msg2["type"] == "state.change"


def test_unauthenticated_actions_impossible():
    """Without an authenticated handshake, clients receive 4401 and cannot send or receive sensitive messages."""
    client = TestClient(app)
    # Attempting to open socket without auth fails
    with pytest.raises(WebSocketDisconnect) as exc_info:
        with client.websocket_connect("/ws") as ws:
            ws.send_json({"type": "killswitch.resume"})
    assert exc_info.value.code == 4401


def test_missing_session_token_refuses_everything():
    """If PHENOM_SESSION_TOKEN is unset in environment, websocket refuses all connections (fail closed)."""
    os.environ.pop("PHENOM_SESSION_TOKEN", None)
    client = TestClient(app)
    with pytest.raises(WebSocketDisconnect) as exc_info:
        with client.websocket_connect(
            "/ws",
            subprotocols=[f"phenom.{VALID_TOKEN}"],
            headers={"origin": "http://localhost:5173"}
        ):
            pass
    assert exc_info.value.code == 4401


def test_token_never_logged(caplog):
    """The session token must never appear in server logs during connection attempts."""
    import logging
    client = TestClient(app)
    with caplog.at_level(logging.DEBUG):
        # Attempt with valid token
        with client.websocket_connect(
            "/ws",
            subprotocols=[f"phenom.{VALID_TOKEN}"],
            headers={"origin": "http://localhost:5173"}
        ) as ws:
            ws.receive_json()

        # Attempt with invalid token
        with pytest.raises(WebSocketDisconnect):
            with client.websocket_connect("/ws", subprotocols=["phenom.super_secret_bad_token"]):
                pass

    log_text = caplog.text
    assert VALID_TOKEN not in log_text
    assert "super_secret_bad_token" not in log_text


def test_rate_limiting_after_five_failed_attempts():
    """More than 5 failed handshakes within 60 seconds triggers rate limiting."""
    client = TestClient(app)
    for _ in range(5):
        with pytest.raises(WebSocketDisconnect) as exc:
            with client.websocket_connect("/ws", subprotocols=["phenom.bad"]):
                pass
        assert exc.value.code == 4401

    # 6th attempt should be blocked immediately by rate limiter even with valid credentials
    with pytest.raises(WebSocketDisconnect) as exc:
        with client.websocket_connect(
            "/ws",
            subprotocols=[f"phenom.{VALID_TOKEN}"],
            headers={"origin": "http://localhost:5173"}
        ):
            pass
    assert exc.value.code == 4401


def test_rest_auth_protection():
    """Unauthenticated REST calls must return 401; /health returns 200 without secrets."""
    client = TestClient(app)
    
    # Public health check
    res_health = client.get("/health")
    assert res_health.status_code == 200
    assert res_health.json() == {"status": "ok"}
    
    # Unauthenticated protected route
    res_logs_unauth = client.get("/api/logs")
    assert res_logs_unauth.status_code == 401
    
    # Invalid token
    res_logs_bad = client.get("/api/logs", headers={"Authorization": "Bearer badtoken"})
    assert res_logs_bad.status_code == 401
    
    # Valid token
    res_logs_ok = client.get("/api/logs", headers={"Authorization": f"Bearer {VALID_TOKEN}"})
    assert res_logs_ok.status_code == 200
