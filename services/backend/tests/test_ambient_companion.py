"""Tests for Ambient Context Watchdog & Telegram Super-Companion v2 (Milestone 30 Phase 4).

Validates:
- Context watchdog focus drift & calendar reminder alerts (AMB-01.1, AMB-01.2)
- Telegram super-companion voice note processing & audio replies (TEL-02.1)
- Remote desktop file search with Rule 11 secret filtering (TEL-02.2)
- Rule 8 checkout / payment rejection (raises Rule8ViolationError)
- Rule 11 credential protection ([REDACTED])
- Rule 3 Universal Guardian kill switch SLA < 25.0ms
- Safety Tool Registry integration (Tiers 0 & 1)
"""

import time
import pytest

from services.backend.safety.guardian import guardian
from services.backend.safety.registry import registry
from services.backend.ambient.context_watchdog import (
    ContextWatchdog,
    Rule8ViolationError as WatchdogRule8ViolationError,
)
from services.backend.remote.telegram_super_companion import (
    TelegramSuperCompanion,
    Rule8ViolationError as CompanionRule8ViolationError,
)
import services.backend.tools.ambient_companion_tools  # Registers tools in ToolRegistry


@pytest.fixture(autouse=True)
def reset_guardian():
    """Ensure Guardian is resumed before and after every test."""
    guardian.resume()
    yield
    guardian.resume()


@pytest.fixture
def watchdog():
    """Creates a fresh ContextWatchdog instance with zero cooldown for testing."""
    return ContextWatchdog(cooldown_seconds=0.01)


@pytest.fixture
def companion():
    """Creates a fresh TelegramSuperCompanion instance."""
    return TelegramSuperCompanion()


def test_context_watchdog_focus_drift_nudge(watchdog):
    """AMB-01.1: Context watchdog emits focus drift nudge on distraction window switch."""
    # Productive window switch -> no distraction
    nudge1 = watchdog.evaluate_app_switch("Visual Studio Code - Phenom", "Code.exe")
    assert nudge1 is None

    # Distraction window switch -> generates nudge
    nudge2 = watchdog.evaluate_app_switch("YouTube - Chill Lo-Fi Beats", "chrome.exe")
    assert nudge2 is not None
    assert nudge2.category == "FOCUS"
    assert "Focus Drift Detected" in nudge2.title
    assert "YouTube" in nudge2.message
    assert "stay locked" in (nudge2.voice_phrase or "")


def test_context_watchdog_calendar_reminder(watchdog):
    """AMB-01.2: Context watchdog emits schedule alerts within 15-minute window."""
    # Event far in future (60 mins) -> no premature alert
    nudge_far = watchdog.evaluate_calendar_event("Sprint Retro", 60)
    assert nudge_far is None

    # Event in 10 mins -> timely alert
    nudge_near = watchdog.evaluate_calendar_event("Milestone 30 Sync", 10)
    assert nudge_near is not None
    assert nudge_near.category == "CALENDAR"
    assert "Milestone 30 Sync" in nudge_near.title or "Milestone 30 Sync" in nudge_near.message
    assert nudge_near.metadata["minutes_until"] == 10


def test_telegram_voice_note_processing(companion):
    """TEL-02.1: Telegram companion transcribes voice note and replies with speech."""
    raw_transcript = "Bro, what is the current milestone status?"
    res = companion.process_voice_note(raw_transcript, user_id="telegram_user_42")

    assert res.transcription == raw_transcript
    assert "Haan bro!" in res.reply_text
    assert res.audio_synthesized is True
    assert companion.total_voice_notes_processed == 1


def test_remote_desktop_file_search_and_privacy(companion):
    """TEL-02.2: Remote file search retrieves valid docs while strictly blocking .env and keys."""
    # Valid file search
    results = companion.search_desktop_files("ROADMAP", max_results=3)
    assert len(results) >= 1
    assert any("ROADMAP" in f["file_name"] for f in results)

    # Privacy filtering check: .env and credentials must NEVER be returned
    sensitive_results = companion.search_desktop_files(".env", max_results=5)
    assert len(sensitive_results) == 0

    key_results = companion.search_desktop_files("id_rsa", max_results=5)
    assert len(key_results) == 0


