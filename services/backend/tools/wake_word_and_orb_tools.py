"""
Phenom Wake-Word, Streaming Whisper & Particle Orb Tools (VOX-04.1, VOX-04.2, ORB-02.1, ORB-02.2, SAF-01)
Milestone 18.0 Phase 3 Deliverable

Safety Layer Endpoints:
- get_wake_word_status (Tier 0): Read-only status of wake-word listener & streaming whisper
- set_wake_word_sensitivity (Tier 1): Adjusts wake detection threshold with preview
- trigger_manual_wake (Tier 0): Triggers wake activation or push-to-talk listening
- set_orb_emotion_preset (Tier 1): Modulates particle orb visual emotion state
- mute_audio_input (Tier 0): Mutes or unmutes microphone input streams
"""

from typing import Dict, Any, Optional
from pydantic import BaseModel, Field

from services.backend.safety.registry import registry
from services.backend.safety.guardian import guardian
from services.backend.voice.wake_word_listener import wake_word_listener
from services.backend.voice.streaming_whisper import streaming_whisper

# ---------------- In-memory Orb Emotion State ----------------
_orb_emotion_state = {
    "current_emotion": "idle",
    "brightness": 0.90,
    "speed": 0.35,
}

VALID_EMOTIONS = ["urgent", "focused", "chill", "idle", "speaking"]


# ---------------- 1. GET WAKE WORD STATUS ----------------

class GetWakeWordStatusArgs(BaseModel):
    """No arguments required."""
    pass


def preview_get_wake_word_status(args: Dict[str, Any]) -> str:
    return "[Tier 0] Read wake-word listener status, sensitivity, and streaming whisper metrics (Read-only)"


@registry.register(
    name="get_wake_word_status",
    tier=0,
    description="Returns real-time status of on-device wake-word listener, sensitivity, and streaming Whisper engine",
    args_schema=GetWakeWordStatusArgs,
    preview_fn=preview_get_wake_word_status,
)
def get_wake_word_status(**kwargs) -> Dict[str, Any]:
    return {
        "status": "ok",
        "wake_listener": wake_word_listener.get_status(),
        "streaming_whisper": streaming_whisper.get_status(),
        "orb_emotion": _orb_emotion_state,
    }


# ---------------- 2. SET WAKE WORD SENSITIVITY ----------------

class SetWakeWordSensitivityArgs(BaseModel):
    sensitivity: float = Field(
        ge=0.0,
        le=1.0,
        description="Wake-word detection sensitivity scale from 0.0 (conservative) to 1.0 (highly sensitive)",
    )


def preview_set_wake_word_sensitivity(args: Dict[str, Any]) -> str:
    val = args.get("sensitivity", 0.5)
    return f"[Tier 1] Set Wake-Word Sensitivity: Adjust local keyword detection sensitivity to {val:.2f}"


@registry.register(
    name="set_wake_word_sensitivity",
    tier=1,
    description="Configures detection sensitivity for local wake-word listener ('Hey Phenom', 'Phenom')",
    args_schema=SetWakeWordSensitivityArgs,
    preview_fn=preview_set_wake_word_sensitivity,
)
def set_wake_word_sensitivity(sensitivity: float, **kwargs) -> Dict[str, Any]:
    if guardian.is_halted:
        raise RuntimeError("Operation halted by Guardian Kill Switch")
    wake_word_listener.set_sensitivity(sensitivity)
    return {
        "status": "success",
        "sensitivity": wake_word_listener.sensitivity,
        "message": f"Wake-word sensitivity configured to {wake_word_listener.sensitivity:.2f}",
    }


# ---------------- 3. TRIGGER MANUAL WAKE ----------------

class TriggerManualWakeArgs(BaseModel):
    phrase: Optional[str] = Field(
        default="hey phenom",
        description="Wake phrase keyword to simulate ('hey phenom', 'phenom', 'hey jarvis')",
    )


