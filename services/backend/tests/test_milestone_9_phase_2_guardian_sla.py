"""
Phenom Milestone 9.0 Phase 2: Guardian Kill Switch Sub-25ms SLA & Safety Verification (SAF-01, SAF-02)

Verifies:
1. Strict ToolRegistry registration, risk tiering (Tier 0 & Tier 1), Pydantic schemas, and preview generation (SAF-01).
2. Synchronous execution time of Guardian trigger is strictly < 25.0ms SLA (< 1ms typical) across the streaming voice engine (SAF-02).
3. Synchronous halt cascade halts StreamingVoiceEngine, purges audio buffers, cuts off TTS playback immediately.
4. Universal rejection of subsequent voice operations and tool calls with PermissionError while halted.
5. Clean state restoration and resumption via guardian.resume().
"""

import time
import pytest
import numpy as np

from services.backend.main import on_guardian_state_change
from services.backend.safety.guardian import guardian
from services.backend.safety.registry import registry
from services.backend.safety.engine import safety_engine
from services.backend.voice.streaming_engine import (
    streaming_voice_engine,
    StreamingVoiceState,
)
from services.backend.voice.tts import tts_engine
from services.backend.schemas.streaming_voice import (
    VoiceConfigureArgs,
    VoiceSpeakArgs,
    VoiceStatusArgs,
)
import services.backend.tools.voice_tools


@pytest.fixture(autouse=True)
def reset_milestone_9_phase_2_components():
    """Ensure clean state before and after each test."""
    guardian.resume()
    streaming_voice_engine.reset()
    tts_engine.stop_speech()
    yield
    guardian.resume()
    streaming_voice_engine.reset()
    tts_engine.stop_speech()


def test_tool_registry_registration_and_metadata():
    """SAF-01: Verifies all Phase 2 tools are registered with correct tiers, schemas, and previews."""
    # 1. voice_get_engine_status (Tier 0 Read-Only)
    tool_status = registry.get("voice_get_engine_status")
    assert tool_status is not None, "voice_get_engine_status not registered in ToolRegistry"
    assert tool_status.tier == 0
    assert tool_status.args_schema == VoiceStatusArgs
    preview_status = tool_status.generate_preview({})
    assert "Inspect streaming voice engine status" in preview_status

    # 2. voice_speak_utterance (Tier 0 Read-Only Audio Playback)
    tool_speak = registry.get("voice_speak_utterance")
    assert tool_speak is not None, "voice_speak_utterance not registered in ToolRegistry"
    assert tool_speak.tier == 0
    assert tool_speak.args_schema == VoiceSpeakArgs
    preview_speak = tool_speak.generate_preview({"text": "System check complete."})
    assert "Synthesize and play spoken utterance" in preview_speak

    # 3. voice_configure_engine (Tier 1 Reversible Change)
    tool_config = registry.get("voice_configure_engine")
    assert tool_config is not None, "voice_configure_engine not registered in ToolRegistry"
    assert tool_config.tier == 1
    assert tool_config.args_schema == VoiceConfigureArgs
    preview_config = tool_config.generate_preview({
        "persona_mode": "conversational",
        "speech_speed": 1.1,
        "barge_in_sensitivity": 0.45,
    })
    assert "Configure streaming voice engine settings" in preview_config


def test_guardian_kill_switch_synchronous_sla():
    """SAF-02: Measure synchronous execution time of Guardian trigger across voice engine (< 25ms SLA)."""
    # Put engine into active speaking state
    streaming_voice_engine._set_state(StreamingVoiceState.SPEAKING)
    tts_engine._is_speaking = True

    # Pre-populate audio chunks in RAM
    for _ in range(10):
        streaming_voice_engine._ring_buffer.append(np.zeros(512, dtype=np.float32))

    t0 = time.perf_counter()
    guardian.trigger("emergency_voice_killswitch_sla_test")
    elapsed_ms = (time.perf_counter() - t0) * 1000.0

    assert elapsed_ms < 25.0, f"Guardian kill switch SLA breached: {elapsed_ms:.2f}ms >= 25.0ms"
    assert guardian.is_halted is True
    assert streaming_voice_engine.is_halted is True
    assert streaming_voice_engine.state == StreamingVoiceState.HALTED
    assert len(streaming_voice_engine._ring_buffer) == 0
    assert tts_engine.is_speaking is False


@pytest.mark.asyncio
async def test_voice_operations_blocked_while_halted():
    """Verify speech synthesis and tool calls are strictly blocked with PermissionError while halted."""
    guardian.trigger("emergency_block_test")
    assert guardian.is_halted is True
    assert streaming_voice_engine.is_halted is True

    # Direct engine call raises PermissionError
    with pytest.raises(PermissionError) as exc_info:
        streaming_voice_engine.speak_utterance("Phenom speaking under halt.")
    assert "halted by Guardian kill switch" in str(exc_info.value)

    # Ingesting chunks while halted returns ignored
    res = streaming_voice_engine.ingest_audio_chunk(np.zeros(512, dtype=np.int16))
    assert res["status"] == "ignored"

    # Direct tool call raises PermissionError
    with pytest.raises(PermissionError):
        services.backend.tools.voice_tools.voice_speak_utterance(text="Test speech")

    # Tool invocation through safety engine is blocked by Guardian
    with pytest.raises(PermissionError, match="Guardian kill switch is active"):
        await safety_engine.execute_tool("voice_speak_utterance", {"text": "Test speech"})


def test_clean_recovery_on_guardian_resume():
    """Verify clean state restoration and resumed speech capability after guardian.resume()."""
    guardian.trigger("emergency_recovery_test")
    assert streaming_voice_engine.is_halted is True
    assert streaming_voice_engine.state == StreamingVoiceState.HALTED

    # Resume Guardian
    guardian.resume()
    assert guardian.is_halted is False
    assert streaming_voice_engine.is_halted is False
    assert streaming_voice_engine.state == StreamingVoiceState.IDLE

    # Voice operations now execute cleanly
    res = streaming_voice_engine.speak_utterance("All systems back online, sir.")
    assert res["status"] == "speaking"
    assert "All systems back online, sir." in res["formatted_text"]
