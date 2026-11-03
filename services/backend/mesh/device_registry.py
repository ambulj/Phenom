"""
Paired Device Registry for Phenom P2P Mesh
Stores and persists paired companion node identities, shared secrets,
and authorization scopes in an atomic JSON file.
"""

import json
import logging
import os
import threading
import time
from pathlib import Path
from typing import Dict, List, Optional
from services.backend.schemas.mesh import PairedDeviceProfile

logger = logging.getLogger("phenom.mesh.device_registry")

DEFAULT_STORAGE_PATH = Path("services/backend/data/paired_devices.json")


class PairedDeviceRegistry:
    """
    Manages persistent metadata and authorized scopes for paired companion devices.
    Uses in-memory cache for sub-millisecond lookup with atomic JSON file persistence.
    """

    def __init__(self, storage_path: Path = DEFAULT_STORAGE_PATH):
        self._storage_path = storage_path
        self._lock = threading.Lock()
        self._devices: Dict[str, PairedDeviceProfile] = {}
        self._load()

    def _load(self) -> None:
        """Load paired devices from disk if file exists."""
        if not self._storage_path.exists():
            return

        try:
            with open(self._storage_path, "r", encoding="utf-8") as f:
                data = json.load(f)
                for item in data.get("devices", []):
                    profile = PairedDeviceProfile.model_validate(item)
                    self._devices[profile.node_id] = profile
        except Exception as e:
            logger.error(f"Failed to load paired devices from {self._storage_path}: {e}")

    def _save(self) -> None:
        """Atomically persist device cache to disk using write-replace pattern."""
        try:
            self._storage_path.parent.mkdir(parents=True, exist_ok=True)
            tmp_path = self._storage_path.with_suffix(".tmp")
            data = {
                "version": 1,
                "updated_at": time.time(),
                "devices": [p.model_dump() for p in self._devices.values()]
            }
            with open(tmp_path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2)
            os.replace(tmp_path, self._storage_path)
        except Exception as e:
            logger.error(f"Failed to persist paired devices to {self._storage_path}: {e}")

    def register_device(self, profile: PairedDeviceProfile) -> None:
        """Register or update a paired companion device."""
        with self._lock:
            self._devices[profile.node_id] = profile
            self._save()

    def get_device(self, node_id: str) -> Optional[PairedDeviceProfile]:
        """Lookup a device by node_id in memory."""
        with self._lock:
            return self._devices.get(node_id)

    def list_devices(self) -> List[PairedDeviceProfile]:
        """List all registered paired devices."""
        with self._lock:
            return list(self._devices.values())

    def unpair_device(self, node_id: str) -> bool:
        """Revoke and delete a paired companion device."""
        with self._lock:
            if node_id in self._devices:
                del self._devices[node_id]
                self._save()
                return True
            return False

    def update_last_seen(self, node_id: str, ip_address: Optional[str] = None) -> None:
        """Update last seen timestamp and optional IP for a device."""
        with self._lock:
            device = self._devices.get(node_id)
            if device:
                device.last_seen_at = time.time()
                if ip_address:
                    device.ip_address = ip_address
                self._save()
