"""
Phenom Cloud Hindi & Hinglish TTS Client (Sarvam AI Bulbul v4-flash & v3)
Implements natural Indian-language TTS synthesis for non-private replies.
Strict Privacy Guarantee:
- Evaluates text through privacy_classifier.is_private() BEFORE transmission.
- Private content is NEVER sent to Sarvam AI; falls back to local voice.
- Audio is decoded in-memory (RAM only); 0 bytes written to disk.
- Free-tier rate limits (HTTP 429) & exhausted credits (402) gracefully fall back to offline voice.
- Credit Conservation: Short trivial pings (<4 words) and raw code blocks are handled locally to save credits.
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

# V4-Flash Conversational Speaker Mapping
V4_FLASH_SPEAKERS = {
    "kabir": "kabir_hi_conversational",
    "shubh": "shubh_enhi_companion",
    "aditya": "aditya_hi_conversational",
    "priya": "sanchita_hi_assistant",
    "simran": "simran_enhi_companion",
    "ishita": "ishita_enhi_companion",
    "pooja": "pooja_gu_conversational",
    "rahul": "rahul_hi_conversational",
    "amit": "amit_hi_conversational",
    "dev": "dev_en_conversational",
    "ratan": "ratan_hi_conversational",
    "ashutosh": "ashutosh_hi_conversational",
    "kavya": "kavya_hi_conversational"
}

# Standard Bulbul v3 Speakers
VALID_V3_SPEAKERS = [
    "shubh", "aditya", "rahul", "rohan", "amit", "dev", "ratan",
    "varun", "manan", "sumit", "kabir", "aayan", "ashutosh", "advait",
    "priya", "pooja", "simran", "kavya", "ishita", "shreya", "roopa", "ritu", "neha"
]

DEVANAGARI_REGEX = re.compile(r"[\u0900-\u097F]")
HINGLISH_KEYWORDS = {
    "aap", "tum", "main", "hum", "hai", "hain", "kya", "kyun", "kaise", "kaha", 
    "nahi", "karo", "karna", "baat", "batao", "shukriya", "dhanyawad", "theek",
    "bilkul", "zaroor", "samajh", "aaj", "kal", "ab", "kab", "yeh", "woh",
    "sorted", "scene", "phod", "bata", "bhai", "yaar", "chal", "accha", "sahi"
}

class SarvamTTSClient:
    def __init__(self, api_key: Optional[str] = None):
        self._api_key = api_key
        self._quota_alert_fired = False
        self._quota_exhausted = False

    def get_api_key(self) -> Optional[str]:
        if self._api_key:
            return self._api_key
        env_key = os.environ.get("SARVAM_API_KEY")
        if env_key:
            return env_key
        try:
            return get_credential("sarvam-api-key")
        except Exception:
            return None

    def is_hindi_or_hinglish(self, text: str) -> bool:
        """Determines if text contains Hindi (Devanagari) or conversational Hinglish vocabulary."""
        if DEVANAGARI_REGEX.search(text):
            return True
        tokens = set(re.findall(r"\b[a-zA-Z]+\b", text.lower()))
        matching = tokens.intersection(HINGLISH_KEYWORDS)
        return len(matching) >= 1 or len(tokens) <= 8

    def can_synthesize(self, text: str) -> bool:
        """
        Credit efficiency guard:
        - Skips cloud TTS if quota exhausted.
        - Skips trivial 1-3 word system pings ('Done', 'Saved', 'OK') to conserve API quota.
        - Skips raw URLs, stack traces, and code blocks.
        """
        if self._quota_exhausted:
            return False

        if not self.get_api_key():
            return False

        clean = text.strip()
        words = clean.split()
        if len(words) < 4:
            # Conserve cloud quota for full conversational sentences
            return False

        # If text looks like a raw URL or code traceback, save credits
        if clean.startswith("http://") or clean.startswith("https://") or "Traceback (most recent call last)" in clean:
            return False

        return True

    def synthesize(
        self,
        text: str,
        is_shareable: bool = False,
        speaker: str = "kabir",
        model: str = "bulbul:v4-flash"
    ) -> Optional[bytes]:
        """
        Synthesizes speech using Sarvam Bulbul v4-flash (or v3).
        Enforces strict privacy and quota failover to local voice.
        """
        clean_text = text.strip()
        if not clean_text or self._quota_exhausted:
            return None

        # 1. Privacy Enforcement
        if not is_shareable and privacy_classifier.is_private(clean_text):
            logger.info("Sarvam Cloud TTS bypassed: text classified as private. Falling back to local voice.")
            return None
        elif is_shareable:
            pii = privacy_classifier.detect_pii_or_secrets(clean_text)
            if pii:
                logger.warning(f"Sarvam Cloud TTS blocked: PII detected in shareable text ({pii[0]}).")
                return None

        # 2. Retrieve API Key
        key = self.get_api_key()
        if not key:
            return None

        # 3. Resolve Speaker for Model Version
        if model == "bulbul:v4-flash":
            actual_speaker = V4_FLASH_SPEAKERS.get(speaker.lower(), speaker)
            if not actual_speaker.endswith(("_conversational", "_companion", "_assistant", "_customer")):
                actual_speaker = "kabir_hi_conversational"
        else:
            actual_speaker = speaker if speaker in VALID_V3_SPEAKERS else "kabir"

        # 4. Invoke Sarvam Bulbul API
        headers = {
            "api-subscription-key": key,
            "Content-Type": "application/json"
        }
        payload = {
            "inputs": [clean_text],
            "target_language_code": "hi-IN",
            "speaker": actual_speaker,
            "pace": 1.0,
            "speech_sample_rate": 16000,
            "enable_preprocessing": True,
            "model": model
        }

        try:
            with httpx.Client(timeout=8.0) as client:
                resp = client.post(SARVAM_TTS_URL, headers=headers, json=payload)

            if resp.status_code == 200:
                data = resp.json()
                audios = data.get("audios", [])
                if audios:
                    return base64.b64decode(audios[0])
                return None
            elif resp.status_code in (402, 429):
                # Quota exhausted or rate limited -> Seamlessly trigger offline fallback
                if not self._quota_alert_fired:
                    logger.warning(f"Sarvam TTS credit limit reached (HTTP {resp.status_code}). Switching to offline voice.")
                    self._quota_alert_fired = True
                self._quota_exhausted = True
                return None
            else:
                logger.error(f"Sarvam TTS failed with HTTP {resp.status_code}: {resp.text}")
                return None
        except Exception as e:
            logger.error(f"Sarvam TTS request exception: {e}")
            return None

    def reset_quota_alert(self):
        self._quota_alert_fired = False
        self._quota_exhausted = False

sarvam_tts = SarvamTTSClient()
