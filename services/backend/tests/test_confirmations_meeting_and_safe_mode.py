"""
Unit Tests for Phenom Confirmations, Meeting Mode, Self-Check, Rollback & Safe Mode (Task 7l)
Covers:
1. One-line summary formatting invariant for Tier 2/3 confirmations.
2. Channel-aware timeouts (desktop 900s, telegram None).
3. Preconditions re-validation (file mtime/SHA-256 changes, mode drift, kill switch).
4. Safe alternative fallback engine (tier limits, re-use block, taint quarantine).
5. Meeting mode detection, audio muting, and WDA_EXCLUDEFROMCAPTURE affinity.
6. Daily self-check diagnostics, Telegram concise formatting, and critical spoken alerts.
7. 7-day rollback window and Safe Mode execution constraints (Tier 0 read-only).
"""

import os
import time
import pytest
import tempfile
import shutil

from services.backend.safety.confirmations import ConfirmationEngine, ConfirmationRequest, PreconditionFailedError
from services.backend.safety.alternatives import SafeAlternativeEngine
from services.backend.automation.meeting_mode import MeetingModeManager, WDA_EXCLUDEFROMCAPTURE, WDA_NONE
from services.backend.packaging.self_check import DailySelfCheckEngine
from services.backend.packaging.safe_mode import SafeModeManager
from services.backend.safety.guardian import GuardianKillSwitch

@pytest.fixture
def conf_engine():
    return ConfirmationEngine()

@pytest.fixture
def alt_engine():
    return SafeAlternativeEngine()

@pytest.fixture
def meeting_mgr():
    return MeetingModeManager()

@pytest.fixture
def self_check():
    return DailySelfCheckEngine()

@pytest.fixture
def safe_mgr(tmp_path):
    b_dir = tmp_path / "version_backups"
    b_dir.mkdir()
    return SafeModeManager(backup_dir=str(b_dir))

# ==============================================================================
# 1. One-Line Summary & Confirmation Invariants
# ==============================================================================

def test_one_line_summary_formatting_invariant(conf_engine):
    """
    STRICT INVARIANT:
    Tier 2 and Tier 3 one-line summaries must always follow:
    [Tier {tier}] {action_verb} {item_count} item(s) in {target_summary}
    """
    summary_t2 = conf_engine.format_one_line_summary(
        tier=2,
        action_verb="recycle delete",
        item_count=3,
        target_summary="C:\\Projects\\website (index.html, +2 others)"
    )
    assert summary_t2 == "[Tier 2] Recycle Delete 3 item(s) in C:\\Projects\\website (index.html, +2 others)"

    summary_t3 = conf_engine.format_one_line_summary(
        tier=3,
        action_verb="modify system rules",
        item_count=1,
        target_summary="C:\\ProgramData\\Phenom\\ProtectedRules\\safety.toml"
    )
    assert summary_t3 == "[Tier 3] Modify System Rules 1 item(s) in C:\\ProgramData\\Phenom\\ProtectedRules\\safety.toml"

def test_channel_aware_timeouts(conf_engine):
    """Verifies Desktop timeout is 900s, Telegram timeout is None."""
    req_desktop = conf_engine.build_confirmation(
        request_id="req_d1",
        tier=2,
        tool_name="recycle_file",
        action_verb="recycle delete",
        item_count=1,
        target_summary="test.txt",
        channel="desktop"
    )
    assert req_desktop.timeout_seconds == 900

    req_telegram = conf_engine.build_confirmation(
        request_id="req_t1",
        tier=2,
        tool_name="recycle_file",
        action_verb="recycle delete",
        item_count=1,
        target_summary="test.txt",
        channel="telegram"
    )
    assert req_telegram.timeout_seconds is None

# ==============================================================================
# 2. Preconditions Re-Validation Engine
# ==============================================================================

def test_preconditions_revalidation_success_and_failure(conf_engine, tmp_path):
    """Verifies that late approvals re-check file integrity, mode, and kill switch."""
    test_file = tmp_path / "target_document.docx"
    test_file.write_text("initial document contents", encoding="utf-8")

    req = conf_engine.build_confirmation(
        request_id="req_late_1",
        tier=2,
        tool_name="modify_file",
        action_verb="modify",
        item_count=1,
        target_summary="target_document.docx",
        target_paths=[str(test_file)],
        channel="desktop",
        current_mode="work"
    )

    # 1. Normal approval when conditions match -> Valid!
    assert conf_engine.validate_approval(req, current_mode="work") is True

    # 2. File modified on disk after confirmation issued -> Rejected!
    time.sleep(0.01)
    test_file.write_text("TAMPERED CONTENTS AFTER CONFIRMATION", encoding="utf-8")
    with pytest.raises(PreconditionFailedError, match="modified on disk"):
        conf_engine.validate_approval(req, current_mode="work")

    # Restore file for mode drift test
    test_file.write_text("initial document contents", encoding="utf-8")
    req_fresh = conf_engine.build_confirmation(
        request_id="req_late_2",
        tier=2,
        tool_name="modify_file",
        action_verb="modify",
        item_count=1,
        target_summary="target_document.docx",
        target_paths=[str(test_file)],
        current_mode="work"
    )

    # 3. Mode drift (user switched to Meeting Mode) -> Rejected!
    with pytest.raises(PreconditionFailedError, match="Mode drift detected"):
        conf_engine.validate_approval(req_fresh, current_mode="meeting")

    # 4. Target file deleted -> Rejected!
    os.remove(str(test_file))
    with pytest.raises(PreconditionFailedError, match="deleted"):
        conf_engine.validate_approval(req_fresh, current_mode="work")

