"""
Phenom Text-To-Speech (TTS) Engine
Uses Windows SAPI5 local male voice (Microsoft David Desktop).
Streams speech sentence-by-sentence so audio playback begins while subsequent tokens are generating.
Supports instantaneous barge-in interruption.
"""

import threading
import queue
import time
import re
from typing import Optional, Callable
import win32com.client
import pythoncom

# SAPI flags
SVSFlagsAsync = 1
SVSFPurgeBeforeSpeak = 2

class TTSEngine:
    def __init__(self):
        self._speech_queue: queue.Queue[Optional[str]] = queue.Queue()
        self._is_speaking = False
        self._stop_event = threading.Event()
        self._worker_thread: Optional[threading.Thread] = None
        self._speaker = None
        self._amplitude_callback: Optional[Callable[[float], None]] = None
        self._lock = threading.Lock()
        self._start_worker()

    def set_amplitude_callback(self, cb: Callable[[float], None]):
        self._amplitude_callback = cb

    @property
    def is_speaking(self) -> bool:
        return self._is_speaking

    def _start_worker(self):
        self._worker_thread = threading.Thread(target=self._speech_worker, daemon=True)
        self._worker_thread.start()

    def _speech_worker(self):
        # Initialize COM in this thread
        pythoncom.CoInitialize()
        speaker = win32com.client.Dispatch("SAPI.SpVoice")
        
        # Select local male voice (Microsoft David)
        voices = speaker.GetVoices()
        for i in range(voices.Count):
            desc = voices.Item(i).GetDescription()
            if "david" in desc.lower() or "male" in desc.lower():
                speaker.Voice = voices.Item(i)
                break
                
        self._speaker = speaker

        while True:
            text = self._speech_queue.get()
            if text is None:
                break
                
            if self._stop_event.is_set():
                self._speech_queue.task_done()
                continue

            with self._lock:
                self._is_speaking = True

            try:
                # Speak sentence asynchronously
                speaker.Speak(text, SVSFlagsAsync)
                
                # Monitor playback and simulate amplitude bursts
                while speaker.Status.RunningState != 1: # 1 = SRSEDone
                    if self._stop_event.is_set():
                        speaker.Speak("", SVSFPurgeBeforeSpeak)
                        break
                    if self._amplitude_callback:
                        # Report speaking pulse
                        self._amplitude_callback(0.85)
                    time.sleep(0.05)

                if self._amplitude_callback:
                    self._amplitude_callback(0.0)
            except Exception as e:
                pass
            finally:
                with self._lock:
                    if self._speech_queue.empty():
                        self._is_speaking = False
                self._speech_queue.task_done()

        pythoncom.CoUninitialize()

    def feed_token(self, token: str, buffer: list[str]) -> Optional[str]:
        """
        Buffers incoming tokens and extracts completed sentences.
        Returns the sentence if one was ready and enqueued.
        """
        buffer.append(token)
        combined = "".join(buffer)
        
        # Split on sentence boundaries: period/exclamation/question followed by space or newline
        match = re.search(r"^(.*?[.!?])(?:\s+|\n+)(.*)$", combined, re.DOTALL)
        if match:
            sentence = match.group(1).strip()
            remainder = match.group(2)
            buffer.clear()
            if remainder:
                buffer.append(remainder)
            if sentence:
                self.speak(sentence)
                return sentence
        return None

    def flush_buffer(self, buffer: list[str]):
        """Flushes remaining text at the end of generation."""
        remaining = "".join(buffer).strip()
        buffer.clear()
        if remaining:
            self.speak(remaining)

    def speak(self, sentence: str):
        """Enqueues a sentence to be spoken."""
        clean_text = sentence.strip()
        if not clean_text:
            return
        # Filter markdown formatting for speech
        clean_text = re.sub(r"[*_`#\[\]]", "", clean_text)
        self._stop_event.clear()
        self._speech_queue.put(clean_text)

    def stop_speech(self):
        """Instantaneous barge-in: Purges current speech and clears the queue."""
        self._stop_event.set()
        # Clear queue
        while not self._speech_queue.empty():
            try:
                self._speech_queue.get_nowait()
                self._speech_queue.task_done()
            except queue.Empty:
                break
                
        # Purge active SAPI voice
        if self._speaker:
            try:
                self._speaker.Speak("", SVSFPurgeBeforeSpeak)
            except Exception:
                pass
                
        with self._lock:
            self._is_speaking = False

        if self._amplitude_callback:
            self._amplitude_callback(0.0)

tts_engine = TTSEngine()
