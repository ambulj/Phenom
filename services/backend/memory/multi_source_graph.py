"""
Phenom Unified Multi-Source Personal Knowledge Graph Engine
Coordinates knowledge nodes across 4 personal domains:
1. Obsidian vault notes (vault://)
2. Code repositories and git history (code://, git://)
3. Local documents and PDF chunks (doc://)
4. Workspace emails and calendar meetings (email://, meeting://)

Features:
- Bidirectional typed relationships (references, implements, discussed_in, authored_by, documents, calls, contains)
- Heuristic cross-domain link synthesis
- Topology analytics (orphan nodes, concept hub centrality)
- Credential sanitization
- Synchronous sub-1ms Guardian kill switch halt and clean state reset
"""

from __future__ import annotations

import logging
import os
import time
from collections import defaultdict
from typing import Any, Dict, List, Optional, Set, Tuple

from services.backend.memory.graph_parsers import (
    CodeRepositoryParser,
    DocumentParser,
    ObsidianVaultParser,
    WorkspaceHistoryParser,
    is_secret_or_ignored_file,
    scrub_credentials,
)
from services.backend.safety.guardian import guardian
from services.backend.schemas.graph_rag import GraphEdge, GraphNode, GraphStats

logger = logging.getLogger("phenom.multi_source_graph")


