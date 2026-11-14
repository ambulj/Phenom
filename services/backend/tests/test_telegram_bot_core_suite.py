"""Unit tests for Telegram Bot Core Controller & Single-User Whitelist (Milestone 46 Phase 1)."""

import time
import pytest
from services.backend.safety.guardian import guardian
from services.backend.schemas.telegram import (
    TelegramChat,
    TelegramMessage,
    TelegramUpdate,
    TelegramUser,
)
from services.backend.telegram.bot_controller import TelegramBotController

TEST_USER_ID = 777888999


@pytest.fixture(autouse=True)
def clean_guardian_and_bot():
    """Reset guardian before and after each test."""
    guardian.resume()
    yield
    guardian.resume()


def create_test_update(sender_id: int, text: str) -> TelegramUpdate:
    return TelegramUpdate(
        update_id=1001,
        message=TelegramMessage(
            message_id=2001,
            from_user=TelegramUser(id=sender_id, first_name="AuthorizedOwner"),
            chat=TelegramChat(id=sender_id, type="private"),
            date=int(time.time()),
            text=text,
        )
    )


def test_unauthorized_sender_silently_dropped():
    """Tests that any update from an unauthorized user is dropped silently without response."""
    bot = TelegramBotController(authorized_user_id=TEST_USER_ID, dry_run=True)
    unauthorized_id = 999999999

    update = create_test_update(unauthorized_id, "/status")
    result = bot.handle_update(update)

    assert result.authorized is False
    assert result.success is False
    assert result.command == "UNAUTHORIZED_DROP"
    assert len(bot.outbound_messages) == 0


def test_authorized_start_and_help_commands():
    """Tests that authorized user receives witty Jarvis onboarding and command listing."""
    bot = TelegramBotController(authorized_user_id=TEST_USER_ID, dry_run=True)

    # Test /start
    update_start = create_test_update(TEST_USER_ID, "/start")
    res_start = bot.handle_update(update_start)
    assert res_start.authorized is True
    assert res_start.success is True
    assert "Phenom Remote Mobile Uplink" in res_start.response_text
    assert "/status" in res_start.response_text
    assert "/halt" in res_start.response_text

    # Test /help
    update_help = create_test_update(TEST_USER_ID, "/help")
    res_help = bot.handle_update(update_help)
    assert res_help.success is True
    assert len(bot.outbound_messages) == 2


def test_status_command_reports_subsystem_health():
    """Tests /status diagnostic command output."""
    bot = TelegramBotController(authorized_user_id=TEST_USER_ID, dry_run=True)

    update = create_test_update(TEST_USER_ID, "/status")
    result = bot.handle_update(update)

    assert result.success is True
    assert "RTX 3050" in result.response_text
    assert "Neocortex Vision" in result.response_text
    assert "Speed-Demon" in result.response_text
    assert "Anti-Checkout" in result.response_text


def test_remote_halt_guardian_kill_switch_sla_under_25ms():
    """Tests that remote /halt synchronously triggers Guardian kill switch in <25ms SLA."""
    bot = TelegramBotController(authorized_user_id=TEST_USER_ID, dry_run=True)
    assert guardian.is_halted is False

    update_halt = create_test_update(TEST_USER_ID, "/halt")

    t0 = time.perf_counter()
    result = bot.handle_update(update_halt)
    elapsed_ms = (time.perf_counter() - t0) * 1000.0

    assert result.success is True
    assert result.guardian_triggered is True
    assert guardian.is_halted is True
    assert "GUARDIAN KILL SWITCH ENGAGED REMOTELY" in result.response_text
    assert elapsed_ms < 25.0, f"Remote Guardian halt SLA breached: {elapsed_ms}ms >= 25.0ms"

    # Test /resume
    update_resume = create_test_update(TEST_USER_ID, "/resume")
    res_resume = bot.handle_update(update_resume)
    assert res_resume.success is True
    assert guardian.is_halted is False
    assert "RESUMED" in res_resume.response_text


def test_task_dispatch_under_guardian_halt():
    """Tests that task dispatch fails closed while Guardian is halted, and succeeds when nominal."""
    bot = TelegramBotController(authorized_user_id=TEST_USER_ID, dry_run=True)

    # Halt workstation
    guardian.trigger("Test halt")
    update_task = create_test_update(TEST_USER_ID, "/task run security audit")
    res_halted = bot.handle_update(update_task)
    assert res_halted.success is False
    assert "Guardian Kill Switch is active" in res_halted.response_text

    # Resume workstation
    guardian.resume()
    res_active = bot.handle_update(update_task)
    assert res_active.success is True
    assert "Task Dispatched to Action Agent" in res_active.response_text
