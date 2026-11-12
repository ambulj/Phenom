"""
Unit Tests & Guardian SLA Benchmark for Autonomous Multi-App Context Fusion (CTX-01, SAF-01, SAF-02)
"""

import pytest
import time
import asyncio
from unittest.mock import patch

from services.backend.safety.registry import registry
from services.backend.safety.guardian import guardian
from services.backend.ambient.context_sanitizer import context_sanitizer
from services.backend.ambient.multi_app_tracker import multi_app_tracker, set_mock_tracker_mode
from services.backend.ambient.context_fusion import context_fusion
from services.backend.orchestrator.engine import Orchestrator
import services.backend.tools.context_fusion_tools


SAMPLE_MOCK_WINDOWS = [
    {
        "hwnd": 1001,
        "title": "engine.py - Phenom - Visual Studio Code",
        "process_name": "code.exe",
        "pid": 2400,
        "is_foreground": True
    },
    {
        "hwnd": 1002,
        "title": "FastAPI WebSockets Documentation - Google Chrome",
        "process_name": "chrome.exe",
        "pid": 3500,
        "is_foreground": False
    },
    {
        "hwnd": 1003,
        "title": "Windows PowerShell (Administrator)",
        "process_name": "powershell.exe",
        "pid": 4100,
        "is_foreground": False
    },
    {
        "hwnd": 1004,
        "title": "Sprint Notes - Obsidian v1.5",
        "process_name": "obsidian.exe",
        "pid": 5200,
        "is_foreground": False
    }
]


@pytest.fixture(autouse=True)
def setup_context_env():
    set_mock_tracker_mode(True, SAMPLE_MOCK_WINDOWS)
    context_fusion.clear_context()
    guardian._halted = False
    yield
    set_mock_tracker_mode(False)
    context_fusion.clear_context()
    guardian._halted = False


def test_context_fusion_registered_safety_tiers():
    """
    SAF-01: Verifies all 3 context fusion tools are registered with correct safety tiers and schemas.
    """
    expected_tools = {
        "get_active_workspace_context": {"tier": 0, "preview": True},
        "inspect_application_context": {"tier": 0, "preview": True},
        "clear_workspace_context": {"tier": 1, "preview": True},
    }

    for name, spec in expected_tools.items():
        tool = registry.get(name)
        assert tool is not None, f"Tool '{name}' missing from ToolRegistry"
        assert tool.tier == spec["tier"], f"Tool '{name}' tier mismatch: expected {spec['tier']}, got {tool.tier}"
        assert tool.args_schema is not None, f"Tool '{name}' missing args_schema"
        assert tool.preview_fn is not None, f"Tool '{name}' missing preview_fn"

        preview = tool.preview_fn({"category": "ide"})
        assert isinstance(preview, str) and len(preview) > 0


def test_rule_11_credential_sanitizer():
    """
    CTX-01.3 & Rule 11: Invariant test verifying 100% redaction of API keys, tokens, and passwords.
    """
    ghp_dummy = "ghp_" + "1234567890abcdefghijklmnopqrstuvwxyzAB"
    sk_dummy = "sk-" + "abcdefghijklmnopqrstuvwxyz1234567890"
    nvapi_dummy = "nvapi-" + "abcdefghijklmnopqrstuvwxyz123456"

    sensitive_samples = [
        (f"GitHub token: {ghp_dummy}", "ghp_"),
        (f"OpenAI key: {sk_dummy}", "sk-"),
        (f"NVIDIA token: {nvapi_dummy}", "nvapi-"),
        ("Auth header: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.e30.t-ID", "Bearer "),
        ("Database URI: postgresql://admin:SuperSecretPassword123@localhost:5432/db", "SuperSecretPassword123"),
        ("Query string: https://api.service.com/data?token=TopSecretToken987&user=dev", "TopSecretToken987"),
    ]

    for raw, secret_cue in sensitive_samples:
        clean, count = context_sanitizer.sanitize(raw)
        assert count >= 1
        assert "[REDACTED_CREDENTIAL]" in clean
        assert secret_cue not in clean, f"Secret cue '{secret_cue}' leaked in sanitized text: {clean}"


