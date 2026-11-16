"""
Comprehensive Unit Test Battery for Phase 47-05:
Hybrid Model Router, Privacy Sanitization & Multi-Channel Telemetry.
Verifies requirements: ROUTER-01, ROUTER-02, ROUTER-03, ROUTER-04.
"""

import pytest

from services.backend.router.privacy_sanitizer import (
    PrivacySanitizer,
    SanitizationResult,
    privacy_sanitizer
)
from services.backend.router.hybrid_mission_router import (
    HybridMissionRouter,
    RoutingDecision,
    TargetModel,
    hybrid_mission_router
)
from services.backend.remote.telegram_mission_card import (
    TelegramMissionCard,
    telegram_mission_card
)
from services.backend.voice.mission_audio_cues import (
    MissionAudioCues,
    MissionAudioEvent,
    EarconPayload,
    mission_audio_cues
)


# ============================================================================
# 1. High-Precision Privacy Sanitizer (ROUTER-02)
# ============================================================================

def test_privacy_sanitizer_aadhaar():
    """Verifies that Indian Aadhaar numbers are masked with [REDACTED_AADHAAR]."""
    sanitizer = PrivacySanitizer()
    text = "My customer Aadhaar is 5555 4444 3333, please register it."
    res = sanitizer.sanitize(text)
    assert res.contains_sensitive_data is True
    assert "5555 4444 3333" not in res.sanitized_text
    assert "[REDACTED_AADHAAR]" in res.sanitized_text
    assert "AADHAAR" in res.redacted_types


def test_privacy_sanitizer_pan():
    """Verifies that Indian PAN cards are masked with [REDACTED_PAN]."""
    sanitizer = PrivacySanitizer()
    text = "Tax PAN number: ABCDE1234F for filing."
    res = sanitizer.sanitize(text)
    assert res.contains_sensitive_data is True
    assert "ABCDE1234F" not in res.sanitized_text
    assert "[REDACTED_PAN]" in res.sanitized_text
    assert "PAN" in res.redacted_types


def test_privacy_sanitizer_phone_and_upi():
    """Verifies that mobile numbers and UPI handles are masked."""
    sanitizer = PrivacySanitizer()
    text = "Contact 9876543210 or pay via trader@okhdfcbank."
    res = sanitizer.sanitize(text)
    assert res.contains_sensitive_data is True
    assert "9876543210" not in res.sanitized_text
    assert "trader@okhdfcbank" not in res.sanitized_text
    assert "[REDACTED_PHONE]" in res.sanitized_text
    assert "[REDACTED_UPI]" in res.sanitized_text


def test_privacy_sanitizer_api_keys_and_secrets():
    """Verifies that cloud API keys and password strings are redacted."""
    sanitizer = PrivacySanitizer()
    sample_nv = "nv" + "api-abcdef1234567890abcdef1234567890abcdef12"
    text = (
        f"NVIDIA_KEY = {sample_nv}\n"
        "AWS_KEY = AKIAIOSFODNN7EXAMPLE\n"
        "password = 'SuperSecretPassword123!'"
    )
    res = sanitizer.sanitize(text)
    assert res.contains_sensitive_data is True
    assert "nvapi-" not in res.sanitized_text
    assert "AKIAIOSFODNN7EXAMPLE" not in res.sanitized_text
    assert "SuperSecretPassword123!" not in res.sanitized_text
    assert "[REDACTED_NVIDIA_KEY]" in res.sanitized_text
    assert "[REDACTED_AWS_KEY]" in res.sanitized_text
    assert "[REDACTED_PASSWORD]" in res.sanitized_text


# ============================================================================
# 2. Hybrid Model Mission Router (ROUTER-01, ROUTER-02)
# ============================================================================

def test_hybrid_router_local_first_priority():
    """Verifies that typical coding, file actions, and DAG tasks route locally to Llama 3.1 8B."""
    router = HybridMissionRouter()
    prompt = "Read services/backend/main.py and execute the pytest suite."
    decision = router.evaluate_task(prompt)

    assert decision.target_model == TargetModel.LOCAL_8B
    assert decision.is_cloud is False
    assert decision.redactions_count == 0
    assert decision.sanitized_prompt == prompt


def test_hybrid_router_deep_reasoning_cloud_routing_with_sanitization():
    """
    Verifies that deep reasoning tasks cascade to cloud Nemotron,
    and all outbound prompt text is automatically scrubbed of sensitive PII.
    """
    router = HybridMissionRouter()
    sensitive_deep_prompt = (
        "Perform deep architectural synthesis for high-throughput messaging. "
        "Contact developer at 9876543210 or AWS key AKIAIOSFODNN7EXAMPLE."
    )
    decision = router.evaluate_task(sensitive_deep_prompt)

    assert decision.target_model == TargetModel.CLOUD_NEMOTRON
    assert decision.is_cloud is True
    assert decision.redactions_count >= 2
    # Ensure zero unredacted PII is dispatched
    assert "9876543210" not in decision.sanitized_prompt
    assert "AKIAIOSFODNN7EXAMPLE" not in decision.sanitized_prompt
    assert "[REDACTED_PHONE]" in decision.sanitized_prompt
    assert "[REDACTED_AWS_KEY]" in decision.sanitized_prompt


# ============================================================================
# 3. Telegram Editable Mission Card Telemetry (ROUTER-04)
# ============================================================================

def test_telegram_mission_card_formatting_and_progress():
    """Verifies formatting of Telegram status cards with ASCII progress bar and buttons."""
    card_gen = TelegramMissionCard()

    # Progress bar tests
    assert card_gen.generate_progress_bar(0, 10) == "[░░░░░░░░░░] 0%"
    assert card_gen.generate_progress_bar(5, 10) == "[█████░░░░░] 50%"
    assert card_gen.generate_progress_bar(10, 10) == "[██████████] 100%"

    # Card text tests
    card_md = card_gen.format_mission_card(
        mission_id="mission_1234567890",
        goal="Fix test suite failures in backend",
        status="running",
        current_step_title="Run regression tests",
        completed_steps=3,
        total_steps=5,
        elapsed_seconds=125.0
    )

    assert "*PHENOM AUTONOMOUS MISSION*" in card_md
    assert "Fix test suite failures in backend" in card_md
    assert "RUNNING" in card_md
    assert "60%" in card_md
    assert "02:05" in card_md
    assert "Run regression tests" in card_md

    # Button markup tests
    running_kb = card_gen.get_inline_keyboard("m1", status="running")
    assert len(running_kb[0]) == 2
    assert "HALT" in running_kb[0][1]["text"]


# ============================================================================
# 4. Mission Audio Cues & Earcons (ROUTER-04)
# ============================================================================

def test_mission_audio_cues_events():
    """Verifies earcon audio mappings and spoken milestone generation."""
    cues = MissionAudioCues()

    # Start event
    start_payload = cues.get_earcon(MissionAudioEvent.MISSION_STARTED)
    assert start_payload.sound_file == "chime_mission_start.wav"
    assert "Mission initiated" in str(start_payload.spoken_summary)

    # Step complete event
    step_payload = cues.get_earcon(
        MissionAudioEvent.STEP_COMPLETED,
        step_title="Build AST index",
        percent=40
    )
    assert step_payload.sound_file == "chime_step_success.wav"
    assert "40 percent" in str(step_payload.spoken_summary)

    # Guardian halt event
    halt_payload = cues.get_earcon(MissionAudioEvent.KILL_SWITCH_HALTED)
    assert halt_payload.sound_file == "alert_guardian_halt.wav"
    assert "Emergency halt" in str(halt_payload.spoken_summary)
