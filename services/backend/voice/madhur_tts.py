"""
Phenom Madhur Neural TTS Client
Uses hi-IN-MadhurNeural for natural Indian English and Hindi speech synthesis.
100% Free, zero external API keys required.
In-memory synthesis (0 bytes written to disk).
Gracefully times out in 2.5s and returns None if offline to allow local fallback.
"""

import asyncio
import io
import logging
from typing import Optional

logger = logging.getLogger("phenom.voice.madhur_tts")

DEFAULT_VOICE = "hi-IN-MadhurNeural"

class MadhurTTSClient:
    def __init__(self, voice: str = DEFAULT_VOICE):
        self.voice = voice

    async def _synthesize_async(self, text: str) -> Optional[bytes]:
        try:
            import edge_tts
            comm = edge_tts.Communicate(text, self.voice)
            chunks = []
            async for chunk in comm.stream():
                if chunk["type"] == "audio":
                    chunks.append(chunk["data"])
            if chunks:
                return b"".join(chunks)
        except Exception as e:
            logger.debug(f"Madhur TTS network error: {e}")
        return None

    def synthesize(self, text: str, timeout_seconds: float = 3.0) -> Optional[bytes]:
        """
        Synchronously synthesizes text to audio bytes using hi-IN-MadhurNeural.
        Returns audio bytes on success, or None if offline/timed out.
        """
        clean_text = text.strip()
        if not clean_text:
            return None

        try:
            loop = asyncio.new_event_loop()
            try:
                task = self._synthesize_async(clean_text)
                audio_bytes = loop.run_until_complete(asyncio.wait_for(task, timeout=timeout_seconds))
                return audio_bytes
            finally:
                loop.close()
        except Exception as e:
            logger.debug(f"Madhur TTS synthesis fallback triggered: {e}")
            return None

madhur_tts = MadhurTTSClient()
