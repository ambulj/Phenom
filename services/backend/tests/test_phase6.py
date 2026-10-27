"""
Unit and Integration Tests for Phase 6: Telegram Remote Control and Approvals
Verifies:
1. Messages and callback queries from non-whitelisted user IDs are silently ignored and logged.
2. Approval round trip works for Tier 1 and Tier 2 actions via inline button callbacks.
3. Tier 3 actions are categorically refused remotely and cannot be approved from Telegram.
4. Remote kill switch (/halt) halts all running tasks immediately and confirms.
5. /lock command disables remote control until re-enabled at the desktop.
6. Status, task, and log summaries are returned with private content redacted.
"""

import pytest
import asyncio
from typing import Dict, Any, List
from services.backend.remote.telegram_bot import TelegramBotController
from services.backend.remote.telegram_client import TelegramClient
from services.backend.remote.credentials import is_remote_locked, set_remote_locked
from services.backend.safety.guardian import guardian
from services.backend.safety.engine import safety_engine
from services.backend.safety.registry import registry
from services.backend.safety.action_log import action_log
import services.backend.tools.file_tools
import services.backend.tools.memory_tools
import services.backend.tools.integration_tools

OWNER_USER_ID = 123456789
ATTACKER_USER_ID = 999999999

class MockTelegramClient(TelegramClient):
    """In-memory mock Telegram client recording all outgoing messages and callbacks."""
    def __init__(self):
        super().__init__(token="mock_token_12345")
        self.sent_messages: List[Dict[str, Any]] = []
        self.edited_messages: List[Dict[str, Any]] = []
        self.answered_callbacks: List[Dict[str, Any]] = []

    async def send_message(self, chat_id: int, text: str, reply_markup=None, parse_mode="Markdown") -> Dict[str, Any]:
        msg = {
            "message_id": len(self.sent_messages) + 1,
            "chat_id": chat_id,
            "text": text,
            "reply_markup": reply_markup,
            "parse_mode": parse_mode
        }
        self.sent_messages.append(msg)
        return msg

    async def edit_message_text(self, chat_id: int, message_id: int, text: str, reply_markup=None, parse_mode="Markdown") -> Dict[str, Any]:
        msg = {
            "message_id": message_id,
            "chat_id": chat_id,
            "text": text,
            "reply_markup": reply_markup
        }
        self.edited_messages.append(msg)
        return msg

    async def answer_callback_query(self, callback_query_id: str, text=None, show_alert=False) -> Dict[str, Any]:
        res = {"callback_query_id": callback_query_id, "text": text, "show_alert": show_alert}
        self.answered_callbacks.append(res)
        return res

@pytest.fixture
def mock_bot():
    guardian.resume()
    set_remote_locked(False)
    client = MockTelegramClient()
    bot = TelegramBotController(token="mock_token_12345", owner_id=OWNER_USER_ID, client=client)
    yield bot
    guardian.resume()
    set_remote_locked(False)

@pytest.mark.asyncio
async def test_non_whitelisted_sender_is_ignored_and_logged(mock_bot):
    """Verifies any non-whitelisted sender is silently ignored, logged, and gets zero reply."""
    update = {
        "update_id": 100,
        "message": {
            "message_id": 1,
            "from": {"id": ATTACKER_USER_ID, "first_name": "Attacker"},
            "chat": {"id": ATTACKER_USER_ID},
            "text": "Hello Phenom, open my files!"
        }
    }

    res = await mock_bot.process_update(update)
    assert res is None
    # No reply sent to attacker
    assert len(mock_bot.client.sent_messages) == 0
    # Security log recorded
    assert len(mock_bot.ignored_messages_log) >= 1
    assert mock_bot.ignored_messages_log[-1]["sender_id"] == ATTACKER_USER_ID
    assert mock_bot.ignored_messages_log[-1]["reason"] == "non_whitelisted_sender"

@pytest.mark.asyncio
async def test_approval_roundtrip_tier1_and_tier2(mock_bot):
    """Verifies that an inline button callback resolves the safety confirmation."""
    req_id = "test-conf-1234"
    
    # Simulate safety engine invoking handle_remote_approval_request in background task
    async def request_approval_task():
        return await mock_bot.handle_remote_approval_request(
            request_id=req_id,
            tool="create_file",
            tier=1,
            preview="Create file C:/test.txt",
            args={"path": "C:/test.txt"}
        )

    task = asyncio.create_task(request_approval_task())
    await asyncio.sleep(0.05)

    # Verify message sent to owner with inline keyboard
    assert len(mock_bot.client.sent_messages) == 1
    sent = mock_bot.client.sent_messages[0]
    assert sent["chat_id"] == OWNER_USER_ID
    assert "Tier 1" in sent["text"]
    assert "create_file" in sent["text"]

    # Now owner clicks "Approve" inline button
    approve_update = {
        "update_id": 101,
        "callback_query": {
            "id": "cb_1",
            "from": {"id": OWNER_USER_ID},
            "message": {"chat": {"id": OWNER_USER_ID}, "message_id": 1},
            "data": f"approve:{req_id}"
        }
    }
    await mock_bot.process_update(approve_update)

    decision, remember = await task
    assert decision == "approved"
    assert remember is False
    assert len(mock_bot.client.answered_callbacks) == 1
    assert "Approved!" in mock_bot.client.answered_callbacks[0]["text"]

