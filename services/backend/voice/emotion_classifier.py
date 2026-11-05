"""
Phenom Zero-Latency Emotion & Sentiment Classifier (VOX-03.1)
Heuristic token and regex scoring engine.
Classifies user text into 6 core emotion states in < 0.1ms:
- urgent: Rapid, high-priority emergency or time-sensitive commands
- frustrated: Annoyance, repeated errors, broken workflows
- excited: Enthusiasm, celebratory energy, high motivation
- focused: Deep technical, analytical, coding mindset
- calm: Peaceful, reflective, low-energy inquiries
- casual: Default witty, conversational banter
"""

import re
import time
from typing import Dict, Any, List, Literal, Tuple
from pydantic import BaseModel, Field

EmotionType = Literal["urgent", "frustrated", "excited", "focused", "calm", "casual"]


class EmotionResult(BaseModel):
    emotion: EmotionType = Field(..., description="Primary detected emotional tone")
    confidence: float = Field(..., ge=0.0, le=1.0, description="Detection confidence score")
    intensity: float = Field(..., ge=0.0, le=1.0, description="Tone emotional intensity")
    matched_cues: List[str] = Field(default_factory=list, description="Keywords or regex cues triggering classification")
    latency_ms: float = Field(..., description="Classification latency in milliseconds")


class EmotionClassifier:
    """
    Sub-0.1ms heuristic emotion classifier.
    Avoids heavy neural NLP overhead for real-time speech responses.
    """

    def __init__(self):
        # Precompiled regex patterns for maximum execution speed
        self._urgent_patterns = [
            re.compile(r"\b(?:urgent|asap|emergency|immediately|hurry|crisis|quick|fast|right\s+now|danger|fatal)\b", re.I),
            re.compile(r"!{2,}"),
            re.compile(r"\b(?:stop\s+everything|halt\s+all|killswitch)\b", re.I)
        ]

        self._frustrated_patterns = [
            re.compile(r"\b(?:damn|broken|not\s+working|fails?|stuck|wrong|hate|useless|horrible|terrible|screw\s+this|frustrated|annoying|buggy)\b", re.I),
            re.compile(r"\?{2,}"),
            re.compile(r"\b(?:why\s+won'?t\s+this|why\s+does\s+it\s+keep)\b", re.I)
        ]

        self._excited_patterns = [
            re.compile(r"\b(?:awesome|amazing|phenomenal|brilliant|lets\s+go|let's\s+go|wow|hell\s+yeah|great\s+job|super|fire|celebrate|stoked|epic)\b", re.I),
            re.compile(r"\b(?:yes!|yess+)\b", re.I)
        ]

        self._focused_patterns = [
            re.compile(r"\b(?:def\s+[a-zA-Z_]|class\s+[a-zA-Z_]|refactor|quicksort|algorithm|benchmark|profiling|optimize|architecture|database|schema|async\s+def)\b", re.I),
            re.compile(r"\b(?:deep\s+dive|step\s+by\s+step|root\s+cause|analyze\s+thoroughly)\b", re.I)
        ]

        self._calm_patterns = [
            re.compile(r"\b(?:peaceful|gentle|slow\s+down|whisper|relax|chill|quiet|softly|meditate|sleep|soothing|calm\s+down)\b", re.I),
            re.compile(r"\b(?:take\s+your\s+time|no\s+rush)\b", re.I)
        ]

    def classify(self, text: str) -> EmotionResult:
        """
        Evaluates input text and returns emotional classification in < 0.1ms.
        """
        t0 = time.perf_counter()
        clean = text.strip()
        if not clean:
            latency = (time.perf_counter() - t0) * 1000.0
            return EmotionResult(
                emotion="casual",
                confidence=0.5,
                intensity=0.2,
                matched_cues=[],
                latency_ms=round(latency, 4)
            )

        scores: Dict[EmotionType, float] = {
            "urgent": 0.0,
            "frustrated": 0.0,
            "excited": 0.0,
            "focused": 0.0,
            "calm": 0.0,
            "casual": 0.1  # baseline casual bias
        }
        matched: Dict[EmotionType, List[str]] = {k: [] for k in scores}

        # Check Urgent cues
        for pat in self._urgent_patterns:
            m = pat.findall(clean)
            if m:
                scores["urgent"] += len(m) * 2.5
                matched["urgent"].extend([str(x) for x in m])

        # Check Frustrated cues
        for pat in self._frustrated_patterns:
            m = pat.findall(clean)
            if m:
                scores["frustrated"] += len(m) * 2.0
                matched["frustrated"].extend([str(x) for x in m])

        # Check Excited cues
        for pat in self._excited_patterns:
            m = pat.findall(clean)
            if m:
                scores["excited"] += len(m) * 2.0
                matched["excited"].extend([str(x) for x in m])

        # Check Focused cues
        for pat in self._focused_patterns:
            m = pat.findall(clean)
            if m:
                scores["focused"] += len(m) * 1.8
                matched["focused"].extend([str(x) for x in m])

        # Check Calm cues
        for pat in self._calm_patterns:
            m = pat.findall(clean)
            if m:
                scores["calm"] += len(m) * 2.2
                matched["calm"].extend([str(x) for x in m])

        # Exclamation density adds to urgent or excited
        exclamations = clean.count("!")
        if exclamations >= 2:
            if scores["frustrated"] > 0:
                scores["frustrated"] += 1.0
            elif scores["urgent"] > 0:
                scores["urgent"] += 1.0
            else:
                scores["excited"] += 1.0

        # Select highest scoring emotion
        best_emotion: EmotionType = max(scores, key=lambda k: scores[k])
        best_score = scores[best_emotion]

        if best_score <= 0.1:
            best_emotion = "casual"
            confidence = 0.8
            intensity = 0.3
        else:
            confidence = min(0.99, round(best_score / (best_score + 1.5), 2))
            intensity = min(1.0, round(best_score / 4.0, 2))

        latency = (time.perf_counter() - t0) * 1000.0

        return EmotionResult(
            emotion=best_emotion,
            confidence=max(0.5, confidence),
            intensity=max(0.2, intensity),
            matched_cues=matched[best_emotion][:5],
            latency_ms=round(latency, 4)
        )


# Global singleton instance
emotion_classifier = EmotionClassifier()
