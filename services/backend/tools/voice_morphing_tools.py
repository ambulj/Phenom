"""
Phenom Voice Morphing & Biometric Consent Safety Tools
ToolRegistry integration for cross-identity acoustic timbre interpolation,
SHA-256 biometric consent signing, and 1-click voiceprint revocation.
"""

from typing import Any, Dict, Optional
from pydantic import BaseModel, Field

from services.backend.safety.registry import registry
from services.backend.voice.voice_morphing_matrix import (
    voice_morphing_matrix,
    enforce_anti_checkout,
    Rule8ViolationError,
)


# ==========================================
# 1. Morph Voice Identity (Tier 1)
# ==========================================

class MorphVoiceIdentityArgs(BaseModel):
    target_profile_id: str = Field(
        ...,
        description="Profile ID of the target voice to blend towards",
    )
    blend_ratio: float = Field(
        0.5,
        ge=0.0,
        le=1.0,
        description="Morphing blend ratio: 0.0 (100% source base), 0.5 (50/50 hybrid), 1.0 (100% target)",
    )
    source_profile_id: str = Field(
        "jarvis_base",
        description="Profile ID of the source base voice (defaults to 'jarvis_base')",
    )


def preview_morph_voice_identity(args: Dict[str, Any]) -> str:
    target = args.get("target_profile_id", "")
    ratio = args.get("blend_ratio", 0.5)
    return f"Morph acoustic timbre towards '{target}' at blend ratio {ratio:.2f} (Tier 1 confirmation)."


@registry.register(
    name="morph_voice_identity",
    tier=1,
    description="Interpolates acoustic timbre between source and target voice profiles (Tier 1 voice modulation).",
    args_schema=MorphVoiceIdentityArgs,
    preview_fn=preview_morph_voice_identity,
    can_remember_per_folder=False,
)
def handle_morph_voice_identity(
    target_profile_id: str,
    blend_ratio: float = 0.5,
    source_profile_id: str = "jarvis_base",
) -> Dict[str, Any]:
    telemetry = voice_morphing_matrix.set_morphing_target(
        target_profile_id=target_profile_id,
        blend_ratio=blend_ratio,
        source_profile_id=source_profile_id,
    )
    return {
        "status": "MORPHED",
        "source_profile_id": telemetry.source_profile_id,
        "target_profile_id": telemetry.target_profile_id,
        "blend_ratio": telemetry.blend_ratio,
        "morphed_pitch_mean_hz": telemetry.morphed_pitch_mean_hz,
        "morphed_centroid_hz": telemetry.morphed_centroid_hz,
        "timbre_norm": telemetry.timbre_norm,
    }


# ==========================================
# 2. Get Voice Morphing Telemetry (Tier 0)
# ==========================================

class GetVoiceMorphingTelemetryArgs(BaseModel):
    pass


def preview_get_voice_morphing_telemetry(args: Dict[str, Any]) -> str:
    return "Query real-time cross-identity voice morphing ratio, active identities, and timbre telemetry."


@registry.register(
    name="get_voice_morphing_telemetry",
    tier=0,
    description="Queries real-time cross-identity voice morphing ratio and acoustic timbre telemetry (Tier 0 read-only).",
    args_schema=GetVoiceMorphingTelemetryArgs,
    preview_fn=preview_get_voice_morphing_telemetry,
    can_remember_per_folder=False,
)
def handle_get_voice_morphing_telemetry() -> Dict[str, Any]:
    telemetry = voice_morphing_matrix.get_telemetry()
    return {
        "source_profile_id": telemetry.source_profile_id,
        "target_profile_id": telemetry.target_profile_id,
        "blend_ratio": telemetry.blend_ratio,
        "morphed_pitch_mean_hz": telemetry.morphed_pitch_mean_hz,
        "morphed_centroid_hz": telemetry.morphed_centroid_hz,
        "is_halted": telemetry.is_halted,
        "active_consents_count": len(voice_morphing_matrix.list_consents()),
        "timestamp": telemetry.timestamp,
    }


# ==========================================
# 3. Sign Biometric Voice Consent (Tier 1)
# ==========================================

class SignBiometricVoiceConsentArgs(BaseModel):
    target_identity_name: str = Field(
        ...,
        description="Name of the person or voice identity being authorized for neural cloning",
    )
    operator_confirmation: str = Field(
        ...,
        description="Cryptographic confirmation statement from the operator (e.g. 'I authorize voice cloning for local assistance')",
    )


def preview_sign_biometric_voice_consent(args: Dict[str, Any]) -> str:
    name = args.get("target_identity_name", "")
    return f"Cryptographically sign biometric voiceprint consent for '{name}' with SHA-256 token (Tier 1 biometric operation)."


@registry.register(
    name="sign_biometric_voice_consent",
    tier=1,
    description="Cryptographically signs biometric voiceprint consent token for neural cloning (Tier 1 biometric consent).",
    args_schema=SignBiometricVoiceConsentArgs,
    preview_fn=preview_sign_biometric_voice_consent,
    can_remember_per_folder=False,
)
def handle_sign_biometric_voice_consent(
    target_identity_name: str,
    operator_confirmation: str,
) -> Dict[str, Any]:
    record = voice_morphing_matrix.sign_consent(
        target_identity_name=target_identity_name,
        operator_confirmation=operator_confirmation,
    )
    return {
        "status": "SIGNED",
        "consent_id": record.consent_id,
        "target_identity_name": record.target_identity_name,
        "consent_token": record.consent_token,
        "signed_at": record.signed_at,
        "is_active": record.is_active,
    }


# ==========================================
# 4. Revoke Biometric Voiceprint (Tier 1)
# ==========================================

class RevokeBiometricVoiceprintArgs(BaseModel):
    consent_id: str = Field(
        ...,
        description="Unique identifier of the biometric consent to permanently revoke",
    )


def preview_revoke_biometric_voiceprint(args: Dict[str, Any]) -> str:
    cid = args.get("consent_id", "")
    return f"Permanently revoke biometric voiceprint '{cid}', purge embeddings, and fallback to base Jarvis (Tier 1 destructive operation)."


@registry.register(
    name="revoke_biometric_voiceprint",
    tier=1,
    description="Permanently revokes biometric voiceprint consent, purges matching embeddings, and resets to base Jarvis (Tier 1 revocation).",
    args_schema=RevokeBiometricVoiceprintArgs,
    preview_fn=preview_revoke_biometric_voiceprint,
    can_remember_per_folder=False,
)
def handle_revoke_biometric_voiceprint(consent_id: str) -> Dict[str, Any]:
    success = voice_morphing_matrix.revoke_consent(consent_id)
    return {
        "status": "REVOKED" if success else "NOT_FOUND",
        "consent_id": consent_id,
        "is_purged": success,
        "active_blend_ratio": 0.0,
    }
