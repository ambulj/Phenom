"""
Phenom Cinematic Sound Effects & Audio Branding
Synthesizes and plays procedural audio cues (wake chime, done tone, error alert) directly in RAM.
Zero external audio files required. Non-blocking and thread-safe.
"""

import threading
from typing import Optional
import numpy as np
import sounddevice as sd

SAMPLE_RATE = 24000

class SoundEffectsManager:
    def __init__(self, enabled: bool = True, volume: float = 0.22):
        self.enabled = enabled
        self.volume = volume
        self._lock = threading.Lock()

    def _play_async(self, audio_data: np.ndarray):
        if not self.enabled:
            return

        def _worker():
            try:
                sd.play(audio_data * self.volume, samplerate=SAMPLE_RATE, blocking=True)
            except Exception:
                # In environments without audio playback devices, fail silently
                pass

        threading.Thread(target=_worker, daemon=True).start()

    def play_wake_chime(self):
        """Play a rising two-tone futuristic bell chime (D5 -> A5) on wake word detection."""
        t1 = np.linspace(0, 0.10, int(SAMPLE_RATE * 0.10), endpoint=False)
        t2 = np.linspace(0, 0.22, int(SAMPLE_RATE * 0.22), endpoint=False)
        tone1 = np.sin(2 * np.pi * 587.33 * t1) * np.exp(-14 * t1)
        tone2 = np.sin(2 * np.pi * 880.00 * t2) * np.exp(-9 * t2)
        chime = np.concatenate([tone1, tone2]).astype(np.float32)
        self._play_async(chime)

    def play_done_chime(self):
        """Play a soft confirmation tone (G5 -> C6) when an action finishes."""
        t1 = np.linspace(0, 0.08, int(SAMPLE_RATE * 0.08), endpoint=False)
        t2 = np.linspace(0, 0.18, int(SAMPLE_RATE * 0.18), endpoint=False)
        tone1 = np.sin(2 * np.pi * 783.99 * t1) * np.exp(-16 * t1)
        tone2 = np.sin(2 * np.pi * 1046.50 * t2) * np.exp(-10 * t2)
        chime = np.concatenate([tone1, tone2]).astype(np.float32)
        self._play_async(chime)

    def play_error_chime(self):
        """Play a low double-tone warning when an action is blocked or fails."""
        t = np.linspace(0, 0.12, int(SAMPLE_RATE * 0.12), endpoint=False)
        tone1 = np.sin(2 * np.pi * 329.63 * t) * np.exp(-12 * t)
        gap = np.zeros(int(SAMPLE_RATE * 0.04), dtype=np.float32)
        tone2 = np.sin(2 * np.pi * 293.66 * t) * np.exp(-12 * t)
        chime = np.concatenate([tone1, gap, tone2]).astype(np.float32)
        self._play_async(chime)

    def play_automation_start(self):
        """Low-latency 150ms rising chime (440Hz -> 660Hz -> 880Hz) on screen control acquisition."""
        t = np.linspace(0, 0.05, int(SAMPLE_RATE * 0.05), endpoint=False)
        tone1 = np.sin(2 * np.pi * 440.0 * t) * np.exp(-12 * t)
        tone2 = np.sin(2 * np.pi * 660.0 * t) * np.exp(-12 * t)
        tone3 = np.sin(2 * np.pi * 880.0 * t) * np.exp(-8 * t)
        chime = np.concatenate([tone1, tone2, tone3]).astype(np.float32)
        self._play_async(chime)

    def play_automation_stop(self):
        """120ms soft chime (880Hz -> 587Hz) on control release."""
        t1 = np.linspace(0, 0.05, int(SAMPLE_RATE * 0.05), endpoint=False)
        t2 = np.linspace(0, 0.07, int(SAMPLE_RATE * 0.07), endpoint=False)
        tone1 = np.sin(2 * np.pi * 880.0 * t1) * np.exp(-14 * t1)
        tone2 = np.sin(2 * np.pi * 587.33 * t2) * np.exp(-10 * t2)
        chime = np.concatenate([tone1, tone2]).astype(np.float32)
        self._play_async(chime)

    def play_automation_halt(self):
        """Sharp double beep (750Hz double pulse) when user interrupts or kill switch triggers."""
        t = np.linspace(0, 0.06, int(SAMPLE_RATE * 0.06), endpoint=False)
        tone1 = np.sin(2 * np.pi * 750.0 * t) * np.exp(-10 * t)
        gap = np.zeros(int(SAMPLE_RATE * 0.03), dtype=np.float32)
        tone2 = np.sin(2 * np.pi * 750.0 * t) * np.exp(-10 * t)
        chime = np.concatenate([tone1, gap, tone2]).astype(np.float32)
        self._play_async(chime)

sound_fx = SoundEffectsManager()
