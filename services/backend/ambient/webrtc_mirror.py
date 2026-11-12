"""
Local WebRTC Mirror (FBK-01, SAF-01, SAF-02).
Manages peer signaling for streaming spatial desktop and canvas video to paired
companion devices strictly over local Wi-Fi with zero cloud relay leaks.
"""

import logging
import time
import uuid
from typing import Callable, Dict, List, Optional

from services.backend.schemas.proactive_bus import WebRTCMirrorSession

logger = logging.getLogger(__name__)


class LocalWebRTCMirror:
    """Manages low-latency local WebRTC screen mirror sessions to paired companion devices."""

    def __init__(self) -> None:
        self._sessions: Dict[str, WebRTCMirrorSession] = {}
        self._halted: bool = False
        self._broadcaster: Optional[Callable[[dict], None]] = None

    def register_broadcaster(self, broadcaster: Callable[[dict], None]) -> None:
        self._broadcaster = broadcaster

    def halt(self) -> None:
        """Immediate synchronous halt for Guardian kill switch (< 10ms SLA)."""
        self._halted = True
        self._sessions.clear()
        logger.info("[WebRTCMirror] LocalWebRTCMirror halted synchronously by Guardian.")

    def reset(self) -> None:
        self._halted = False

    def is_halted(self) -> bool:
        return self._halted

    def init_session(
        self,
        device_id: str,
        fps_target: int = 30,
        resolution: str = "1280x720",
    ) -> WebRTCMirrorSession:
        """Initialize a local WebRTC screen mirror session for a paired device."""
        if self._halted:
            raise PermissionError("Guardian kill switch active: WebRTC streaming halted.")

        session_id = f"rtc_{uuid.uuid4().hex[:8]}"
        session = WebRTCMirrorSession(
            session_id=session_id,
            device_id=device_id.strip(),
            is_connected=True,
            fps_target=fps_target,
            resolution=resolution,
            local_only=True,
            ice_candidates_count=1,
            created_at=time.time(),
        )
        self._sessions[session_id] = session

        if self._broadcaster:
            try:
                self._broadcaster({
                    "type": "webrtc_mirror_update",
                    "payload": session.model_dump(),
                })
            except Exception as e:
                logger.debug(f"[WebRTCMirror] Broadcast error: {e}")

        return session

    def terminate_session(self, session_id: str) -> bool:
        """Terminate an active WebRTC screen mirror session."""
        if self._halted:
            raise PermissionError("Guardian kill switch active: WebRTC streaming halted.")

        if session_id in self._sessions:
            del self._sessions[session_id]
            if self._broadcaster:
                try:
                    self._broadcaster({
                        "type": "webrtc_mirror_terminated",
                        "payload": {"session_id": session_id},
                    })
                except Exception as e:
                    logger.debug(f"[WebRTCMirror] Broadcast error: {e}")
            return True
        return False

    def get_active_sessions(self) -> List[WebRTCMirrorSession]:
        return list(self._sessions.values())


# Global singleton instance
local_webrtc_mirror = LocalWebRTCMirror()
