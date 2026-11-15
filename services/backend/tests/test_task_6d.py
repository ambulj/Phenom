"""
Unit and Integration Tests for Task 6D: Security / Kali Mode with Specialist Model
Verifies:
1. Model acquisition fails loudly on wrong model name instead of substituting one.
2. Setup successfully resolves specialist model and writes manifest with digest.
3. General chat stays on Llama 3.1 8B while security mode uses specialist model.
4. Destructive step (kali_exploit_payload) is blocked pending confirmation and logs target & action.
5. Non-destructive recon step (kali_recon_scan) runs automatically at Tier 0.
6. Action log entries in security mode are tagged with specialist model name.
"""

import sys
from unittest.mock import MagicMock

# Mock keyboard and mouse to prevent low-level win32 hook access violations
if "keyboard" not in sys.modules:
    sys.modules["keyboard"] = MagicMock()
if "mouse" not in sys.modules:
    sys.modules["mouse"] = MagicMock()

import os
import pytest
import asyncio
from unittest.mock import patch, AsyncMock

from services.backend.scripts.setup_specialist_model import (
    acquire_and_verify_specialist_model,
    DEFAULT_SPECIALIST_MODEL
)
from services.backend.modes.mode_manager import mode_manager, AssistantMode, SPECIALIST_MODEL_NAME
from services.backend.router.router import ModelRouter
from services.backend.safety.engine import safety_engine
from services.backend.safety.registry import registry
from services.backend.safety.action_log import action_log
import services.backend.tools.kali_security_tools  # Ensure tools are registered

def test_setup_fails_loudly_on_wrong_model_name():
    """Acceptance: setup run that fails loudly on a wrong model name instead of substituting one."""
    fake_bad_model = "hf.co/nonexistent-org/fake-exploit-model-q4:latest"
    with pytest.raises(RuntimeError) as exc_info:
        acquire_and_verify_specialist_model(fake_bad_model, pull_if_missing=False)

    err_text = str(exc_info.value)
    assert fake_bad_model in err_text
    assert "Phenom will NOT silently substitute a different model" in err_text


def test_setup_resolves_specialist_model_and_records_manifest():
    """Verifies that resolving the genuine specialist model records its digest and size."""
    manifest = acquire_and_verify_specialist_model(DEFAULT_SPECIALIST_MODEL, pull_if_missing=False)
    assert manifest["status"] == "VERIFIED_SPECIALIST_READY"
    assert manifest["model_name"] == DEFAULT_SPECIALIST_MODEL
    assert manifest["digest"] != ""
    assert manifest["size_bytes"] > 0
    assert os.path.exists("reports/specialist_model_manifest.json")


@pytest.mark.asyncio
async def test_general_chat_vs_security_mode_routing():
    """Acceptance: demonstration that general chat stays on Llama 3.1 8B while security mode uses specialist."""
    router = ModelRouter()

    # 1. Normal mode (Work / Default)
    mode_manager.set_mode("work")
    assert mode_manager.is_security_mode_active is False

    model_normal, backend_normal, meta_normal = await router.route_request("Hello, what is the agenda today?")
    assert model_normal == "phenom-jarvis:latest"
    assert backend_normal == "local"

    # 2. Enter Security Mode
    mode_manager.set_mode("security")
    assert mode_manager.is_security_mode_active is True
    assert mode_manager.active_specialist_model == SPECIALIST_MODEL_NAME

    model_sec, backend_sec, meta_sec = await router.route_request("Analyze network packet capture for beaconing")
    assert model_sec == SPECIALIST_MODEL_NAME
    assert backend_sec == "local"
    assert meta_sec.get("task_type") == "security"

    # 3. Exit Security Mode -> Immediately reverts
    mode_manager.set_mode("work")
    assert mode_manager.is_security_mode_active is False

    model_reverted, backend_reverted, _ = await router.route_request("Tell me a quick joke Bro")
    assert model_reverted == "phenom-jarvis:latest"


@pytest.mark.asyncio
async def test_destructive_step_blocked_pending_confirmation_and_logs_target():
    """Acceptance: destructive-step test that is blocked pending confirmation and logs the target."""
    target_ip = "192.168.1.185"
    action_type = "heap_overflow_poc"

    tool_def = registry.get("kali_exploit_payload")
    assert tool_def is not None
    assert tool_def.tier == 2

    # Without confirmation handler registered, Tier 2 must be blocked
    safety_engine.set_confirmation_handler(None)

    with pytest.raises(PermissionError) as exc_info:
        await safety_engine.execute_tool(
            "kali_exploit_payload",
            {"target": target_ip, "action": action_type, "payload_type": "poc"}
        )

    assert "requires confirmation (Tier 2)" in str(exc_info.value) or "confirmation handler is unavailable" in str(exc_info.value)

    # Verify action log contains target and action
    entries = action_log.list_entries(limit=10)
    matching_entry = None
    for e in entries:
        if e["tool"] == "kali_exploit_payload":
            matching_entry = e
            break

    assert matching_entry is not None
    assert matching_entry["tier"] == 2
    assert matching_entry["decision"] == "denied"
    assert target_ip in matching_entry["arguments_redacted"]
    assert action_type in matching_entry["arguments_redacted"]


@pytest.mark.asyncio
async def test_non_destructive_recon_scan_auto_executes_tier0():
    """Verifies that non-destructive reconnaissance runs automatically at Tier 0 without confirmation."""
    target_host = "scanme.nmap.org"
    tool_def = registry.get("kali_recon_scan")
    assert tool_def is not None
    assert tool_def.tier == 0

    result = await safety_engine.execute_tool(
        "kali_recon_scan",
        {"target": target_host, "ports": "80,443", "scan_type": "syn"}
    )

    assert result["status"] == "success"
    inner_res = result.get("result", result)
    assert inner_res["target"] == target_host
    assert len(inner_res["discovered_services"]) > 0


@pytest.mark.asyncio
async def test_action_log_tagged_with_specialist_model_in_security_mode():
    """Verifies that every action-log entry produced in security mode is tagged with the specialist model name."""
    mode_manager.set_mode("security")

    result = await safety_engine.execute_tool(
        "kali_recon_scan",
        {"target": "10.0.0.1", "ports": "22,80"}
    )

    entries = action_log.list_entries(limit=5)
    matching = next((e for e in entries if e["tool"] == "kali_recon_scan" and "10.0.0.1" in e["arguments_redacted"]), None)

    assert matching is not None
    assert matching["model"] == SPECIALIST_MODEL_NAME

    # Reset mode
    mode_manager.set_mode("work")
