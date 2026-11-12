"""
Phenom Dynamic Prosody & Persona Manager (VOX-03.2, VOX-03.5, SAF-02)
Modulates speech rate, pitch variance, volume, and conversational Jarvis framing
based on detected user emotion or explicit style locks.
Sub-10ms Guardian audio mute SLA.
"""

import os
import sys
import time
import random
import asyncio
from typing import Dict, Any, Optional, List, Tuple, Callable, Awaitable
from pydantic import BaseModel, Field

from services.backend.voice.emotion_classifier import emotion_classifier, EmotionType, EmotionResult
from services.backend.voice.tts import tts_engine
from services.backend.safety.guardian import guardian

VoiceStyleType = str  # "witty_jarvis", "whisper", "calm", "fast", "urgent", "normal"

# Default Prosody Profiles per Emotion
EMOTION_PROSODY_MAP: Dict[EmotionType, Dict[str, Any]] = {
    "urgent": {
        "rate": 3,
        "volume": 1.0,
        "pitch_name": "crisp_elevated",
        "prefixes": [
            "On it right away.",
            "Acknowledged. Executing immediately.",
            "Priority override engaged.",
            "Direct action dispatched."
        ]
    },
    "frustrated": {
        "rate": -1,
        "volume": 0.85,
        "pitch_name": "grounded_calming",
        "prefixes": [
            "Deep breath, Bro. Let's solve this step by step.",
            "No panic, Bro. I've got you covered.",
            "Understood. Let's untangle this methodically.",
            "Right with you. We'll get this sorted."
        ]
    },
    "excited": {
        "rate": 2,
        "volume": 1.0,
        "pitch_name": "energetic_sharp",
        "prefixes": [
            "Now that is what I call momentum, Bro!",
            "Splendid energy! Let's roll.",
            "Love the drive, Bro. Making it happen!",
            "Phenomenal! Let's get straight to it."
        ]
    },
    "focused": {
        "rate": 1,
        "volume": 0.8,
        "pitch_name": "analytical_precise",
        "prefixes": [
            "Compiling analysis.",
            "Executing technical routine.",
            "Synthesizing architecture now.",
            "Tracking precision flow."
        ]
    },
    "calm": {
        "rate": -2,
        "volume": 0.5,
        "pitch_name": "soft_gentle",
        "prefixes": [
            "Peace and quiet, Bro. Taking our time.",
            "Smooth and steady.",
            "No rush at all. Proceeding gently.",
            "Calm waters ahead."
        ]
    },
    "casual": {
        "rate": 0,
        "volume": 0.9,
        "pitch_name": "witty_british",
        "prefixes": [
            "Right you are, Bro.",
            "At your service, as always.",
            "Consider it done, Bro.",
            "Splendid, let's take a look."
        ]
    }
}

STYLE_PRESETS: Dict[str, Dict[str, Any]] = {
    "witty_jarvis": {"rate": 0, "volume": 0.9, "desc": "Witty British Jarvis banter with dynamic emotion adaptation."},
    "whisper": {"rate": -2, "volume": 0.25, "desc": "Low volume soft whisper mode for late-night sessions."},
    "calm": {"rate": -1, "volume": 0.55, "desc": "Gentle, measured scholar pace."},
    "fast": {"rate": 3, "volume": 1.0, "desc": "High-velocity brisk briefing cadence."},
    "urgent": {"rate": 4, "volume": 1.0, "desc": "Maximum priority zero-latency urgent cadence."},
    "normal": {"rate": 0, "volume": 1.0, "desc": "Standard unmodulated baseline voice."}
}

_broadcaster: Optional[Callable[[Dict[str, Any]], Awaitable[None]]] = None


def register_broadcaster(broadcaster: Callable[[Dict[str, Any]], Awaitable[None]]) -> None:
    """Registers the WebSocket broadcast callback."""
    global _broadcaster
    _broadcaster = broadcaster


def broadcast_persona_event(event_type: str, payload: Dict[str, Any]):
    """Broadcasts voice persona telemetry to connected Electron UI clients."""
    broadcaster = _broadcaster
    if not broadcaster:
        main_mod = sys.modules.get("services.backend.main")
        if main_mod:
            active_ws = getattr(main_mod, "active_websockets", None)
            if active_ws is not None and not active_ws:
                return
            if hasattr(main_mod, "broadcast_message"):
                broadcaster = main_mod.broadcast_message
    if not broadcaster:
        return
    msg = {
        "id": f"vox-{os.urandom(2).hex()}",
        "type": event_type,
        "ts": str(time.time()),
        "payload": payload
    }
    try:
        loop = asyncio.get_running_loop()
        loop.create_task(broadcaster(msg))
    except RuntimeError:
        pass


