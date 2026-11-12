"""Local Expressive Neural Voice Synthesis Tools for Phenom (Milestone 31 Phase 2).

Registers 4 specialized tools in ToolRegistry:
1. synthesize_expressive_speech (Tier 1)
2. set_voice_emotion_style (Tier 1)
3. get_expressive_voice_metrics (Tier 0)
4. purge_expressive_voice_buffer (Tier 0)
"""

from typing import Any, Dict, Optional
from pydantic import BaseModel, Field

from services.backend.safety.registry import registry
from services.backend.voice.expressive_voice_engine import (
    expressive_voice_engine,
    EmotionStyle,
)


# ==========================================
# 1. Synthesize Expressive Speech (Tier 1)
# ==========================================

class SynthesizeExpressiveSpeechArgs(BaseModel):
    text: str = Field(..., description="Text content to speak, supporting non-verbal markers like [laughter], [sigh], [pause:300ms].")
    emotion_style: Optional[str] = Field(
        None,
        description="Emotion style: 'WITTY_BANTER', 'TECHNICAL_REASONING', 'URGENT_WARNING', 'EMPATHIC_CALM', 'NEUTRAL_JARVIS'.",
    )
    simulate_playback: Optional[bool] = Field(
        False, description="If True, performs audio synthesis and TTFA benchmark without physical audio speaker output."
    )


def preview_synthesize_expressive_speech(args: Dict[str, Any]) -> str:
    txt = args.get("text", "")
    preview_txt = (txt[:60] + "...") if len(txt) > 60 else txt
    style = args.get("emotion_style") or expressive_voice_engine.active_emotion.value
    return f"Synthesize expressive speech ({style}): \"{preview_txt}\""


@registry.register(
    name="synthesize_expressive_speech",
    tier=1,
    description="Synthesizes expressive voice speech with emotional prosody and non-verbal tokens (Tier 1 action).",
    args_schema=SynthesizeExpressiveSpeechArgs,
    preview_fn=preview_synthesize_expressive_speech,
    can_remember_per_folder=False,
)
def handle_synthesize_expressive_speech(
    text: str,
    emotion_style: Optional[str] = None,
    simulate_playback: bool = False,
) -> Dict[str, Any]:
    style_enum = None
    if emotion_style:
        style_enum = EmotionStyle(emotion_style.upper())
    result = expressive_voice_engine.synthesize(
        text=text,
        style=style_enum,
        simulate_playback=simulate_playback,
    )
    return result.model_dump()


# ==========================================
# 2. Set Voice Emotion Style (Tier 1)
# ==========================================

class SetVoiceEmotionStyleArgs(BaseModel):
    emotion_style: str = Field(
        ...,
        description="Emotion style: 'WITTY_BANTER', 'TECHNICAL_REASONING', 'URGENT_WARNING', 'EMPATHIC_CALM', 'NEUTRAL_JARVIS'.",
    )


def preview_set_voice_emotion_style(args: Dict[str, Any]) -> str:
    style = args.get("emotion_style", "NEUTRAL_JARVIS")
    return f"Change active voice emotional prosody style to [{style}]"


@registry.register(
    name="set_voice_emotion_style",
    tier=1,
    description="Updates the active emotional prosody style for the neural voice engine (Tier 1 configuration).",
    args_schema=SetVoiceEmotionStyleArgs,
    preview_fn=preview_set_voice_emotion_style,
    can_remember_per_folder=False,
)
def handle_set_voice_emotion_style(emotion_style: str) -> Dict[str, Any]:
    style_enum = EmotionStyle(emotion_style.upper())
    prosody = expressive_voice_engine.set_emotion_style(style_enum)
    return {
        "status": "UPDATED",
        "active_emotion_style": style_enum.value,
        "prosody": prosody.model_dump(),
    }


# ==========================================
# 3. Get Expressive Voice Metrics (Tier 0)
# ==========================================

class GetExpressiveVoiceMetricsArgs(BaseModel):
    pass


def preview_get_expressive_voice_metrics(args: Dict[str, Any]) -> str:
    return "Query real-time expressive neural voice synthesis and buffer telemetry"


@registry.register(
    name="get_expressive_voice_metrics",
    tier=0,
    description="Returns buffer metrics, TTFA latency, active emotion style, and barge-in statistics (Tier 0 read-only).",
    args_schema=GetExpressiveVoiceMetricsArgs,
    preview_fn=preview_get_expressive_voice_metrics,
    can_remember_per_folder=False,
)
def handle_get_expressive_voice_metrics() -> Dict[str, Any]:
    return expressive_voice_engine.get_metrics()


# ==========================================
# 4. Purge Expressive Voice Buffer (Tier 0)
# ==========================================

class PurgeExpressiveVoiceBufferArgs(BaseModel):
    pass


def preview_purge_expressive_voice_buffer(args: Dict[str, Any]) -> str:
    return "Purge pending sentence token buffer and stop active voice synthesis"


@registry.register(
    name="purge_expressive_voice_buffer",
    tier=0,
    description="Safely clears the streaming sentence token buffer and halts ongoing synthesis (Tier 0 safe reset).",
    args_schema=PurgeExpressiveVoiceBufferArgs,
    preview_fn=preview_purge_expressive_voice_buffer,
    can_remember_per_folder=False,
)
def handle_purge_expressive_voice_buffer() -> Dict[str, Any]:
    return expressive_voice_engine.purge_buffer()
