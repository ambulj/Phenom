"""
Phase 4 Verification Suite: Mobile Remote Companion & Safety Hardening
Tests:
1. Telegram owner whitelisting & stranger silent drop.
2. Remote /status command real-time telemetry formatting.
3. Remote /halt and /resume kill switch controls.
4. Remote PIN gate & 3-strike lockout with ephemeral deletion.
5. Proactive broadcast_remote_alert ambient dispatch.
6. Multi-layer Rule 8 zero-payment enforcement across all 4 defense layers.
7. Guardian kill switch synchronous halt latency (< 25ms SLA) & autonomous engine abort.
"""

import time
import pytest
import asyncio
from typing import Dict, Any, List

from services.backend.remote.telegram_bot import TelegramBotController
from services.backend.remote.telegram_client import TelegramClient
from services.backend.remote.credentials import (
    set_remote_pin, verify_remote_pin, get_failed_pin_attempts,
    reset_failed_pin_attempts, is_remote_locked, set_remote_locked,
    unlock_remote_from_desktop
)
from services.backend.safety.guardian import guardian
from services.backend.safety.action_log import action_log
from services.backend.automation.goal_planner import AutonomousGoalPlanner
from services.backend.tools.automation_tools import checkout_pay, enter_payment_info
from services.backend.browser.cart_automator import cart_automator
from services.backend.automation.autonomous_engine import autonomous_engine
from services.backend.main import on_guardian_state_change


OWNER_ID = 99887766
ATTACKER_ID = 11223344


class MockTelegramClient(TelegramClient):
    """In-memory mock Telegram client for testing."""
    def __init__(self):
        super().__init__(token="mock_token_phase4")
        self.sent_messages: List[Dict[str, Any]] = []
        self.edited_messages: List[Dict[str, Any]] = []
        self.answered_callbacks: List[Dict[str, Any]] = []
        self.deleted_messages: List[Dict[str, Any]] = []

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

    async def delete_message(self, chat_id: int, message_id: int) -> bool:
        self.deleted_messages.append({"chat_id": chat_id, "message_id": message_id})
        return True


@pytest.fixture
def mock_bot():
    """Provides a fresh TelegramBotController configured with mock client and owner."""
    bot = TelegramBotController()
    bot._token = "mock_token_phase4"
    bot._owner_id = OWNER_ID
    mock_client = MockTelegramClient()
    bot.client = mock_client
    bot.ignored_messages_log.clear()
    bot._pending_pin_tasks.clear()

    # Reset security state
    unlock_remote_from_desktop()
    set_remote_pin("123456")
    guardian.resume()

    yield bot, mock_client

    # Teardown
    unlock_remote_from_desktop()
    guardian.resume()


# ==============================================================================
# TEST 1: Telegram Owner Whitelisting & Stranger Silent Drop
# ==============================================================================

@pytest.mark.asyncio
async def test_telegram_owner_whitelisting_and_stranger_silent_drop(mock_bot):
    bot, client = mock_bot

    # Attacker tries sending command
    attacker_update = {
        "update_id": 101,
        "message": {
            "message_id": 1,
            "from": {"id": ATTACKER_ID, "username": "attacker"},
            "chat": {"id": ATTACKER_ID},
            "text": "/status"
        }
    }
    res = await bot.process_update(attacker_update)
    assert res is None, "Stranger update must return None"
    assert len(client.sent_messages) == 0, "No messages should ever be sent to stranger"
    assert len(bot.ignored_messages_log) == 1
    assert bot.ignored_messages_log[0]["sender_id"] == ATTACKER_ID
    assert bot.ignored_messages_log[0]["reason"] == "non_whitelisted_sender"

    # Attacker tries callback query
    attacker_cb = {
        "update_id": 102,
        "callback_query": {
            "id": "cb_attack",
            "from": {"id": ATTACKER_ID},
            "data": "status:refresh",
            "message": {"message_id": 2, "chat": {"id": ATTACKER_ID}}
        }
    }
    res_cb = await bot.process_update(attacker_cb)
    assert res_cb is None
    assert len(client.answered_callbacks) == 0
    assert len(bot.ignored_messages_log) == 2


# ==============================================================================
# TEST 2: Remote /status Command Formatting
# ==============================================================================

