"""
Phenom Milestone 9.0 Phase 2: Smart Minimalist Jarvis Persona Policy Tests
Tests:
1. Spontaneous speech strictly gated to the 4 permitted triggers.
2. Complete suppression during user typing or deep focus.
3. Imminent calendar deadline (< 10m threshold) evaluation.
4. Witty British Jarvis cadence formatting and conversational fluff stripping.
5. Mode switching ('minimalist' vs 'conversational').
"""

import pytest
from services.backend.voice.persona_policy import MinimalistVoicePolicy
from services.backend.schemas.streaming_voice import SpontaneousSpeechDecision


def test_spontaneous_speech_permitted_triggers():
    """Verify spontaneous speech evaluates to True ONLY for the 4 core triggers."""
    policy = MinimalistVoicePolicy(mode="minimalist")

    # 1. Critical error
    dec_err = policy.evaluate_spontaneous_speech("critical_error", {"detail": "Segmentation fault in test_auth.py"})
    assert dec_err.should_speak is True
    assert dec_err.urgency_level == "critical"

    # 2. Urgent calendar deadline (< 10 min)
    dec_cal = policy.evaluate_spontaneous_speech("calendar_urgent", {"minutes_until": 5, "event": "Architecture Review"})
    assert dec_cal.should_speak is True
    assert dec_cal.urgency_level == "urgent"

    # Non-urgent calendar (> 10 min)
    dec_cal_far = policy.evaluate_spontaneous_speech("calendar_urgent", {"minutes_until": 25, "event": "Sprint Planning"})
    assert dec_cal_far.should_speak is False

    # 3. Guardian security alert
    dec_sec = policy.evaluate_spontaneous_speech("guardian_security", {"reason": "Permission escalation blocked"})
    assert dec_sec.should_speak is True
    assert dec_sec.urgency_level == "security"

    # 4. Direct summon / wake word
    dec_sum = policy.evaluate_spontaneous_speech("direct_summon", {"query": "Phenom status"})
    assert dec_sum.should_speak is True
    assert dec_sum.urgency_level == "direct"

    # Non-permitted routine updates in minimalist mode
    dec_obs = policy.evaluate_spontaneous_speech("desktop_observation", {"window": "VSCode"})
    assert dec_obs.should_speak is False

    dec_rout = policy.evaluate_spontaneous_speech("routine_update", {"cpu": 12})
    assert dec_rout.should_speak is False


def test_spontaneous_speech_suppressed_during_typing_and_deep_focus():
    """Verify spontaneous speech is strictly suppressed during user typing or deep focus."""
    policy = MinimalistVoicePolicy(mode="minimalist")

    # Critical error occurring while user is typing
    dec_typing = policy.evaluate_spontaneous_speech(
        "critical_error",
        {"user_typing": True, "detail": "Syntax error"}
    )
    assert dec_typing.should_speak is False
    assert "user typing" in dec_typing.reason.lower()

    # Calendar event occurring during deep focus
    dec_focus = policy.evaluate_spontaneous_speech(
        "calendar_urgent",
        {"minutes_until": 3, "activity": "deep_focus"}
    )
    assert dec_focus.should_speak is False
    assert "focus" in dec_focus.reason.lower()

    # Direct summon STILL speaks even if user was typing
    dec_summon = policy.evaluate_spontaneous_speech(
        "direct_summon",
        {"user_typing": True}
    )
    assert dec_summon.should_speak is True


def test_conversational_vs_minimalist_mode():
    """Verify switching to conversational mode allows proactive ambient updates."""
    policy = MinimalistVoicePolicy(mode="minimalist")

    # In minimalist mode: desktop observation is suppressed
    assert policy.evaluate_spontaneous_speech("desktop_observation").should_speak is False

    # Switch to conversational mode
    policy.set_mode("conversational")
    assert policy.get_mode() == "conversational"

    # In conversational mode: desktop observation is allowed
    assert policy.evaluate_spontaneous_speech("desktop_observation").should_speak is True

    # Invalid mode raises ValueError
    with pytest.raises(ValueError):
        policy.set_mode("unsupported_mode")


def test_jarvis_cadence_formatting():
    """Verify Jarvis cadence formatting strips fillers and formats refined British tone."""
    policy = MinimalistVoicePolicy(cadence="british_jarvis")

    fluffy_input = "Hello there, how are you today? I would be delighted to help you with that. The server has restarted."
    formatted = policy.format_jarvis_cadence(fluffy_input, context_type="general")
    
    assert "Hello there" not in formatted
    assert "delighted to help" not in formatted
    assert "The server has restarted." in formatted

    # Critical error context formatting
    err_input = "The compilation failed on line 102."
    formatted_err = policy.format_jarvis_cadence(err_input, context_type="critical_error")
    assert formatted_err.startswith("Pardon the intrusion, sir.")
    assert "line 102" in formatted_err

    # Direct summon context formatting
    sum_input = "Standing by for instructions."
    formatted_sum = policy.format_jarvis_cadence(sum_input, context_type="direct_summon")
    assert formatted_sum.startswith("Right then.")
