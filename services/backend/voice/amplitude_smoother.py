"""
Phenom Audio Amplitude Envelope Smoother
Asymmetric attack/decay filter to smooth real-time voice amplitude telemetry
for the Three.js particle orb, eliminating visual jitter and driving fluid
filament blooming between Electric Cobalt (#0052FF) and Acid Lime (#CCFF00).
"""

from typing import Optional


class AmplitudeSmoother:
    def __init__(self, attack_rate: float = 0.65, decay_rate: float = 0.15):
        """
        :param attack_rate: Responsive rise rate when voice amplitude increases (0.0 to 1.0)
        :param decay_rate: Smooth release rate when voice amplitude decreases (0.0 to 1.0)
        """
        self.attack_rate = attack_rate
        self.decay_rate = decay_rate
        self.current_amplitude: float = 0.0

    def update(self, raw_amplitude: float) -> float:
        """
        Updates internal envelope filter with incoming raw RMS amplitude.
        Returns smoothed amplitude clamped between 0.0 and 1.0.
        """
        clamped = max(0.0, min(1.0, float(raw_amplitude)))

        if clamped > self.current_amplitude:
            self.current_amplitude += (clamped - self.current_amplitude) * self.attack_rate
        else:
            self.current_amplitude += (clamped - self.current_amplitude) * self.decay_rate

        # Snap near-zero values to 0.0
        if self.current_amplitude < 0.005:
            self.current_amplitude = 0.0

        return round(self.current_amplitude, 4)

    def reset(self):
        self.current_amplitude = 0.0


amplitude_smoother = AmplitudeSmoother()