def test_multi_app_tracking_and_categorization():
    """
    CTX-01.1: Verifies desktop window enumeration, document inference, and domain grouping.
    """
    windows = multi_app_tracker.enumerate_active_windows()
    assert len(windows) == 4

    categories = {w.process_name: w.category for w in windows}
    assert categories["code.exe"] == "ide"
    assert categories["chrome.exe"] == "browser"
    assert categories["powershell.exe"] == "terminal"
    assert categories["obsidian.exe"] == "notes"

    fg = multi_app_tracker.get_foreground_window()
    assert fg is not None
    assert fg.process_name == "code.exe"
    assert fg.active_document == "engine.py"
    assert fg.is_foreground is True


def test_context_query_enrichment():
    """
    CTX-01.4: Verifies contextual prompt enrichment for ambiguous queries.
    """
    context_fusion.update_context()

    # Ambiguous query should receive active workspace prefix
    ambiguous_query = "Why is this bug happening in this file?"
    enriched, meta = context_fusion.enrich_query(ambiguous_query)

    assert meta["enriched"] is True
    assert meta["foreground_app"] == "code.exe"
    assert meta["active_document"] == "engine.py"
    assert "[Active Workspace Context: IDE - code.exe (engine.py)" in enriched
    assert ambiguous_query in enriched

    # General non-ambiguous query should remain unaltered
    clean_query = "What is the boiling point of liquid nitrogen?"
    not_enriched, clean_meta = context_fusion.enrich_query(clean_query)

    assert clean_meta["enriched"] is False
    assert not_enriched == clean_query


def test_direct_voice_intents_context_fusion():
    """
    Verifies orchestrator direct voice intent matching for context tools.
    """
    orch = Orchestrator()

    intent_map = {
        "workspace context": ("get_active_workspace_context", {}),
        "active context": ("get_active_workspace_context", {}),
        "what am i working on": ("get_active_workspace_context", {}),
        "clear context": ("clear_workspace_context", {}),
        "flush context": ("clear_workspace_context", {}),
        "running apps": ("inspect_application_context", {}),
        "open applications": ("inspect_application_context", {}),
    }

    for phrase, (expected_tool, expected_args) in intent_map.items():
        matched = orch._detect_direct_intent(phrase)
        assert matched is not None, f"Phrase '{phrase}' failed to match direct intent"
        tool_name, args, msg = matched
        assert tool_name == expected_tool, f"Phrase '{phrase}' matched tool {tool_name}, expected {expected_tool}"
        assert args == expected_args, f"Phrase '{phrase}' args mismatch: {args} != {expected_args}"


def test_guardian_context_tracker_freeze_sla_benchmark():
    """
    CTX-01.2 & SAF-02: Universal synchronous Guardian context freeze & purge SLA benchmark.
    Tests 50 iterations asserting instantaneous ring buffer purge and tracking freeze.
    Hard SLA: < 25.0ms (target < 1.0ms typical).
    """
    durations_ms = []

    with patch("services.backend.ambient.context_fusion.broadcast_context_event"), \
         patch("services.backend.tools.media_tools._send_virtual_key"), \
         patch("services.backend.tools.media_tools.broadcast_media_event"), \
         patch("services.backend.safety.action_log.action_log.log_action"):
        for i in range(50):
            context_fusion.update_context()
            assert context_fusion.is_frozen is False

            t0 = time.perf_counter()
            guardian.trigger(f"context_benchmark_halt_{i}")
            elapsed_ms = (time.perf_counter() - t0) * 1000.0
            durations_ms.append(elapsed_ms)

            assert guardian.is_halted is True
            assert context_fusion.is_frozen is True
            assert len(context_fusion._ring_buffer) == 0

            guardian.resume()
            assert context_fusion.is_frozen is False

    avg_ms = sum(durations_ms) / len(durations_ms)
    max_ms = max(durations_ms)
    print(f"\n[Guardian Context Freeze SLA Benchmark] 50 runs -> Avg: {avg_ms:.4f}ms, Max: {max_ms:.4f}ms (< 25.0ms SLA)")

    assert avg_ms < 25.0, f"Average freeze latency {avg_ms:.4f}ms exceeded 25.0ms SLA"
    assert max_ms < 25.0, f"Peak freeze latency {max_ms:.4f}ms exceeded 25.0ms SLA"
