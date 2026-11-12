"""
Core P2P Mesh Engine for Phenom Milestone 10.0
Coordinates local network discovery, ephemeral pairing, session transport,
message routing, and sub-25ms synchronous Guardian kill switch shutdown (< 1ms typical).
"""

import logging
import socket
import threading
import time
from typing import Callable, Dict, List, Optional
from services.backend.schemas.mesh import (
    EphemeralPairingPayload,
    MeshDeviceRole,
    PairedDeviceProfile
)
from services.backend.mesh.crypto import MeshCryptoEngine
from services.backend.mesh.device_registry import PairedDeviceRegistry
from services.backend.mesh.discovery import MeshDiscoveryEngine, get_local_ip
from services.backend.mesh.pairing import PairingManager
from services.backend.safety.guardian import GuardianKillSwitch

logger = logging.getLogger("phenom.mesh.engine")


class MeshSession:
    """Represents an active encrypted session with a paired companion device."""

    def __init__(
        self,
        node_id: str,
        crypto_engine: MeshCryptoEngine,
        sock: Optional[socket.socket] = None
    ):
        self.node_id = node_id
        self.crypto_engine = crypto_engine
        self.sock = sock
        self.connected_at = time.time()
        self.last_activity = time.time()

    def close(self) -> None:
        """Close session socket."""
        if self.sock:
            try:
                self.sock.close()
            except Exception:
                pass
            self.sock = None


