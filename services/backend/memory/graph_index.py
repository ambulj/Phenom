"""
Phenom Obsidian Knowledge Graph Indexer
Builds and maintains an in-memory bidirectional knowledge graph for Obsidian markdown notes.
Extracts [[wikilinks]], inline #tags, and YAML frontmatter metadata.
Discovers orphan notes, dangling links, and concept hubs.
"""

import os
import re
import yaml
import logging
from typing import Dict, Any, List, Set, Optional

from services.backend.memory.vault import vault_manager, resolve_and_sandbox_vault_path

logger = logging.getLogger("phenom.graph_index")

WIKILINK_REGEX = re.compile(r"\[\[([^\]\|\#]+)(?:#[^\]\|]+)?(?:\|[^\]]+)?\]\]")
INLINE_TAG_REGEX = re.compile(r"(?:^|\s)#([a-zA-Z][a-zA-Z0-9_\-\/]*)")
FRONTMATTER_REGEX = re.compile(r"^---\s*\n(.*?)\n---\s*\n", re.DOTALL)


class ObsidianGraphNode:
    def __init__(
        self,
        title: str,
        filename: str,
        rel_path: str,
        word_count: int = 0,
        mtime: float = 0.0
    ):
        self.title: str = title
        self.filename: str = filename
        self.rel_path: str = rel_path
        self.word_count: int = word_count
        self.mtime: float = mtime
        self.tags: Set[str] = set()
        self.aliases: List[str] = []
        self.links_out: Set[str] = set()
        self.links_in: Set[str] = set()

    def to_dict(self) -> Dict[str, Any]:
        return {
            "title": self.title,
            "filename": self.filename,
            "rel_path": self.rel_path,
            "word_count": self.word_count,
            "mtime": self.mtime,
            "tags": sorted(list(self.tags)),
            "aliases": self.aliases,
            "links_out": sorted(list(self.links_out)),
            "links_in": sorted(list(self.links_in)),
            "is_orphan": (len(self.links_out) == 0 and len(self.links_in) == 0)
        }


