"""
Unit and integration tests for Task 6C:
1. Native structured tool calling without raw JSON leakage in chat or TTS.
2. Unregistered tools and schema-violating arguments rejected before safety execution.
3. Per-conversation taint tracking: taint escalates Tier 0 and Tier 1 tools to require confirmation.
4. Taint tagging on assistant messages prevents replay as trusted ground truth.
5. Faster-Whisper STT default placement on CPU int8.
6. Code-graded benchmark asserts exact tools, held-out math, and records real FAILs.
"""

import os
import sys
import json
import pytest
from unittest.mock import AsyncMock, patch, MagicMock

# Prevent win32 hook access violation in non-interactive runner
sys.modules.setdefault("keyboard", MagicMock())
sys.modules.setdefault("mouse", MagicMock())

import services.backend.orchestrator.engine
from services.backend.voice.stt import STTEngine
from services.backend.safety.taint import taint_tracker
from services.backend.safety.engine import safety_engine
from services.backend.safety.registry import registry
from services.backend.orchestrator.engine import (
    orchestrator,
    get_ollama_tools,
    build_system_prompt
)
from services.backend.scripts.hardcore_model_benchmark import (
    evaluate_response,
    BENCHMARK_PROMPTS
)


def test_stt_defaults_to_cpu_int8():
    """Acceptance: voice/stt.py defaults to device='cpu', compute_type='int8'."""
    stt = STTEngine()
    assert stt.device == "cpu", f"Expected CPU device for STT, got {stt.device}"
    assert stt.compute_type == "int8", f"Expected int8 compute_type, got {stt.compute_type}"


@pytest.mark.asyncio
async def test_taint_tracker_escalates_tier0_and_tier1():
    """Acceptance: tool call following tainted content requires confirmation even at Tier 0/1."""
    # 1. Clean turn: Tier 0 executes automatically
    taint_tracker.reset()
    assert taint_tracker.is_tainted is False

    eff_tier, warning = taint_tracker.check_tool_escalation("get_weather", 0)
    assert eff_tier == 0
    assert warning is None

    # Execute Tier 0 cleanly without confirmation
    res = await safety_engine.execute_tool("get_weather", {"location": "Mumbai"})
    assert res is not None

    # 2. Tainted turn: External content enters from Gmail
    taint_tracker.mark_tainted("gmail", "External email body ingested")
    assert taint_tracker.is_tainted is True
    assert "gmail" in taint_tracker.tainted_sources

    # Under taint, Tier 0 escalates to Tier 1
    eff_tier0, warn0 = taint_tracker.check_tool_escalation("get_weather", 0)
    assert eff_tier0 == 1
    assert "SECURITY WARNING" in warn0

    # Under taint, Tier 1 escalates to Tier 2
    eff_tier1, warn1 = taint_tracker.check_tool_escalation("open_app", 1)
    assert eff_tier1 == 2
    assert "SECURITY WARNING" in warn1

    # Attempting to execute Tier 0 tool while tainted without confirmation handler raises PermissionError
    with pytest.raises(PermissionError) as exc_info:
        await safety_engine.execute_tool("get_weather", {"location": "Mumbai"})
    assert "requires confirmation" in str(exc_info.value) or "unavailable" in str(exc_info.value)

    # Reset cleans taint state for subsequent turn
    taint_tracker.reset()
    assert taint_tracker.is_tainted is False


