import time
import uuid
from collections import deque
from typing import Optional, List, Dict, Any

from services.backend.schemas.voice_action import (
    VoiceKernelState,
    IntentType,
    VoiceChunkMetadata,
    DispatchedActionRecord,
    VoiceActionKernelStatus,
)
from services.backend.voice_action.intent_parser import StreamingIntentParser


class StreamingVoiceActionKernel:
    """
    Ultra-low latency streaming voice-to-action kernel.
    Integrates streaming VAD, acoustic noise calibration, real-time intent parsing,
    and sub-10ms synchronous Guardian disengagement.
    """

    def __init__(self, max_buffer_size: int = 200):
        self._state: VoiceKernelState = VoiceKernelState.IDLE
        self._is_listening: bool = False
        self._active_session_id: Optional[str] = None
        self._noise_floor_rms: float = 0.05
        self._vad_threshold: float = 0.50
        self._barge_in_sensitivity: float = 0.80

        # In-memory transient bounded ring buffer (Rule 4: Zero audio persistence)
        self._chunk_buffer: deque = deque(maxlen=max_buffer_size)
        self._recent_actions: deque = deque(maxlen=50)
        self._total_dispatched: int = 0

        self._intent_parser = StreamingIntentParser()

    @property
    def state(self) -> VoiceKernelState:
        return self._state

    @property
    def is_listening(self) -> bool:
        return self._is_listening

    def start_session(self, session_id: Optional[str] = None) -> str:
        """Starts a live streaming voice session."""
        if self._state == VoiceKernelState.HALTED:
            raise PermissionError("Guardian kill switch is engaged. Cannot start voice session.")

        self._active_session_id = session_id or f"vox-{uuid.uuid4().hex[:8]}"
        self._is_listening = True
        self._state = VoiceKernelState.LISTENING
        return self._active_session_id

    def stop_session(self) -> None:
        """Stops the active voice session and clears transient buffers."""
        self._is_listening = False
        self._active_session_id = None
        if self._state != VoiceKernelState.HALTED:
            self._state = VoiceKernelState.IDLE
        self._chunk_buffer.clear()

    def configure(
        self,
        vad_threshold: Optional[float] = None,
        noise_floor_rms: Optional[float] = None,
        barge_in_sensitivity: Optional[float] = None,
    ) -> Dict[str, float]:
        """Configures acoustic and VAD thresholds."""
        if self._state == VoiceKernelState.HALTED:
            raise PermissionError("Guardian kill switch is engaged.")

        if vad_threshold is not None:
            self._vad_threshold = max(0.0, min(1.0, vad_threshold))
        if noise_floor_rms is not None:
            self._noise_floor_rms = max(0.0, min(1.0, noise_floor_rms))
        if barge_in_sensitivity is not None:
            self._barge_in_sensitivity = max(0.0, min(1.0, barge_in_sensitivity))

        return {
            "vad_threshold": self._vad_threshold,
            "noise_floor_rms": self._noise_floor_rms,
            "barge_in_sensitivity": self._barge_in_sensitivity,
        }

    def ingest_chunk(
        self,
        rms_energy: float,
        speech_prob: float,
        transcript_text: Optional[str] = None,
        duration_ms: float = 30.0,
    ) -> Dict[str, Any]:
        """
        Ingests a streaming audio frame with VAD telemetry.
        Triggers instant intent parsing if transcript is present.
        """
        start_time = time.time()

        if self._state == VoiceKernelState.HALTED:
            raise PermissionError("Guardian kill switch is engaged. Voice ingest blocked.")

        chunk_meta = VoiceChunkMetadata(
            chunk_id=f"chk-{uuid.uuid4().hex[:6]}",
            rms_energy=rms_energy,
            speech_prob=speech_prob,
            duration_ms=duration_ms,
            timestamp=start_time,
        )
        self._chunk_buffer.append(chunk_meta)

        # Dynamic noise floor calibration when silent
        if speech_prob < 0.20 and rms_energy < 0.15:
            self._noise_floor_rms = 0.95 * self._noise_floor_rms + 0.05 * rms_energy

        # Detect speech presence
        is_speech = (speech_prob >= self._vad_threshold) and (rms_energy > self._noise_floor_rms * 1.2)

        dispatched_record: Optional[DispatchedActionRecord] = None

        if transcript_text:
            self._state = VoiceKernelState.TRANSCRIBING

            # Parse intent through safety rules
            intent_type, tool_name, confidence = self._intent_parser.parse(transcript_text)

            latency_ms = (time.time() - start_time) * 1000.0

            if intent_type == IntentType.INTERRUPTION:
                self._state = VoiceKernelState.BARGED_IN
                dispatched_record = DispatchedActionRecord(
                    action_id=f"act-{uuid.uuid4().hex[:8]}",
                    raw_transcript=transcript_text,
                    matched_intent=intent_type,
                    tool_name=None,
                    confidence=confidence,
                    latency_ms=latency_ms,
                    status="barged_in",
                    timestamp=time.time(),
                )
            else:
                self._state = VoiceKernelState.DISPATCHING
                dispatched_record = DispatchedActionRecord(
                    action_id=f"act-{uuid.uuid4().hex[:8]}",
                    raw_transcript=transcript_text,
                    matched_intent=intent_type,
                    tool_name=tool_name,
                    confidence=confidence,
                    latency_ms=latency_ms,
                    status="dispatched",
                    timestamp=time.time(),
                )
                self._total_dispatched += 1

            self._recent_actions.appendleft(dispatched_record)
        elif is_speech:
            self._state = VoiceKernelState.LISTENING
        else:
            if self._state not in [VoiceKernelState.DISPATCHING, VoiceKernelState.BARGED_IN]:
                self._state = VoiceKernelState.IDLE if not self._is_listening else VoiceKernelState.LISTENING

        return {
            "chunk_id": chunk_meta.chunk_id,
            "is_speech": is_speech,
            "state": self._state.value,
            "dispatched_action": dispatched_record.model_dump() if dispatched_record else None,
        }

    def abort_action(self, action_id: str) -> bool:
        """Aborts a pending or active voice action."""
        for action in self._recent_actions:
            if action.action_id == action_id:
                action.status = "aborted"
                return True
        return False

    def get_status(self) -> VoiceActionKernelStatus:
        """Returns the current state and telemetry of the voice kernel."""
        return VoiceActionKernelStatus(
            state=self._state,
            is_listening=self._is_listening,
            noise_floor_rms=round(self._noise_floor_rms, 4),
            vad_threshold=round(self._vad_threshold, 4),
            active_session_id=self._active_session_id,
            total_dispatched=self._total_dispatched,
            recent_actions=list(self._recent_actions),
        )

    def halt(self) -> None:
        """
        Synchronous Guardian kill switch halt (< 10ms SLA).
        Instantly halts capture, drops all transient chunk buffers, and locks state.
        """
        self._state = VoiceKernelState.HALTED
        self._is_listening = False
        self._active_session_id = None
        self._chunk_buffer.clear()
        for action in self._recent_actions:
            if action.status in ["dispatched", "barged_in"]:
                action.status = "guardian_halted"

    def reset(self) -> None:
        """Resets the voice kernel to IDLE after Guardian resume."""
        self._state = VoiceKernelState.IDLE
        self._is_listening = False
        self._active_session_id = None
        self._chunk_buffer.clear()