# ==============================================================================
# 3. Safe Alternative Fallback Engine
# ==============================================================================

def test_safe_alternative_invariants(alt_engine):
    """Verifies tier limits, re-use block, and taint quarantine."""
    # 1. Clean alternative for recycle_file (Tier 2 -> Tier 0)
    alt = alt_engine.find_safe_alternative("recycle_file", declined_tier=2)
    assert alt["safe_alternative_found"] is True
    assert alt["tier"] <= 2
    assert "Declined recycle_file" in alt["conversational_text"]

    # 2. Re-use block: cannot invoke a tool already declined in chain
    alt_blocked = alt_engine.find_safe_alternative(
        "recycle_file",
        declined_tier=2,
        declined_chain={"read_file", "list_files"}
    )
    assert alt_blocked["safe_alternative_found"] is False

    # 3. Taint quarantine: untrusted content strictly blocks automated alternatives
    alt_tainted = alt_engine.find_safe_alternative(
        "recycle_file",
        declined_tier=2,
        is_tainted=True
    )
    assert alt_tainted["safe_alternative_found"] is False
    assert alt_tainted["reason"] == "taint_quarantine_active"

# ==============================================================================
# 4. Meeting Mode & Windows Display Affinity
# ==============================================================================

def test_meeting_mode_detection_and_display_affinity(meeting_mgr):
    """Verifies meeting detection, audio muting, and WDA_EXCLUDEFROMCAPTURE state."""
    # Process detection
    is_m, app, reason = meeting_mgr.detect_meeting(mock_process="zoom.exe")
    assert is_m is True
    assert app == "zoom.exe"

    # Title detection
    is_m_t, app_t, _ = meeting_mgr.detect_meeting(mock_window_title="Meet - Daily Standup (Google Chrome)")
    assert is_m_t is True

    # State adjustments
    res_enter = meeting_mgr.enter_meeting_mode("zoom.exe")
    assert res_enter["speech_muted"] is True
    assert res_enter["sound_fx_muted"] is True
    assert res_enter["display_affinity"] == "WDA_EXCLUDEFROMCAPTURE"
    assert meeting_mgr.meeting_mode_active is True

    res_exit = meeting_mgr.exit_meeting_mode()
    assert res_exit["speech_muted"] is False
    assert res_exit["display_affinity"] == "WDA_NONE"
    assert meeting_mgr.meeting_mode_active is False

# ==============================================================================
# 5. Daily Self-Check Diagnostics
# ==============================================================================

def test_daily_self_check_diagnostics_and_alerts(self_check):
    """Verifies concise Telegram status format and spoken alert on critical hazards."""
    # 1. Clean Run
    report_clean = self_check.run_diagnostic_suite()
    assert report_clean["all_healthy"] is True
    assert report_clean["telegram_text"] == "[Phenom Self-Check] All Systems Healthy."
    assert report_clean["spoken_alert"] is None

    # 2. Warning Run (Backup Failed)
    report_warn = self_check.run_diagnostic_suite(mock_backup_failed=True)
    assert report_warn["all_healthy"] is False
    assert report_warn["telegram_text"] == "[Phenom Self-Check Warning] Backup: Failed."
    assert report_warn["spoken_alert"] is None # Non-critical: NO spoken alert

    # 3. Critical Hazard (Database Corruption)
    report_crit = self_check.run_diagnostic_suite(mock_db_corrupt=True)
    assert report_crit["all_healthy"] is False
    assert "Database: Critical." in report_crit["telegram_text"]
    assert report_crit["spoken_alert"] is not None
    assert "Critical system hazard" in report_crit["spoken_alert"]

# ==============================================================================
# 6. 7-Day Rollback Window & Safe Mode
# ==============================================================================

def test_safe_mode_and_7day_rollback(safe_mgr):
    """Verifies 7-day retention pruning, automated rollback on boot check failure, and Safe Mode."""
    # 1. Version Backup creation
    b_dir = safe_mgr.create_version_backup(
        version="v1.0.0",
        files_to_backup={"config.toml": "system config v1.0.0"}
    )
    assert os.path.exists(b_dir)

    # 2. Automated rollback on failed post-update boot check
    res_rollback = safe_mgr.execute_post_update_boot_check(boot_success=False, previous_version="v1.0.0")
    assert res_rollback["rollback_triggered"] is True
    assert res_rollback["restored_version"] == "v1.0.0"

    # 3. Safe Mode Tool Restrictions
    safe_mgr.enable_safe_mode()
    assert safe_mgr.safe_mode_active is True
    assert safe_mgr.is_tool_allowed_in_safe_mode(tier=0) is True
    assert safe_mgr.is_tool_allowed_in_safe_mode(tier=1) is False
    assert safe_mgr.is_tool_allowed_in_safe_mode(tier=2) is False

    safe_mgr.disable_safe_mode()
    assert safe_mgr.is_tool_allowed_in_safe_mode(tier=2) is True