class ObsidianGraphIndex:
    """
    Bidirectional graph model for the Obsidian second-brain vault.
    """

    def __init__(self, vault_path: Optional[str] = None):
        self.vault_path = os.path.abspath(vault_path or vault_manager.vault_path)
        self.nodes: Dict[str, ObsidianGraphNode] = {}
        self.tag_index: Dict[str, Set[str]] = {}
        self.dangling_links: Set[str] = set()

    def normalize_title(self, raw_title: str) -> str:
        """Normalizes note title for case-insensitive matching."""
        clean = raw_title.strip()
        if clean.endswith(".md"):
            clean = clean[:-3]
        return clean

    def build_index(self) -> Dict[str, Any]:
        """
        Scans vault and reconstructs the full bidirectional graph.
        """
        self.nodes.clear()
        self.tag_index.clear()
        self.dangling_links.clear()

        if not os.path.exists(self.vault_path):
            return {"total_notes": 0, "total_links": 0, "orphans_count": 0}

        # 1. First Pass: Create nodes and extract outgoing links & metadata
        for root, dirs, files in os.walk(self.vault_path):
            # Exclude git and obsidian configuration dirs
            dirs[:] = [d for d in dirs if d not in (".git", ".obsidian", "node_modules")]

            for file in files:
                if not file.endswith(".md"):
                    continue

                full_p = os.path.join(root, file)
                rel_p = os.path.relpath(full_p, self.vault_path)
                title = self.normalize_title(file)

                try:
                    with open(full_p, "r", encoding="utf-8", errors="replace") as f:
                        content = f.read()
                except Exception as e:
                    logger.debug(f"Failed to read note {rel_p}: {e}")
                    continue

                node = ObsidianGraphNode(
                    title=title,
                    filename=file,
                    rel_path=rel_p,
                    word_count=len(content.split()),
                    mtime=os.path.getmtime(full_p)
                )

                # Parse Frontmatter
                fm_match = FRONTMATTER_REGEX.match(content)
                body = content
                if fm_match:
                    raw_yaml = fm_match.group(1)
                    body = content[fm_match.end():]
                    try:
                        parsed_yaml = yaml.safe_load(raw_yaml)
                        if isinstance(parsed_yaml, dict):
                            # Tags in YAML
                            raw_tags = parsed_yaml.get("tags") or []
                            if isinstance(raw_tags, str):
                                raw_tags = [t.strip() for t in raw_tags.split(",")]
                            for t in raw_tags:
                                clean_t = str(t).lstrip("#").strip()
                                if clean_t:
                                    node.tags.add(clean_t.lower())

                            # Aliases
                            raw_aliases = parsed_yaml.get("aliases") or []
                            if isinstance(raw_aliases, str):
                                raw_aliases = [a.strip() for a in raw_aliases.split(",")]
                            node.aliases = [str(a).strip() for a in raw_aliases if a]
                    except Exception:
                        pass

                # Parse Inline Tags
                inline_tags = INLINE_TAG_REGEX.findall(body)
                for t in inline_tags:
                    node.tags.add(t.lower())

                # Parse Wikilinks
                links = WIKILINK_REGEX.findall(body)
                for target in links:
                    norm_target = self.normalize_title(target)
                    if norm_target and norm_target.lower() != title.lower():
                        node.links_out.add(norm_target)

                # Store node by normalized lowercase key
                self.nodes[title.lower()] = node

                # Update tag reverse index
                for t in node.tags:
                    if t not in self.tag_index:
                        self.tag_index[t] = set()
                    self.tag_index[t].add(title)

        # 2. Second Pass: Resolve incoming backlinks and detect dangling links
        total_links = 0
        for node in self.nodes.values():
            for target_title in node.links_out:
                target_key = target_title.lower()
                if target_key in self.nodes:
                    self.nodes[target_key].links_in.add(node.title)
                    total_links += 1
                else:
                    self.dangling_links.add(target_title)

        orphans = self.get_orphans()
        return {
            "total_notes": len(self.nodes),
            "total_links": total_links,
            "orphans_count": len(orphans),
            "dangling_count": len(self.dangling_links),
            "tags_count": len(self.tag_index)
        }

    def get_node(self, title: str) -> Optional[ObsidianGraphNode]:
        """Retrieves a node by note title (case-insensitive)."""
        key = self.normalize_title(title).lower()
        return self.nodes.get(key)

    def get_orphans(self) -> List[Dict[str, Any]]:
        """Returns all notes with zero incoming and zero outgoing links."""
        orphans = []
        for node in self.nodes.values():
            if len(node.links_out) == 0 and len(node.links_in) == 0:
                orphans.append(node.to_dict())
        return sorted(orphans, key=lambda n: n["mtime"], reverse=True)

    def get_concept_hubs(self, top_k: int = 5) -> List[Dict[str, Any]]:
        """Returns top hub notes ranked by degree centrality (links in + links out)."""
        hubs = []
        for node in self.nodes.values():
            degree = len(node.links_in) + len(node.links_out)
            if degree > 0:
                hubs.append({
                    "title": node.title,
                    "degree": degree,
                    "links_in_count": len(node.links_in),
                    "links_out_count": len(node.links_out),
                    "rel_path": node.rel_path
                })
        return sorted(hubs, key=lambda h: h["degree"], reverse=True)[:top_k]

    def get_backlinks(self, title: str) -> List[str]:
        """Returns note titles that link to the specified note."""
        node = self.get_node(title)
        return sorted(list(node.links_in)) if node else []

    def get_forward_links(self, title: str) -> List[str]:
        """Returns note titles linked from the specified note."""
        node = self.get_node(title)
        return sorted(list(node.links_out)) if node else []

    def get_notes_by_tag(self, tag: str) -> List[str]:
        """Returns note titles tagged with the specified tag."""
        clean_tag = tag.lstrip("#").lower().strip()
        return sorted(list(self.tag_index.get(clean_tag, set())))

    def get_connected_subgraph(self, title: str, hops: int = 1) -> Dict[str, Any]:
        """
        Extracts a local neighborhood subgraph around the specified note.
        """
        center_node = self.get_node(title)
        if not center_node:
            return {"center": title, "nodes": [], "edges": []}

        visited_titles: Set[str] = {center_node.title}
        frontier: Set[str] = {center_node.title}

        for _ in range(hops):
            next_frontier = set()
            for current_title in frontier:
                curr = self.get_node(current_title)
                if curr:
                    neighbors = curr.links_out.union(curr.links_in)
                    for n in neighbors:
                        if n not in visited_titles:
                            visited_titles.add(n)
                            next_frontier.add(n)
            frontier = next_frontier

        subgraph_nodes = []
        edges = []
        for t in visited_titles:
            n = self.get_node(t)
            if n:
                subgraph_nodes.append(n.to_dict())
                for target in n.links_out:
                    if target in visited_titles:
                        edges.append({"from": n.title, "to": target})

        return {
            "center": center_node.title,
            "nodes": subgraph_nodes,
            "edges": edges,
            "node_count": len(subgraph_nodes),
            "edge_count": len(edges)
        }


# Global graph index singleton
graph_index = ObsidianGraphIndex()
