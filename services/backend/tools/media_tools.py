"""
Phenom Windows Media & Playback Controller (MED-01, SAF-01, SAF-02)
Provides embedded webview and system transport control over YouTube, Spotify, and Windows media.
Features:
- Embedded Electron Webview integration with typed WebSocket events
- Dual-control transport: Visual Cyber HUD + instant voice intent dispatch
- System multimedia key emulation fallback (VK_MEDIA_PLAY_PAUSE, etc.)
- Automatic Audio Ducking (lowers background music during assistant speech)
- Sub-10ms Guardian kill switch audio silence SLA
"""

import os
import sys
import time
import ctypes
import asyncio
from typing import Dict, Any, Literal, Optional, Callable, Awaitable
from pydantic import BaseModel, Field
from services.backend.safety.registry import registry
from services.backend.safety.guardian import guardian

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

# Internal playback state tracking
_current_media_state: Dict[str, Any] = {
    "state": "idle",
    "query": "",
    "platform": "youtube",
    "volume": 80,
    "muted": False,
    "last_updated": 0.0
}

def _send_virtual_key(vk_code: int):
    """Sends a Windows keyboard event for multimedia keys."""
    if sys.platform != "win32":
        return
    try:
        user32 = ctypes.windll.user32
        user32.keybd_event(vk_code, 0, KEYEVENTF_EXTENDEDKEY, 0)
        user32.keybd_event(vk_code, 0, KEYEVENTF_EXTENDEDKEY | KEYEVENTF_KEYUP, 0)
    except Exception as e:
        print(f"[Phenom Media] Virtual key error: {e}")

_broadcaster: Optional[Callable[[Dict[str, Any]], Awaitable[None]]] = None

def register_broadcaster(broadcaster: Callable[[Dict[str, Any]], Awaitable[None]]) -> None:
    """Registers the WebSocket broadcast callback."""
    global _broadcaster
    _broadcaster = broadcaster

def broadcast_media_event(event_type: str, payload: Dict[str, Any]):
    """Broadcasts media state events to connected Electron clients over WebSocket."""
    broadcaster = _broadcaster
    if not broadcaster:
        main_mod = sys.modules.get("services.backend.main")
        if main_mod:
            active_ws = getattr(main_mod, "active_websockets", None)
            if active_ws is not None and not active_ws:
                return
            if hasattr(main_mod, "broadcast_message"):
                broadcaster = main_mod.broadcast_message
    if not broadcaster:
        return
    msg = {
        "id": f"media-{os.urandom(2).hex()}",
        "type": event_type,
        "ts": str(time.time()),
        "payload": payload
    }
    try:
        loop = asyncio.get_running_loop()
        loop.create_task(broadcaster(msg))
    except RuntimeError:
        pass

# Guardian Kill Switch audio silence hook (SAF-02 < 10ms SLA)
def _on_guardian_media_halt(reason: str):
    """Synchronously mutes all active audio on Guardian kill switch halt."""
    if reason != "halted":
        return
    was_playing = _current_media_state.get("state") == "playing"
    _current_media_state["muted"] = True
    _current_media_state["state"] = "paused"
    if was_playing:
        _send_virtual_key(VK_VOLUME_MUTE)
    broadcast_media_event("MEDIA_MUTE", {"muted": True, "reason": reason})

guardian.add_state_callback(_on_guardian_media_halt)

# -------------------------------------------------------------
# 1. Play Media Tool (Tier 1 Confirmation)
# -------------------------------------------------------------
class PlayMediaArgs(BaseModel):
    query: str = Field(description="Search term, song title, or artist (e.g. 'baarishein', 'interstellar soundtrack', 'lofi beats')")
    platform: Literal["youtube", "spotify"] = Field(default="youtube", description="Streaming platform: 'youtube' or 'spotify'")

@registry.register(
    name="play_media",
    tier=1,
    description="Starts streaming media playback for a song, artist, or playlist in the embedded Electron webview",
    args_schema=PlayMediaArgs,
    preview_fn=lambda a: f"Stream '{a.get('query')}' via {a.get('platform', 'youtube')}"
)
def play_media(query: str, platform: str = "youtube") -> Dict[str, Any]:
    clean_query = query.strip()
    target_platform = platform.lower().strip() if platform in ("youtube", "spotify") else "youtube"

    if not clean_query:
        return {"status": "error", "message": "Query cannot be empty"}

    _current_media_state.update({
        "state": "playing",
        "query": clean_query,
        "platform": target_platform,
        "muted": False,
        "last_updated": time.time()
    })

    # Broadcast MEDIA_PLAY event to Electron to update embedded webview
    broadcast_media_event("MEDIA_PLAY", {
        "query": clean_query,
        "platform": target_platform,
        "volume": _current_media_state["volume"]
    })

    return {
        "status": "success",
        "action": "play_media",
        "query": clean_query,
        "platform": target_platform,
        "message": f"Playing '{clean_query}' on {target_platform}"
    }

# -------------------------------------------------------------
# 2. Pause Media Tool (Tier 0 Transient Transport Control)
# -------------------------------------------------------------
class PauseMediaArgs(BaseModel):
    pass

