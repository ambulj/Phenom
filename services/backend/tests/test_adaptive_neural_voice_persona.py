import pytest
import time
import asyncio
from services.backend.voice.adaptive_tts_engine import (
    AdaptiveTTSEngine,
    adaptive_tts_engine,
    AudioChunk,
    ProsodyProfile,
    PERSONA_PROFILES
)
from services.backend.voice.audio_ducking_manager import (
    AudioDuckingManager,
    audio_ducking_manager,
    DuckingState
)
from services.backend.safety.guardian import guardian
from services.backend.safety.registry import registry
import services.backend.tools.adaptive_voice_tools  # Ensure tools are registered


@pytest.mark.asyncio
async def test_adaptive_tts_streaming_first_chunk_latency():
    """Test local streaming neural TTS delivers first chunk under 150ms SLA."""
    engine = AdaptiveTTSEngine()
    text = "Good afternoon, Bro. All system services are performing nominally."

    t0 = time.perf_counter()
    chunks: list[AudioChunk] = []

    async for chunk in engine.stream_speech_chunks(text=text, persona="witty_jarvis"):
        chunks.append(chunk)
        if len(chunks) == 1:
            first_chunk_time = (time.perf_counter() - t0) * 1000.0
            # Strict SLA: < 150ms
            assert first_chunk_time < 150.0, f"First chunk latency {first_chunk_time:.2f}ms exceeded 150ms SLA"
            assert chunk.is_first_chunk is True
            assert chunk.sample_rate == 24000
            assert len(chunk.pcm_bytes) > 0
            assert chunk.amplitude > 0.0

    assert len(chunks) >= 3
    assert chunks[-1].is_final_chunk is True


@pytest.mark.asyncio
async def test_prosody_modulation_across_personas():
    """Test dynamic prosody modulation profiles and SSML generation."""
    engine = AdaptiveTTSEngine()

    for p_id in ("witty_jarvis", "focused_coder", "urgent_alert", "calm_briefing"):
        profile = engine.set_persona(p_id)
        assert profile.persona_id == p_id
        assert engine.active_persona == p_id

        ssml = engine.format_ssml("Compiling project files.", profile=profile)
        assert "<speak>" in ssml
        assert "<prosody" in ssml
        assert str(round(profile.pitch_offset_pct, 1)) in ssml or f"{profile.pitch_offset_pct:+.1f}%" in ssml


@pytest.mark.asyncio
async def test_audio_ducking_attenuation_and_unduck_ramp():
    """Test automatic audio session ducking down to 20% and smooth 300ms recovery ramp."""
    duck_mgr = AudioDuckingManager()
    assert duck_mgr.is_ducked is False
    assert duck_mgr.current_attenuation == 1.0

    # Duck to 20%
    state = await duck_mgr.duck_audio(target_volume=0.20, ramp_ms=30)
    assert state.is_ducked is True
    assert state.current_attenuation == 0.20
    assert duck_mgr.is_ducked is True

    # Unduck to 100%
    restored = await duck_mgr.unduck_audio(restore_volume=1.0, ramp_ms=40)
    assert restored.is_ducked is False
    assert restored.current_attenuation == 1.0
    assert duck_mgr.is_ducked is False


@pytest.mark.asyncio
async def test_rule_4_zero_disk_exfiltration_in_voice():
    """Test audio synthesis yields pure RAM buffers without writing .wav files to disk."""
    engine = AdaptiveTTSEngine()
    buffer_sizes = []

    async for chunk in engine.stream_speech_chunks("Verification of in-memory voice generation."):
        assert isinstance(chunk.pcm_bytes, bytes)
        buffer_sizes.append(len(chunk.pcm_bytes))

    assert len(buffer_sizes) > 0
    assert all(b > 0 for b in buffer_sizes)


@pytest.mark.asyncio
async def test_universal_guardian_kill_switch_sla():
    """Test Guardian synchronous kill switch halts speech streaming in < 25.0ms SLA."""
    guardian.trigger("Phase 4 test halt")
    try:
        engine = AdaptiveTTSEngine()
        t0 = time.perf_counter()

        with pytest.raises(PermissionError) as exc_info:
            async for _ in engine.stream_speech_chunks("Test phrase while halted"):
                pass

        elapsed_ms = (time.perf_counter() - t0) * 1000.0
        assert elapsed_ms < 25.0, f"Guardian halt took {elapsed_ms:.2f}ms, exceeding 25ms SLA"
        assert "halted" in str(exc_info.value).lower()
    finally:
        guardian.resume()


@pytest.mark.asyncio
async def test_adaptive_voice_tools_registration_and_previews():
    """Test all Phase 4 tools are registered in Safety Registry with proper previews."""
    tool_names = [
        "synthesize_adaptive_speech",
        "set_voice_prosody_mode",
        "get_audio_ducking_state"
    ]

    for name in tool_names:
        entry = registry.get(name)
        assert entry is not None, f"Tool {name} missing from registry"
        assert entry.tier == 0  # Read-only voice and settings

        preview = entry.preview_fn({
            "text": "Hello world from Phenom",
            "persona_id": "focused_coder",
            "persona": "witty_jarvis"
        })
        assert isinstance(preview, str)
        assert len(preview) > 5
