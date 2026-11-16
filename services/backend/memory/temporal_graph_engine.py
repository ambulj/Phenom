"""Bi-Temporal Episodic Knowledge Graph Engine for Phenom (Milestone 49 Phase 1).

Maintains both:
- Valid Time (T_v): when facts/events occurred in reality.
- Transaction Time (T_t): when facts/events were asserted or recorded in Phenom.

Features:
- Encrypted SQLite / SQLite persistent store.
- Versioned non-destructive updates along transaction time (audit preservation).
- Dual time-travel queries (as-of T_v and as-of T_t).
- In-memory NetworkX MultiDiGraph projection for multi-hop graph traversals.
- Rule 8 anti-checkout enforcement, Rule 11 credential scrubbing, and Guardian kill switch SLA (< 25ms).
"""

from __future__ import annotations

import json
import logging
import math
import os
import re
import sqlite3
import threading
import time
from typing import Any, Dict, List, Optional, Set, Tuple

import networkx as nx

from services.backend.schemas.temporal_graph import (
    EntityType,
    RelationType,
    TemporalEntity,
    TemporalRelation,
    TemporalEpisode,
)
from services.backend.safety.guardian import guardian
from services.backend.safety.action_log import action_log

logger = logging.getLogger("phenom.memory.temporal_graph_engine")

try:
    import sqlcipher3
except ImportError:
    sqlcipher3 = None


class Rule8ViolationError(PermissionError):
    """Raised when an entity, relation, or query violates Rule 8 anti-checkout rules."""
    pass


