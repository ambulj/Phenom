"""
Unit Tests for Phenom Gaming Mode & Notification Digest (Task 7j)
Covers:
1. Detection engine triggering on game executables and full-screen DirectX/Vulkan apps.
2. Strict exclusion filters for browsers, video players, presentations, and remote desktop.
3. Resource governance: notification mute, scheduler pause, power plan switch, VRAM offload, and Orb freeze.
4. Full restoration on game exit.
5. 'What Did I Miss' notification digest with strict zero-leakage guarantee for OTPs and financial details.
"""

import re
import pytest
from services.backend.automation.gaming_mode import GamingModeManager, KNOWN_GAME_PROCESSES, EXCLUDED_PROCESSES
from services.backend.automation.notification_digest import NotificationDigestManager, notification_digest_manager
from services.backend.resource.vram_manager import vram_manager
from services.backend.scheduler.cron import background_scheduler

@pytest.fixture
def gaming_mgr():
    return GamingModeManager()

@pytest.fixture
def digest_mgr():
    return NotificationDigestManager()

# ==============================================================================
# 1. Gaming Mode Detection & Strict Exclusion Tests
# ==============================================================================

def test_detects_known_game_executables(gaming_mgr):
    """Verifies that known games trigger gaming mode."""
    test_games = ["cs2.exe", "valorant.exe", "steam.exe", "cyberpunk2077.exe", "dota2.exe"]
    for game in test_games:
        is_gaming, detected, reason = gaming_mgr.detect_gaming_state(mock_foreground_proc=game)
        assert is_gaming is True, f"Failed to detect known game: {game}"
        assert detected == game
        assert "known_game_executable" in reason

def test_detects_fullscreen_directx_application(gaming_mgr):
    """Verifies that generic unlisted full-screen 3D app triggers gaming mode."""
    is_gaming, detected, reason = gaming_mgr.detect_gaming_state(
        mock_foreground_proc="custom_unreal_engine_game.exe",
        mock_is_fullscreen=True
    )
    assert is_gaming is True
    assert detected == "custom_unreal_engine_game.exe"
    assert "fullscreen_directx_app" in reason

def test_strict_exclusions_never_trigger_gaming_mode(gaming_mgr):
    """
    STRICT INVARIANT: Fullscreen browsers, video players, presentations,
    and remote desktop tools must NEVER trigger gaming mode.
    """
    excluded_samples = [
        # Video players & Browsers
        "chrome.exe", "brave.exe", "msedge.exe", "firefox.exe", "vlc.exe", "mpv.exe",
        # Presentations
        "powerpnt.exe",
        # Remote Desktop / VMs
        "mstsc.exe", "vmware.exe", "virtualbox.exe", "teamviewer.exe", "anydesk.exe",
        # System / Shell
        "phenom.exe", "explorer.exe", "code.exe"
    ]
    for proc in excluded_samples:
        is_gaming, detected, reason = gaming_mgr.detect_gaming_state(
            mock_foreground_proc=proc,
            mock_is_fullscreen=True
        )
        assert is_gaming is False, f"Exclusion filter violated: {proc} triggered gaming mode!"
        assert detected is None
        assert "excluded_application" in reason

# ==============================================================================
# 2. Resource Governance & Restoration Lifecycle Tests
# ==============================================================================