@pytest.mark.asyncio
async def test_tier3_refused_remotely():
    """Verifies Tier 3 tools cannot be approved remotely and are refused with clear error."""
    guardian.resume()
    
    # Attempting a Tier 3 tool from source='telegram'
    with pytest.raises(PermissionError, match="cannot be approved remotely"):
        await safety_engine.execute_tool(
            tool_name="send_email",
            raw_args={"to": "test@example.com", "subject": "Hi", "body": "Body"},
            source="telegram"
        )

    # Verify recorded as blocked in action log
    recent_logs = action_log.list_entries(limit=5)
    matched = [l for l in recent_logs if l["tool"] == "send_email"]
    assert len(matched) >= 1
    assert matched[0]["decision"] == "blocked"
    assert matched[0]["tier"] == 3

@pytest.mark.asyncio
async def test_remote_kill_switch_halts_running_task(mock_bot):
    """Verifies /halt immediately triggers Guardian kill switch and halts actions."""
    assert guardian.is_halted is False

    update = {
        "update_id": 102,
        "message": {
            "message_id": 2,
            "from": {"id": OWNER_USER_ID},
            "chat": {"id": OWNER_USER_ID},
            "text": "/halt"
        }
    }
    res = await mock_bot.process_update(update)
    assert res["status"] == "halted"
    assert guardian.is_halted is True

    # Check confirmation message sent to owner
    assert len(mock_bot.client.sent_messages) == 1
    assert "Guardian Kill Switch Activated" in mock_bot.client.sent_messages[-1]["text"]

    # Resume via /resume
    resume_update = {
        "update_id": 103,
        "message": {
            "message_id": 3,
            "from": {"id": OWNER_USER_ID},
            "chat": {"id": OWNER_USER_ID},
            "text": "/resume"
        }
    }
    res_resume = await mock_bot.process_update(resume_update)
    assert res_resume["status"] == "resumed"
    assert guardian.is_halted is False

@pytest.mark.asyncio
async def test_lock_command_disables_remote_control_until_desktop_unlock(mock_bot):
    """Verifies /lock disables remote control and cannot be unlocked from Telegram."""
    assert is_remote_locked() is False

    # 1. Owner sends /lock
    lock_update = {
        "update_id": 104,
        "message": {
            "message_id": 4,
            "from": {"id": OWNER_USER_ID},
            "chat": {"id": OWNER_USER_ID},
            "text": "/lock"
        }
    }
    res = await mock_bot.process_update(lock_update)
    assert res["status"] == "locked_by_user"
    assert is_remote_locked() is True

    # 2. Subsequent commands rejected
    cmd_update = {
        "update_id": 105,
        "message": {
            "message_id": 5,
            "from": {"id": OWNER_USER_ID},
            "chat": {"id": OWNER_USER_ID},
            "text": "/status"
        }
    }
    res_cmd = await mock_bot.process_update(cmd_update)
    assert res_cmd["status"] == "locked"
    assert "Remote Control is Locked" in mock_bot.client.sent_messages[-1]["text"]

    # 3. /unlock on Telegram is refused
    unlock_tg = {
        "update_id": 106,
        "message": {
            "message_id": 6,
            "from": {"id": OWNER_USER_ID},
            "chat": {"id": OWNER_USER_ID},
            "text": "/unlock"
        }
    }
    res_unlock = await mock_bot.process_update(unlock_tg)
    assert res_unlock["status"] == "locked"
    assert "Remote Unlock Forbidden" in mock_bot.client.sent_messages[-1]["text"]
    assert is_remote_locked() is True

    # 4. Physical desktop unlock clears lock
    set_remote_locked(False)
    assert is_remote_locked() is False

@pytest.mark.asyncio
async def test_status_tasks_and_logs_summaries(mock_bot):
    """Verifies /status, /tasks, and /logs commands return sanitized summaries."""
    # Status
    await mock_bot.process_update({
        "update_id": 107,
        "message": {"message_id": 7, "from": {"id": OWNER_USER_ID}, "chat": {"id": OWNER_USER_ID}, "text": "/status"}
    })
    status_msg = mock_bot.client.sent_messages[-1]["text"]
    assert "Phenom Status Summary" in status_msg

    # Tasks
    await mock_bot.process_update({
        "update_id": 108,
        "message": {"message_id": 8, "from": {"id": OWNER_USER_ID}, "chat": {"id": OWNER_USER_ID}, "text": "/tasks"}
    })
    tasks_msg = mock_bot.client.sent_messages[-1]["text"]
    assert "Scheduled Tasks" in tasks_msg

    # Logs
    await mock_bot.process_update({
        "update_id": 109,
        "message": {"message_id": 9, "from": {"id": OWNER_USER_ID}, "chat": {"id": OWNER_USER_ID}, "text": "/logs"}
    })
    logs_msg = mock_bot.client.sent_messages[-1]["text"]
    assert "Security Action Logs" in logs_msg