@pytest.mark.asyncio
async def test_telegram_status_command(mock_bot):
    bot, client = mock_bot

    owner_update = {
        "update_id": 201,
        "message": {
            "message_id": 10,
            "from": {"id": OWNER_ID, "username": "owner"},
            "chat": {"id": OWNER_ID},
            "text": "/status"
        }
    }
    res = await bot.process_update(owner_update)
    assert res == {"status": "status_sent"}
    assert len(client.sent_messages) == 1
    msg = client.sent_messages[0]
    assert msg["chat_id"] == OWNER_ID
    assert "Phenom Operational Status" in msg["text"]
    assert "CPU:" in msg["text"]
    assert "RAM:" in msg["text"]
    assert "Guardian:" in msg["text"]
    assert "Mode:" in msg["text"]
    assert "Remote:" in msg["text"]
    assert "reply_markup" in msg


# ==============================================================================
# TEST 3: Remote /halt and /resume Kill Switch
# ==============================================================================

@pytest.mark.asyncio
async def test_telegram_remote_halt_and_resume(mock_bot):
    bot, client = mock_bot

    # Halt command
    halt_update = {
        "update_id": 301,
        "message": {
            "message_id": 20,
            "from": {"id": OWNER_ID},
            "chat": {"id": OWNER_ID},
            "text": "/halt"
        }
    }
    res_halt = await bot.process_update(halt_update)
    assert res_halt == {"status": "halted"}
    assert guardian.is_halted is True
    assert len(client.sent_messages) == 1
    assert "Guardian Kill Switch Activated" in client.sent_messages[0]["text"]

    # Resume command
    resume_update = {
        "update_id": 302,
        "message": {
            "message_id": 21,
            "from": {"id": OWNER_ID},
            "chat": {"id": OWNER_ID},
            "text": "/resume"
        }
    }
    res_resume = await bot.process_update(resume_update)
    assert res_resume == {"status": "resumed"}
    assert guardian.is_halted is False
    assert len(client.sent_messages) == 2
    assert "Guardian Kill Switch Resumed" in client.sent_messages[1]["text"]


# ==============================================================================
# TEST 4: Remote PIN Gate & 3-Strike Lockout
# ==============================================================================

@pytest.mark.asyncio
async def test_telegram_remote_pin_gate_and_lockout(mock_bot):
    bot, client = mock_bot

    # 1. Tier 2 task /do triggers PIN requirement
    do_update = {
        "update_id": 401,
        "message": {
            "message_id": 30,
            "from": {"id": OWNER_ID},
            "chat": {"id": OWNER_ID},
            "text": "/do delete old_archive.zip"
        }
    }
    res_do = await bot.process_update(do_update)
    assert res_do is not None
    assert res_do.get("status") == "pin_required"
    assert len(client.sent_messages) == 1
    assert "PIN Authorization Required" in client.sent_messages[0]["text"]

    # 2. Enter wrong PIN attempt 1
    pin1_update = {
        "update_id": 402,
        "message": {
            "message_id": 31,
            "from": {"id": OWNER_ID},
            "chat": {"id": OWNER_ID},
            "text": "000000"
        }
    }
    res_pin1 = await bot.process_update(pin1_update)
    assert res_pin1["status"] == "invalid_pin"
    assert res_pin1["remaining"] == 2
    assert get_failed_pin_attempts() == 1

    # 3. Enter wrong PIN attempt 2
    pin2_update = {
        "update_id": 403,
        "message": {
            "message_id": 32,
            "from": {"id": OWNER_ID},
            "chat": {"id": OWNER_ID},
            "text": "111111"
        }
    }
    res_pin2 = await bot.process_update(pin2_update)
    assert res_pin2["status"] == "invalid_pin"
    assert res_pin2["remaining"] == 1
    assert get_failed_pin_attempts() == 2

    # 4. Enter wrong PIN attempt 3 -> Lockout
    pin3_update = {
        "update_id": 404,
        "message": {
            "message_id": 33,
            "from": {"id": OWNER_ID},
            "chat": {"id": OWNER_ID},
            "text": "222222"
        }
    }
    res_pin3 = await bot.process_update(pin3_update)
    assert res_pin3["status"] == "lockout_triggered"
    assert is_remote_locked() is True

    # 5. When locked, commands are rejected
    status_while_locked = {
        "update_id": 405,
        "message": {
            "message_id": 34,
            "from": {"id": OWNER_ID},
            "chat": {"id": OWNER_ID},
            "text": "/status"
        }
    }
    res_locked = await bot.process_update(status_while_locked)
    assert res_locked == {"status": "locked"}

    # 6. Physical desktop unlock restores access
    unlock_remote_from_desktop()
    assert is_remote_locked() is False
    assert get_failed_pin_attempts() == 0


# ==============================================================================
# TEST 5: Proactive Ambient Broadcast Remote Alert
# ==============================================================================

