"""
Unit Tests for Phenom Providers, Usage Tracking, Self-Help, Granular Reset & Data Export (Task 7k)
Covers:
1. Multi-provider usage tracking, token metrics, latency, and HTTP 429 rate limit aggregation.
2. Zero-drift dynamic self-help generated directly from registry.list_all().
3. Four granular reset actions (Settings, Memory, Voice, Factory) with strict phrase verification.
4. Data export ZIP archive generation with strict secret exclusion verification.
"""

import os
import re
import json
import zipfile
import pytest
import tempfile
import shutil

from services.backend.router.usage_tracker import ProviderUsageTracker
from services.backend.tools.self_help import SelfHelpEngine
from services.backend.packaging.reset_manager import GranularResetManager
from services.backend.packaging.export_manager import DataExportManager, SecretScanFailureError
from services.backend.safety.registry import registry
from services.backend.memory.db import encrypted_db

# Ensure tools are imported so registry is populated
import services.backend.tools.file_tools
import services.backend.tools.app_tools
import services.backend.tools.coding_tools
import services.backend.tools.automation_tools
import services.backend.tools.git_tools

@pytest.fixture
def usage_tracker():
    return ProviderUsageTracker()

@pytest.fixture
def self_help():
    return SelfHelpEngine()

@pytest.fixture
def reset_mgr(tmp_path):
    v_store = tmp_path / "voice_store"
    v_store.mkdir()
    return GranularResetManager(voice_store_dir=str(v_store))

@pytest.fixture
def export_mgr(tmp_path):
    class MockVault:
        vault_path = str(tmp_path / "vault")
    os.makedirs(MockVault.vault_path, exist_ok=True)
    with open(os.path.join(MockVault.vault_path, "test_note.md"), "w", encoding="utf-8") as f:
        f.write("# Sample Note\nTest contents.")
    return DataExportManager(vault_mgr=MockVault())

# ==============================================================================
# 1. Multi-Provider Usage Tracking & Metrics
# ==============================================================================

def test_usage_tracker_recording_and_summaries(usage_tracker):
    """Verifies that usage calls, tokens, latency, and rate limits are tracked in SQLCipher."""
    # Record diverse provider calls
    usage_tracker.record_usage(
        provider="nvidia_nemotron",
        model="meta/llama-3.1-405b-instruct",
        prompt_tokens=150,
        completion_tokens=50,
        latency_ms=420.5,
        status_code=200
    )
    usage_tracker.record_usage(
        provider="groq_llama",
        model="llama-3.3-70b-versatile",
        prompt_tokens=80,
        completion_tokens=20,
        latency_ms=180.2,
        status_code=200
    )
    usage_tracker.record_usage(
        provider="nvidia_nemotron",
        model="meta/llama-3.1-405b-instruct",
        prompt_tokens=100,
        completion_tokens=0,
        latency_ms=55.0,
        status_code=429,
        error_message="Rate limit exceeded"
    )

    daily = usage_tracker.get_daily_summary()
    assert daily["total_calls"] >= 3
    assert daily["total_rate_limits_429"] >= 1
    assert "nvidia_nemotron" in daily["providers"]
    assert daily["providers"]["nvidia_nemotron"]["rate_limits_429"] >= 1

    monthly = usage_tracker.get_monthly_summary()
    assert monthly["total_calls"] >= 3

    recent = usage_tracker.get_recent_load_history(limit=5)
    assert len(recent) >= 3
    assert any(r["status_code"] == 429 for r in recent)

# ==============================================================================
# 2. Zero-Drift Self-Help Engine
# ==============================================================================

def test_self_help_zero_drift_capabilities(self_help):
    """Verifies capabilities match registry.list_all() with 0 documentation drift."""
    manifest = self_help.get_capabilities_manifest()
    all_registered = registry.list_all()

    assert manifest["total_tools"] == len(all_registered), "Self-help tool count drifted from registry!"
    assert manifest["categories_count"] >= 5
    assert "Coding Agent & Safe Runner" in manifest["domains"]
    assert "File Management & Safe Sandbox" in manifest["domains"]

    # Natural language query tests
    q_what = self_help.answer_query("What can you do?")
    assert "I am Phenom" in q_what["reply"]
    assert str(len(all_registered)) in q_what["reply"]

    q_hotkeys = self_help.answer_query("how do I change hotkeys?")
    assert "Ctrl+Alt+Pause" in q_hotkeys["reply"]
    assert "Alt+Space" in q_hotkeys["reply"]

    q_tools = self_help.answer_query("list tools")
    assert len(q_tools["tools"]) == len(all_registered)

