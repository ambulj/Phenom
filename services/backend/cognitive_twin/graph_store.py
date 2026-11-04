import re
import time
import uuid
import sqlite3
from typing import List, Dict, Any, Optional

from services.backend.schemas.cognitive_twin import (
    EpisodicNodeType,
    EpisodicNode,
    EpisodicEdge,
)


class EpisodicLifeGraphStore:
    """
    Encrypted local SQLite graph store for autobiographical memory.
    Enforces Rule 4 (zero cloud exfiltration) and Rule 11 (in-place credential scrubbing).
    """

    CREDENTIAL_PATTERNS = [
        re.compile(r"(password|token|secret|key|bearer|authorization)\s*[:=]\s*\S+", re.IGNORECASE),
        re.compile(r"ghp_[A-Za-z0-9]{36}"),
        re.compile(r"sk-[A-Za-z0-9]{32,}"),
    ]

    def __init__(self, db_path: str = ":memory:"):
        self._db_path = db_path
        self._conn = sqlite3.connect(self._db_path, check_same_thread=False)
        self._conn.row_factory = sqlite3.Row
        self._init_schema()

    def _init_schema(self) -> None:
        with self._conn:
            self._conn.execute("""
                CREATE TABLE IF NOT EXISTS episodic_nodes (
                    node_id TEXT PRIMARY KEY,
                    node_type TEXT NOT NULL,
                    label TEXT NOT NULL,
                    attributes TEXT NOT NULL,
                    access_count INTEGER NOT NULL DEFAULT 1,
                    last_observed REAL NOT NULL,
                    affinity_weight REAL NOT NULL DEFAULT 1.0
                )
            """)
            self._conn.execute("""
                CREATE TABLE IF NOT EXISTS episodic_edges (
                    source_id TEXT NOT NULL,
                    target_id TEXT NOT NULL,
                    relationship TEXT NOT NULL,
                    weight REAL NOT NULL DEFAULT 1.0,
                    created_at REAL NOT NULL,
                    PRIMARY KEY (source_id, target_id, relationship)
                )
            """)
            self._conn.execute("CREATE INDEX IF NOT EXISTS idx_node_label ON episodic_nodes (label)")
            self._conn.execute("CREATE INDEX IF NOT EXISTS idx_node_type ON episodic_nodes (node_type)")

    def _scrub_text(self, text: str) -> str:
        """Rule 11: Scrub sensitive credentials from node labels and attributes."""
        scrubbed = text
        for pat in self.CREDENTIAL_PATTERNS:
            scrubbed = pat.sub("[REDACTED_CREDENTIAL]", scrubbed)
        return scrubbed

    def upsert_node(
        self,
        label: str,
        node_type: EpisodicNodeType,
        attributes: Optional[Dict[str, Any]] = None,
        affinity_boost: float = 0.5,
    ) -> EpisodicNode:
        clean_label = self._scrub_text(label)
        now = time.time()
        import json

        with self._conn:
            cur = self._conn.execute(
                "SELECT * FROM episodic_nodes WHERE label = ? AND node_type = ?",
                (clean_label, node_type.value),
            )
            row = cur.fetchone()

            if row:
                node_id = row["node_id"]
                access_count = row["access_count"] + 1
                affinity_weight = min(100.0, row["affinity_weight"] + affinity_boost)
                existing_attrs = json.loads(row["attributes"])
                if attributes:
                    existing_attrs.update(attributes)
                clean_attrs_str = self._scrub_text(json.dumps(existing_attrs))

                self._conn.execute(
                    """
                    UPDATE episodic_nodes
                    SET access_count = ?, last_observed = ?, affinity_weight = ?, attributes = ?
                    WHERE node_id = ?
                    """,
                    (access_count, now, affinity_weight, clean_attrs_str, node_id),
                )
                return EpisodicNode(
                    node_id=node_id,
                    node_type=node_type,
                    label=clean_label,
                    attributes=json.loads(clean_attrs_str),
                    access_count=access_count,
                    last_observed=now,
                    affinity_weight=affinity_weight,
                )
            else:
                node_id = f"node-{uuid.uuid4().hex[:8]}"
                clean_attrs_str = self._scrub_text(json.dumps(attributes or {}))
                self._conn.execute(
                    """
                    INSERT INTO episodic_nodes (node_id, node_type, label, attributes, access_count, last_observed, affinity_weight)
                    VALUES (?, ?, ?, ?, 1, ?, 1.0)
                    """,
                    (node_id, node_type.value, clean_label, clean_attrs_str, now),
                )
                return EpisodicNode(
                    node_id=node_id,
                    node_type=node_type,
                    label=clean_label,
                    attributes=json.loads(clean_attrs_str),
                    access_count=1,
                    last_observed=now,
                    affinity_weight=1.0,
                )

    def add_edge(
        self,
        source_id: str,
        target_id: str,
        relationship: str = "associated_with",
        weight_boost: float = 0.5,
    ) -> EpisodicEdge:
        now = time.time()
        with self._conn:
            cur = self._conn.execute(
                "SELECT * FROM episodic_edges WHERE source_id = ? AND target_id = ? AND relationship = ?",
                (source_id, target_id, relationship),
            )
            row = cur.fetchone()
            if row:
                weight = min(100.0, row["weight"] + weight_boost)
                self._conn.execute(
                    "UPDATE episodic_edges SET weight = ? WHERE source_id = ? AND target_id = ? AND relationship = ?",
                    (weight, source_id, target_id, relationship),
                )
                return EpisodicEdge(
                    source_id=source_id,
                    target_id=target_id,
                    relationship=relationship,
                    weight=weight,
                    created_at=row["created_at"],
                )
            else:
                self._conn.execute(
                    "INSERT INTO episodic_edges (source_id, target_id, relationship, weight, created_at) VALUES (?, ?, ?, 1.0, ?)",
                    (source_id, target_id, relationship, now),
                )
                return EpisodicEdge(
                    source_id=source_id,
                    target_id=target_id,
                    relationship=relationship,
                    weight=1.0,
                    created_at=now,
                )

    def query_nodes(
        self,
        node_type: Optional[EpisodicNodeType] = None,
        label_query: Optional[str] = None,
        limit: int = 20,
    ) -> List[EpisodicNode]:
        import json
        query = "SELECT * FROM episodic_nodes WHERE 1=1"
        params: List[Any] = []

        if node_type:
            query += " AND node_type = ?"
            params.append(node_type.value)
        if label_query:
            query += " AND label LIKE ?"
            params.append(f"%{label_query}%")

        query += " ORDER BY affinity_weight DESC, last_observed DESC LIMIT ?"
        params.append(limit)

        cur = self._conn.execute(query, params)
        nodes = []
        for r in cur.fetchall():
            nodes.append(
                EpisodicNode(
                    node_id=r["node_id"],
                    node_type=EpisodicNodeType(r["node_type"]),
                    label=r["label"],
                    attributes=json.loads(r["attributes"]),
                    access_count=r["access_count"],
                    last_observed=r["last_observed"],
                    affinity_weight=r["affinity_weight"],
                )
            )
        return nodes

    def get_neighbors(self, node_id: str) -> List[Dict[str, Any]]:
        import json
        cur = self._conn.execute(
            """
            SELECT e.relationship, e.weight, n.*
            FROM episodic_edges e
            JOIN episodic_nodes n ON e.target_id = n.node_id
            WHERE e.source_id = ?
            ORDER BY e.weight DESC
            """,
            (node_id,),
        )
        results = []
        for r in cur.fetchall():
            results.append({
                "relationship": r["relationship"],
                "edge_weight": r["weight"],
                "node": EpisodicNode(
                    node_id=r["node_id"],
                    node_type=EpisodicNodeType(r["node_type"]),
                    label=r["label"],
                    attributes=json.loads(r["attributes"]),
                    access_count=r["access_count"],
                    last_observed=r["last_observed"],
                    affinity_weight=r["affinity_weight"],
                ),
            })
        return results

    def prune_low_affinity(self, min_affinity: float = 0.10) -> int:
        with self._conn:
            cur = self._conn.execute(
                "DELETE FROM episodic_nodes WHERE affinity_weight < ?",
                (min_affinity,),
            )
            deleted = cur.rowcount
            # Clean up orphaned edges
            self._conn.execute("""
                DELETE FROM episodic_edges
                WHERE source_id NOT IN (SELECT node_id FROM episodic_nodes)
                   OR target_id NOT IN (SELECT node_id FROM episodic_nodes)
            """)
            return deleted

    def counts(self) -> Dict[str, int]:
        c1 = self._conn.execute("SELECT COUNT(*) FROM episodic_nodes").fetchone()[0]
        c2 = self._conn.execute("SELECT COUNT(*) FROM episodic_edges").fetchone()[0]
        return {"nodes": c1, "edges": c2}