@pytest.mark.asyncio
async def test_telegram_broadcast_remote_alert(mock_bot):
    bot, client = mock_bot

    # Normal broadcast
    success = await bot.broadcast_remote_alert(
        title="High CPU Sustained",
        message="Phenom background task CPU load exceeded 92%",
        urgency="high"
    )
    assert success is True
    assert len(client.sent_messages) == 1
    msg = client.sent_messages[0]
    assert msg["chat_id"] == OWNER_ID
    assert "High CPU Sustained" in msg["text"]
    assert "⚠️" in msg["text"]

    # When remote locked, broadcast returns False
    set_remote_locked(True)
    success_locked = await bot.broadcast_remote_alert(
        title="Meeting Reminder",
        message="Sprint review starting in 5 minutes",
        urgency="critical"
    )
    assert success_locked is False
    assert len(client.sent_messages) == 1  # No additional message sent


# ==============================================================================
# TEST 6: Multi-Layer Rule 8 Zero-Payment Enforcement Audit
# ==============================================================================

@pytest.mark.asyncio
async def test_rule_8_multi_layer_zero_payment_enforcement(mock_bot):
    bot, client = mock_bot

    # --- LAYER 1: Telegram Remote Bridge Gate ---
    payment_command = {
        "update_id": 601,
        "message": {
            "message_id": 40,
            "from": {"id": OWNER_ID},
            "chat": {"id": OWNER_ID},
            "text": "/do pay for grocery cart on instamart"
        }
    }
    res_l1 = await bot.process_update(payment_command)
    assert res_l1 is not None
    assert res_l1.get("status") == "payment_prohibited"
    assert len(client.sent_messages) == 1
    assert "Rule 8" in client.sent_messages[0]["text"]
    assert "prohibited from executing purchases" in client.sent_messages[0]["text"]

    # Verify action log has blocked entry
    entries = action_log.list_entries(limit=1)
    assert len(entries) >= 1
    assert entries[0]["tool"] == "telegram_do"
    assert entries[0]["decision"] == "blocked"

    # --- LAYER 2: Goal Planner Pre-Flight Prohibition ---
    planner = AutonomousGoalPlanner()
    with pytest.raises(PermissionError) as exc_info:
        planner.plan_goal("Complete checkout and pay for headphones on Amazon")
    assert "prohibited by SAFETY.md" in str(exc_info.value)

    with pytest.raises(PermissionError) as exc_info2:
        planner.plan_goal("place order for Swiggy food delivery")
    assert "prohibited by SAFETY.md" in str(exc_info2.value)

    # --- LAYER 3: Safety Tool Registry Permanent Blocks ---
    with pytest.raises(PermissionError) as exc_tool1:
        checkout_pay(payment_method="credit_card")
    assert "strictly prohibited" in str(exc_tool1.value)

    with pytest.raises(PermissionError) as exc_tool2:
        enter_payment_info(card_details="4111222233334444")
    assert "strictly prohibited" in str(exc_tool2.value)

    # --- LAYER 4: Cart Automator Code-Level Keyword Check ---
    with pytest.raises(PermissionError) as exc_cart1:
        cart_automator.verify_no_payment_action("Proceed to pay now")
    assert "prohibited by SAFETY.md" in str(exc_cart1.value)

    with pytest.raises(PermissionError) as exc_cart2:
        cart_automator.verify_no_payment_action("Submit OTP to bank")
    assert "prohibited by SAFETY.md" in str(exc_cart2.value)


# ==============================================================================
# TEST 7: Guardian Kill Switch Synchronous Latency & Autonomous Abort
# ==============================================================================

@pytest.mark.asyncio
async def test_guardian_kill_switch_synchronous_latency_and_autonomous_abort():
    # Setup autonomous engine state
    autonomous_engine.is_running = True
    autonomous_engine._stop_requested = False
    autonomous_engine.abort_reason = None
    guardian.resume()
    assert guardian.is_halted is False

    # Measure halt execution time including on_guardian_state_change
    t_start = time.perf_counter()
    guardian.trigger("Test Synchronous Kill Switch Trigger")
    on_guardian_state_change("halted")
    t_elapsed = time.perf_counter() - t_start

    # SLA Verification: Must halt in < 25.0 milliseconds
    latency_ms = t_elapsed * 1000.0
    print(f"\n[GUARDIAN SLA TEST] Synchronous halt latency: {latency_ms:.3f} ms (SLA < 25.0 ms)")
    assert t_elapsed < 0.025, f"Guardian halt exceeded 25ms SLA: {latency_ms:.2f}ms"

    # Verify Guardian and Autonomous state
    assert guardian.is_halted is True
    assert autonomous_engine.is_running is False
    assert autonomous_engine._stop_requested is True
    assert autonomous_engine.abort_reason == "guardian_halt"

    # Clean up
    guardian.resume()
    assert guardian.is_halted is False
