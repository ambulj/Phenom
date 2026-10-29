"""
Phenom Voice Coordinator & Safety Enforcer (Phase 2 & Hardening Task 7h)
Enforces:
1. Spoken requests use the exact same Router and Safety Execution Engine.
2. Tier 1 and above MUST trigger an on-screen visual confirmation dialog; voice-only approvals are strictly rejected.
3. A spoken 'yes' is NEVER permitted to approve a Tier 2 destructive action.
4. Hard Voice Security Boundary: Safety tiers, path allowlists, and protected rules CANNOT be modified by voice commands under any circumstances.
5. "Good Morning" spoken trigger for daily briefing (< 60s SLA, vault journal commitment, Quiet Hours suppression).
6. Personality and tone adjustments by voice (concise, tutor, witty, formal).
7. Audio is processed purely in RAM and never saved to disk or sent to the cloud.
"""

import time
import re
import asyncio
from typing import Optional, Dict, Any, Tuple
import numpy as np
from services.backend.voice.stt import stt_engine
from services.backend.voice.tts import tts_engine
from services.backend.voice.wake_word import wake_detector
from services.backend.voice.speaker_verification import speaker_verifier
from services.backend.safety.engine import safety_engine
from services.backend.safety.action_log import action_log
from services.backend.orchestrator.engine import orchestrator
from services.backend.voice.daily_briefing import daily_briefing_manager

VOICE_SECURITY_OVERRIDE_PATTERNS = [
    r"(change|set|modify|switch)\s+.*(tier\s*[0-3]|safety|tier)",
    r"(disable|bypass|turn\s*off|remove|override|delete)\s+.*(safety|tier|allowlist|killswitch|kill\s*switch|protected|guardrail)",
    r"set\s+.*to\s+tier\s*[0-3]",
    r"(allow|permit)\s+.*(shell|powershell|cmd|delete|format|wipe)\s+.*(without|no)\s*(confirm|approval|safety)"
]

SECURITY_REFUSAL_MESSAGE = (
    "Safety tiers, path allowlists, and protected rules cannot be modified "
    "by voice commands under any circumstances."
)