@pytest.mark.asyncio
async def test_gaming_mode_enter_and_exit_lifecycle(gaming_mgr):
    """
    Verifies that entering gaming mode mutes notifications, pauses scheduler,
    switches power plan, unloads VRAM (<100MB), and freezes Orb LOD.
    Verifies clean restoration on exit.
    """
    # 1. Enter gaming mode
    res_enter = await gaming_mgr.enter_gaming_mode("cyberpunk2077.exe", reason="test_runner")
    assert res_enter["status"] == "gaming_mode_active"
    assert res_enter["game"] == "cyberpunk2077.exe"
    assert res_enter["power_plan"] == "high_performance"
    assert res_enter["notifications_muted"] is True
    assert res_enter["scheduler_paused"] is True
    assert res_enter["vram_offloaded"] <= 100.0
    assert res_enter["orb_lod"] == "freeze"

    assert gaming_mgr.gaming_mode_active is True
    assert background_scheduler.is_paused is True
    assert vram_manager.gaming_mode_active is True
    assert vram_manager.get_orb_lod_quality() == "freeze"

    # 2. Exit gaming mode
    res_exit = await gaming_mgr.exit_gaming_mode()
    assert res_exit["status"] == "gaming_mode_exited"
    assert res_exit["previous_game"] == "cyberpunk2077.exe"
    assert res_exit["power_plan"] == "balanced"
    assert res_exit["notifications_muted"] is False
    assert res_exit["scheduler_paused"] is False
    assert res_exit["orb_lod"] in ["high", "medium", "low"]

    assert gaming_mgr.gaming_mode_active is False
    assert background_scheduler.is_paused is False
    assert vram_manager.gaming_mode_active is False
    assert vram_manager.get_orb_lod_quality() != "freeze"

# ==============================================================================
# 3. 'What Did I Miss' Notification Digest Tests (Zero Leakage Guarantee)
# ==============================================================================

def test_notification_digest_empty(digest_mgr):
    """When no notifications were buffered, returns clean polite response."""
    digest = digest_mgr.generate_spoken_digest()
    assert digest["count"] == 0
    assert digest["spoken_text"] == "You have no missed notifications, sir."

def test_notification_digest_redacts_otp_and_financial_data(digest_mgr):
    """
    STRICT SECURITY INVARIANT:
    OTPs and financial details are NEVER spoken or leaked in the digest.
    """
    # 1. Telegram chat message
    digest_mgr.buffer_notification(
        source="Telegram",
        title="Alex",
        body="Hey mate, let's catch up online later tonight."
    )
    # 2. OTP authentication notification
    digest_mgr.buffer_notification(
        source="Google",
        title="Google Verification",
        body="Your Google verification code is 849201. Never share this OTP with anyone."
    )
    # 3. Calendar event
    digest_mgr.buffer_notification(
        source="Calendar",
        title="Team Sync Meeting",
        body="Sprint retrospective in 15 minutes in room 4."
    )
    # 4. Bank debit alert
    digest_mgr.buffer_notification(
        source="HDFC Bank",
        title="Account Alert",
        body="INR 45,000 debited from account ending in xx8912 on 29-Oct."
    )
    # 5. System update
    digest_mgr.buffer_notification(
        source="System",
        title="Windows Security Update",
        body="Patch KB5034441 downloaded and ready to apply."
    )

    digest = digest_mgr.generate_spoken_digest()
    assert digest["count"] == 5
    spoken_text = digest["spoken_text"]

    # Verify conversational format
    assert spoken_text.startswith("You missed 5 notifications:")
    assert "Telegram message from Alex" in spoken_text
    assert "verification alert from Google (code hidden for security)" in spoken_text
    assert "calendar reminder for Team Sync Meeting" in spoken_text
    assert "bank alert from HDFC Bank (financial details hidden for security)" in spoken_text
    assert "System update for Windows Security Update" in spoken_text

    # STRICT CHECK: Zero OTP digits or financial numbers in spoken text!
    assert "849201" not in spoken_text, "CRITICAL: OTP digit leaked in spoken digest!"
    assert "45,000" not in spoken_text, "CRITICAL: Financial amount leaked in spoken digest!"
    assert "xx8912" not in spoken_text, "CRITICAL: Account digits leaked in spoken digest!"
    assert "8912" not in spoken_text, "CRITICAL: Account number leaked in spoken digest!"

    # Ensure no 4-8 digit numbers leaked anywhere in the spoken string
    numeric_leaks = re.findall(r"\b\d{4,8}\b", spoken_text)
    assert len(numeric_leaks) == 0, f"Found numeric leaks: {numeric_leaks}"

    # Buffer clearing
    cleared = digest_mgr.clear_buffer()
    assert cleared == 5
    assert len(digest_mgr.get_missed_notifications()) == 0
