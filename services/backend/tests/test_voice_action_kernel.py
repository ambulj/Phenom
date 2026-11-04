import pytest
import time
from services.backend.schemas.voice_action import VoiceKernelState, IntentType
from services.backend.voice_action.kernel import StreamingVoiceActionKernel


def test_voice_kernel_session_lifecycle():
    kernel = StreamingVoiceActionKernel(max_buffer_size=50)
    assert kernel.state == VoiceKernelState.IDLE
    assert not kernel.is_listening

    session_id = kernel.start_session("test-vox-01")
    assert session_id == "test-vox-01"
    assert kernel.state == VoiceKernelState.LISTENING
    assert kernel.is_listening

    status = kernel.get_status()
    assert status.active_session_id == "test-vox-01"
    assert status.total_dispatched == 0

    kernel.stop_session()
    assert kernel.state == VoiceKernelState.IDLE
    assert not kernel.is_listening
    assert kernel.get_status().active_session_id is None


def test_voice_kernel_chunk_ingest_and_noise_calibration():
    kernel = StreamingVoiceActionKernel(max_buffer_size=50)
    kernel.start_session()

    # Ingest silence frames to calibrate noise floor
    for _ in range(10):
        res = kernel.ingest_chunk(rms_energy=0.04, speech_prob=0.05)
        assert not res["is_speech"]
        assert res["state"] == "listening"

    # Ingest speech frame without transcript
    speech_res = kernel.ingest_chunk(rms_energy=0.35, speech_prob=0.88)
    assert speech_res["is_speech"]
    assert speech_res["state"] == "listening"


def test_voice_kernel_intent_dispatch_and_barge_in():
    kernel = StreamingVoiceActionKernel(max_buffer_size=50)
    kernel.start_session()

    # Dispatch tool call
    res = kernel.ingest_chunk(
        rms_energy=0.40,
        speech_prob=0.92,
        transcript_text="open search workspace",
    )
    assert res["is_speech"]
    assert res["state"] == "dispatching"
    dispatched = res["dispatched_action"]
    assert dispatched is not None
    assert dispatched["matched_intent"] == IntentType.TOOL_CALL
    assert dispatched["tool_name"] == "workspace_search"
    assert dispatched["status"] == "dispatched"

    # Test barge-in interruption
    barge_res = kernel.ingest_chunk(
        rms_energy=0.45,
        speech_prob=0.95,
        transcript_text="stop wait halt",
    )
    assert barge_res["state"] == "barged_in"
    barge_action = barge_res["dispatched_action"]
    assert barge_action["matched_intent"] == IntentType.INTERRUPTION
    assert barge_action["status"] == "barged_in"


def test_voice_kernel_safety_rule_8_payment_blocked():
    kernel = StreamingVoiceActionKernel()
    kernel.start_session()

    # Rule 8: Voice-initiated financial transactions blocked
    with pytest.raises(PermissionError) as exc_info:
        kernel.ingest_chunk(
            rms_energy=0.50,
            speech_prob=0.90,
            transcript_text="please pay now for my order",
        )
    assert "Rule 8 Violation" in str(exc_info.value)


def test_voice_kernel_safety_rule_8_11_passwords_blocked():
    kernel = StreamingVoiceActionKernel()
    kernel.start_session()

    # Rule 8/11: Password speech blocked
    with pytest.raises(PermissionError) as exc_info:
        kernel.ingest_chunk(
            rms_energy=0.50,
            speech_prob=0.90,
            transcript_text="my password is secret 123",
        )
    assert "Rule 8/11 Violation" in str(exc_info.value)


def test_voice_kernel_safety_rule_7_permanent_delete_blocked():
    kernel = StreamingVoiceActionKernel()
    kernel.start_session()

    # Rule 7: Permanent deletion blocked
    with pytest.raises(PermissionError) as exc_info:
        kernel.ingest_chunk(
            rms_energy=0.50,
            speech_prob=0.90,
            transcript_text="delete permanently this document",
        )
    assert "Rule 7 Violation" in str(exc_info.value)


def test_voice_kernel_safety_rule_9_send_email_blocked():
    kernel = StreamingVoiceActionKernel()
    kernel.start_session()

    # Rule 9: Send email blocked (drafts only)
    with pytest.raises(PermissionError) as exc_info:
        kernel.ingest_chunk(
            rms_energy=0.50,
            speech_prob=0.90,
            transcript_text="send email to my colleague",
        )
    assert "Rule 9 Violation" in str(exc_info.value)


def test_voice_kernel_transient_ring_buffer_bounds():
    kernel = StreamingVoiceActionKernel(max_buffer_size=10)
    kernel.start_session()

    # Ingest 25 chunks into ring buffer bounded at 10
    for i in range(25):
        kernel.ingest_chunk(rms_energy=0.1, speech_prob=0.3)

    assert len(kernel._chunk_buffer) == 10