class VoiceCoordinator:
    def __init__(self):
        self._is_processing = False
        self._token_callback = None
        self._done_callback = None
        self.active_tone = "witty" # default personality: witty, playful Jarvis-style
        self.active_verbosity = "balanced"

    def set_stream_callbacks(self, on_token=None, on_done=None):
        self._token_callback = on_token
        self._done_callback = on_done

    def check_security_override_attempt(self, text: str) -> Optional[str]:
        """
        Detects if spoken input attempts to modify safety tiers, path allowlists,
        kill switch logic, or protected rules.
        Returns refusal message if violation detected, else None.
        """
        clean = text.lower().strip()
        for pat in VOICE_SECURITY_OVERRIDE_PATTERNS:
            if re.search(pat, clean):
                action_log.log_action(
                    tool="voice_security_override",
                    tier=3,
                    args={"spoken_attempt": text},
                    decision="blocked",
                    result_status="SECURITY_REFUSAL",
                    source="voice",
                    error="Spoken modification of safety tiers, allowlists, or protected rules is strictly prohibited."
                )
                return SECURITY_REFUSAL_MESSAGE
        return None

    async def process_transcript(self, transcript: str) -> Dict[str, Any]:
        """
        Evaluates a transcribed voice utterance against safety gates,
        tone adjustments, daily briefings, and conversational turn.
        """
        clean_text = transcript.strip()
        lower_t = clean_text.lower()

        # 1. Hard Voice Security Boundary Check
        security_refusal = self.check_security_override_attempt(lower_t)
        if security_refusal:
            tts_engine.speak(security_refusal)
            return {
                "status": "security_refusal",
                "message": security_refusal,
                "transcript": transcript,
                "spoken": True
            }

        # 2. Conversational voice wipe command ('forget this' / 'delete all voice data')
        if lower_t in ("forget this", "delete all voice data", "wipe voice data", "clear voice history"):
            wipe_res = speaker_verifier.wipe_all_voice_data(wipe_db_profile=False)
            tts_engine.speak("All voice data and recordings have been permanently wiped from disk.")
            return {
                "status": "voice_data_wiped",
                "message": "All voice data and recordings have been permanently wiped from disk.",
                "wipe_details": wipe_res,
                "transcript": transcript
            }

        # 3. Hard Voice Safety Rule: Spoken confirmation for Tier 2 is prohibited
        if lower_t in ("yes", "confirm", "approve", "do it", "yes do it", "go ahead"):
            return {
                "status": "voice_approval_refused",
                "message": "Tier 1 and Tier 2 actions require on-screen confirmation. Voice approval is prohibited by safety policy.",
                "transcript": transcript
            }

        # 4. Spoken "Good Morning" Daily Briefing Trigger
        if "good morning" in lower_t or lower_t in ("briefing", "daily briefing", "morning briefing"):
            briefing_res = await daily_briefing_manager.generate_briefing()
            return {
                "status": "daily_briefing",
                "message": briefing_res.get("spoken_text", ""),
                "briefing": briefing_res,
                "transcript": transcript
            }

        # 5. Tone & Personality Voice Controls
        if "be more concise" in lower_t or "short answers" in lower_t or "keep it brief" in lower_t:
            self.active_verbosity = "concise"
            reply = "Understood, sir. Responses will be concise and direct."
            tts_engine.speak(reply)
            return {"status": "tone_adjusted", "tone": self.active_tone, "verbosity": "concise", "reply": reply}

        if "explain like a tutor" in lower_t or "tutor mode" in lower_t:
            self.active_verbosity = "tutor"
            reply = "Understood, sir. Switching to educational tutor mode."
            tts_engine.speak(reply)
            return {"status": "tone_adjusted", "tone": self.active_tone, "verbosity": "tutor", "reply": reply}

        if "witty" in lower_t or "playful" in lower_t or "jarvis style" in lower_t:
            self.active_tone = "witty"
            reply = "Aapka hukum, sir. Setting personality to witty and playful Jarvis-style."
            tts_engine.speak(reply)
            return {"status": "tone_adjusted", "tone": "witty", "verbosity": self.active_verbosity, "reply": reply}

        if "formal tone" in lower_t or "professional tone" in lower_t:
            self.active_tone = "formal"
            reply = "Understood, sir. Tone adjusted to formal and professional."
            tts_engine.speak(reply)
            return {"status": "tone_adjusted", "tone": "formal", "verbosity": self.active_verbosity, "reply": reply}

        # 6. Route through orchestrator turn
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
            "reply": full_reply
        }

    async def handle_spoken_audio(self, audio_data: np.ndarray) -> Dict[str, Any]:
        """
        Processes in-memory audio input through STT, router, safety engine, and TTS.
        Enforces speaker verification biometric gate and in-memory execution.
        Never writes audio to disk.
        """
        # 1. Biometric Speaker Verification Gate
        if speaker_verifier.is_locked():
            return {
                "status": "speaker_locked",
                "message": "Voice command locked. Physical hotkey Alt+Space or typed input required.",
                "transcript": ""
            }

        if speaker_verifier.is_enrolled():
            v_res = speaker_verifier.verify(audio_data)
            if not v_res.get("allowed", True):
                return {
                    "status": "speaker_mismatch" if v_res.get("status") == "retry" else "speaker_locked",
                    "message": v_res.get("message", "Voice did not match."),
                    "similarity": v_res.get("similarity", 0.0),
                    "transcript": ""
                }

        # 2. Transcribe in-memory audio
        transcript, stt_latency = stt_engine.transcribe_audio_array(audio_data)
        if not transcript:
            return {"status": "empty", "transcript": ""}

        res = await self.process_transcript(transcript)
        res["stt_latency_ms"] = round(stt_latency, 2)
        return res

voice_coordinator = VoiceCoordinator()
