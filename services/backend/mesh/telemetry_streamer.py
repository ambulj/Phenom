"""
Swarm Debate and Mission Progress Telemetry Broadcaster for Phenom P2P Mesh
Streams multi-agent consensus rounds and unattended mission progress to companion nodes.
Strictly non-blocking and asynchronous to prevent slow companion links from stalling execution.
"""

import json
import logging
import queue
import threading
import time
from typing import Any, Dict, Optional
from services.backend.schemas.mesh import MeshMessageType
from services.backend.mesh.p2p_mesh_engine import P2PMeshEngine, p2p_mesh_engine

logger = logging.getLogger("phenom.mesh.telemetry")


class MeshTelemetryBroadcaster:
    """
    Asynchronous event broadcaster for Swarm debates and Unattended Mission progress.
    Employs a background daemon worker and bounded queue to guarantee non-blocking dispatch.
    """

    def __init__(self, engine: Optional[P2PMeshEngine] = None, queue_size: int = 1000):
        self._engine = engine or p2p_mesh_engine
        self._queue: queue.Queue[Dict[str, Any]] = queue.Queue(maxsize=queue_size)
        self._running = True
        self._worker_thread = threading.Thread(
            target=self._broadcast_worker,
            name="MeshTelemetryWorker",
            daemon=True
        )
        self._worker_thread.start()

    def stop(self) -> None:
        """Stop background telemetry worker."""
        self._running = False
        try:
            self._queue.put_nowait({"_command": "shutdown"})
        except queue.Full:
            pass

    def broadcast_swarm_debate(
        self,
        debate_id: str,
        round_num: int,
        specialist_role: str,
        critique: str,
        consensus_score: float
    ) -> bool:
        """
        Enqueue a swarm debate round update for broadcast.
        Non-blocking: returns False if queue is saturated rather than blocking execution.
        """
        event = {
            "type": MeshMessageType.SWARM_STREAM.value,
            "timestamp": time.time(),
            "payload": {
                "debate_id": debate_id,
                "round_num": round_num,
                "specialist_role": specialist_role,
                "critique": critique,
                "consensus_score": consensus_score
            }
        }
        try:
            self._queue.put_nowait(event)
            return True
        except queue.Full:
            logger.warning("Telemetry queue saturated; dropping swarm debate event.")
            return False

    def broadcast_mission_progress(
        self,
        mission_id: str,
        phase: str,
        progress_pct: float,
        log_line: str,
        morning_debrief: Optional[str] = None
    ) -> bool:
        """
        Enqueue an unattended mission milestone progress update for broadcast.
        Non-blocking: returns immediately.
        """
        event = {
            "type": MeshMessageType.MISSION_STREAM.value,
            "timestamp": time.time(),
            "payload": {
                "mission_id": mission_id,
                "phase": phase,
                "progress_pct": progress_pct,
                "log_line": log_line,
                "morning_debrief": morning_debrief
            }
        }
        try:
            self._queue.put_nowait(event)
            return True
        except queue.Full:
            logger.warning("Telemetry queue saturated; dropping mission progress event.")
            return False

    def _broadcast_worker(self) -> None:
        """Dedicated background worker draining telemetry events."""
        while self._running:
            try:
                event = self._queue.get(timeout=0.5)
                if event.get("_command") == "shutdown":
                    break

                if self._engine.is_halted:
                    continue

                msg_type_str = event.get("type", "")
                msg_type_code = 5 if msg_type_str == MeshMessageType.SWARM_STREAM.value else 6
                payload_bytes = json.dumps(event).encode("utf-8")

                paired = self._engine.get_paired_devices(include_offline=False)
                for device in paired:
                    try:
                        self._engine.send_frame(
                            node_id=device.node_id,
                            msg_type=msg_type_code,
                            payload=payload_bytes
                        )
                    except Exception as e:
                        logger.debug(f"Failed to stream telemetry to {device.node_id}: {e}")
            except queue.Empty:
                continue
            except Exception as e:
                logger.debug(f"Telemetry worker error: {e}")