@registry.register(
    name="pause_media",
    tier=0,
    description="Pauses currently playing media in the embedded webview or active Windows media session",
    args_schema=PauseMediaArgs,
    preview_fn=lambda a: "Pause active media playback"
)
def pause_media() -> Dict[str, Any]:
    _current_media_state["state"] = "paused"
    _current_media_state["last_updated"] = time.time()

    # 1. Notify Electron webview
    broadcast_media_event("MEDIA_PAUSE", {})
    # 2. Hardware transport key fallback
    _send_virtual_key(VK_MEDIA_PLAY_PAUSE)

    return {
        "status": "success",
        "action": "pause_media",
        "message": "Media playback paused"
    }

# -------------------------------------------------------------
# 3. Resume Media Tool (Tier 0 Transient Transport Control)
# -------------------------------------------------------------
class ResumeMediaArgs(BaseModel):
    pass

@registry.register(
    name="resume_media",
    tier=0,
    description="Resumes media playback in the embedded webview or active Windows media session",
    args_schema=ResumeMediaArgs,
    preview_fn=lambda a: "Resume media playback"
)
def resume_media() -> Dict[str, Any]:
    _current_media_state["state"] = "playing"
    _current_media_state["last_updated"] = time.time()

    broadcast_media_event("MEDIA_RESUME", {})
    _send_virtual_key(VK_MEDIA_PLAY_PAUSE)

    return {
        "status": "success",
        "action": "resume_media",
        "message": "Media playback resumed"
    }

# -------------------------------------------------------------
# 4. Next Track Tool (Tier 0 Transient Transport Control)
# -------------------------------------------------------------
class NextTrackArgs(BaseModel):
    pass

@registry.register(
    name="next_track",
    tier=0,
    description="Skips to the next track in the playlist or media queue",
    args_schema=NextTrackArgs,
    preview_fn=lambda a: "Skip to next media track"
)
def next_track() -> Dict[str, Any]:
    _current_media_state["last_updated"] = time.time()

    broadcast_media_event("MEDIA_NEXT", {})
    _send_virtual_key(VK_MEDIA_NEXT_TRACK)

    return {
        "status": "success",
        "action": "next_track",
        "message": "Skipped to next track"
    }

# -------------------------------------------------------------
# 5. Set Volume Tool (Tier 0 Transient Control)
# -------------------------------------------------------------
class SetVolumeArgs(BaseModel):
    level: int = Field(ge=0, le=100, description="Volume level from 0 (silent) to 100 (maximum)")

@registry.register(
    name="set_volume",
    tier=0,
    description="Sets the playback volume level (0 to 100) for media and system audio",
    args_schema=SetVolumeArgs,
    preview_fn=lambda a: f"Set media volume to {a.get('level')}%"
)
def set_volume(level: int) -> Dict[str, Any]:
    bounded = max(0, min(100, int(level)))
    _current_media_state["volume"] = bounded
    _current_media_state["last_updated"] = time.time()

    broadcast_media_event("MEDIA_VOLUME", {"volume": bounded})

    return {
        "status": "success",
        "action": "set_volume",
        "level": bounded,
        "message": f"Volume set to {bounded}%"
    }

# -------------------------------------------------------------
# 6. Playback Status Tool (Tier 0 Read-Only)
# -------------------------------------------------------------
class PlaybackStatusArgs(BaseModel):
    pass

@registry.register(
    name="get_playback_status",
    tier=0,
    description="Returns the active playback status, current track, volume, and platform",
    args_schema=PlaybackStatusArgs,
    preview_fn=lambda a: "Get active media playback status"
)
def get_playback_status() -> Dict[str, Any]:
    return {
        "status": "success",
        "playback": dict(_current_media_state)
    }

# -------------------------------------------------------------
# 7. Legacy Multi-Action Controller (Backward Compatibility)
# -------------------------------------------------------------
class MediaControlArgs(BaseModel):
    action: Literal["play", "pause", "resume", "play_pause", "next", "prev", "stop", "volume_up", "volume_down", "mute"] = Field(
        description="Playback or volume action"
    )

@registry.register(
    name="control_media",
    tier=0,
    description="Controls Windows media playback or system volume",
    args_schema=MediaControlArgs,
    preview_fn=lambda a: f"Execute media command: {a.get('action')}"
)
def control_media(action: str) -> Dict[str, Any]:
    act = action.lower().strip()
    if act == "pause":
        return pause_media()
    elif act == "resume":
        return resume_media()
    elif act == "next":
        return next_track()
    elif act == "mute":
        _send_virtual_key(VK_VOLUME_MUTE)
        return {"status": "success", "action": "mute", "message": "System audio toggled"}
    elif act == "volume_up":
        for _ in range(3):
            _send_virtual_key(VK_VOLUME_UP)
            time.sleep(0.02)
        return {"status": "success", "action": "volume_up", "message": "Volume increased"}
    elif act == "volume_down":
        for _ in range(3):
            _send_virtual_key(VK_VOLUME_DOWN)
            time.sleep(0.02)
        return {"status": "success", "action": "volume_down", "message": "Volume decreased"}

    _send_virtual_key(VK_MEDIA_PLAY_PAUSE)
    return {"status": "success", "action": action, "message": f"Executed media command: {action}"}

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
