"""
Safety-Wrapped Adaptive Voice & Persona Tools.
Registers tools with ToolRegistry for adaptive speech synthesis, dynamic prosody
switching, and desktop audio ducking telemetry (Phase 21-04 VOX-05 / PER-02).
"""

from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field

from services.backend.safety.registry import registry
from services.backend.voice.adaptive_tts_engine import adaptive_tts_engine
from services.backend.voice.audio_ducking_manager import audio_ducking_manager


# ==========================================
# 1. Synthesize Adaptive Speech (Tier 0)
# ==========================================

class SynthesizeAdaptiveSpeechArgs(BaseModel):
    text: str = Field(..., description="Text content to speak")
    persona: Optional[str] = Field(default=None, description="Persona override: witty_jarvis, focused_coder, urgent_alert, calm_briefing")

def synthesize_adaptive_speech_preview(args: Dict[str, Any]) -> str:
    text = args.get("text", "")
    p = args.get("persona") or "default"
    return f"Synthesize adaptive local speech for '{text[:40]}...' (Persona: {p})."

@registry.register(
    name="synthesize_adaptive_speech",
    tier=0,
    description="Synthesizes streaming local neural speech with sub-150ms first-chunk audio latency and dynamic prosody.",
    args_schema=SynthesizeAdaptiveSpeechArgs,
    preview_fn=synthesize_adaptive_speech_preview,
    can_remember_per_folder=False
)
async def handle_synthesize_adaptive_speech(
    text: str,
    persona: Optional[str] = None
) -> Dict[str, Any]:
    chunks = []
    first_chunk_latency = 0.0
    async for chunk in adaptive_tts_engine.stream_speech_chunks(text=text, persona=persona):
        if chunk.is_first_chunk:
            first_chunk_latency = chunk.latency_to_first_chunk_ms
        chunks.append({
            "chunk_index": chunk.chunk_index,
            "duration_ms": chunk.duration_ms,
            "amplitude": chunk.amplitude,
            "bytes_len": len(chunk.pcm_bytes),
        })

    return {
        "text": text,
        "persona": persona or adaptive_tts_engine.active_persona,
        "total_chunks": len(chunks),
        "first_chunk_latency_ms": first_chunk_latency,
        "chunks_summary": chunks[:3],
    }


# ==========================================
# 2. Set Voice Prosody Mode (Tier 0)
# ==========================================

class SetVoiceProsodyModeArgs(BaseModel):
    persona_id: str = Field(..., description="Persona preset: witty_jarvis, focused_coder, urgent_alert, calm_briefing")

def set_voice_prosody_mode_preview(args: Dict[str, Any]) -> str:
    p = args.get("persona_id", "witty_jarvis")
    return f"Set active voice persona and dynamic prosody profile to '{p}'."

@registry.register(
    name="set_voice_prosody_mode",
    tier=0,
    description="Sets the assistant voice persona and prosody modulation preset.",
    args_schema=SetVoiceProsodyModeArgs,
    preview_fn=set_voice_prosody_mode_preview,
    can_remember_per_folder=False
)
def handle_set_voice_prosody_mode(persona_id: str) -> Dict[str, Any]:
    profile = adaptive_tts_engine.set_persona(persona_id)
    return profile.model_dump()


# ==========================================
# 3. Get Audio Ducking State (Tier 0)
# ==========================================

class GetAudioDuckingStateArgs(BaseModel):
    pass

def get_audio_ducking_state_preview(args: Dict[str, Any]) -> str:
    return "Inspect desktop system audio ducking attenuation level and active sessions."

@registry.register(
    name="get_audio_ducking_state",
    tier=0,
    description="Returns current desktop audio session ducking state, attenuation factor, and active sessions count.",
    args_schema=GetAudioDuckingStateArgs,
    preview_fn=get_audio_ducking_state_preview,
    can_remember_per_folder=False
)
def handle_get_audio_ducking_state() -> Dict[str, Any]:
    state = audio_ducking_manager.get_state()
    return state.model_dump()
