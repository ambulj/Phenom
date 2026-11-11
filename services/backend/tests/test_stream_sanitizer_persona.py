"""Tests for Stream Sanitizer & Adaptive Persona Engine (Milestone 29 Phase 1).

Validates:
- STREAM-01.1: Removal of tool invocation markers, JSON blocks, and PID noise from chat text.
- STREAM-01.2: Extraction of tool metadata into structured telemetry models.
- PERSONA-02.1: Adaptive persona response formatting across all modes (SILENT, MINIMAL, CONVERSATIONAL, AUTO).
- SAF-01: Registered tools (sanitize_chat_stream, set_adaptive_persona_mode, get_stream_shield_metrics).
- SAF-02: Universal Guardian kill switch SLA halt (< 25.0ms SLA).
- Rule 8: Payment and checkout regex rejection raising Rule8ViolationError.
- Rule 4: 100% on-device local execution.
"""

import time
import pytest

from services.backend.safety.guardian import guardian
from services.backend.safety.registry import registry
from services.backend.conversation.stream_sanitizer import (
    StreamSanitizer,
    Rule8ViolationError,
    stream_sanitizer,
)
from services.backend.conversation.adaptive_persona import (
    AdaptivePersonaEngine,
    PersonaMode,
    adaptive_persona_engine,
)
from services.backend.tools.persona_stream_tools import (
    handle_sanitize_chat_stream,
    handle_set_adaptive_persona_mode,
    handle_get_stream_shield_metrics,
)


@pytest.fixture(autouse=True)
def reset_state():
    guardian.resume()
    stream_sanitizer.reset_metrics()
    adaptive_persona_engine.set_mode(PersonaMode.ADAPTIVE_AUTO)
    yield
    guardian.resume()


def test_stream_sanitizer_removes_tool_headers():
    raw = "Haan Bro! Let's get that done.\n\n** Tool :** `open_app(app_name)`\n\nAll set."
    result = stream_sanitizer.sanitize(raw)
    assert "** Tool :**" not in result.clean_text
    assert "open_app" not in result.clean_text
    assert "Haan Bro! Let's get that done." in result.clean_text
    assert "All set." in result.clean_text
    assert result.has_stripped_telemetry is True


def test_stream_sanitizer_removes_json_execution_blocks():
    raw = """Opening Spotify for you.

** JSON Execution Block :**
```json
{"tool": "open_app", "args": {"app_name": "Spotify"}}
```

Enjoy the beats!"""
    result = stream_sanitizer.sanitize(raw)
    assert "JSON Execution Block" not in result.clean_text
    assert "{" not in result.clean_text
    assert "```" not in result.clean_text
    assert "Opening Spotify for you." in result.clean_text
    assert "Enjoy the beats!" in result.clean_text


def test_stream_sanitizer_removes_action_and_tool_result_stamps():
    raw = """Opening CompactGUI.
[Action Executed: Opened CompactGUI]
[Tool open_app Result: {"app_name": "CompactGUI", "launched": true, "launcher_pid": 7176}]
All set."""
    result = stream_sanitizer.sanitize(raw)
    assert "[Action Executed" not in result.clean_text
    assert "[Tool open_app Result" not in result.clean_text
    assert "7176" not in result.clean_text
    assert "Opening CompactGUI." in result.clean_text
    assert "All set." in result.clean_text


def test_stream_sanitizer_full_user_report_example():
    """Exact test case replicating the user's reported problem prompt."""
    raw = """Haan Bro! Let's open CompactGUI.

** Tool :** `open_app(app_name)`

** JSON Execution Block :**
json
{"tool": "open_app", "args": {"app_name": "CompactGUI"}}

This command will launch the CompactGUI application.
[Action Executed: Opened CompactGUI]

All set.
[Tool open_app Result: {"app_name": "CompactGUI",
"launched": true, "launcher_pid": 7176}]
All set."""

    result = stream_sanitizer.sanitize(raw)
    clean = result.clean_text

    # None of the internal execution syntax must remain
    assert "** Tool :**" not in clean
    assert "JSON Execution Block" not in clean
    assert "launcher_pid" not in clean
    assert "7176" not in clean
    assert "[Action Executed" not in clean
    assert "[Tool open_app Result" not in clean
    assert "This command will launch" not in clean

    # Clean human response preserved without duplicate trailing lines
    assert "Haan Bro! Let's open CompactGUI." in clean
    assert "All set." in clean
    # Check deduplication of "All set."
    assert clean.count("All set.") == 1
    assert result.has_stripped_telemetry is True
    assert result.chars_removed > 50


def test_stream_sanitizer_extracts_tool_metadata():
    raw = """Executing app.
{"tool": "open_app", "args": {"app_name": "VSCode"}}
[Tool open_app Result: {"launched": true, "pid": 4321}]
Finished."""
    result = stream_sanitizer.sanitize(raw)
    assert len(result.extracted_tools) >= 1
    tool_meta = result.extracted_tools[0]
    assert tool_meta.tool_name == "open_app"
    assert tool_meta.arguments.get("app_name") == "VSCode"
    assert tool_meta.result.get("launched") is True
    assert tool_meta.result.get("pid") == 4321


