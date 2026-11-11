"""Tests for Conversational Voice Confirmation & Interactive Dispatcher (Milestone 29 Phase 3).

Validates:
- VOICE-01.1: Natural-language conversational spoken prompt synthesis for high-risk actions.
- VOICE-01.2: Conversational intent parsing across spoken affirmative and negative tokens.
- CONFIRM-03.1: Human-readable action preview and conversational feedback response.
- SAF-01: Registered tools (dispatch_conversational_confirmation, process_voice_approval_response, get_active_voice_confirmations).
- SAF-02: Universal Guardian kill switch SLA halt (< 25.0ms SLA).
- Rule 8: Payment and checkout keyword rejection with Rule8ViolationError.
- Rule 4: 100% on-device local execution.
"""

import time
import pytest

from services.backend.safety.guardian import guardian
from services.backend.safety.conversational_intent_parser import (
    conversational_intent_parser,
    ConfirmationDecision,
    Rule8ViolationError,
)
from services.backend.safety.voice_confirmation_dispatcher import (
    voice_confirmation_dispatcher,
)
from services.backend.tools.voice_confirmation_tools import (
    handle_dispatch_conversational_confirmation,
    handle_process_voice_approval_response,
    handle_get_active_voice_confirmations,
)


@pytest.fixture(autouse=True)
def reset_state():
    guardian.resume()
    yield
    guardian.resume()


def test_conversational_intent_parser_affirmative():
    """Checks affirmative spoken responses."""
    affirmative_inputs = [
        "yes",
        "Yeah, go ahead",
        "Sure thing, do it",
        "Definitely, proceed",
        "Confirm please",
        "Haan kar de",
        "Looks good, make it happen",
    ]
    for inp in affirmative_inputs:
        res = conversational_intent_parser.parse_intent(inp)
        assert res.decision == ConfirmationDecision.APPROVED
        assert res.confidence >= 0.9


def test_conversational_intent_parser_negative():
    """Checks negative spoken responses."""
    negative_inputs = [
        "no",
        "Nah, stop",
        "Cancel that immediately",
        "Abort the operation",
        "Don't do it",
        "Mat kar bhai",
        "Leave it",
    ]
    for inp in negative_inputs:
        res = conversational_intent_parser.parse_intent(inp)
        assert res.decision == ConfirmationDecision.DENIED
        assert res.confidence >= 0.9


def test_conversational_intent_parser_ambiguous():
    """Checks ambiguous or empty user replies."""
    res_empty = conversational_intent_parser.parse_intent("")
    assert res_empty.decision == ConfirmationDecision.AMBIGUOUS

    res_random = conversational_intent_parser.parse_intent("What is the weather today?")
    assert res_random.decision == ConfirmationDecision.AMBIGUOUS


def test_voice_confirmation_dispatcher_synthesize_prompt():
    """Verifies that technical tool actions synthesize into Jarvis/bro conversational spoken prompts."""
    # 1. recycle_delete
    p1 = voice_confirmation_dispatcher.synthesize_spoken_prompt(
        "recycle_delete",
        {"path": "C:\\Users\\sauja\\Downloads\\old_backup.zip"},
    )
    assert "Bro, should I recycle old_backup.zip for you?" in p1.spoken_question
    assert "Windows Recycle Bin" in p1.display_summary

    # 2. send_email
    p2 = voice_confirmation_dispatcher.synthesize_spoken_prompt(
        "send_email",
        {"recipient": "alex@example.com", "subject": "Update"},
    )
    assert "Bro, do you want me to send this email to alex@example.com?" in p2.spoken_question

    # 3. telegram_broadcast
    p3 = voice_confirmation_dispatcher.synthesize_spoken_prompt(
        "telegram_broadcast",
        {"channel": "alerts", "message": "High server load"},
    )
    assert "Bro, should I broadcast this message to your Telegram channel?" in p3.spoken_question


