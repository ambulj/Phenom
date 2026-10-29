"""
Phenom Cloud Hindi TTS Client (Sarvam AI Bulbul)
Implements natural Indian-language TTS synthesis for non-private replies.
Strict Privacy Guarantee:
- Evaluates text through privacy_classifier.is_private() BEFORE transmission.
- Private content is NEVER sent to Sarvam AI; falls back to local SAPI voice.
- Audio is decoded in-memory (RAM only); 0 bytes written to disk.
- Free-tier rate limits (HTTP 429) gracefully fall back to local voice with one-time alert.
"""

import base64
import io
import os
import re
import logging
from typing import Optional, Dict, Any
import httpx

from services.backend.router.privacy import privacy_classifier
from services.backend.remote.credentials import get_credential

logger = logging.getLogger("phenom.voice.cloud_tts")

SARVAM_TTS_URL = "https://api.sarvam.ai/text-to-speech"
CREDENTIAL_KEY = "Phenom/sarvam-api-key"

# Hindi & Hinglish detection patterns
DEVANAGARI_REGEX = re.compile(r"[\u0900-\u097F]")
HINGLISH_KEYWORDS = {
    "aap", "tum", "main", "hum", "hai", "hain", "kya", "kyun", "kaise", "kaha", 
    "nahi", "karo", "karna", "baat", "batao", "shukriya", "dhanyawad", "theek",
    "bilkul", "zaroor", "samajh", "aaj", "kal", "ab", "kab", "yeh", "woh"
}

class SarvamTTSClient:
    def __init__(self, api_key: Optional[str] = None):
        self._api_key = api_key
        self._quota_alert_fired = False

    def get_api_key(self) -> Optional[str]:
        if self._api_key:
            return self._api_key
        # Check environment variable first (for test harnesses)
        env_key = os.environ.get("SARVAM_API_KEY")
        if env_key:
            return env_key
        # Check Windows Credential Manager
        try:
            return get_credential("sarvam-api-key")
        except Exception:
            return None

    def is_hindi_or_hinglish(self, text: str) -> bool:
        """Determines if text contains Hindi (Devanagari) or conversational Hinglish vocabulary."""
        if DEVANAGARI_REGEX.search(text):
            return True
        # Check word token overlap with Hinglish lexicon
        tokens = set(re.findall(r"\b[a-zA-Z]+\b", text.lower()))
        matching = tokens.intersection(HINGLISH_KEYWORDS)
        return len(matching) >= 2 or (len(matching) >= 1 and len(tokens) <= 5)

    def synthesize(self, text: str, is_shareable: bool = False, speaker: str = "arvind") -> Optional[bytes]:
        """
        Synthesizes Hindi/Hinglish speech using Sarvam Bulbul API.
        Enforces strict pre-flight privacy check and in-memory audio return.
        Returns WAV audio bytes if successful, None if bypassed or on fallback.
        """
        clean_text = text.strip()
        if not clean_text:
            return None

        # 1. Privacy Enforcement: Strictly local for private data or detected PII/secrets
        if not is_shareable and privacy_classifier.is_private(clean_text):
            logger.info("Sarvam Cloud TTS bypassed: text classified as private. Falling back to local voice.")
            return None
        elif is_shareable:
            # Even when marked shareable, never send PII or credentials
            pii = privacy_classifier.detect_pii_or_secrets(clean_text)
            if pii:
                logger.warning(f"Sarvam Cloud TTS blocked: PII detected in shareable text ({pii[0]}).")
                return None

        # 2. Check if text is Hindi or Hinglish
        if not self.is_hindi_or_hinglish(clean_text):
            return None

        # 3. Retrieve API Key
        key = self.get_api_key()
        if not key:
            logger.debug("Sarvam API key not configured; falling back to local voice.")
            return None

        # 4. Invoke Sarvam Bulbul API
        headers = {
            "api-subscription-key": key,
            "Content-Type": "application/json"
        }
        payload = {
            "inputs": [clean_text],
            "target_language_code": "hi-IN",
            "speaker": speaker,
            "pitch": 0,
            "pace": 1.0,
            "loudness": 1.5,
            "speech_sample_rate": 16000,
            "enable_preprocessing": True,
            "model": "bulbul:v1"
        }

        try:
            with httpx.Client(timeout=10.0) as client:
                resp = client.post(SARVAM_TTS_URL, headers=headers, json=payload)

            if resp.status_code == 200:
                data = resp.json()
                audios = data.get("audios", [])
                if audios:
                    # In-memory base64 decode (RAM only)
                    wav_bytes = base64.b64decode(audios[0])
                    return wav_bytes
                return None
            elif resp.status_code == 429:
                if not self._quota_alert_fired:
                    logger.warning("Sarvam TTS free quota limit reached (HTTP 429). Falling back to local voice.")
                    self._quota_alert_fired = True
                return None
            else:
                logger.error(f"Sarvam TTS failed with HTTP {resp.status_code}: {resp.text}")
                return None
        except Exception as e:
            logger.error(f"Sarvam TTS request exception: {e}")
            return None

    def reset_quota_alert(self):
        self._quota_alert_fired = False

sarvam_tts = SarvamTTSClient()
