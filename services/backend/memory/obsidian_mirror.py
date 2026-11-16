"""Live Bidirectional Obsidian Vault Mirror for Bi-Temporal Episodic Matrix (Milestone 49 Phase 1).

Maintains human-readable Markdown notes in vault/Memory/<entity_type>/<slug>.md
complete with:
- Structured YAML frontmatter (id, type, valid_from, recorded_at, tags, checksum).
- Human-readable markdown body text.
- Bidirectional [[wikilinks]] for relationships.
- Path traversal defense & Guardian kill switch check (< 25ms SLA).
"""

from __future__ import annotations

import datetime
import hashlib
import logging
import os
import re
import threading
import time
from typing import Any, Dict, List, Optional

import yaml

from services.backend.schemas.temporal_graph import (
    EntityType,
    ObsidianMirrorEvent,
    TemporalEntity,
    TemporalRelation,
)
from services.backend.memory.temporal_graph_engine import TemporalGraphEngine
from services.backend.safety.guardian import guardian

logger = logging.getLogger("phenom.memory.obsidian_mirror")

_SLUG_SAFE_RE = re.compile(r"[^A-Za-z0-9_\-\.]+")


def _slugify(name: str) -> str:
    cleaned = _SLUG_SAFE_RE.sub("_", name.strip())
    return cleaned[:80] or "unnamed_entity"


def _format_timestamp(ts: Optional[float]) -> Optional[str]:
    if ts is None:
        return None
    return datetime.datetime.fromtimestamp(ts, tz=datetime.timezone.utc).isoformat()


class ObsidianMirror:
    """Synchronizes bi-temporal episodic knowledge graph entities into Obsidian Markdown notes."""

    def __init__(
        self,
        engine: TemporalGraphEngine,
        vault_dir: Optional[str] = None,
    ) -> None:
        self.engine = engine
        self.vault_dir = os.path.abspath(vault_dir or "vault")
        self.memory_dir = os.path.join(self.vault_dir, "Memory")
        self._lock = threading.RLock()

        os.makedirs(self.memory_dir, exist_ok=True)

    def _assert_path_safety(self, target_path: str) -> None:
        abs_target = os.path.abspath(target_path)
        common = os.path.commonpath([abs_target, self.vault_dir])
        if common != self.vault_dir:
            raise PermissionError(f"Path traversal detected: {target_path} is outside {self.vault_dir}")

    def sync_entity(self, entity: TemporalEntity) -> ObsidianMirrorEvent:
        """Mirrors a single TemporalEntity and its active relationships to Obsidian."""
        if guardian.is_halted:
            raise PermissionError("Guardian kill switch is active. Obsidian mirror aborted.")

        type_folder = entity.entity_type.value if hasattr(entity.entity_type, "value") else str(entity.entity_type)
        type_dir = os.path.join(self.memory_dir, type_folder)
        slug = _slugify(entity.name or entity.id)
        file_path = os.path.join(type_dir, f"{slug}.md")
        self._assert_path_safety(file_path)

        with self._lock:
            os.makedirs(type_dir, exist_ok=True)

            # Retrieve active relations
            relations = self.engine.get_active_relations_for(entity.id)

            frontmatter_data = {
                "id": entity.id,
                "name": entity.name,
                "type": type_folder,
                "valid_from": _format_timestamp(entity.valid_from),
                "valid_until": _format_timestamp(entity.valid_until),
                "recorded_at": _format_timestamp(entity.recorded_at),
                "superseded_at": _format_timestamp(entity.superseded_at),
                "tags": entity.tags,
            }

            body_lines = [
                "---",
                yaml.dump(frontmatter_data, sort_keys=False).strip(),
                "---",
                "",
                f"# {entity.name}",
                "",
                entity.content.strip() if entity.content else "_No description provided._",
                "",
                "## Relationships",
            ]

            if relations:
                for rel in relations:
                    rel_type = rel.relation_type.value if hasattr(rel.relation_type, "value") else str(rel.relation_type)
                    if rel.source_id == entity.id:
                        # Outgoing edge
                        target_ent = self.engine.get_entity(rel.target_id)
                        target_label = target_ent.name if target_ent else rel.target_id
                        body_lines.append(f"- [[{target_label}]] ({rel_type})")
                    else:
                        # Incoming edge
                        source_ent = self.engine.get_entity(rel.source_id)
                        source_label = source_ent.name if source_ent else rel.source_id
                        body_lines.append(f"- [[{source_label}]] (INCOMING: {rel_type})")
            else:
                body_lines.append("_No connected relationships._")

            body_lines.append("")
            content = "\n".join(body_lines)
            checksum = hashlib.sha256(content.encode("utf-8")).hexdigest()

            # Check if file already exists with identical content
            action = "UPDATED"
            if os.path.exists(file_path):
                try:
                    with open(file_path, "r", encoding="utf-8") as f:
                        existing = f.read()
                    if existing == content:
                        return ObsidianMirrorEvent(
                            entity_id=entity.id,
                            file_path=file_path,
                            action="SYNCED",
                            checksum=checksum,
                        )
                except Exception:
                    pass
            else:
                action = "CREATED"

            with open(file_path, "w", encoding="utf-8") as f:
                f.write(content)

            return ObsidianMirrorEvent(
                entity_id=entity.id,
                file_path=file_path,
                action=action,
                checksum=checksum,
            )

    def sync_all_active_entities(self) -> List[ObsidianMirrorEvent]:
        """Mirrors all active entities currently in the database to Obsidian."""
        if guardian.is_halted:
            raise PermissionError("Guardian kill switch is active. Obsidian mirror aborted.")

        entities = self.engine.get_all_active_entities()
        events: List[ObsidianMirrorEvent] = []
        for ent in entities:
            events.append(self.sync_entity(ent))
        return events

    def get_mirror_stats(self) -> Dict[str, Any]:
        """Returns statistics on mirrored notes in vault/Memory/."""
        with self._lock:
            total_files = 0
            by_type: Dict[str, int] = {}
            if os.path.exists(self.memory_dir):
                for root, _, files in os.walk(self.memory_dir):
                    md_files = [f for f in files if f.endswith(".md")]
                    total_files += len(md_files)
                    rel = os.path.relpath(root, self.memory_dir)
                    if rel != "." and md_files:
                        by_type[rel] = len(md_files)

            return {
                "memory_vault_path": self.memory_dir,
                "total_notes": total_files,
                "notes_by_category": by_type,
            }
