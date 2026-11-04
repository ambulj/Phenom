"""
Unit Test Suite for 100% Offline Ollama Screen Vision Engine (VIS-02, SAF-01, SAF-02)
Verifies:
1. Local in-RAM screen inspection with zero cloud exfiltration (Rule 4).
2. Offline window cropping and target element query.
3. Offline health verification and local loopback isolation.
4. Direct voice intents for offline screen inspection.
5. Immediate Guardian kill switch halt (< 25ms SLA).
"""

import pytest
import time
from services.backend.tools.offline_vision_tools import (
    inspect_screen_offline,
    capture_window_offline,
    verify_offline_vision_status,
    set_mock_offline_vision
)
from services.backend.tools.window_tiler import set_mock_windows_mode
from services.backend.safety.guardian import guardian
from services.backend.safety.registry import registry
from services.backend.orchestrator.engine import Orchestrator


@pytest.fixture(autouse=True)
def setup_mock_vision_environment():
    """Sets up deterministic mock vision and window fixtures."""
    set_mock_offline_vision(True)
    mock_wins = [
        {"hwnd": 2001, "title": "Visual Studio Code - Phenom Core", "rect": {"left": 0, "top": 0, "width": 800, "height": 600}},
        {"hwnd": 2002, "title": "Brave Browser - GitHub Pull Requests", "rect": {"left": 800, "top": 0, "width": 800, "height": 600}},
    ]
    set_mock_windows_mode(True, mock_wins)
    guardian._halted = False
    yield
    set_mock_offline_vision(False)
    set_mock_windows_mode(False)
    guardian._halted = False


def test_offline_vision_tool_tiers():
    """Asserts all offline vision tools are classified as Tier 0 (read-only, logged)."""
    inspect_tool = registry.get("inspect_screen_offline")
    capture_tool = registry.get("capture_window_offline")
    verify_tool = registry.get("verify_offline_vision_status")

    assert inspect_tool is not None and inspect_tool.tier == 0
    assert capture_tool is not None and capture_tool.tier == 0
    assert verify_tool is not None and verify_tool.tier == 0


@pytest.mark.asyncio
async def test_inspect_screen_offline_execution():
    """Verifies screen is inspected in RAM with zero cloud exfiltration."""
    res = await inspect_screen_offline(prompt="Check for compiler errors")
    assert res["status"] == "success"
    assert res["cloud_exfiltration"] is False
    assert "moondream" in res["model"]
    assert res["latency_ms"] >= 0


@pytest.mark.asyncio
async def test_capture_window_offline_execution():
    """Verifies cropping and analyzing a specific window offline."""
    res = await capture_window_offline(window_title="Visual Studio Code", question="What code is visible?")
    assert res["status"] == "success"
    assert res["cloud_exfiltration"] is False
    assert "Visual Studio Code" in res["window"]


@pytest.mark.asyncio
async def test_verify_offline_vision_status():
    """Verifies loopback connectivity check and zero-cloud invariants."""
    res = await verify_offline_vision_status()
    assert res["status"] == "success"
    assert res["ollama_loopback_reachable"] is True
    assert res["cloud_exfiltration_allowed"] is False
    assert res["in_ram_only"] is True


def test_direct_voice_intents_offline_vision():
    """Verifies voice intents map deterministically to offline vision tools."""
    orchestrator = Orchestrator()

    intent_screen = orchestrator._detect_direct_intent("what's on my screen")
    assert intent_screen is not None
    assert intent_screen[0] == "inspect_screen_offline"

    intent_hindi = orchestrator._detect_direct_intent("screen pe kya hai")
    assert intent_hindi is not None
    assert intent_hindi[0] == "inspect_screen_offline"

    intent_status = orchestrator._detect_direct_intent("offline vision status")
    assert intent_status is not None
    assert intent_status[0] == "verify_offline_vision_status"


@pytest.mark.asyncio
async def test_offline_vision_guardian_killswitch_abort():
    """Verifies that Guardian halt prevents offline vision calls immediately (< 25ms SLA)."""
    guardian._halted = True
    t0 = time.perf_counter()
    res = await inspect_screen_offline()
    elapsed_ms = (time.perf_counter() - t0) * 1000.0

    assert res["status"] == "halted"
    assert res["reason"] == "GUARDIAN_KILLSWITCH"
    assert elapsed_ms < 25.0
