"""Unit tests for Telegram Screen Snapshot & Remote Uplink Tools (Milestone 46 Phase 3)."""

import pytest
from services.backend.safety.guardian import guardian
from services.backend.safety.registry import registry
from services.backend.telegram.bot_controller import bot_controller
from services.backend.telegram.screen_snapshot import telegram_snapshot_provider
from services.backend.tools.telegram_tools import (
    handle_dispatch_telegram_notification,
    handle_send_telegram_voice_note,
    handle_get_telegram_uplink_status,
    handle_trigger_remote_screen_snapshot,
)


@pytest.fixture(autouse=True)
def clean_guardian_and_telegram():
    """Reset guardian and bot controller state before and after each test."""
    guardian.resume()
    bot_controller.outbound_messages.clear()
    yield
    guardian.resume()


def test_sensitive_window_triggers_privacy_shield_snapshot(tmp_path):
    """Tests that active password managers or banking portals generate opaque privacy shield (Rule 4)."""
    files_before = list(tmp_path.glob("**/*"))

    image_bytes, is_shielded, caption = telegram_snapshot_provider.capture_snapshot(
        active_window_title="KeePassXC - Master Database",
        active_window_process="keepassxc.exe",
    )

    files_after = list(tmp_path.glob("**/*"))

    assert len(files_before) == len(files_after)  # Rule 4: zero disk writes
    assert is_shielded is True
    assert "PRIVACY SHIELD ACTIVE" in caption
    assert len(image_bytes) > 0


def test_non_sensitive_window_snapshot_generation():
    """Tests that developer terminal snapshots are captured in RAM with caption telemetry."""
    image_bytes, is_shielded, caption = telegram_snapshot_provider.capture_snapshot(
        active_window_title="kali@kali: ~ (WSL2)",
        active_window_process="wsl.exe",
    )

    assert is_shielded is False
    assert "Desktop Snapshot" in caption
    assert "Rule 4 Zero-Disk" in caption
    assert len(image_bytes) > 0


def test_telegram_tools_registration_and_execution():
    """Verifies that all 4 Telegram tools are registered in Safety registry and execute cleanly."""
    expected_tools = [
        "dispatch_telegram_notification",
        "send_telegram_voice_note",
        "get_telegram_uplink_status",
        "trigger_remote_screen_snapshot",
    ]

    for tool_name in expected_tools:
        assert registry.get(tool_name) is not None, f"Tool '{tool_name}' not registered in Safety registry"

    # 1. Dispatch Notification
    notif_res = handle_dispatch_telegram_notification(text="Nmap scan completed on 127.0.0.1", priority="high")
    assert notif_res["success"] is True
    assert notif_res["queued_messages_count"] == 1

    # 2. Send Voice Note
    voice_res = handle_send_telegram_voice_note(text="Good evening, sir. Workstation is nominal.")
    assert voice_res["success"] is True
    assert voice_res["audio_bytes_length"] > 44
    assert voice_res["zero_disk_compliance"] is True

    # 3. Uplink Status
    status_res = handle_get_telegram_uplink_status()
    assert status_res["online"] is True
    assert status_res["guardian_halted"] is False

    # 4. Screen Snapshot Tool
    snap_res = handle_trigger_remote_screen_snapshot(window_title="VS Code", process_name="code.exe")
    assert snap_res["success"] is True
    assert snap_res["is_shielded"] is False
    assert snap_res["zero_disk_compliance"] is True


def test_guardian_halt_blocks_telegram_dispatches():
    """Tests that Guardian Kill Switch immediately blocks tool execution and dispatches."""
    guardian.trigger("Emergency stop during remote operation")

    notif_res = handle_dispatch_telegram_notification(text="Should not send")
    assert notif_res["success"] is False
    assert notif_res["guardian_halted"] is True

    voice_res = handle_send_telegram_voice_note(text="Should not synthesize")
    assert voice_res["success"] is False
    assert voice_res["guardian_halted"] is True

    snap_res = handle_trigger_remote_screen_snapshot()
    assert snap_res["success"] is False
    assert snap_res["guardian_halted"] is True