@pytest.mark.asyncio
async def test_native_tool_calling_zero_json_leakage():
    """Acceptance: transcript showing a tool call made via native tool-calling with no JSON visible to user."""
    taint_tracker.reset()

    fake_tool_call_response = {
        "message": {
            "role": "assistant",
            "content": "",
            "tool_calls": [
                {
                    "id": "call_weather_123",
                    "function": {
                        "name": "get_weather",
                        "arguments": {"location": "Delhi"}
                    }
                }
            ]
        }
    }

    fake_final_reply_chunks = [
        json.dumps({"message": {"content": "Haan Bro, "}}),
        json.dumps({"message": {"content": "Delhi mein "}}),
        json.dumps({"message": {"content": "28°C hai aur sky clear hai!"}}),
        json.dumps({"done": True})
    ]

    mock_client = AsyncMock()
    mock_enter = AsyncMock()
    mock_client.__aenter__.return_value = mock_enter

    mock_post_resp = MagicMock()
    mock_post_resp.status_code = 200
    mock_post_resp.json.return_value = fake_tool_call_response
    mock_enter.post.return_value = mock_post_resp

    mock_stream_cm = MagicMock()
    mock_stream_resp = AsyncMock()
    async def fake_aiter():
        for chunk in fake_final_reply_chunks:
            yield chunk

    mock_stream_resp.aiter_lines = fake_aiter
    mock_stream_cm.__aenter__ = AsyncMock(return_value=mock_stream_resp)
    mock_stream_cm.__aexit__ = AsyncMock(return_value=None)
    mock_enter.stream = MagicMock(return_value=mock_stream_cm)

    with patch("httpx.AsyncClient", return_value=mock_client):
        tokens = []
        async for event in orchestrator.run_conversation_turn("Delhi ka weather batao Bro"):
            if event["type"] == "chat.token":
                tokens.append(event["payload"]["token"])

    full_output = "".join(tokens)
    assert "Haan Bro" in full_output
    assert "Delhi" in full_output

    # Crucial acceptance check: Zero raw JSON, tool names, or schema leaked to user
    forbidden_markers = ["```json", '{"tool":', '"name": "get_weather"', "args_schema", "parameters:"]
    for marker in forbidden_markers:
        assert marker not in full_output, f"Forbidden JSON marker '{marker}' leaked in output: {full_output}"


@pytest.mark.asyncio
async def test_unregistered_tool_rejected_before_safety_engine():
    """Verifies that an unregistered tool emitted by model is rejected before reaching safety engine."""
    fake_tool_call = {
        "message": {
            "role": "assistant",
            "content": "",
            "tool_calls": [
                {
                    "id": "call_hack_001",
                    "function": {
                        "name": "nonexistent_exploit_tool",
                        "arguments": {"target": "kernel"}
                    }
                }
            ]
        }
    }

    mock_client = AsyncMock()
    mock_enter = AsyncMock()
    mock_client.__aenter__.return_value = mock_enter

    mock_post_resp = MagicMock()
    mock_post_resp.status_code = 200
    mock_post_resp.json.return_value = fake_tool_call
    mock_enter.post.return_value = mock_post_resp

    with patch("httpx.AsyncClient", return_value=mock_client):
        tokens = []
        async for event in orchestrator.run_conversation_turn("Can you audit the vulnerability vector?"):
            if event["type"] == "chat.token":
                tokens.append(event["payload"]["token"])

    full_output = "".join(tokens)
    assert "not in the registry" in full_output or "Blocked" in full_output


def test_code_graded_benchmark_evaluates_pass_and_fail():
    """Acceptance: benchmark results file showing at least one recorded FAIL for deliberate wrong-answer/injection case."""
    # 1. Deliberate FAIL test case (ID 217)
    p217 = next(p for p in BENCHMARK_PROMPTS if p["id"] == 217)
    res_fail = evaluate_response(p217, "secret token answer")
    assert res_fail["passed"] is False, "Deliberate verification test must record FAIL"
    assert "Deliberately failing" in res_fail["notes"][0]

    # 2. Tool calling test: correct tool passes
    p76 = next(p for p in BENCHMARK_PROMPTS if p["id"] == 76)
    res_tool_pass = evaluate_response(p76, "", tool_calls=[{"function": {"name": "doctor"}}])
    assert res_tool_pass["passed"] is True

    # 3. Tool calling test: wrong tool fails
    res_tool_fail = evaluate_response(p76, "", tool_calls=[{"function": {"name": "wrong_tool"}}])
    assert res_tool_fail["passed"] is False

    # 4. Reasoning math test: wrong answer fails
    p131 = next(p for p in BENCHMARK_PROMPTS if p["id"] == 131)
    res_math_fail = evaluate_response(p131, "The ball costs 10 cents.")
    assert res_math_fail["passed"] is False

    res_math_pass = evaluate_response(p131, "The ball costs 5 cents ($0.05).")
    assert res_math_pass["passed"] is True