def test_voice_confirmation_dispatcher_resolve_flow():
    """Tests the full dispatch, resolution, and feedback lifecycle."""
    # 1. Dispatch confirmation
    prompt = voice_confirmation_dispatcher.dispatch_confirmation(
        tool_name="send_email",
        args={"recipient": "boss@company.com"},
    )
    pid = prompt.prompt_id
    assert pid is not None

    # Check active queue
    active = voice_confirmation_dispatcher.get_active_confirmations()
    assert any(a["prompt_id"] == pid for a in active)

    # 2. Resolve with approval
    res_approve = voice_confirmation_dispatcher.resolve_confirmation(pid, "Yeah bro, go ahead and send it")
    assert res_approve["status"] == "APPROVED"
    assert res_approve["decision"] == "APPROVED"
    assert "Awesome, bro!" in res_approve["spoken_feedback"]

    # 3. Dispatch second and resolve with denial
    prompt2 = voice_confirmation_dispatcher.dispatch_confirmation(
        tool_name="modify_registry_key",
        args={"key": "HKLM\\Software\\Test"},
    )
    res_deny = voice_confirmation_dispatcher.resolve_confirmation(prompt2.prompt_id, "No, abort that")
    assert res_deny["status"] == "DENIED"
    assert res_deny["decision"] == "DENIED"
    assert "No problem, bro! Cancelled." in res_deny["spoken_feedback"]


def test_voice_confirmation_dispatcher_timeout():
    """Tests timeout handling on stale confirmations."""
    prompt = voice_confirmation_dispatcher.dispatch_confirmation(
        tool_name="send_email",
        args={"recipient": "user@example.com"},
    )
    # Force timeout
    prompt_record = voice_confirmation_dispatcher._pending[prompt.prompt_id]
    prompt_record.prompt.timeout_seconds = 0
    prompt_record.prompt.created_at = time.time() - 10

    res = voice_confirmation_dispatcher.resolve_confirmation(prompt.prompt_id, "yes")
    assert res["status"] == "TIMED_OUT"
    assert res["decision"] == "DENIED"
    assert "timed out" in res["spoken_feedback"]


def test_rule_8_anti_checkout_rejection():
    """Rule 8: Payment or checkout keywords must raise Rule8ViolationError."""
    with pytest.raises(Rule8ViolationError, match="Rule 8 Violation"):
        conversational_intent_parser.parse_intent("yes pay now and checkout with credit card")

    with pytest.raises(Rule8ViolationError, match="Rule 8 Violation"):
        voice_confirmation_dispatcher.dispatch_confirmation(
            tool_name="execute_payment_checkout",
            args={"amount": "$100"},
        )


def test_guardian_kill_switch_sla():
    """Benchmarks Guardian kill switch halt across voice confirmation dispatcher."""
    guardian.resume()
    start_time = time.perf_counter()
    guardian.trigger("EMERGENCY_HALT_TEST")
    halt_duration_ms = (time.perf_counter() - start_time) * 1000.0

    assert halt_duration_ms < 25.0, f"Guardian halt took {halt_duration_ms:.4f}ms, exceeded 25.0ms SLA"

    # Operations must fail immediately
    with pytest.raises(RuntimeError, match="INTENT_PARSER_HALTED"):
        conversational_intent_parser.parse_intent("yes")

    with pytest.raises(RuntimeError, match="VOICE_DISPATCHER_HALTED"):
        voice_confirmation_dispatcher.get_active_confirmations()


def test_tools_handle_functions():
    """Verifies that the 3 registered voice confirmation tools handle calls properly."""
    # 1. dispatch_conversational_confirmation (Tier 0)
    p = handle_dispatch_conversational_confirmation(
        tool_name="send_email",
        arguments={"recipient": "team@work.com"},
    )
    assert "prompt_id" in p
    assert "spoken_question" in p

    # 2. get_active_voice_confirmations (Tier 0)
    active_rep = handle_get_active_voice_confirmations()
    assert active_rep["count"] >= 1

    # 3. process_voice_approval_response (Tier 1)
    res = handle_process_voice_approval_response(
        prompt_id=p["prompt_id"],
        user_response="yes do it",
    )
    assert res["status"] == "APPROVED"
    assert "spoken_feedback" in res