class MultiSourceKnowledgeGraph:
    """
    In-memory cross-domain personal knowledge graph.
    Maintains deterministic URIs, bidirectional adjacency lists, and domain indexes.
    """

    def __init__(self) -> None:
        self._nodes: Dict[str, GraphNode] = {}
        self._out_edges: Dict[str, Set[GraphEdge]] = defaultdict(set)
        self._in_edges: Dict[str, Set[GraphEdge]] = defaultdict(set)
        self._domain_index: Dict[str, Set[str]] = defaultdict(set)

        self._is_indexing: bool = False
        self._is_halted: bool = False

        # Parsers
        self.vault_parser = ObsidianVaultParser()
        self.code_parser = CodeRepositoryParser()
        self.doc_parser = DocumentParser()
        self.workspace_parser = WorkspaceHistoryParser()

    @property
    def is_halted(self) -> bool:
        return self._is_halted or getattr(guardian, "is_halted", False)

    @property
    def is_indexing(self) -> bool:
        return self._is_indexing

    def halt(self) -> None:
        """Synchronously halts all graph indexing and traversal immediately (< 1ms)."""
        self._is_halted = True
        self._is_indexing = False
        logger.info("MultiSourceKnowledgeGraph halted by Guardian kill switch.")

    def reset(self) -> None:
        """Resets halted state when Guardian transitions back to idle."""
        self._is_halted = False
        self._is_indexing = False
        logger.info("MultiSourceKnowledgeGraph reset to active state.")

    def clear(self) -> None:
        """Clears all nodes and edges from the graph."""
        self._nodes.clear()
        self._out_edges.clear()
        self._in_edges.clear()
        self._domain_index.clear()

    def clear_domain(self, domain: str) -> None:
        """Removes all nodes belonging to a specific domain."""
        node_ids_to_remove = list(self._domain_index.get(domain, set()))
        for nid in node_ids_to_remove:
            self.remove_node(nid)
        self._domain_index.pop(domain, None)

    def add_node(self, node: GraphNode) -> None:
        """
        Inserts or updates a node in the graph.
        Applies credential scrubbing to title and summary.
        Maintains domain index and associated edges.
        """
        if self.is_halted:
            raise PermissionError("MultiSourceKnowledgeGraph is halted by Guardian.")

        node.title = scrub_credentials(node.title)
        node.summary = scrub_credentials(node.summary)

        # Remove previous edges if updating existing node
        if node.node_id in self._nodes:
            self._remove_node_edges(node.node_id)

        self._nodes[node.node_id] = node
        self._domain_index[node.domain].add(node.node_id)

        # Register outgoing edges
        for edge in node.edges:
            self.add_edge(edge)

    def add_edge(self, edge: GraphEdge) -> None:
        """Registers a directed typed edge and updates in/out adjacency sets."""
        if self.is_halted:
            raise PermissionError("MultiSourceKnowledgeGraph is halted by Guardian.")

        self._out_edges[edge.source_id].add(edge)
        self._in_edges[edge.target_id].add(edge)

    def _remove_node_edges(self, node_id: str) -> None:
        """Removes all in/out edges associated with a node."""
        out_edges = list(self._out_edges.get(node_id, set()))
        for e in out_edges:
            self._in_edges[e.target_id].discard(e)
        self._out_edges.pop(node_id, None)

        in_edges = list(self._in_edges.get(node_id, set()))
        for e in in_edges:
            self._out_edges[e.source_id].discard(e)
        self._in_edges.pop(node_id, None)

    def remove_node(self, node_id: str) -> bool:
        """Removes a node and its associated in/out edges."""
        if node_id not in self._nodes:
            return False

        node = self._nodes.pop(node_id)
        self._domain_index[node.domain].discard(node_id)
        self._remove_node_edges(node_id)
        return True

    def get_node(self, node_id: str) -> Optional[GraphNode]:
        """Returns node by deterministic URI."""
        return self._nodes.get(node_id)

    def list_nodes(self, domain: Optional[str] = None) -> List[GraphNode]:
        """Returns all nodes, optionally filtered by domain."""
        if domain:
            ids = self._domain_index.get(domain, set())
            return [self._nodes[nid] for nid in ids if nid in self._nodes]
        return list(self._nodes.values())

    def get_neighbors(
        self,
        node_id: str,
        direction: str = "both"
    ) -> List[Tuple[GraphNode, GraphEdge]]:
        """
        Returns direct 1-hop neighbor nodes along with their connecting edges.
        direction: 'out', 'in', or 'both'.
        """
        results: List[Tuple[GraphNode, GraphEdge]] = []
        seen_targets: Set[str] = set()

        if direction in ("out", "both"):
            for edge in self._out_edges.get(node_id, set()):
                target_node = self._nodes.get(edge.target_id)
                if target_node and target_node.node_id not in seen_targets:
                    results.append((target_node, edge))
                    seen_targets.add(target_node.node_id)

        if direction in ("in", "both"):
            for edge in self._in_edges.get(node_id, set()):
                source_node = self._nodes.get(edge.source_id)
                if source_node and source_node.node_id not in seen_targets:
                    results.append((source_node, edge))
                    seen_targets.add(source_node.node_id)

        return results

    def get_subgraph(
        self,
        seed_node_ids: List[str],
        hops: int = 1
    ) -> Tuple[List[GraphNode], List[GraphEdge]]:
        """
        Assembles connected subgraph starting from seed nodes up to N hops.
        Returns unique nodes and traversed edges.
        """
        if self.is_halted:
            raise PermissionError("MultiSourceKnowledgeGraph is halted by Guardian.")

        visited_nodes: Dict[str, GraphNode] = {}
        collected_edges: Set[GraphEdge] = set()
        current_frontier: Set[str] = set()

        for sid in seed_node_ids:
            node = self._nodes.get(sid)
            if node:
                visited_nodes[sid] = node
                current_frontier.add(sid)

        for _ in range(hops):
            next_frontier: Set[str] = set()
            for curr_id in current_frontier:
                # Traverse out-edges
                for edge in self._out_edges.get(curr_id, set()):
                    collected_edges.add(edge)
                    target = self._nodes.get(edge.target_id)
                    if target and target.node_id not in visited_nodes:
                        visited_nodes[target.node_id] = target
                        next_frontier.add(target.node_id)

                # Traverse in-edges
                for edge in self._in_edges.get(curr_id, set()):
                    collected_edges.add(edge)
                    source = self._nodes.get(edge.source_id)
                    if source and source.node_id not in visited_nodes:
                        visited_nodes[source.node_id] = source
                        next_frontier.add(source.node_id)

            current_frontier = next_frontier
            if not current_frontier:
                break

        return list(visited_nodes.values()), list(collected_edges)

    def synthesize_cross_domain_links(self) -> int:
        """
        Cross-domain link synthesizer:
        Heuristically correlates nodes across different domains:
        1. Links Vault notes mentioning Code symbols or doc titles to code:// or doc:// nodes.
        2. Links Calendar meetings and Emails discussing code symbols or vault notes.
        3. Links Git commits to Vault notes referencing the same feature.
        Returns number of new synthesized edges.
        """
        if self.is_halted:
            return 0

        new_edges_count = 0
        all_nodes = list(self._nodes.values())

        # Build symbol & title index
        # title -> list of nodes
        title_index: Dict[str, List[GraphNode]] = defaultdict(list)
        for n in all_nodes:
            if len(n.title) >= 4:
                title_index[n.title.lower()].append(n)

        # Cross-correlate nodes
        for node in all_nodes:
            text_corpus = f"{node.title} {node.summary}".lower()

            for target_title, candidates in title_index.items():
                if target_title in text_corpus:
                    for candidate in candidates:
                        if candidate.node_id == node.node_id or candidate.domain == node.domain:
                            continue

                        # Determine relation based on domains
                        if node.domain in ("meeting", "email"):
                            rel = "discussed_in"
                        elif node.domain == "vault" and candidate.domain == "code":
                            rel = "documents"
                        elif node.domain == "code" and candidate.domain == "vault":
                            rel = "implements"
                        elif node.domain == "code" and candidate.domain == "doc":
                            rel = "implements"
                        else:
                            rel = "references"

                        new_edge = GraphEdge(
                            source_id=node.node_id,
                            target_id=candidate.node_id,
                            relation=rel,
                            weight=0.85,
                            metadata={"synthesized": True, "term": target_title}
                        )

                        # Check if edge already exists
                        if new_edge not in self._out_edges.get(node.node_id, set()):
                            self.add_edge(new_edge)
                            new_edges_count += 1

        logger.info(f"Cross-domain link synthesizer generated {new_edges_count} new edges.")
        return new_edges_count

    def get_stats(self) -> GraphStats:
        """Calculates topology statistics, orphan nodes, and concept hub centrality."""
        total_nodes = len(self._nodes)
        total_edges = sum(len(edges) for edges in self._out_edges.values())

        domain_breakdown: Dict[str, int] = {
            dom: len(ids) for dom, ids in self._domain_index.items()
        }

        orphan_count = 0
        hub_count = 0

        for nid in self._nodes:
            in_deg = len(self._in_edges.get(nid, set()))
            out_deg = len(self._out_edges.get(nid, set()))
            total_deg = in_deg + out_deg

            if total_deg == 0:
                orphan_count += 1
            elif total_deg >= 4:
                hub_count += 1

        return GraphStats(
            total_nodes=total_nodes,
            total_edges=total_edges,
            domain_breakdown=domain_breakdown,
            orphan_count=orphan_count,
            hub_count=hub_count,
            is_indexing=self._is_indexing,
            is_halted=self.is_halted
        )

    # ==========================================================================
    # Domain Ingestion Routines
    # ==========================================================================

    def index_vault(self, vault_root: Optional[str] = None) -> int:
        """Parses and ingests Obsidian vault notes."""
        if self.is_halted:
            raise PermissionError("MultiSourceKnowledgeGraph is halted by Guardian.")

        self._is_indexing = True
        try:
            nodes = self.vault_parser.parse_vault(vault_root)
            for node in nodes:
                if self.is_halted:
                    break
                self.add_node(node)
            return len(nodes)
        finally:
            self._is_indexing = False

    def index_code_file(self, file_path: str, repo_root: Optional[str] = None) -> int:
        """Parses and ingests symbols from a single code file."""
        if self.is_halted or is_secret_or_ignored_file(file_path):
            return 0
        nodes = self.code_parser.parse_file(file_path, repo_root)
        for node in nodes:
            self.add_node(node)
        return len(nodes)

    def index_code_repo(
        self,
        repo_root: Optional[str] = None,
        max_files: int = 200,
        include_git: bool = True
    ) -> int:
        """Scans code repository, parsing source code AST and git history."""
        if self.is_halted:
            raise PermissionError("MultiSourceKnowledgeGraph is halted by Guardian.")

        root = repo_root or self.code_parser.repo_root
        if not root or not os.path.isdir(root):
            return 0

        self._is_indexing = True
        ingested_count = 0
        try:
            file_count = 0
            for dirpath, dirnames, filenames in os.walk(root):
                if self.is_halted:
                    break
                # Skip ignored directories
                dirnames[:] = [d for d in dirnames if not is_secret_or_ignored_file(os.path.join(dirpath, d))]

                for fname in filenames:
                    if self.is_halted or file_count >= max_files:
                        break
                    if fname.endswith((".py", ".ts", ".tsx", ".js")):
                        full_path = os.path.join(dirpath, fname)
                        if not is_secret_or_ignored_file(full_path):
                            cnt = self.index_code_file(full_path, root)
                            ingested_count += cnt
                            file_count += 1

            if include_git and not self.is_halted:
                git_nodes = self.code_parser.parse_git_history(root, max_commits=30)
                for gnode in git_nodes:
                    self.add_node(gnode)
                    ingested_count += 1

            return ingested_count
        finally:
            self._is_indexing = False

    def index_document(self, file_path: str, doc_root: Optional[str] = None) -> int:
        """Parses and ingests a local document with semantic chunking."""
        if self.is_halted or is_secret_or_ignored_file(file_path):
            return 0
        nodes = self.doc_parser.parse_document(file_path, doc_root)
        for node in nodes:
            self.add_node(node)
        return len(nodes)

    def index_workspace(
        self,
        emails: Optional[List[Dict[str, Any]]] = None,
        meetings: Optional[List[Dict[str, Any]]] = None
    ) -> int:
        """Ingests email threads and calendar meetings."""
        if self.is_halted:
            raise PermissionError("MultiSourceKnowledgeGraph is halted by Guardian.")

        count = 0
        if emails:
            e_nodes = self.workspace_parser.parse_email_threads(emails)
            for node in e_nodes:
                self.add_node(node)
                count += 1

        if meetings:
            m_nodes = self.workspace_parser.parse_calendar_events(meetings)
            for node in m_nodes:
                self.add_node(node)
                count += 1

        return count


# Global singleton instance
multi_source_graph = MultiSourceKnowledgeGraph()