def test_rule_8_anti_checkout_rejection(watchdog, companion):
    """Rule 8: Payment and checkout directives are unconditionally blocked."""
    with pytest.raises(WatchdogRule8ViolationError) as exc_info1:
        watchdog.evaluate_calendar_event("Checkout Amazon cart and pay invoice", 5)
    assert "Rule 8 Violation" in str(exc_info1.value)

    with pytest.raises(CompanionRule8ViolationError) as exc_info2:
        companion.process_voice_note("Phenom, authorize payment for server hosting")
    assert "Rule 8 Violation" in str(exc_info2.value)


def test_rule_11_credential_protection(watchdog, companion):
    """Rule 11: Passwords, tokens, and secret keys are scrubbed to [REDACTED]."""
    dirty_text = "Nudge for user token eyJhbGciOiJIUzI1Ni... and password=SuperSecretPassword789!"
    clean_text, count = watchdog.scrub_credentials(dirty_text)
    assert count >= 1
    assert "SuperSecretPassword789!" not in clean_text
    assert "[REDACTED]" in clean_text

    clean_comp, count_comp = companion.scrub_credentials("token: abcd1234efgh5678")
    assert count_comp >= 1
    assert "[REDACTED]" in clean_comp


def test_guardian_kill_switch_sla(watchdog, companion):
    """Rule 3: Universal Guardian kill switch halts operations in < 25.0ms SLA."""
    guardian.trigger("EMERGENCY TEST TRIGGER")
    assert guardian.is_halted

    t0 = time.perf_counter()
    with pytest.raises(RuntimeError) as exc_info1:
        watchdog.evaluate_app_switch("VS Code", "Code.exe")
    elapsed1_ms = (time.perf_counter() - t0) * 1000.0

    assert "Execution halted by Guardian kill switch" in str(exc_info1.value)
    assert elapsed1_ms < 25.0, f"Watchdog SLA violated: took {elapsed1_ms:.2f}ms >= 25.0ms"

    t1 = time.perf_counter()
    with pytest.raises(RuntimeError) as exc_info2:
        companion.process_voice_note("Hello Phenom")
    elapsed2_ms = (time.perf_counter() - t1) * 1000.0

    assert "Execution halted by Guardian kill switch" in str(exc_info2.value)
    assert elapsed2_ms < 25.0, f"Companion SLA violated: took {elapsed2_ms:.2f}ms >= 25.0ms"


def test_tool_registry_and_tiers():
    """Verify tool registration, risk tiers (Tier 0 & Tier 1), and preview functions."""
    # 1. trigger_ambient_context_nudge (Tier 1)
    nudge_tool = registry.get("trigger_ambient_context_nudge")
    assert nudge_tool is not None
    assert nudge_tool.tier == 1
    assert "trigger" in nudge_tool.preview_fn({"category": "FOCUS", "message": "Stay focused"}).lower()

    # 2. query_ambient_companion_status (Tier 0)
    status_tool = registry.get("query_ambient_companion_status")
    assert status_tool is not None
    assert status_tool.tier == 0
    st_out = status_tool.handler_fn()
    assert "watchdog" in st_out
    assert "companion" in st_out

    # 3. process_remote_companion_request (Tier 1)
    remote_tool = registry.get("process_remote_companion_request")
    assert remote_tool is not None
    assert remote_tool.tier == 1
    assert "process" in remote_tool.preview_fn({"audio_transcript": "Status check"}).lower()

    # 4. search_remote_desktop_file (Tier 0)
    search_tool = registry.get("search_remote_desktop_file")
    assert search_tool is not None
    assert search_tool.tier == 0
    search_out = search_tool.handler_fn(query="ROADMAP", max_results=2)
    assert "files" in search_out
    assert search_out["matched_count"] >= 1
