"""Visual HUD Target Halo Emitter (Milestone 49 Phase 4, CHOREO-03).

Emits screen bounding-box highlight specs to CyberHUD overlay prior to mouse action dispatch,
providing transparent visual confirmation of intended control targets.
"""

from __future__ import annotations

import collections
import logging
import threading
import time
from typing import Deque, Dict, List, Optional, Tuple

from services.backend.schemas.desktop_choreography import TargetHaloSpec
from services.backend.safety.guardian import guardian

logger = logging.getLogger("phenom.desktop.visual_target_halo")


class VisualTargetHaloEmitter:
    """Manages active target bounding box halos for CyberHUD overlay rendering."""

    def __init__(self, max_history: int = 50) -> None:
        self._lock = threading.RLock()
        self._active_halo: Optional[TargetHaloSpec] = None
        self._history: Deque[TargetHaloSpec] = collections.deque(maxlen=max_history)

    def _assert_guardian(self) -> None:
        if guardian.is_halted:
            raise PermissionError("Guardian kill switch is active. Target halo emission aborted.")

    def create_halo(
        self,
        target_name: str,
        bounding_box: Tuple[int, int, int, int],
        action_type: str = "CLICK",
        duration_ms: int = 300,
        color_hex: str = "#00FFCC",
    ) -> TargetHaloSpec:
        """Formulates and emits a new visual target halo."""
        self._assert_guardian()

        halo_id = f"halo_{int(time.time() * 1000)}"
        spec = TargetHaloSpec(
            halo_id=halo_id,
            target_name=target_name,
            bounding_box=bounding_box,
            color_hex=color_hex,
            duration_ms=duration_ms,
            action_type=action_type,
            timestamp=time.time(),
        )

        with self._lock:
            self._active_halo = spec
            self._history.append(spec)

        return spec

    def get_active_halo(self) -> Optional[TargetHaloSpec]:
        """Returns the currently active target halo if within display duration."""
        self._assert_guardian()
        with self._lock:
            if not self._active_halo:
                return None
            elapsed_ms = (time.time() - self._active_halo.timestamp) * 1000.0
            if elapsed_ms > self._active_halo.duration_ms:
                self._active_halo = None
                return None
            return self._active_halo

    def list_recent_halos(self, limit: int = 10) -> List[TargetHaloSpec]:
        self._assert_guardian()
        with self._lock:
            return list(self._history)[-limit:]

    def clear(self) -> None:
        with self._lock:
            self._active_halo = None
            self._history.clear()