class P2PMeshEngine:
    """
    Singleton orchestrator for Phenom's encrypted cross-device local P2P mesh.
    Enforces strict local privacy (no cloud relay) and sub-25ms Guardian universal kill switch.
    """

    def __init__(
        self,
        node_id: str = "phenom-desktop-host",
        device_name: str = "Phenom Windows 11 Desktop",
        service_port: int = 8765,
        discovery_port: int = 53530,
        guardian: Optional[GuardianKillSwitch] = None,
        registry_path: Optional[str] = None
    ):
        self.node_id = node_id
        self.device_name = device_name
        self.service_port = service_port
        self.discovery_port = discovery_port
        self.host_ip = get_local_ip()

        self._guardian = guardian
        self._is_halted = False
        self._lock = threading.Lock()

        # Initialize sub-components
        if registry_path:
            from pathlib import Path
            self.device_registry = PairedDeviceRegistry(Path(registry_path))
        else:
            self.device_registry = PairedDeviceRegistry()

        self.pairing = PairingManager(
            node_id=self.node_id,
            host=self.host_ip,
            port=self.service_port,
            device_registry=self.device_registry
        )

        self.discovery = MeshDiscoveryEngine(
            node_id=self.node_id,
            device_name=self.device_name,
            port=self.service_port,
            discovery_port=self.discovery_port
        )

        self._sessions: Dict[str, MeshSession] = {}
        self._handlers: Dict[int, List[Callable[[str, bytes], None]]] = {}
        self._server_sock: Optional[socket.socket] = None

        # Auto-register guardian callback if provided
        if self._guardian:
            self._guardian.add_state_callback(self.on_guardian_state)

    @property
    def is_halted(self) -> bool:
        with self._lock:
            return self._is_halted or (self._guardian.is_halted if self._guardian else False)

    def _check_halted(self) -> None:
        """Enforce Guardian kill switch invariant on every operation."""
        if self.is_halted:
            raise PermissionError("Operation blocked: P2P Mesh is halted by Guardian Kill Switch.")

    def on_guardian_state(self, state: str) -> None:
        """Callback invoked by GuardianKillSwitch on state changes."""
        if state == "halted":
            self.halt()
        elif state == "idle":
            self.reset()

    def start(self) -> None:
        """Start discovery and local networking services."""
        self._check_halted()
        self.discovery.start()

    def stop(self) -> None:
        """Gracefully stop discovery and active sessions."""
        self.discovery.stop()
        with self._lock:
            for session in list(self._sessions.values()):
                session.close()
            self._sessions.clear()

            if self._server_sock:
                try:
                    self._server_sock.close()
                except Exception:
                    pass
                self._server_sock = None

    def halt(self) -> None:
        """
        Sub-25ms synchronous Guardian kill switch shutdown (< 1.0ms typical).
        Immediately closes all active sockets, stops broadcaster, and invalidates tokens.
        """
        with self._lock:
            self._is_halted = True

            # Terminate all active sessions immediately
            for session in list(self._sessions.values()):
                session.close()
            self._sessions.clear()

            # Close server listener
            if self._server_sock:
                try:
                    self._server_sock.close()
                except Exception:
                    pass
                self._server_sock = None

        # Stop discovery beacon thread and invalidate pairing tokens
        self.discovery.stop()
        self.pairing.invalidate_all()
        logger.warning("P2P Mesh Engine synchronously HALTED by Guardian Kill Switch.")

    def reset(self) -> None:
        """Resume P2P mesh operations after Guardian release."""
        with self._lock:
            self._is_halted = False
        self.discovery.start()
        logger.info("P2P Mesh Engine RESUMED from Guardian halt.")

    def resume(self) -> None:
        """Alias for reset()."""
        self.reset()

    # --- Pairing Operations ---

    def generate_pairing_qr(self, ttl_seconds: int = 120) -> EphemeralPairingPayload:
        """Generate 1-time ephemeral QR pairing token and visual SVG payload."""
        self._check_halted()
        return self.pairing.generate_ephemeral_token(ttl_seconds)

    def verify_pairing(
        self,
        node_id: str,
        device_name: str,
        device_role: MeshDeviceRole,
        token: str,
        client_ip: Optional[str] = None
    ) -> Optional[PairedDeviceProfile]:
        """Verify an incoming pairing request."""
        self._check_halted()
        return self.pairing.verify_pairing_request(
            companion_node_id=node_id,
            device_name=device_name,
            device_role=device_role,
            token=token,
            client_ip=client_ip
        )

    def get_paired_devices(self, include_offline: bool = True) -> List[PairedDeviceProfile]:
        """List registered paired companion devices."""
        self._check_halted()
        devices = self.device_registry.list_devices()
        if include_offline:
            return devices

        # Filter only devices with active sessions
        with self._lock:
            active_ids = set(self._sessions.keys())
        return [d for d in devices if d.node_id in active_ids]

    def unpair_device(self, node_id: str) -> bool:
        """Revoke a companion device pairing and terminate its active session."""
        self._check_halted()
        with self._lock:
            session = self._sessions.pop(node_id, None)
            if session:
                session.close()
        return self.device_registry.unpair_device(node_id)

    # --- Session & Message Routing ---

    def register_session(
        self,
        node_id: str,
        crypto_engine: MeshCryptoEngine,
        sock: Optional[socket.socket] = None
    ) -> MeshSession:
        """Register an active encrypted session."""
        self._check_halted()
        session = MeshSession(node_id=node_id, crypto_engine=crypto_engine, sock=sock)
        with self._lock:
            old_session = self._sessions.get(node_id)
            if old_session:
                old_session.close()
            self._sessions[node_id] = session
        return session

    def close_session(self, node_id: str) -> None:
        """Close and remove an active session."""
        with self._lock:
            session = self._sessions.pop(node_id, None)
            if session:
                session.close()

    def get_session(self, node_id: str) -> Optional[MeshSession]:
        """Retrieve an active session by node ID."""
        with self._lock:
            return self._sessions.get(node_id)

    def register_handler(self, msg_type: int, handler_fn: Callable[[str, bytes], None]) -> None:
        """Register a callback for incoming messages of a given type."""
        with self._lock:
            self._handlers.setdefault(msg_type, []).append(handler_fn)

    def dispatch_incoming_frame(self, node_id: str, frame_bytes: bytes) -> None:
        """Decrypt an incoming frame and dispatch to registered handlers."""
        self._check_halted()
        session = self.get_session(node_id)
        if not session:
            raise ValueError(f"No active session for node {node_id}")

        msg_type, payload = session.crypto_engine.decrypt_frame(frame_bytes)
        session.last_activity = time.time()
        self.device_registry.update_last_seen(node_id)

        with self._lock:
            handlers = list(self._handlers.get(msg_type, []))

        for h in handlers:
            try:
                h(node_id, payload)
            except Exception as e:
                logger.error(f"Error in handler for msg_type {msg_type}: {e}")

    def send_frame(self, node_id: str, msg_type: int, payload: bytes) -> bytes:
        """Encrypt a payload for a connected companion node."""
        self._check_halted()
        session = self.get_session(node_id)
        if not session:
            raise ValueError(f"No active session for node {node_id}")

        frame = session.crypto_engine.encrypt_frame(payload, msg_type)
        session.last_activity = time.time()
        if session.sock:
            try:
                session.sock.sendall(frame)
            except Exception as e:
                logger.error(f"Failed to send socket frame to {node_id}: {e}")
                self.close_session(node_id)
        return frame


# Singleton instance
p2p_mesh_engine = P2PMeshEngine()
