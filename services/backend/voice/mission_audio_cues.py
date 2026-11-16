"""
Mission Audio Cues & Earcon Telemetry (Phase 47-05, ROUTER-04).
Generates subtle non-intrusive auditory chimes and spoken milestone updates
during autonomous mission execution.
"""

from enum import Enum
from typing import Dict, Any, Optional
from pydantic import BaseModel, Field


class MissionAudioEvent(str, Enum):
    MISSION_STARTED = "mission_started"
    STEP_COMPLETED = "step_completed"
    STEP_FAILED = "step_failed"
    CIRCUIT_BREAKER_TRIPPED = "circuit_breaker_tripped"
    KILL_SWITCH_HALTED = "kill_switch_halted"
    MISSION_COMPLETED = "mission_completed"


class EarconPayload(BaseModel):
    """Audio cue event descriptor for desktop and sound system playback."""
    event: MissionAudioEvent
    sound_file: str = Field(..., description="Sound asset identifier or filename")
    haptic_pattern: Optional[str] = Field(default=None, description="Optional vibration pattern identifier")
    spoken_summary: Optional[str] = Field(default=None, description="Short TTS verbal update")


class MissionAudioCues:
    """Manages audio earcon mapping and milestone speech synthesis generation."""

    EARCON_MAP = {
        MissionAudioEvent.MISSION_STARTED: "chime_mission_start.wav",
        MissionAudioEvent.STEP_COMPLETED: "chime_step_success.wav",
        MissionAudioEvent.STEP_FAILED: "chime_step_fail.wav",
        MissionAudioEvent.CIRCUIT_BREAKER_TRIPPED: "alert_circuit_breaker.wav",
        MissionAudioEvent.KILL_SWITCH_HALTED: "alert_guardian_halt.wav",
        MissionAudioEvent.MISSION_COMPLETED: "chime_mission_complete.wav",
    }

    def __init__(self):
        pass

    def get_earcon(
        self,
        event: MissionAudioEvent,
        step_title: Optional[str] = None,
        percent: Optional[int] = None
    ) -> EarconPayload:
        """Constructs an earcon audio cue payload with optional spoken announcement."""
        sound_file = self.EARCON_MAP.get(event, "chime_step_success.wav")
        spoken = self.generate_verbal_update(event, step_title, percent)

        return EarconPayload(
            event=event,
            sound_file=sound_file,
            spoken_summary=spoken
        )

    def generate_verbal_update(
        self,
        event: MissionAudioEvent,
        step_title: Optional[str] = None,
        percent: Optional[int] = None
    ) -> Optional[str]:
        """Synthesizes concise spoken milestone lines in Phenom's Jarvis-style voice."""
        if event == MissionAudioEvent.MISSION_STARTED:
            return "Mission initiated. Executing autonomous plan."
        elif event == MissionAudioEvent.STEP_COMPLETED:
            if step_title and percent is not None:
                return f"{step_title} complete. Progress at {percent} percent."
            return "Step complete."
        elif event == MissionAudioEvent.STEP_FAILED:
            return f"Step encountered an issue. Initiating self-reflective repair."
        elif event == MissionAudioEvent.CIRCUIT_BREAKER_TRIPPED:
            return "Circuit breaker tripped. Pausing for operator review."
        elif event == MissionAudioEvent.KILL_SWITCH_HALTED:
            return "Emergency halt. All operations frozen."
        elif event == MissionAudioEvent.MISSION_COMPLETED:
            return "Mission accomplished, boss. All steps verified."
        return None


# Global singleton instance
mission_audio_cues = MissionAudioCues()
