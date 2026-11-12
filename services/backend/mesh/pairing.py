"""
Zero-Config Ephemeral QR Pairing Protocol for Phenom P2P Mesh
Manages 120s TTL single-use pairing tokens, timing-safe verification,
and automatic credential registry enrollment.
"""

import hashlib
import hmac
import logging
import secrets
import threading
import time
from typing import Dict, Optional
from services.backend.schemas.mesh import (
    EphemeralPairingPayload,
    MeshDeviceRole,
    PairedDeviceProfile
)
from services.backend.mesh.device_registry import PairedDeviceRegistry
from services.backend.mesh.qr_generator import (
    generate_qr_matrix,
    render_qr_svg,
    render_qr_base64_png
)

logger = logging.getLogger("phenom.mesh.pairing")


class PairingManager:
    """
    Manages ephemeral QR pairing sessions.
    Tokens are strictly single-use and expire after their TTL (default 120s).
    """

    def __init__(
        self,
        node_id: str,
        host: str,
        port: int,
        device_registry: PairedDeviceRegistry,
        tls_fingerprint: str = "sha256-local-mesh-default"
    ):
        self.node_id = node_id
        self.host = host
        self.port = port
        self.device_registry = device_registry
        self.tls_fingerprint = tls_fingerprint

        self._active_tokens: Dict[str, float] = {}  # token -> expires_at
        self._lock = threading.Lock()

    def generate_ephemeral_token(self, ttl_seconds: int = 120) -> EphemeralPairingPayload:
        """
        Generate a single-use 256-bit ephemeral pairing token and QR payload.
        Purges any previously expired tokens.
        """
        self.purge_expired()
        token = secrets.token_urlsafe(32)
        expires_at = time.time() + ttl_seconds

        with self._lock:
            self._active_tokens[token] = expires_at

        pairing_uri = (
            f"phenom-mesh://pair?node_id={self.node_id}&host={self.host}"
            f"&port={self.port}&token={token}&fp={self.tls_fingerprint}"
            f"&exp={int(expires_at)}"
        )

        matrix = generate_qr_matrix(pairing_uri)
        svg = render_qr_svg(matrix, box_size=8, border=4)
        png_b64 = render_qr_base64_png(matrix, box_size=8, border=4)

        return EphemeralPairingPayload(
            node_id=self.node_id,
            host=self.host,
            port=self.port,
            token=token,
            tls_fingerprint=self.tls_fingerprint,
            expires_at=expires_at,
            pairing_uri=pairing_uri,
            qr_matrix_svg=svg,
            qr_png_base64=png_b64
        )

    def verify_pairing_request(
        self,
        companion_node_id: str,
        device_name: str,
        device_role: MeshDeviceRole,
        token: str,
        client_ip: Optional[str] = None
    ) -> Optional[PairedDeviceProfile]:
        """
        Verify an incoming pairing request from a companion device.
        Uses timing-safe comparison, enforces TTL, and purges the token immediately on use.
        """
        self.purge_expired()
        now = time.time()

        with self._lock:
            matched_token: Optional[str] = None
            for active_token, exp in list(self._active_tokens.items()):
                # Timing-safe token comparison
                if hmac.compare_digest(active_token, token):
                    if now <= exp:
                        matched_token = active_token
                    break

            if not matched_token:
                logger.warning(f"Pairing verification failed for node {companion_node_id}: invalid or expired token.")
                return None

            # Single-use invariant: consume immediately
            del self._active_tokens[matched_token]

        # Compute shared secret hash for registry profile
        secret_hash = hashlib.sha256(matched_token.encode("utf-8")).hexdigest()

        profile = PairedDeviceProfile(
            node_id=companion_node_id,
            device_name=device_name,
            device_role=device_role,
            shared_secret_hash=secret_hash,
            paired_at=now,
            last_seen_at=now,
            ip_address=client_ip,
            authorized_scopes=["approvals", "telemetry", "graph_sync", "voice"]
        )

        self.device_registry.register_device(profile)
        logger.info(f"Successfully paired device {device_name} ({companion_node_id}) as {device_role.value}")
        return profile

    def purge_expired(self) -> int:
        """Purge expired tokens from memory. Returns number of purged tokens."""
        now = time.time()
        purged = 0
        with self._lock:
            for token, exp in list(self._active_tokens.items()):
                if now > exp:
                    del self._active_tokens[token]
                    purged += 1
        return purged

    def invalidate_all(self) -> None:
        """Synchronously invalidate all pending pairing tokens on Guardian halt (< 1ms)."""
        with self._lock:
            self._active_tokens.clear()