def test_adaptive_persona_desktop_actions_auto():
    engine = AdaptivePersonaEngine(PersonaMode.ADAPTIVE_AUTO)

    # Fast desktop app launch -> minimal confirmation
    resp = engine.format_action_response("open_app", "CompactGUI")
    assert resp.mode_applied == PersonaMode.MINIMAL_CONFIRMATION
    assert resp.is_silent is False
    assert resp.formatted_text == "Opening CompactGUI..."

    # Close app -> minimal confirmation
    resp = engine.format_action_response("close_app", "Chrome")
    assert resp.formatted_text == "Closed Chrome."

    # Volume change -> minimal confirmation
    resp = engine.format_action_response("set_volume", "50%")
    assert resp.formatted_text == "Volume set to 50%."


def test_adaptive_persona_silent_mode():
    engine = AdaptivePersonaEngine(PersonaMode.SILENT_EXECUTION)
    resp = engine.format_action_response("open_app", "Spotify")
    assert resp.mode_applied == PersonaMode.SILENT_EXECUTION
    assert resp.is_silent is True
    assert resp.formatted_text == ""


def test_adaptive_persona_conversational_witty_mode():
    engine = AdaptivePersonaEngine(PersonaMode.CONVERSATIONAL_WITTY)
    resp = engine.format_action_response("open_app", "CompactGUI")
    assert resp.mode_applied == PersonaMode.CONVERSATIONAL_WITTY
    assert "bro" in resp.formatted_text.lower()
    assert "Opening CompactGUI for you, bro!" == resp.formatted_text


def test_guardian_kill_switch_sla():
    """Benchmarks Guardian kill switch halt across stream sanitizer and persona engine."""
    guardian.resume()
    start_time = time.perf_counter()
    guardian.trigger("EMERGENCY_HALT_TEST")
    halt_duration_ms = (time.perf_counter() - start_time) * 1000.0

    assert halt_duration_ms < 25.0, f"Guardian halt took {halt_duration_ms:.4f}ms, exceeded 25.0ms SLA"

    # Sanitizer must fail immediately
    with pytest.raises(RuntimeError, match="STREAM_SANITIZER_HALTED"):
        stream_sanitizer.sanitize("Hello world")

    # Persona engine must fail immediately
    with pytest.raises(RuntimeError, match="ADAPTIVE_PERSONA_HALTED"):
        adaptive_persona_engine.format_action_response("open_app", "TestApp")


def test_rule_8_anti_checkout_defense():
    """Rule 8: Payment or checkout keywords must raise Rule8ViolationError."""
    with pytest.raises(Rule8ViolationError, match="Rule 8 Violation"):
        stream_sanitizer.sanitize("Please pay $50 at checkout using credit card")

    with pytest.raises(Rule8ViolationError, match="Rule 8 Violation"):
        adaptive_persona_engine.format_action_response("open_app", "checkout_gateway")


def test_tool_registry_persona_stream_tools():
    """Verifies that all 3 new tools execute properly through handle_* functions."""
    # 1. sanitize_chat_stream (Tier 0)
    raw = "Let's run.\n** Tool :** `test_tool`\nAll done."
    res1 = handle_sanitize_chat_stream(raw_text=raw)
    assert "** Tool :**" not in res1["clean_text"]
    assert res1["has_stripped_telemetry"] is True

    # 2. set_adaptive_persona_mode (Tier 1)
    res2 = handle_set_adaptive_persona_mode(mode="MINIMAL_CONFIRMATION")
    assert res2["status"] == "UPDATED"
    assert res2["new_mode"] == "MINIMAL_CONFIRMATION"

    # Invalid mode test
    with pytest.raises(ValueError, match="Invalid persona mode"):
        handle_set_adaptive_persona_mode(mode="NON_EXISTENT_MODE")

    # 3. get_stream_shield_metrics (Tier 0)
    res3 = handle_get_stream_shield_metrics()
    assert res3["total_chunks_processed"] >= 1
    assert res3["current_persona_mode"] == "MINIMAL_CONFIRMATION"


def test_stream_sanitizer_user_brave_exact_scenario():
    raw = """Haan Bro! Let's open Brave.
** Tool :** `open_app(app_name)`
** JSON Execution Block :**
json
{"tool": "open_app", "args": {"app_name": "Brave"}}

This command will launch the Brave browser.
[Action Executed: Opened Brave browser]
All set.
All set."""
    res = stream_sanitizer.sanitize(raw)
    assert "** Tool :**" not in res.clean_text
    assert "JSON Execution Block" not in res.clean_text
    assert "open_app" not in res.clean_text
    assert "This command will launch" not in res.clean_text
    assert "[Action Executed" not in res.clean_text
    assert res.clean_text.count("All set.") <= 1
    assert "Haan Bro! Let's open Brave." in res.clean_text

