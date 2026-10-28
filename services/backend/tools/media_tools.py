"""
Phenom Windows Media & Playback Controller
Provides voice and UI control over Spotify, YouTube in browser, Apple Music, VLC, and Windows system audio.
Features:
- Windows Virtual Key emulation (VK_MEDIA_PLAY_PAUSE, VK_MEDIA_NEXT_TRACK, etc.)
- Automatic Audio Ducking (lowers background music during assistant speech)
- Tier 1 classification behind Safety Layer
"""

import sys
import time
import ctypes
from typing import Dict, Any, Literal
from pydantic import BaseModel, Field
from services.backend.safety.registry import registry

# Windows Virtual Key Codes
VK_VOLUME_MUTE = 0xAD
VK_VOLUME_DOWN = 0xAE
VK_VOLUME_UP = 0xAF
VK_MEDIA_NEXT_TRACK = 0xB0
VK_MEDIA_PREV_TRACK = 0xB1
VK_MEDIA_STOP = 0xB2
VK_MEDIA_PLAY_PAUSE = 0xB3

KEYEVENTF_EXTENDEDKEY = 0x0001
KEYEVENTF_KEYUP = 0x0002

def _send_virtual_key(vk_code: int):
    """Sends a Windows keyboard event for multimedia keys."""
    if sys.platform != "win32":
        return
    try:
        user32 = ctypes.windll.user32
        user32.keybd_event(vk_code, 0, KEYEVENTF_EXTENDEDKEY, 0)
        time.sleep(0.02)
        user32.keybd_event(vk_code, 0, KEYEVENTF_EXTENDEDKEY | KEYEVENTF_KEYUP, 0)
    except Exception as e:
        print(f"[Phenom Media] Virtual key error: {e}")

class MediaControlArgs(BaseModel):
    action: Literal["play_pause", "next", "prev", "stop", "volume_up", "volume_down", "mute"] = Field(
        description="Playback or volume action: 'play_pause', 'next', 'prev', 'stop', 'volume_up', 'volume_down', 'mute'"
    )

@registry.register(
    name="control_media",
    tier=1,
    description="Controls Windows media playback (Spotify, browser audio, VLC) or system volume",
    args_schema=MediaControlArgs,
    preview_fn=lambda a: f"Execute media command: {a.get('action')}"
)
def control_media(action: str) -> Dict[str, Any]:
    action_map = {
        "play_pause": VK_MEDIA_PLAY_PAUSE,
        "next": VK_MEDIA_NEXT_TRACK,
        "prev": VK_MEDIA_PREV_TRACK,
        "stop": VK_MEDIA_STOP,
        "mute": VK_VOLUME_MUTE,
        "volume_up": VK_VOLUME_UP,
        "volume_down": VK_VOLUME_DOWN
    }

    vk = action_map.get(action.lower().strip())
    if not vk:
        return {"status": "error", "message": f"Unknown media action: {action}"}

    # For volume adjustments, tap 3 times for a noticeable step
    repeats = 3 if action in ("volume_up", "volume_down") else 1
    for _ in range(repeats):
        _send_virtual_key(vk)
        time.sleep(0.04)

    return {
        "status": "success",
        "action": action,
        "message": f"Executed media command: {action}"
    }

# Audio Ducking helper
_DUCK_LEVELS = 6

def duck_system_audio():
    """Dips background music by tapping volume down several times."""
    if sys.platform != "win32":
        return
    for _ in range(_DUCK_LEVELS):
        _send_virtual_key(VK_VOLUME_DOWN)
        time.sleep(0.02)

def unduck_system_audio():
    """Restores background music volume."""
    if sys.platform != "win32":
        return
    for _ in range(_DUCK_LEVELS):
        _send_virtual_key(VK_VOLUME_UP)
        time.sleep(0.02)