class DynamicProsodyManager:
    """
    Coordinates real-time emotion detection, speech prosody parameters, and persona voice style.
    """

    def __init__(self, tts=None):
        self.tts = tts or tts_engine
        self._locked_style: Optional[str] = None
        self._current_emotion: EmotionType = "casual"
        self._current_rate: int = 0
        self._current_volume: float = 1.0
        self._is_muted: bool = False
        self._last_prefix: str = ""

        # Register Guardian Kill Switch audio silence hook (VOX-03.5 < 10ms SLA)
        guardian.add_state_callback(self._on_guardian_state_change)

    @property
    def locked_style(self) -> Optional[str]:
        return self._locked_style

    @property
    def current_emotion(self) -> EmotionType:
        return self._current_emotion

    @property
    def is_muted(self) -> bool:
        return self._is_muted

    def set_muted(self, muted: bool):
        self._is_muted = muted
        if self._is_muted:
            self.tts.set_volume(0.0)
            if hasattr(self.tts, "stop_speech"):
                self.tts.stop_speech()
            elif hasattr(self.tts, "stop"):
                self.tts.stop()
        else:
            self.tts.set_volume(self._current_volume)
        self._broadcast_state()

    def set_style(self, style_name: Optional[str]) -> Dict[str, Any]:
        """Locks or clears a voice persona style preset."""
        if not style_name or style_name.lower() in ("none", "auto", "dynamic"):
            self._locked_style = None
            self._apply_prosody(self._current_emotion)
            return {"status": "success", "mode": "dynamic_auto", "message": "Voice persona restored to dynamic emotion adaptation."}

        s_key = style_name.lower().strip()
        if s_key not in STYLE_PRESETS:
            raise ValueError(f"Unknown voice style '{style_name}'. Valid styles: {list(STYLE_PRESETS.keys())}")

        self._locked_style = s_key
        preset = STYLE_PRESETS[s_key]
        self._current_rate = preset["rate"]
        self._current_volume = preset["volume"]
        self.tts.set_rate(self._current_rate)
        if not self._is_muted:
            self.tts.set_volume(self._current_volume)

        self._broadcast_state()
        return {
            "status": "success",
            "locked_style": self._locked_style,
            "rate": self._current_rate,
            "volume": self._current_volume,
            "description": preset["desc"]
        }

    def adjust_prosody(self, rate_delta: Optional[int] = None, volume_scale: Optional[float] = None) -> Dict[str, Any]:
        """Fine-tunes cadence rate and volume scale directly."""
        if rate_delta is not None:
            self._current_rate = max(-10, min(10, self._current_rate + int(rate_delta)))
            self.tts.set_rate(self._current_rate)

        if volume_scale is not None:
            self._current_volume = max(0.0, min(1.0, float(volume_scale)))
            if not self._is_muted:
                self.tts.set_volume(self._current_volume)

        self._broadcast_state()
        return {
            "status": "success",
            "rate": self._current_rate,
            "volume": self._current_volume,
            "message": f"Prosody adjusted: rate={self._current_rate}, volume={int(self._current_volume * 100)}%"
        }

    def reset_persona(self) -> Dict[str, Any]:
        """Resets voice persona and prosody to baseline defaults."""
        self._locked_style = None
        self._current_emotion = "casual"
        self._current_rate = 0
        self._current_volume = 1.0
        self._is_muted = False
        self.tts.set_rate(0)
        self.tts.set_volume(1.0)
        self._broadcast_state()
        return {
            "status": "success",
            "message": "Voice persona and prosody reset to baseline defaults."
        }

    def modulate_for_prompt(self, user_prompt: str) -> Tuple[str, EmotionResult, Dict[str, Any]]:
        """
        Evaluates user prompt emotion and computes adaptive TTS prosody + witty Jarvis prefix.
        Returns: (jarvis_prefix, emotion_result, prosody_dict)
        """
        em_res = emotion_classifier.classify(user_prompt)
        self._current_emotion = em_res.emotion

        # If a manual style is locked, keep locked rate and volume
        if self._locked_style:
            prefix = random.choice(EMOTION_PROSODY_MAP[self._current_emotion]["prefixes"])
            self._last_prefix = prefix
            prosody = {
                "rate": self._current_rate,
                "volume": self._current_volume,
                "locked_style": self._locked_style,
                "emotion": self._current_emotion
            }
            self._broadcast_state()
            return prefix, em_res, prosody

        # Apply dynamic emotion prosody
        prof = EMOTION_PROSODY_MAP[self._current_emotion]
        self._current_rate = prof["rate"]
        self._current_volume = prof["volume"]
        self.tts.set_rate(self._current_rate)
        if not self._is_muted:
            self.tts.set_volume(self._current_volume)

        prefix = random.choice(prof["prefixes"])
        self._last_prefix = prefix

        prosody = {
            "rate": self._current_rate,
            "volume": self._current_volume,
            "pitch_name": prof["pitch_name"],
            "emotion": self._current_emotion
        }
        self._broadcast_state()
        return prefix, em_res, prosody

    def _apply_prosody(self, emotion: EmotionType):
        prof = EMOTION_PROSODY_MAP[emotion]
        self._current_rate = prof["rate"]
        self._current_volume = prof["volume"]
        self.tts.set_rate(self._current_rate)
        if not self._is_muted:
            self.tts.set_volume(self._current_volume)

    def _on_guardian_state_change(self, new_state: str):
        """Guardian kill switch hook: immediately silences audio on halt (< 10ms SLA)."""
        if new_state == "halted":
            self._is_muted = True
            # Cut off active speech immediately and drain queue
            if hasattr(self.tts, "stop_speech"):
                self.tts.stop_speech()
            elif hasattr(self.tts, "stop"):
                self.tts.stop()
            self._current_rate = 0
            self._current_volume = 0.0
            broadcast_persona_event("VOICE_PERSONA_HALTED", {
                "muted": True,
                "reason": "guardian_killswitch",
                "ts": time.time()
            })
        elif new_state == "idle":
            self._is_muted = False
            self._current_volume = 1.0
            self.tts.set_volume(1.0)
            self._broadcast_state()

    def get_status(self) -> Dict[str, Any]:
        """Returns active voice persona and prosody telemetry."""
        return {
            "active_emotion": self._current_emotion,
            "locked_style": self._locked_style,
            "rate": self._current_rate,
            "volume": round(self._current_volume, 2),
            "is_muted": self._is_muted,
            "last_prefix": self._last_prefix,
            "available_styles": list(STYLE_PRESETS.keys())
        }

    def _broadcast_state(self):
        broadcast_persona_event("VOICE_PERSONA_UPDATED", self.get_status())


# Global singleton instance
prosody_manager = DynamicProsodyManager()
