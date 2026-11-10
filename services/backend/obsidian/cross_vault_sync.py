"""
Multi-Vault Obsidian Synchronizer & Cross-Vault Knowledge Graph.
Manages Developer, Research, and Daily Personal Obsidian vaults with
collision-free cross-vault wikilink resolution and unified bidirectional backlink mapping.

Part of Phenom 20.0 Sovereign Autonomous Developer (KNG-02.1).
"""

import os
import re
import time
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional, Set
import yaml
from pydantic import BaseModel, Field

from services.backend.safety.guardian import guardian

logger = logging.getLogger("phenom.obsidian.cross_vault")


class VaultNote(BaseModel):
    node_id: str = Field(..., description="Globally unique node ID e.g. dev:ADR-001")
    vault: str = Field(..., description="Origin vault name: dev, research, daily, etc.")
    title: str = Field(..., description="Note title without extension")
    relative_path: str = Field(..., description="Path relative to vault root")
    absolute_path: str = Field(..., description="Absolute path on disk")
    frontmatter: Dict[str, Any] = Field(default_factory=dict, description="Parsed YAML metadata")
    tags: List[str] = Field(default_factory=list, description="Tags declared in frontmatter and body")
    outgoing_links: List[str] = Field(default_factory=list, description="Target wikilinks [[Target]]")
    backlinks: List[str] = Field(default_factory=list, description="Incoming backlinks from other notes")
    size_bytes: int = Field(default=0, description="File size on disk")
    modified_time: float = Field(default=0.0, description="Last modification timestamp")


class CrossVaultGraph(BaseModel):
    nodes: List[VaultNote] = Field(default_factory=list, description="All indexed vault notes")
    edges: List[Dict[str, str]] = Field(default_factory=list, description="Wikilink edges {source, target}")
    tag_taxonomy: Dict[str, List[str]] = Field(default_factory=dict, description="Tag to node_ids index")
    total_notes: int = Field(default=0, description="Total indexed notes")
    total_links: int = Field(default=0, description="Total wikilinks resolved")


