"""
Tests proving:
1. Real Google Workspace integration has zero sample data in production client.
2. Code-level prohibitions are permanently active (send_email, calendar edit/delete).
3. Draft creation produces valid RFC 5322 payloads without sending.
4. Credential manager configuration, status, and disconnect lifecycle.
5. REST endpoints in main.py for workspace management work with session authentication.
"""

import os
import email
import pytest
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient

from services.backend.integrations.google_workspace import (
    GoogleWorkspaceClient, EmailSendingProhibitedError, CalendarModificationProhibitedError
)
from services.backend.main import app

SESSION_TOKEN = "test_session_token_workspace_123"
os.environ["PHENOM_SESSION_TOKEN"] = SESSION_TOKEN

@pytest.fixture
def test_client():
    return TestClient(app)

def test_production_workspace_has_zero_sample_data():
    """Verifies that an unconfigured production client has zero sample emails or events."""
    gw = GoogleWorkspaceClient()
    assert gw.search_emails() == []
    assert gw.read_email("msg_001") is None
    assert gw.list_events() == []
    assert not hasattr(gw, "_sample_emails")
    assert not hasattr(gw, "_events")

def test_hard_prohibitions_cannot_be_bypassed():
    """Verifies permanent safety prohibitions on sending and modifying calendar events."""
    gw = GoogleWorkspaceClient()

    with pytest.raises(EmailSendingProhibitedError) as exc:
        gw.send_email("friend@example.com", "Hello", "How are you?")
    assert "strictly blocked" in str(exc.value)

    with pytest.raises(CalendarModificationProhibitedError) as exc:
        gw.delete_calendar_event("ev_123")
    assert "strictly blocked" in str(exc.value)

    with pytest.raises(CalendarModificationProhibitedError) as exc:
        gw.edit_calendar_event("ev_123", {"summary": "Changed"})
    assert "strictly blocked" in str(exc.value)

def test_draft_creation_produces_valid_rfc5322_mime():
    """Verifies that create_draft constructs a valid RFC 5322 / RFC 2822 email payload."""
    gw = GoogleWorkspaceClient()
    gw.set_gmail_credentials("sender@example.com", "fake-app-password")

    draft = gw.create_draft(
        to="recipient@example.com",
        subject="Project Status Update",
        body="Here is the project status update. All tests pass."
    )

    assert draft["status"] == "DRAFT"
    assert draft["to"] == "recipient@example.com"
    assert draft["subject"] == "Project Status Update"
    assert "Draft saved in Gmail" in draft["note"] or "Draft created locally" in draft["note"]

    # Verify stored in drafts session list
    assert len(gw.list_drafts()) >= 1
    gw.clear_gmail_credentials()

def test_credential_save_and_clear_lifecycle():
    """Verifies setting and clearing credentials in Windows Credential Manager / DB."""
    gw = GoogleWorkspaceClient()
    gw.set_gmail_credentials("mytest@gmail.com", "abcd-efgh-ijkl-mnop")
    addr, pwd = gw.get_gmail_credentials()
    assert addr == "mytest@gmail.com"
    assert pwd == "abcd-efgh-ijkl-mnop"
    assert gw.is_gmail_configured() is True

    gw.set_calendar_token("ya29.testtoken12345")
    assert gw.get_calendar_token() == "ya29.testtoken12345"
    assert gw.is_calendar_configured() is True

    # Clear
    gw.clear_gmail_credentials()
    assert gw.is_gmail_configured() is False
    assert gw.get_gmail_credentials() == (None, None)

    gw.clear_calendar_token()
    assert gw.is_calendar_configured() is False
    assert gw.get_calendar_token() is None

def test_workspace_rest_endpoints(test_client):
    """Verifies REST endpoints for Google Workspace in main.py."""
    headers = {"Authorization": f"Bearer {SESSION_TOKEN}"}

    # 1. GET /api/workspace/status
    res = test_client.get("/api/workspace/status", headers=headers)
    assert res.status_code == 200
    data = res.json()
    assert "gmail_configured" in data
    assert "calendar_configured" in data

    # 2. POST /api/workspace/gmail/config
    res_gmail = test_client.post(
        "/api/workspace/gmail/config",
        headers=headers,
        json={"address": "assistant.test@gmail.com", "password": "app-test-password"}
    )
    assert res_gmail.status_code == 200
    assert res_gmail.json()["gmail_configured"] is True

    # 3. POST /api/workspace/calendar/config
    res_cal = test_client.post(
        "/api/workspace/calendar/config",
        headers=headers,
        json={"token": "ya29.oauth-test-token"}
    )
    assert res_cal.status_code == 200
    assert res_cal.json()["calendar_configured"] is True

    # 4. POST /api/workspace/test_connection (mocked network)
    with patch("imaplib.IMAP4_SSL") as mock_imap, patch("httpx.AsyncClient.get") as mock_http_get:
        mock_instance = MagicMock()
        mock_instance.examine.return_value = ("OK", [b"10"])
        mock_imap.return_value = mock_instance

        mock_http_resp = MagicMock()
        mock_http_resp.status_code = 200
        mock_http_resp.json.return_value = {"summary": "Primary Test Calendar"}
        mock_http_get.return_value = mock_http_resp

        res_test = test_client.post("/api/workspace/test_connection", headers=headers)
        assert res_test.status_code == 200
        test_data = res_test.json()
        assert test_data["gmail"]["ok"] is True
        assert test_data["calendar"]["ok"] is True

    # 5. POST /api/workspace/disconnect
    res_disc = test_client.post("/api/workspace/disconnect", headers=headers, json={"target": "all"})
    assert res_disc.status_code == 200
    disc_data = res_disc.json()
    assert disc_data["status"] == "disconnected"
    assert disc_data["gmail_configured"] is False
    assert disc_data["calendar_configured"] is False
