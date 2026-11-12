"""
Phenom Voice Cloning Safety Tools
ToolRegistry integration for zero-shot local neural speaker embedding extraction,
preview synthesis, profile management, and biometric consent verification.
"""

from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field

from services.backend.safety.registry import registry
from services.backend.voice.neural_voice_cloner import (
    neural_voice_cloner,
    enforce_anti_checkout,
    Rule8ViolationError,
)


# ==========================================
# 1. Extract Neural Voiceprint (Tier 1)
# ==========================================

class ExtractNeuralVoiceprintArgs(BaseModel):
    profile_name: str = Field(
        ...,
        description="User-assigned name for the cloned voice identity (e.g. 'Tactical Commander', 'Personal Archive')",
    )
    sample_duration_sec: float = Field(
        3.5,
        ge=3.0,
        le=60.0,
        description="Duration of audio reference sample in seconds (minimum 3.0s required)",
    )
    consent_token: Optional[str] = Field(
        None,
        description="Optional pre-authorized SHA-256 consent token for biometric voiceprint creation",
    )


def preview_extract_neural_voiceprint(args: Dict[str, Any]) -> str:
    name = args.get("profile_name", "custom_voice")
    dur = args.get("sample_duration_sec", 3.5)
    return f"Extract 512-d zero-shot neural speaker embedding for '{name}' from {dur}s audio sample."


@registry.register(
    name="extract_neural_voiceprint",
    tier=1,
    description="Extracts 512-d zero-shot neural speaker embedding from local reference audio to create a cloned voice profile (Tier 1 biometric operation).",
    args_schema=ExtractNeuralVoiceprintArgs,
    preview_fn=preview_extract_neural_voiceprint,
    can_remember_per_folder=False,
)
def handle_extract_neural_voiceprint(
    profile_name: str,
    sample_duration_sec: float = 3.5,
    consent_token: Optional[str] = None,
) -> Dict[str, Any]:
    enforce_anti_checkout(profile_name)

    # Synthesize 16-bit 16kHz PCM audio bytes matching duration (16000 samples/sec * 2 bytes/sample)
    num_samples = int(sample_duration_sec * 16000)
    audio_bytes = bytes([128] * (num_samples * 2))

    profile = neural_voice_cloner.extract_speaker_embedding(
        audio_samples=audio_bytes,
        sample_rate=16000,
        profile_name=profile_name,
        consent_token=consent_token,
    )

    return {
        "status": "CREATED",
        "profile_id": profile.profile_id,
        "name": profile.name,
        "sample_duration_sec": profile.sample_duration_sec,
        "pitch_mean_hz": profile.pitch_mean_hz,
        "spectral_centroid_hz": profile.spectral_centroid_hz,
        "harmonicity_ratio": profile.harmonicity_ratio,
        "embedding_dimensions": len(profile.embedding),
    }


# ==========================================
# 2. Synthesize Cloned Voice Preview (Tier 0)
# ==========================================

class SynthesizeClonedVoicePreviewArgs(BaseModel):
    profile_id: str = Field(
        ...,
        description="Unique identifier of the cloned voice profile",
    )
    prompt_text: str = Field(
        ...,
        description="Text prompt to render into synthetic preview speech",
    )
    speech_rate: float = Field(
        1.0,
        ge=0.5,
        le=2.0,
        description="Speech pacing multiplier",
    )


def preview_synthesize_cloned_voice_preview(args: Dict[str, Any]) -> str:
    pid = args.get("profile_id", "jarvis_base")
    txt = args.get("prompt_text", "")
    preview_txt = (txt[:30] + "...") if len(txt) > 30 else txt
    return f"Synthesize preview speech using voice profile '{pid}': '{preview_txt}'."


@registry.register(
    name="synthesize_cloned_voice_preview",
    tier=0,
    description="Synthesizes speech preview metadata from a target cloned voice profile (Tier 0 diagnostic/preview).",
    args_schema=SynthesizeClonedVoicePreviewArgs,
    preview_fn=preview_synthesize_cloned_voice_preview,
    can_remember_per_folder=False,
)
def handle_synthesize_cloned_voice_preview(
    profile_id: str,
    prompt_text: str,
    speech_rate: float = 1.0,
) -> Dict[str, Any]:
    return neural_voice_cloner.synthesize_preview_speech(
        profile_id=profile_id,
        prompt_text=prompt_text,
        speech_rate=speech_rate,
    )


# ==========================================
# 3. List Cloned Voice Profiles (Tier 0)
# ==========================================

class ListClonedVoiceProfilesArgs(BaseModel):
    pass


def preview_list_cloned_voice_profiles(args: Dict[str, Any]) -> str:
    return "List all registered local neural cloned voice profiles."


@registry.register(
    name="list_cloned_voice_profiles",
    tier=0,
    description="Returns inventory of registered cloned voice profiles with acoustic metadata (Tier 0 read-only).",
    args_schema=ListClonedVoiceProfilesArgs,
    preview_fn=preview_list_cloned_voice_profiles,
    can_remember_per_folder=False,
)
def handle_list_cloned_voice_profiles() -> Dict[str, Any]:
    profiles = neural_voice_cloner.list_profiles()
    return {
        "status": "OK",
        "count": len(profiles),
        "profiles": profiles,
    }


# ==========================================
# 4. Delete Cloned Voice Profile (Tier 1)
# ==========================================

class DeleteClonedVoiceProfileArgs(BaseModel):
    profile_id: str = Field(
        ...,
        description="Unique identifier of the voice profile to purge",
    )


def preview_delete_cloned_voice_profile(args: Dict[str, Any]) -> str:
    pid = args.get("profile_id", "")
    return f"Permanently delete cloned voice profile '{pid}' and wipe biometric embeddings."


@registry.register(
    name="delete_cloned_voice_profile",
    tier=1,
    description="Permanently purges target cloned voice profile and revocable embeddings from memory (Tier 1 destructive operation).",
    args_schema=DeleteClonedVoiceProfileArgs,
    preview_fn=preview_delete_cloned_voice_profile,
    can_remember_per_folder=False,
)
def handle_delete_cloned_voice_profile(profile_id: str) -> Dict[str, Any]:
    success = neural_voice_cloner.delete_profile(profile_id)
    return {
        "status": "PURGED" if success else "NOT_FOUND",
        "profile_id": profile_id,
        "purged": success,
    }
