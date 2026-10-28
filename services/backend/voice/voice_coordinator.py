"""
Phenom Voice Coordinator & Safety Enforcer
Enforces Phase 2 Safety Rules:
1. Spoken requests use the exact same Router and Safety Execution Engine.
2. Tier 1 and above MUST trigger an on-screen visual confirmation dialog; voice-only approvals are strictly rejected.
3. A spoken 'yes' is NEVER permitted to approve a Tier 2 destructive action.
4. Spoken output is concise; long text is summarized for voice while full detail goes to the chat panel.
5. Audio is processed purely in RAM and never saved to disk or sent to the cloud.
"""

import time
import asyncio
from typing import Optional, Dict, Any, Tuple
import numpy as np
from services.backend.voice.stt import stt_engine
from services.backend.voice.tts import tts_engine
from services.backend.voice.wake_word import wake_detector
from services.backend.safety.engine import safety_engine
from services.backend.orchestrator.engine import orchestrator

class VoiceCoordinator:
    def __init__(self):
        self._is_processing = False
        self._token_callback = None
        self._done_callback = None

    def set_stream_callbacks(self, on_token=None, on_done=None):
        self._token_callback = on_token
        self._done_callback = on_done

    async def handle_spoken_audio(self, audio_data: np.ndarray) -> Dict[str, Any]:
        """
        Processes in-memory audio input through STT, router, safety engine, and TTS.
        Never writes audio to disk.
        """
        # 1. Transcribe in-memory audio
        transcript, stt_latency = stt_engine.transcribe_audio_array(audio_data)
        if not transcript:
            return {"status": "empty", "transcript": ""}

        # 2. Hard Voice Safety Rule: Spoken confirmation for Tier 2 is prohibited
        lower_t = transcript.lower().strip()
        if lower_t in ("yes", "confirm", "approve", "do it", "yes do it", "go ahead"):
            # Check if there is a pending confirmation
            # Disallow voice-only approval for Tier 2 destructive actions!
            return {
                "status": "voice_approval_refused",
                "message": "Tier 1 and Tier 2 actions require on-screen confirmation. Voice approval is prohibited by safety policy.",
                "transcript": transcript
            }

        # 3. Route through orchestrator turn
        tokens = []
        sentence_buffer = []
        sentences_spoken = 0
        max_spoken_sentences = 2
        summarized_for_voice = False
        
        async for event in orchestrator.run_conversation_turn(
            prompt=transcript,
            manual_privacy_override=None
        ):
            etype = event.get("type")
            if etype == "chat.token":
                token = event["payload"]["token"]
                tokens.append(token)
                if self._token_callback:
                    try:
                        await self._token_callback(token)
                    except Exception:
                        pass
                # Stream speech sentence-by-sentence up to max_spoken_sentences
                if not summarized_for_voice:
                    sentence = tts_engine.feed_token(token, sentence_buffer)
                    if sentence:
                        sentences_spoken += 1
                        if sentences_spoken >= max_spoken_sentences:
                            summarized_for_voice = True
                            tts_engine.speak("I've placed the complete details in your chat window, sir.")
            elif etype == "chat.done":
                if not summarized_for_voice:
                    tts_engine.flush_buffer(sentence_buffer)
                if self._done_callback:
                    try:
                        await self._done_callback("".join(tokens))
                    except Exception:
                        pass

        full_reply = "".join(tokens)
        return {
            "status": "success",
            "transcript": transcript,
            "reply": full_reply,
            "stt_latency_ms": round(stt_latency, 2)
        }

voice_coordinator = VoiceCoordinator()