def preview_trigger_manual_wake(args: Dict[str, Any]) -> str:
    p = args.get("phrase", "hey phenom")
    return f"[Tier 0] Trigger Manual Wake: Activate assistant wake-up with phrase '{p}'"


@registry.register(
    name="trigger_manual_wake",
    tier=0,
    description="Manually activates wake-word detection or triggers Push-to-Talk listening state",
    args_schema=TriggerManualWakeArgs,
    preview_fn=preview_trigger_manual_wake,
)
def trigger_manual_wake(phrase: Optional[str] = "hey phenom", **kwargs) -> Dict[str, Any]:
    if guardian.is_halted:
        raise RuntimeError("Operation halted by Guardian Kill Switch")
    success = wake_word_listener.trigger_manual_wake(phrase)
    return {
        "status": "triggered" if success else "suppressed",
        "phrase": phrase,
        "wake_listener_active": wake_word_listener.is_listening,
    }


# ---------------- 4. SET ORB EMOTION PRESET ----------------

class SetOrbEmotionPresetArgs(BaseModel):
    emotion: str = Field(
        description="Emotion shader preset ('urgent', 'focused', 'chill', 'idle', 'speaking')",
    )


def preview_set_orb_emotion_preset(args: Dict[str, Any]) -> str:
    em = args.get("emotion", "idle")
    return f"[Tier 1] Set Orb Emotion: Transition 3D Particle Orb shader color and dynamics to '{em}'"


@registry.register(
    name="set_orb_emotion_preset",
    tier=1,
    description="Modulates the emotional shader preset and visual resonance of the Three.js 3D Particle Orb",
    args_schema=SetOrbEmotionPresetArgs,
    preview_fn=preview_set_orb_emotion_preset,
)
def set_orb_emotion_preset(emotion: str, **kwargs) -> Dict[str, Any]:
    if guardian.is_halted:
        raise RuntimeError("Operation halted by Guardian Kill Switch")
    em = emotion.lower().strip()
    if em not in VALID_EMOTIONS:
        raise ValueError(f"Invalid emotion '{emotion}'. Valid presets: {VALID_EMOTIONS}")

    _orb_emotion_state["current_emotion"] = em
    if em == "urgent":
        _orb_emotion_state["brightness"] = 1.3
        _orb_emotion_state["speed"] = 3.0
    elif em == "focused":
        _orb_emotion_state["brightness"] = 1.1
        _orb_emotion_state["speed"] = 1.5
    elif em == "chill":
        _orb_emotion_state["brightness"] = 0.75
        _orb_emotion_state["speed"] = 0.2
    elif em == "speaking":
        _orb_emotion_state["brightness"] = 1.2
        _orb_emotion_state["speed"] = 2.2
    else:  # idle
        _orb_emotion_state["brightness"] = 0.9
        _orb_emotion_state["speed"] = 0.35

    return {
        "status": "success",
        "current_emotion": em,
        "config": dict(_orb_emotion_state),
    }


# ---------------- 5. MUTE AUDIO INPUT ----------------

class MuteAudioInputArgs(BaseModel):
    muted: bool = Field(description="True to mute microphone input; False to unmute")


def preview_mute_audio_input(args: Dict[str, Any]) -> str:
    m = args.get("muted", True)
    action = "Mute" if m else "Unmute"
    return f"[Tier 0] {action} Audio Input: Immediately {'silence' if m else 'enable'} local microphone streams"


@registry.register(
    name="mute_audio_input",
    tier=0,
    description="Mutes or unmutes local microphone audio input across wake-word detector and streaming Whisper",
    args_schema=MuteAudioInputArgs,
    preview_fn=preview_mute_audio_input,
)
def mute_audio_input(muted: bool, **kwargs) -> Dict[str, Any]:
    wake_word_listener.set_muted(muted)
    streaming_whisper.set_muted(muted)
    return {
        "status": "success",
        "muted": muted,
        "wake_listener_muted": wake_word_listener.is_muted,
    }