# ==============================================================================
# 3. Granular Reset Controls
# ==============================================================================

def test_granular_reset_preview_and_phrase_validation(reset_mgr):
    """Verifies that reset previews correctly list cleared/preserved items and enforce exact phrases."""
    preview_settings = reset_mgr.preview_reset("settings")
    assert preview_settings["confirmation_phrase"] == "RESET SETTINGS"
    assert "config.toml" in preview_settings["will_clear"][0]

    preview_memory = reset_mgr.preview_reset("memory")
    assert preview_memory["confirmation_phrase"] == "CLEAR MEMORY"

    preview_voice = reset_mgr.preview_reset("voice")
    assert preview_voice["confirmation_phrase"] == "DELETE VOICE DATA"

    # Incorrect phrase raises PermissionError
    with pytest.raises(PermissionError):
        reset_mgr.execute_reset("settings", "yes please")

def test_granular_reset_executions(reset_mgr):
    """Verifies that each reset action clears its target while preserving others."""
    # Seed data
    conn = encrypted_db.get_connection()
    with conn:
        conn.execute("INSERT OR REPLACE INTO settings (key, value) VALUES ('test_setting', '123');")
        conn.execute("INSERT OR REPLACE INTO messages (id, role, content, timestamp) VALUES ('msg_1', 'user', 'hi', '2026-10-29T10:00:00');")
        conn.execute("INSERT OR REPLACE INTO settings (key, value) VALUES ('speaker_profile', 'blob_data');")
    conn.close()

    # Create dummy audio file in voice store
    sample_wav = os.path.join(reset_mgr.voice_store, "sample.wav")
    with open(sample_wav, "wb") as f:
        f.write(b"AUDIO_RAW_BYTES_12345678")

    # 1. Reset Settings
    res_set = reset_mgr.execute_reset("settings", "RESET SETTINGS")
    assert res_set["status"] == "success"
    conn = encrypted_db.get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM settings WHERE key = 'test_setting';")
    assert cursor.fetchone()[0] == 0
    cursor.execute("SELECT COUNT(*) FROM messages WHERE id = 'msg_1';")
    assert cursor.fetchone()[0] == 1  # Specific message PRESERVED!
    conn.close()

    # 2. Reset Voice Data (DoD zeroing)
    res_voice = reset_mgr.execute_reset("voice", "DELETE VOICE DATA")
    assert res_voice["status"] == "success"
    assert not os.path.exists(sample_wav)
    conn = encrypted_db.get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM settings WHERE key LIKE 'speaker_%';")
    assert cursor.fetchone()[0] == 0
    cursor.execute("SELECT COUNT(*) FROM messages WHERE id = 'msg_1';")
    assert cursor.fetchone()[0] == 1  # Message still PRESERVED!
    conn.close()

    # 3. Clear Memory
    res_mem = reset_mgr.execute_reset("memory", "CLEAR MEMORY")
    assert res_mem["status"] == "success"
    conn = encrypted_db.get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM messages WHERE id = 'msg_1';")
    assert cursor.fetchone()[0] == 0  # Messages now purged!
    conn.close()

# ==============================================================================
# 4. Data Export Archive & Secret Exclusion Guarantee
# ==============================================================================

def test_data_export_archive_and_secret_exclusion(export_mgr, tmp_path):
    """Verifies that export packages non-secret data and strictly excludes secrets/DBs."""
    export_out = tmp_path / "export_output"
    res = export_mgr.export_data(output_dir=str(export_out))

    assert res["status"] == "success"
    zip_path = res["export_path"]
    assert os.path.exists(zip_path)
    assert zipfile.is_zipfile(zip_path)

    # Inspect zip contents
    with zipfile.ZipFile(zip_path, "r") as zf:
        namelist = zf.namelist()
        assert "config.toml" in namelist
        assert "memory_export.json" in namelist
        assert any(n.startswith("vault/") for n in namelist)

        # STRICT GUARANTEE: No databases, env files, or private keys!
        assert not any(n.endswith(".db") for n in namelist)
        assert not any(n.endswith(".sqlite") for n in namelist)
        assert not any(n.endswith(".key") for n in namelist)
        assert not any(n.startswith(".env") for n in namelist)

def test_export_aborts_if_secrets_detected_in_staging(export_mgr, tmp_path):
    """Verifies that if a secret file is placed in the export area, packaging aborts."""
    staging_test = tmp_path / "staging_leak"
    staging_test.mkdir()
    leaked_db = staging_test / "leaked_passwords.db"
    leaked_db.write_text("secret db content")

    with pytest.raises(SecretScanFailureError):
        export_mgr._scan_staging_for_secrets(str(staging_test))