class TemporalGraphEngine:
    """Manages the bi-temporal episodic knowledge graph with NetworkX and SQLite."""

    _RULE_8_PATTERN = re.compile(
        r"(?:\b|_)(checkout|pay|payment|purchase|buy|order|credit.?card|cvv|billing)(?:\b|_)",
        re.IGNORECASE,
    )

    _CREDENTIAL_PATTERN = re.compile(
        r"(?i)['\"]?\b(api[_-]?key|secret|token|password|bearer|auth[_-]?token|passwd|pwd)\b['\"]?\s*[:=\s]\s*['\"]?([A-Za-z0-9_\-\.]{8,})['\"]?"
    )

    _SECRET_TOKEN_PATTERN = re.compile(
        r"\b(?:nvapi-[A-Za-z0-9_-]{20,}|ghp_[A-Za-z0-9]{36}|sk-[A-Za-z0-9]{20,}|AKIA[0-9A-Z]{16})\b"
    )

    def __init__(
        self,
        db_path: Optional[str] = None,
        encryption_key: Optional[str] = None,
    ) -> None:
        self.db_path = db_path or os.path.abspath("services/backend/data/bitemporal_knowledge_graph.db")
        self.encryption_key = encryption_key
        self._lock = threading.RLock()
        self.graph = nx.MultiDiGraph()

        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        self._init_db()
        self.rebuild_graph_from_db()

    def _get_connection(self) -> sqlite3.Connection:
        if self.encryption_key and sqlcipher3 is not None:
            conn = sqlcipher3.connect(self.db_path, check_same_thread=False)
            conn.execute(f"PRAGMA key = '{self.encryption_key}';")
            conn.execute("PRAGMA cipher_compatibility = 4;")
        else:
            conn = sqlite3.connect(self.db_path, check_same_thread=False)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self) -> None:
        with self._lock:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS temporal_entities (
                        id TEXT NOT NULL,
                        name TEXT NOT NULL,
                        entity_type TEXT NOT NULL,
                        content TEXT,
                        valid_from REAL NOT NULL,
                        valid_until REAL,
                        recorded_at REAL NOT NULL,
                        superseded_at REAL,
                        tags_json TEXT,
                        metadata_json TEXT,
                        PRIMARY KEY (id, recorded_at)
                    );
                """)
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS temporal_relations (
                        id TEXT NOT NULL,
                        source_id TEXT NOT NULL,
                        target_id TEXT NOT NULL,
                        relation_type TEXT NOT NULL,
                        weight REAL NOT NULL DEFAULT 1.0,
                        valid_from REAL NOT NULL,
                        valid_until REAL,
                        recorded_at REAL NOT NULL,
                        superseded_at REAL,
                        metadata_json TEXT,
                        PRIMARY KEY (id, recorded_at)
                    );
                """)
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS temporal_episodes (
                        id TEXT NOT NULL,
                        title TEXT NOT NULL,
                        summary TEXT,
                        episode_type TEXT NOT NULL,
                        event_timestamp REAL NOT NULL,
                        recorded_at REAL NOT NULL,
                        entity_ids_json TEXT,
                        tags_json TEXT,
                        metadata_json TEXT,
                        PRIMARY KEY (id, recorded_at)
                    );
                """)
                cursor.execute("CREATE INDEX IF NOT EXISTS idx_ent_id ON temporal_entities (id);")
                cursor.execute("CREATE INDEX IF NOT EXISTS idx_ent_active ON temporal_entities (superseded_at);")
                cursor.execute("CREATE INDEX IF NOT EXISTS idx_rel_src_tgt ON temporal_relations (source_id, target_id);")
                cursor.execute("CREATE INDEX IF NOT EXISTS idx_rel_active ON temporal_relations (superseded_at);")
                conn.commit()

    # --- Safety & Sanitization ---

    def _assert_guardian(self) -> None:
        if guardian.is_halted:
            raise PermissionError("Guardian kill switch is active. Operation aborted.")

    def _check_rule_8(self, text: str) -> None:
        if self._RULE_8_PATTERN.search(text):
            raise Rule8ViolationError(
                f"Rule 8 Violation: Interaction involves financial, checkout, or payment content: {text[:60]}"
            )

    def _scrub_credentials(self, text: str) -> str:
        if not text:
            return ""
        # Scrub explicit secret keys
        scrubbed = self._SECRET_TOKEN_PATTERN.sub("[REDACTED_SECRET]", text)
        # Scrub key=value credentials
        scrubbed = self._CREDENTIAL_PATTERN.sub(r"\1: [REDACTED_CREDENTIAL]", scrubbed)
        return scrubbed

    # --- Entity Ingestion & Versioning ---

    def upsert_entity(self, entity: TemporalEntity) -> TemporalEntity:
        """Non-destructively upserts an entity along transaction time (T_t)."""
        self._assert_guardian()
        self._check_rule_8(f"{entity.name} {entity.content}")

        clean_name = self._scrub_credentials(entity.name)
        clean_content = self._scrub_credentials(entity.content)
        now_tt = entity.recorded_at or time.time()

        with self._lock:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                # Mark previous active version as superseded at now_tt
                cursor.execute(
                    "UPDATE temporal_entities SET superseded_at = ? WHERE id = ? AND superseded_at IS NULL",
                    (now_tt, entity.id),
                )
                cursor.execute(
                    """
                    INSERT INTO temporal_entities (
                        id, name, entity_type, content, valid_from, valid_until,
                        recorded_at, superseded_at, tags_json, metadata_json
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        entity.id,
                        clean_name,
                        entity.entity_type.value if hasattr(entity.entity_type, "value") else str(entity.entity_type),
                        clean_content,
                        entity.valid_from,
                        entity.valid_until,
                        now_tt,
                        entity.superseded_at,
                        json.dumps(entity.tags),
                        json.dumps(entity.metadata),
                    ),
                )
                conn.commit()

            # Update NetworkX in-memory projection
            self.graph.add_node(
                entity.id,
                name=clean_name,
                entity_type=entity.entity_type.value if hasattr(entity.entity_type, "value") else str(entity.entity_type),
                content=clean_content,
                valid_from=entity.valid_from,
                valid_until=entity.valid_until,
                recorded_at=now_tt,
                superseded_at=entity.superseded_at,
                tags=entity.tags,
                metadata=entity.metadata,
            )

        return entity

    # --- Relation Ingestion & Versioning ---

    def upsert_relation(self, relation: TemporalRelation) -> TemporalRelation:
        """Non-destructively upserts a directed relationship along transaction time (T_t)."""
        self._assert_guardian()
        now_tt = relation.recorded_at or time.time()

        with self._lock:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                # Mark existing active matching edge as superseded
                cursor.execute(
                    """
                    UPDATE temporal_relations SET superseded_at = ?
                    WHERE source_id = ? AND target_id = ? AND relation_type = ? AND superseded_at IS NULL
                    """,
                    (now_tt, relation.source_id, relation.target_id, relation.relation_type.value if hasattr(relation.relation_type, "value") else str(relation.relation_type)),
                )
                cursor.execute(
                    """
                    INSERT INTO temporal_relations (
                        id, source_id, target_id, relation_type, weight,
                        valid_from, valid_until, recorded_at, superseded_at, metadata_json
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        relation.id,
                        relation.source_id,
                        relation.target_id,
                        relation.relation_type.value if hasattr(relation.relation_type, "value") else str(relation.relation_type),
                        relation.weight,
                        relation.valid_from,
                        relation.valid_until,
                        now_tt,
                        relation.superseded_at,
                        json.dumps(relation.metadata),
                    ),
                )
                conn.commit()

            # Update NetworkX edge
            rel_type_str = relation.relation_type.value if hasattr(relation.relation_type, "value") else str(relation.relation_type)
            self.graph.add_edge(
                relation.source_id,
                relation.target_id,
                key=f"{relation.id}_{now_tt}",
                relation_type=rel_type_str,
                weight=relation.weight,
                valid_from=relation.valid_from,
                valid_until=relation.valid_until,
                recorded_at=now_tt,
                superseded_at=relation.superseded_at,
                metadata=relation.metadata,
            )

        return relation

    # --- Episode Logging ---

    def record_episode(self, episode: TemporalEpisode) -> TemporalEpisode:
        """Records an episodic milestone grouping entities and timestamp."""
        self._assert_guardian()
        self._check_rule_8(f"{episode.title} {episode.summary}")

        clean_title = self._scrub_credentials(episode.title)
        clean_summary = self._scrub_credentials(episode.summary)
        now_tt = episode.recorded_at or time.time()

        with self._lock:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    """
                    INSERT INTO temporal_episodes (
                        id, title, summary, episode_type, event_timestamp,
                        recorded_at, entity_ids_json, tags_json, metadata_json
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        episode.id,
                        clean_title,
                        clean_summary,
                        episode.episode_type,
                        episode.event_timestamp,
                        now_tt,
                        json.dumps(episode.entity_ids),
                        json.dumps(episode.tags),
                        json.dumps(episode.metadata),
                    ),
                )
                conn.commit()

        return episode

    # --- Time-Travel Queries ---

    def get_entity(
        self,
        entity_id: str,
        as_of_valid_time: Optional[float] = None,
        as_of_transaction_time: Optional[float] = None,
    ) -> Optional[TemporalEntity]:
        """Retrieves an entity as it was known at transaction time and/or valid at valid time."""
        self._assert_guardian()
        with self._lock:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                if as_of_transaction_time is not None:
                    # Point-in-time along T_t
                    query = """
                        SELECT * FROM temporal_entities
                        WHERE id = ? AND recorded_at <= ? AND (superseded_at IS NULL OR superseded_at > ?)
                        ORDER BY recorded_at DESC LIMIT 1
                    """
                    cursor.execute(query, (entity_id, as_of_transaction_time, as_of_transaction_time))
                else:
                    # Current active assertion along T_t
                    query = "SELECT * FROM temporal_entities WHERE id = ? AND superseded_at IS NULL ORDER BY recorded_at DESC LIMIT 1"
                    cursor.execute(query, (entity_id,))

                row = cursor.fetchone()
                if not row:
                    return None

                entity = self._row_to_entity(row)
                if as_of_valid_time is not None and not entity.is_valid_at(as_of_valid_time):
                    return None

                return entity

    def get_all_active_entities(self, entity_type: Optional[EntityType] = None) -> List[TemporalEntity]:
        """Returns all currently active (non-superseded) entities."""
        self._assert_guardian()
        with self._lock:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                if entity_type:
                    type_str = entity_type.value if hasattr(entity_type, "value") else str(entity_type)
                    cursor.execute(
                        "SELECT * FROM temporal_entities WHERE superseded_at IS NULL AND entity_type = ?",
                        (type_str,),
                    )
                else:
                    cursor.execute("SELECT * FROM temporal_entities WHERE superseded_at IS NULL")
                rows = cursor.fetchall()
                return [self._row_to_entity(r) for r in rows]

    def get_active_relations_for(self, entity_id: str) -> List[TemporalRelation]:
        """Returns all active relations where entity_id is source or target."""
        self._assert_guardian()
        with self._lock:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    """
                    SELECT * FROM temporal_relations
                    WHERE (source_id = ? OR target_id = ?) AND superseded_at IS NULL
                    """,
                    (entity_id, entity_id),
                )
                rows = cursor.fetchall()
                return [self._row_to_relation(r) for r in rows]

    def get_neighborhood(
        self,
        entity_id: str,
        max_hops: int = 1,
        as_of_valid_time: Optional[float] = None,
    ) -> Dict[str, Any]:
        """Extracts the ego subgraph around entity_id up to max_hops."""
        self._assert_guardian()
        with self._lock:
            if entity_id not in self.graph:
                return {"center": entity_id, "nodes": [], "edges": []}

            # Find all nodes within max_hops using undirected view for reachability
            undirected = self.graph.to_undirected()
            try:
                sub_nodes = set(nx.single_source_shortest_path_length(undirected, entity_id, cutoff=max_hops).keys())
            except nx.NodeNotFound:
                return {"center": entity_id, "nodes": [], "edges": []}

            nodes_data = []
            for nid in sub_nodes:
                data = dict(self.graph.nodes[nid])
                data["id"] = nid
                # Check valid time if requested
                if as_of_valid_time is not None:
                    vf = data.get("valid_from", 0.0)
                    vu = data.get("valid_until")
                    if as_of_valid_time < vf or (vu is not None and as_of_valid_time > vu):
                        continue
                nodes_data.append(data)

            edges_data = []
            valid_node_ids = {n["id"] for n in nodes_data}
            for u, v, k, edata in self.graph.edges(sub_nodes, data=True, keys=True):
                if u in valid_node_ids and v in valid_node_ids:
                    if edata.get("superseded_at") is None:
                        edges_data.append({
                            "source": u,
                            "target": v,
                            "relation_type": edata.get("relation_type"),
                            "weight": edata.get("weight", 1.0),
                            "valid_from": edata.get("valid_from"),
                        })

            return {
                "center": entity_id,
                "nodes": nodes_data,
                "edges": edges_data,
                "total_nodes": len(nodes_data),
                "total_edges": len(edges_data),
            }

    # --- In-Memory Rebuild ---

    def rebuild_graph_from_db(self, as_of_transaction_time: Optional[float] = None) -> None:
        """Reconstructs the NetworkX MultiDiGraph from SQLite active or point-in-time records."""
        with self._lock:
            self.graph.clear()
            with self._get_connection() as conn:
                cursor = conn.cursor()
                if as_of_transaction_time is not None:
                    cursor.execute(
                        """
                        SELECT * FROM temporal_entities
                        WHERE recorded_at <= ? AND (superseded_at IS NULL OR superseded_at > ?)
                        """,
                        (as_of_transaction_time, as_of_transaction_time),
                    )
                else:
                    cursor.execute("SELECT * FROM temporal_entities WHERE superseded_at IS NULL")

                for row in cursor.fetchall():
                    self.graph.add_node(
                        row["id"],
                        name=row["name"],
                        entity_type=row["entity_type"],
                        content=row["content"] or "",
                        valid_from=row["valid_from"],
                        valid_until=row["valid_until"],
                        recorded_at=row["recorded_at"],
                        superseded_at=row["superseded_at"],
                        tags=json.loads(row["tags_json"] or "[]"),
                        metadata=json.loads(row["metadata_json"] or "{}"),
                    )

                if as_of_transaction_time is not None:
                    cursor.execute(
                        """
                        SELECT * FROM temporal_relations
                        WHERE recorded_at <= ? AND (superseded_at IS NULL OR superseded_at > ?)
                        """,
                        (as_of_transaction_time, as_of_transaction_time),
                    )
                else:
                    cursor.execute("SELECT * FROM temporal_relations WHERE superseded_at IS NULL")

                for row in cursor.fetchall():
                    self.graph.add_edge(
                        row["source_id"],
                        row["target_id"],
                        key=f"{row['id']}_{row['recorded_at']}",
                        relation_type=row["relation_type"],
                        weight=row["weight"],
                        valid_from=row["valid_from"],
                        valid_until=row["valid_until"],
                        recorded_at=row["recorded_at"],
                        superseded_at=row["superseded_at"],
                        metadata=json.loads(row["metadata_json"] or "{}"),
                    )

    # --- Row Helpers ---

    def _row_to_entity(self, row: sqlite3.Row) -> TemporalEntity:
        return TemporalEntity(
            id=row["id"],
            name=row["name"],
            entity_type=EntityType(row["entity_type"]),
            content=row["content"] or "",
            valid_from=row["valid_from"],
            valid_until=row["valid_until"],
            recorded_at=row["recorded_at"],
            superseded_at=row["superseded_at"],
            tags=json.loads(row["tags_json"] or "[]"),
            metadata=json.loads(row["metadata_json"] or "{}"),
        )

    def _row_to_relation(self, row: sqlite3.Row) -> TemporalRelation:
        return TemporalRelation(
            id=row["id"],
            source_id=row["source_id"],
            target_id=row["target_id"],
            relation_type=RelationType(row["relation_type"]),
            weight=row["weight"],
            valid_from=row["valid_from"],
            valid_until=row["valid_until"],
            recorded_at=row["recorded_at"],
            superseded_at=row["superseded_at"],
            metadata=json.loads(row["metadata_json"] or "{}"),
        )