class CrossVaultManager:
    """
    Synchronizes multiple Obsidian vaults, resolving cross-vault wikilinks and maintaining a live graph.
    """

    FRONTMATTER_RE = re.compile(r"^---\s*\n(.*?)\n---\s*\n", re.DOTALL)
    WIKILINK_RE = re.compile(r"\[\[([^\|\]\n]+)(?:\|[^\]\n]+)?\]\]")
    INLINE_TAG_RE = re.compile(r"(?:^|\s)#([a-zA-Z0-9_\-\/]+)")

    def __init__(self, base_dir: Optional[str] = None):
        root = Path(base_dir).resolve() if base_dir else Path(__file__).resolve().parent.parent.parent.parent
        self.vaults: Dict[str, Path] = {
            "dev": root / "vault" / "developer",
            "research": root / "vault" / "research",
            "daily": root / "vault" / "daily",
        }
        self._notes: Dict[str, VaultNote] = {}
        self._backlinks: Dict[str, Set[str]] = {}
        self._tag_index: Dict[str, Set[str]] = {}
        self._ensure_vault_dirs()

    def _ensure_vault_dirs(self) -> None:
        for p in self.vaults.values():
            try:
                p.mkdir(parents=True, exist_ok=True)
            except Exception:
                pass

    def register_vault(self, name: str, path: str) -> None:
        """Registers a custom vault path."""
        p = Path(path).resolve()
        p.mkdir(parents=True, exist_ok=True)
        self.vaults[name] = p

    def parse_note(self, vault_name: str, file_path: Path) -> Optional[VaultNote]:
        """Parses a markdown note, extracting YAML frontmatter, tags, and wikilinks."""
        try:
            content = file_path.read_text(encoding="utf-8", errors="replace")
        except Exception:
            return None

        stat = file_path.stat()
        title = file_path.stem
        node_id = f"{vault_name}:{title}"

        # 1. Frontmatter
        frontmatter: Dict[str, Any] = {}
        body = content
        fm_match = self.FRONTMATTER_RE.match(content)
        if fm_match:
            try:
                parsed_fm = yaml.safe_load(fm_match.group(1))
                if isinstance(parsed_fm, dict):
                    frontmatter = parsed_fm
            except Exception:
                pass
            body = content[fm_match.end():]

        # 2. Tags
        tags_set: Set[str] = set()
        if "tags" in frontmatter:
            raw_tags = frontmatter["tags"]
            if isinstance(raw_tags, list):
                for t in raw_tags:
                    tags_set.add(str(t).lstrip("#"))
            elif isinstance(raw_tags, str):
                tags_set.add(raw_tags.lstrip("#"))

        for match in self.INLINE_TAG_RE.finditer(body):
            tags_set.add(match.group(1).lstrip("#"))

        # 3. Outgoing Wikilinks
        outgoing: List[str] = []
        for match in self.WIKILINK_RE.finditer(body):
            raw_target = match.group(1).strip()
            # If target has vault prefix e.g. dev:NoteName or research:NoteName
            if ":" in raw_target:
                outgoing.append(raw_target)
            else:
                # Default link within same vault
                outgoing.append(f"{vault_name}:{raw_target}")

        rel_path = str(file_path.relative_to(self.vaults[vault_name]))

        return VaultNote(
            node_id=node_id,
            vault=vault_name,
            title=title,
            relative_path=rel_path,
            absolute_path=str(file_path),
            frontmatter=frontmatter,
            tags=sorted(list(tags_set)),
            outgoing_links=outgoing,
            backlinks=[],
            size_bytes=stat.st_size,
            modified_time=stat.st_mtime,
        )

    def sync_all_vaults(self) -> CrossVaultGraph:
        """
        Scans all registered vaults, rebuilds graph nodes, resolves links, and maps bidirectional backlinks.
        """
        if guardian.is_halted:
            raise PermissionError("Guardian kill switch is active. Cross-vault sync halted.")

        self._ensure_vault_dirs()
        raw_notes: Dict[str, VaultNote] = {}
        backlinks: Dict[str, Set[str]] = {}
        tag_index: Dict[str, Set[str]] = {}

        # 1. Ingest notes across all vaults
        for vault_name, vault_path in self.vaults.items():
            if not vault_path.exists():
                continue
            for item in vault_path.rglob("*.md"):
                if item.is_file():
                    note = self.parse_note(vault_name, item)
                    if note:
                        raw_notes[note.node_id] = note

        # 2. Build bidirectional backlinks and tag taxonomy
        edges: List[Dict[str, str]] = []
        for src_id, note in raw_notes.items():
            # Index tags
            for t in note.tags:
                if t not in tag_index:
                    tag_index[t] = set()
                tag_index[t].add(src_id)

            # Map outgoing links to backlinks
            for target_id in note.outgoing_links:
                edges.append({"source": src_id, "target": target_id})
                if target_id not in backlinks:
                    backlinks[target_id] = set()
                backlinks[target_id].add(src_id)

        # 3. Populate backlinks into notes
        for node_id, note in raw_notes.items():
            if node_id in backlinks:
                note.backlinks = sorted(list(backlinks[node_id]))

        self._notes = raw_notes
        self._backlinks = backlinks
        self._tag_index = tag_index

        tag_taxonomy = {t: sorted(list(ids)) for t, ids in tag_index.items()}

        return CrossVaultGraph(
            nodes=list(raw_notes.values()),
            edges=edges,
            tag_taxonomy=tag_taxonomy,
            total_notes=len(raw_notes),
            total_links=len(edges),
        )

    def get_note(self, node_id: str) -> Optional[VaultNote]:
        """Retrieves note by node_id."""
        return self._notes.get(node_id)

    def search_graph(
        self,
        query: str = "",
        vault: Optional[str] = None,
        tag: Optional[str] = None,
    ) -> List[VaultNote]:
        """Searches graph by text, vault name, or tag."""
        if guardian.is_halted:
            raise PermissionError("Guardian kill switch is active. Graph search halted.")

        results: List[VaultNote] = []
        q_lower = query.lower()

        for note in self._notes.values():
            if vault and note.vault != vault:
                continue
            if tag and tag not in note.tags:
                continue
            if query and (q_lower not in note.title.lower() and not any(q_lower in t.lower() for t in note.tags)):
                continue
            results.append(note)

        return results

    def get_visualization_data(self, limit: int = 60) -> Dict[str, Any]:
        """Returns node-link payload formatted for frontend D3 / SVG graph renderer."""
        nodes_list = []
        for note in list(self._notes.values())[:limit]:
            nodes_list.append({
                "id": note.node_id,
                "label": note.title,
                "vault": note.vault,
                "tags": note.tags,
                "linkCount": len(note.outgoing_links) + len(note.backlinks),
            })

        active_ids = {n["id"] for n in nodes_list}
        links_list = []
        for note in list(self._notes.values())[:limit]:
            for target in note.outgoing_links:
                if target in active_ids:
                    links_list.append({"source": note.node_id, "target": target})

        return {
            "nodes": nodes_list,
            "links": links_list,
            "total_nodes": len(self._notes),
            "total_links": sum(len(n.outgoing_links) for n in self._notes.values()),
        }


# Global singleton
cross_vault_manager = CrossVaultManager()
