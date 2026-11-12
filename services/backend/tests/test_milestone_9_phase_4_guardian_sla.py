"""
Unit & SLA Benchmark Tests for Phenom Milestone 9.0 Phase 4 (SAF-01, SAF-02).
Verifies:
1. Strict ToolRegistry registration, risk tiers (Tier 0 / Tier 1), Pydantic schemas, and preview generation (SAF-01).
2. Sub-25ms synchronous Guardian kill switch SLA benchmark (< 1ms typical).
3. Synchronous halt cascade halting UnattendedMissionRunner immediately upon Guardian trigger (SAF-02).
4. PermissionError rejection of all mission operations while halted.
5. Clean resumption when Guardian resets to idle state via guardian.resume().
"""

import os
import subprocess
import sys
import time
import pytest

from services.backend.main import on_guardian_state_change
from services.backend.missions.unattended_runner import (
    UnattendedMissionRunner,
    unattended_mission_runner,
)
from services.backend.safety.guardian import guardian
from services.backend.safety.registry import registry
import services.backend.tools.mission_tools as mission_tools
from services.backend.schemas.missions import (
    MissionAbortArgs,
    MissionDebriefArgs,
    MissionStartArgs,
    MissionStatusArgs,
)


@pytest.fixture(autouse=True)
def reset_milestone_9_phase_4_components():
    """Ensure clean state before and after each test."""
    guardian.resume()
    unattended_mission_runner.reset()
    yield
    guardian.resume()
    unattended_mission_runner.reset()


def test_tool_registry_registration_and_tiers():
    """Verifies all Phase 4 mission tools are registered in ToolRegistry with correct tiers and previews (SAF-01)."""
    expected_tools = {
        "mission_start_unattended": (1, MissionStartArgs),
        "mission_get_status": (0, MissionStatusArgs),
        "mission_abort": (1, MissionAbortArgs),
        "mission_get_morning_debrief": (0, MissionDebriefArgs),
    }

    for name, (expected_tier, expected_schema) in expected_tools.items():
        tool = registry.get(name)
        assert tool is not None, f"Tool {name} must be registered in ToolRegistry"
        assert tool.tier == expected_tier, f"Tool {name} expected Tier {expected_tier}, got {tool.tier}"
        assert tool.args_schema == expected_schema, f"Tool {name} schema mismatch"

    # Verify Preview Functions
    start_tool = registry.get("mission_start_unattended")
    preview = start_tool.generate_preview({"title": "Fix Auth Bug"})
    assert "Fix Auth Bug" in preview
    assert "Reversible change" in preview

    status_tool = registry.get("mission_get_status")
    preview = status_tool.generate_preview({"mission_id": "msn_123"})
    assert "msn_123" in preview
    assert "Read-only" in preview

    abort_tool = registry.get("mission_abort")
    preview = abort_tool.generate_preview({"mission_id": "msn_123"})
    assert "msn_123" in preview
    assert "Reversible change" in preview

    debrief_tool = registry.get("mission_get_morning_debrief")
    preview = debrief_tool.generate_preview({"date_str": "2026-11-04"})
    assert "2026-11-04" in preview
    assert "Read-only" in preview


def test_synchronous_guardian_halt_sla_benchmark():
    """
    Benchmarks synchronous Guardian halt latency for unattended mission runner.
    Must strictly satisfy sub-25ms SLA (< 1ms typical).
    """
    # Pre-populate dummy active process to simulate load
    proc = subprocess.Popen(
        [sys.executable, "-c", "import time; time.sleep(30)"],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0,
    )
    unattended_mission_runner._active_processes["bench_msn"] = proc

    try:
        t0 = time.perf_counter()
        guardian.trigger("emergency_mission_killswitch_sla_test")
        elapsed_ms = (time.perf_counter() - t0) * 1000.0

        assert elapsed_ms < 25.0, f"Guardian halt exceeded 25ms SLA: {elapsed_ms:.2f}ms"
        assert unattended_mission_runner.is_halted is True
        assert len(unattended_mission_runner._active_processes) == 0

        # Verify process was killed
        time.sleep(0.05)
        assert proc.poll() is not None, "Active subprocess should be terminated after halt()"
    finally:
        try:
            proc.kill()
        except Exception:
            pass


def test_permission_error_enforcement_while_halted():
    """Verifies that all mission tool calls and operations raise PermissionError while halted (SAF-02)."""
    guardian.trigger("test_halt_lockout")
    assert unattended_mission_runner.is_halted is True

    # Tool: mission_start_unattended
    with pytest.raises(PermissionError) as exc_info:
        mission_tools.mission_start_unattended(
            title="Test Title",
            prompt="Test prompt",
        )
    assert "halted by guardian" in str(exc_info.value).lower()

    # Tool: mission_get_status
    with pytest.raises(PermissionError) as exc_info:
        mission_tools.mission_get_status("some_id")
    assert "halted by guardian" in str(exc_info.value).lower()

    # Tool: mission_get_morning_debrief
    with pytest.raises(PermissionError) as exc_info:
        mission_tools.mission_get_morning_debrief("2026-11-04")
    assert "halted by guardian" in str(exc_info.value).lower()

    # Runner sandbox creation
    with pytest.raises(PermissionError) as exc_info:
        unattended_mission_runner.create_sandbox("test_mid", os.getcwd())
    assert "halted by guardian" in str(exc_info.value).lower()


def test_clean_resumption_after_reset():
    """Verifies that runner transitions cleanly between halted and idle states via guardian.resume()."""
    guardian.trigger("test_transition")
    assert unattended_mission_runner.is_halted is True

    guardian.resume()
    assert unattended_mission_runner.is_halted is False

    # Should not raise PermissionError when idle
    assert len(unattended_mission_runner.list_missions()) >= 0
