"""
Phenom Voice Modulator & Presence Awareness Engine
Dynamically adjusts TTS volume, speech cadence (rate), and conversational tone
to match the user's active application context and AssistantMode (Work, Study, Chill, Deep Focus).
"""

import logging
from typing import Optional, Dict, Any
from services.backend.modes.mode_manager import mode_manager, AssistantMode
from services.backend.voice.tts import tts_engine

logger = logging.getLogger("phenom.voice.modulator")

VOICE_MODE_PRESETS: Dict[AssistantMode, Dict[str, Any]] = {
    AssistantMode.WORK: {
        "volume_scale": 1.0,
        "cadence_rate": 1,  # Crisp, slightly brisk Jarvis cadence
        "tone_name": "Crisp Executive",
        "description": "High productivity: 100% volume, brisk cadence, clear executive tone.",
        "muted": False,
    },
    AssistantMode.STUDY: {
        "volume_scale": 0.35,
        "cadence_rate": 0,  # Measured, calm scholar pace
        "tone_name": "Gentle Contemplative",
        "description": "Deep study: 35% gentle volume, measured pace, thoughtful tone.",
        "muted": False,
    },
    AssistantMode.CHILL: {
        "volume_scale": 0.65,
        "cadence_rate": 0,  # Relaxed conversational pace
        "tone_name": "Witty Playful",
        "description": "Chill / Gaming: 65% relaxed volume, witty banter cadence.",
        "muted": False,
    },
    AssistantMode.DEEP_FOCUS: {
        "volume_scale": 0.0,
        "cadence_rate": 0,
        "tone_name": "Silent Focus",
        "description": "Deep focus: 0% volume (muted audio), strictly silent.",
        "muted": True,
    },
}


class VoiceModulator:
    """
    Manages dynamic speech parameter modulation tied to user presence and application context.
    """

    def __init__(self, mode_mgr=None, tts=None):
        self.mode_mgr = mode_mgr or mode_manager
        self.tts = tts or tts_engine
        self._override_volume: Optional[float] = None
        self._override_rate: Optional[int] = None
        self._override_mode: Optional[AssistantMode] = None

    def get_current_mode(self) -> AssistantMode:
        """Returns the active mode considering overrides."""
        if self._override_mode is not None:
            return self._override_mode
        try:
            return self.mode_mgr.current_mode
        except Exception:
            return AssistantMode.WORK

    def get_effective_profile(self) -> Dict[str, Any]:
        """Calculates effective volume, rate, and tone preset."""
        mode = self.get_current_mode()
        preset = VOICE_MODE_PRESETS.get(mode, VOICE_MODE_PRESETS[AssistantMode.WORK]).copy()

        effective_volume = self._override_volume if self._override_volume is not None else preset["volume_scale"]
        effective_rate = self._override_rate if self._override_rate is not None else preset["cadence_rate"]

        effective_volume = max(0.0, min(1.0, float(effective_volume)))
        effective_rate = max(-10, min(10, int(effective_rate)))

        return {
            "mode": mode.value,
            "volume_scale": effective_volume,
            "cadence_rate": effective_rate,
            "tone_name": preset["tone_name"],
            "description": preset["description"],
            "is_muted": effective_volume <= 0.0 or preset.get("muted", False),
            "has_overrides": self.has_overrides(),
        }

    def has_overrides(self) -> bool:
        return (
            self._override_volume is not None
            or self._override_rate is not None
            or self._override_mode is not None
        )

    def set_override(
        self,
        volume: Optional[float] = None,
        rate: Optional[int] = None,
        mode: Optional[AssistantMode] = None,
    ):
        """Sets manual overrides for volume, speech rate, or mode."""
        if volume is not None:
            self._override_volume = max(0.0, min(1.0, float(volume)))
        if rate is not None:
            self._override_rate = max(-10, min(10, int(rate)))
        if mode is not None:
            self._override_mode = mode
        self.apply_to_tts()

    def clear_overrides(self):
        """Clears all manual overrides and restores dynamic context modulation."""
        self._override_volume = None
        self._override_rate = None
        self._override_mode = None
        self.apply_to_tts()

    def apply_to_tts(self) -> Dict[str, Any]:
        """Applies effective volume scale and cadence rate directly to TTSEngine."""
        profile = self.get_effective_profile()
        try:
            if hasattr(self.tts, "set_volume"):
                self.tts.set_volume(profile["volume_scale"])
            if hasattr(self.tts, "set_rate"):
                self.tts.set_rate(profile["cadence_rate"])
        except Exception as e:
            logger.warning("Failed to apply profile to TTS: %s", e)
        return profile

    def get_status(self) -> Dict[str, Any]:
        """Returns comprehensive status representation."""
        profile = self.get_effective_profile()
        return {
            "effective_profile": profile,
            "overrides": {
                "volume": self._override_volume,
                "rate": self._override_rate,
                "mode": self._override_mode.value if self._override_mode else None,
            },
        }


# Global singleton instance
voice_modulator = VoiceModulator()
