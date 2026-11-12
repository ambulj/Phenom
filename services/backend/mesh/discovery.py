"""
Local Network Device Discovery Engine for Phenom P2P Mesh
Broadcasts and listens for local UDP beacons to discover companion nodes
and desktop hosts on the same Wi-Fi / local subnet without cloud dependency.
"""

import json
import logging
import socket
import threading
import time
from typing import Dict, List, Optional
from services.backend.schemas.mesh import MeshDiscoveryBeacon

logger = logging.getLogger("phenom.mesh.discovery")

DEFAULT_DISCOVERY_PORT = 53530
BEACON_INTERVAL_SECONDS = 3.0
PEER_TIMEOUT_SECONDS = 15.0


def get_local_ip() -> str:
    """Best-effort detection of local non-loopback IPv4 address."""
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        # Does not actually transmit packet
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
    except Exception:
        ip = "127.0.0.1"
    finally:
        s.close()
    return ip


class MeshDiscoveryEngine:
    """
    UDP broadcast beacon engine for local mesh discovery.
    Listens on port 53530 (or custom) and emits periodic beacons every 3s.
    """

    def __init__(
        self,
        node_id: str,
        device_name: str,
        port: int = 8765,
        discovery_port: int = DEFAULT_DISCOVERY_PORT,
        broadcast_addr: str = "255.255.255.255",
        tls_fingerprint: str = "sha256-local-mesh-default"
    ):
        self.node_id = node_id
        self.device_name = device_name
        self.service_port = port
        self.discovery_port = discovery_port
        self.broadcast_addr = broadcast_addr
        self.tls_fingerprint = tls_fingerprint

        self._running = False
        self._peers: Dict[str, MeshDiscoveryBeacon] = {}
        self._lock = threading.Lock()

        self._broadcast_sock: Optional[socket.socket] = None
        self._listen_sock: Optional[socket.socket] = None

        self._broadcast_thread: Optional[threading.Thread] = None
        self._listen_thread: Optional[threading.Thread] = None

    def start(self) -> None:
        """Start UDP listener and background broadcast beacon thread."""
        with self._lock:
            if self._running:
                return
            self._running = True

        # Initialize broadcast sender socket
        try:
            self._broadcast_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            self._broadcast_sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
            try:
                self._broadcast_sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            except (AttributeError, OSError):
                pass
        except Exception as e:
            logger.warning(f"Failed to create broadcast sender socket: {e}")

        # Initialize broadcast listener socket
        try:
            self._listen_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            try:
                self._listen_sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            except (AttributeError, OSError):
                pass
            self._listen_sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
            # Bind to discovery port on all interfaces
            self._listen_sock.bind(("", self.discovery_port))
            self._listen_sock.settimeout(1.0)
        except Exception as e:
            logger.warning(f"Failed to bind discovery listener socket on port {self.discovery_port}: {e}")

        # Start background threads
        self._broadcast_thread = threading.Thread(
            target=self._broadcast_loop,
            name="MeshBeaconBroadcast",
            daemon=True
        )
        self._broadcast_thread.start()

        if self._listen_sock:
            self._listen_thread = threading.Thread(
                target=self._listen_loop,
                name="MeshBeaconListener",
                daemon=True
            )
            self._listen_thread.start()

    def stop(self) -> None:
        """Synchronously stop threads and close discovery sockets immediately (< 1ms)."""
        with self._lock:
            self._running = False

        if self._listen_sock:
            try:
                self._listen_sock.close()
            except Exception:
                pass
            self._listen_sock = None

        if self._broadcast_sock:
            try:
                self._broadcast_sock.close()
            except Exception:
                pass
            self._broadcast_sock = None

    def get_active_peers(self, timeout_seconds: float = PEER_TIMEOUT_SECONDS) -> List[MeshDiscoveryBeacon]:
        """Return list of active peers discovered within timeout window."""
        now = time.time()
        active: List[MeshDiscoveryBeacon] = []
        with self._lock:
            for node_id, peer in list(self._peers.items()):
                if (now - peer.timestamp) <= timeout_seconds:
                    active.append(peer)
                else:
                    # Clean up stale peer
                    del self._peers[node_id]
        return active

    def record_peer_beacon(self, beacon: MeshDiscoveryBeacon) -> None:
        """Record or update a discovered peer beacon."""
        if beacon.node_id == self.node_id:
            return  # Discard own loopback beacon
        with self._lock:
            self._peers[beacon.node_id] = beacon

    def _broadcast_loop(self) -> None:
        """Periodic beacon broadcast loop."""
        while self._running:
            try:
                if self._broadcast_sock:
                    beacon = MeshDiscoveryBeacon(
                        protocol="phenom-mesh/1.0",
                        node_id=self.node_id,
                        device_name=self.device_name,
                        host=get_local_ip(),
                        port=self.service_port,
                        tls_fingerprint=self.tls_fingerprint,
                        capabilities=["approvals", "telemetry", "graph_sync", "voice"],
                        timestamp=time.time()
                    )
                    payload = beacon.model_dump_json().encode("utf-8")
                    self._broadcast_sock.sendto(payload, (self.broadcast_addr, self.discovery_port))
            except Exception as e:
                logger.debug(f"Broadcast beacon emission error: {e}")

            # Sleep in small increments for fast responsive stop
            for _ in range(int(BEACON_INTERVAL_SECONDS * 10)):
                if not self._running:
                    break
                time.sleep(0.1)

    def _listen_loop(self) -> None:
        """Listener loop for incoming peer beacons."""
        while self._running and self._listen_sock:
            try:
                data, addr = self._listen_sock.recvfrom(4096)
                try:
                    payload = json.loads(data.decode("utf-8"))
                    beacon = MeshDiscoveryBeacon.model_validate(payload)
                    # Use sender ip if beacon host is 0.0.0.0
                    if beacon.host in ("0.0.0.0", "127.0.0.1") and addr[0] != "127.0.0.1":
                        beacon.host = addr[0]
                    self.record_peer_beacon(beacon)
                except Exception as parse_err:
                    logger.debug(f"Invalid beacon received from {addr}: {parse_err}")
            except socket.timeout:
                continue
            except OSError:
                break
            except Exception as e:
                logger.debug(f"Discovery listener error: {e}")
                break
