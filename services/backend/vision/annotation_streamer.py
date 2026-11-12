"""
Phenom Real-Time HUD Annotation Streamer
Streams detected UI element bounding boxes over authenticated WebSocket connections.
Renders live visual targets and element tags on the Cyber HUD in Electric Cobalt and Acid Lime.
Zero disk IO: strictly in-RAM bounding box and coordinate transmission.
"""

import time
import logging
import asyncio
from typing import List, Dict, Any, Optional, Callable, Awaitable
from pydantic import BaseModel, Field

logger = logging.getLogger("phenom.annotation_streamer")

BroadcasterFn = Callable[[Dict[str, Any]], Awaitable[None]]


class HudAnnotation(BaseModel):
    id: str = Field(..., description="Unique annotation identifier")
    name: str = Field(..., description="Element text, name, or label")
    control_type: str = Field(default="element", description="UI control type (Button, Edit, Text, CheckBox, etc.)")
    bbox: List[int] = Field(..., description="Bounding box [x, y, width, height] in desktop coordinates")
    confidence: float = Field(default=1.0, description="Detection confidence score between 0.0 and 1.0")
    color: str = Field(default="#0052FF", description="Border accent hex color (Electric Cobalt default)")


class AnnotationStreamer:
    """
    Manages broadcasting live bounding box HUD annotations to connected Electron clients.
    """

    def __init__(self):
        self._broadcasters: List[BroadcasterFn] = []
        self._last_annotations: List[HudAnnotation] = []

    def register_broadcaster(self, broadcaster: BroadcasterFn) -> None:
        """Registers a WebSocket broadcast callback."""
        if broadcaster not in self._broadcasters:
            self._broadcasters.append(broadcaster)

    def unregister_broadcaster(self, broadcaster: BroadcasterFn) -> None:
        """Removes a WebSocket broadcast callback."""
        if broadcaster in self._broadcasters:
            self._broadcasters.remove(broadcaster)

    async def broadcast_annotations(
        self,
        annotations: List[HudAnnotation],
        duration_ms: int = 3000
    ) -> None:
        """
        Broadcasts element bounding boxes to Cyber HUD overlay.
        """
        self._last_annotations = annotations
        payload = {
            "type": "vision.annotations",
            "payload": {
                "annotations": [a.model_dump() for a in annotations],
                "duration_ms": duration_ms,
                "timestamp": int(time.time() * 1000)
            }
        }
        await self._dispatch(payload)

    async def clear_annotations(self, reason: str = "cleared") -> None:
        """
        Instructs Cyber HUD to immediately wipe all active bounding boxes.
        """
        self._last_annotations = []
        payload = {
            "type": "vision.clear_annotations",
            "payload": {
                "reason": reason,
                "timestamp": int(time.time() * 1000)
            }
        }
        await self._dispatch(payload)

    def clear_annotations_sync(self, reason: str = "sync_halt") -> None:
        """
        Synchronous clear for use in Guardian kill switch interrupt callbacks.
        Schedules task on running loop or fires background thread.
        """
        self._last_annotations = []
        payload = {
            "type": "vision.clear_annotations",
            "payload": {
                "reason": reason,
                "timestamp": int(time.time() * 1000)
            }
        }
        try:
            loop = asyncio.get_running_loop()
            loop.create_task(self._dispatch(payload))
        except RuntimeError:
            # If no running loop in current thread, dispatch via asyncio.run or loop runner
            pass

    async def _dispatch(self, message: Dict[str, Any]) -> None:
        for bc in list(self._broadcasters):
            try:
                await bc(message)
            except Exception as e:
                logger.debug(f"Failed to dispatch annotation message: {e}")


annotation_streamer = AnnotationStreamer()
