"""Associative Temporal Knowledge Graph & Deep Episodic Memory Matrix for Phenom (Milestone 31 Phase 3).

Coordinates:
- Encrypted SQLite/SQLCipher knowledge graph storing entities, relations, past session goals, and decisions (MEM-01.1).
- Temporal decay and recency weighting balancing fresh working context with long-term memory (MEM-01.2).
- Cross-session episodic memory linking terminal runs, Git commits, and Obsidian daily notes (EPISODE-02.1).
- Rule 11 credential protection scrubbing passwords, tokens, and API keys prior to graph indexing (EPISODE-02.2).
- Strict Rule 4 (offline local), Rule 8 (anti-checkout), and Rule 3 Guardian kill switch SLA < 25.0ms.
"""

from __future__ import annotations

from enum import Enum
import json
import logging
import math
import os
import re
import sqlite3
import threading
import time
from typing import Any, Dict, List, Optional, Set, Tuple
from pydantic import BaseModel, Field

from services.backend.safety.guardian import guardian

logger = logging.getLogger("phenom.memory.temporal_graph")

try:
    import sqlcipher3
except ImportError:
    sqlcipher3 = None


class Rule8ViolationError(Exception):
    """Raised when knowledge graph entity, relation, or query contains payment, billing, or checkout keywords."""
    pass


class EntityType(str, Enum):
    CONCEPT = "CONCEPT"
    FILE = "FILE"
    PROJECT = "PROJECT"
    GOAL = "GOAL"
    DECISION = "DECISION"
    SESSION = "SESSION"


class RelationType(str, Enum):
    DEPENDS_ON = "DEPENDS_ON"
    IMPLEMENTS = "IMPLEMENTS"
    RESOLVES = "RESOLVES"
    MODIFIES = "MODIFIES"
    DERIVED_FROM = "DERIVED_FROM"
    RELATED_TO = "RELATED_TO"


class EpisodeType(str, Enum):
    TERMINAL_RUN = "TERMINAL_RUN"
    GIT_COMMIT = "GIT_COMMIT"
    OBSIDIAN_NOTE = "OBSIDIAN_NOTE"
    MILESTONE_DECISION = "MILESTONE_DECISION"


class GraphEntity(BaseModel):
    id: str
    name: str
    entity_type: EntityType
    properties: Dict[str, Any] = Field(default_factory=dict)
    created_at: float = Field(default_factory=time.time)
    updated_at: float = Field(default_factory=time.time)
    access_count: int = 1
    last_accessed_at: float = Field(default_factory=time.time)
    current_score: float = 1.0


class GraphRelation(BaseModel):
    id: str
    source_id: str
    target_id: str
    relation_type: RelationType
    weight: float = 1.0
    created_at: float = Field(default_factory=time.time)


class GraphEpisode(BaseModel):
    id: str
    session_id: str
    episode_type: EpisodeType
    summary: str
    entity_ids: List[str] = Field(default_factory=list)
    metadata: Dict[str, Any] = Field(default_factory=dict)
    timestamp: float = Field(default_factory=time.time)


class AssociativeQueryResult(BaseModel):
    query: str
    matched_entities: List[Dict[str, Any]]
    relations: List[Dict[str, Any]]
    linked_episodes: List[Dict[str, Any]]
    traversal_depth: int
    latency_ms: float
    status: str


class TemporalKnowledgeGraph:
    """Encrypted SQLite/SQLCipher associative knowledge graph with exponential decay and episodic indexing."""

    _RULE_8_PATTERN = re.compile(
        r"(?:\b|_)(checkout|pay|payment|purchase|buy|order|credit.?card|cvv|billing)(?:\b|_)",
        re.IGNORECASE,
    )

    _CREDENTIAL_PATTERN = re.compile(
        r"(?i)['\"]?\b(api[_-]?key|secret|token|password|bearer|auth[_-]?token|passwd|pwd)\b['\"]?\s*[:=\s]\s*['\"]?([A-Za-z0-9_\-\.]{8,})['\"]?"
    )

    _RULE_11_KEY_PATTERN = re.compile(
        r"(?i)\b(api[_-]?key|secret|token|password|bearer|auth[_-]?token|passwd|pwd)\b"
    )

    def __init__(
        self,
        db_path: Optional[str] = None,
        encryption_key: Optional[str] = None,
        half_life_days: float = 7.0,
        access_boost_alpha: float = 0.25,
    ) -> None:
        self.db_path = db_path or os.path.abspath("services/backend/data/temporal_knowledge_graph.db")
        self.encryption_key = encryption_key
        self.half_life_days = half_life_days
        self.access_boost_alpha = access_boost_alpha
        self.decay_lambda = math.log(2.0) / (half_life_days * 86400.0)
        self._lock = threading.Lock()

        if self.db_path != ":memory:":
            os.makedirs(os.path.dirname(self.db_path), exist_ok=True)

        self._conn = self._get_connection()
        self._init_schema()

    def _get_connection(self) -> sqlite3.Connection:
        """Opens SQLCipher or standard SQLite connection."""
        if self.encryption_key and sqlcipher3 and self.db_path != ":memory:":
            conn = sqlcipher3.connect(self.db_path, timeout=30.0)
            conn.execute(f"PRAGMA key = '{self.encryption_key}';")
            conn.execute("PRAGMA cipher_compatibility = 4;")
            conn.execute("PRAGMA busy_timeout = 30000;")
            return conn
        conn = sqlite3.connect(self.db_path, timeout=30.0, check_same_thread=False)
        conn.execute("PRAGMA busy_timeout = 30000;")
        return conn

    def _init_schema(self) -> None:
        with self._conn:
            self._conn.execute(
                """
                CREATE TABLE IF NOT EXISTS graph_entities (
                    id TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    entity_type TEXT NOT NULL,
                    properties_json TEXT NOT NULL,
                    created_at REAL NOT NULL,
                    updated_at REAL NOT NULL,
                    access_count INTEGER NOT NULL,
                    last_accessed_at REAL NOT NULL
                )
                """
            )
            self._conn.execute(
                """
                CREATE TABLE IF NOT EXISTS graph_relations (
                    id TEXT PRIMARY KEY,
                    source_id TEXT NOT NULL,
                    target_id TEXT NOT NULL,
                    relation_type TEXT NOT NULL,
                    weight REAL NOT NULL,
                    created_at REAL NOT NULL,
                    FOREIGN KEY (source_id) REFERENCES graph_entities (id),
                    FOREIGN KEY (target_id) REFERENCES graph_entities (id)
                )
                """
            )
            self._conn.execute(
                """
                CREATE TABLE IF NOT EXISTS graph_episodes (
                    id TEXT PRIMARY KEY,
                    session_id TEXT NOT NULL,
                    episode_type TEXT NOT NULL,
                    summary TEXT NOT NULL,
                    entity_ids_json TEXT NOT NULL,
                    metadata_json TEXT NOT NULL,
                    timestamp REAL NOT NULL
                )
                """
            )
            self._conn.execute("CREATE INDEX IF NOT EXISTS idx_entities_name ON graph_entities(name)")
            self._conn.execute("CREATE INDEX IF NOT EXISTS idx_relations_source ON graph_relations(source_id)")
            self._conn.execute("CREATE INDEX IF NOT EXISTS idx_relations_target ON graph_relations(target_id)")

    def check_safety(self, text: Optional[str] = None) -> None:
        """Enforces Guardian kill switch (Rule 3) and Anti-Checkout (Rule 8)."""
        if guardian.is_halted:
            raise RuntimeError("Execution halted by Guardian kill switch (TEMPORAL_GRAPH_HALTED)")

        if text and self._RULE_8_PATTERN.search(text):
            raise Rule8ViolationError(
                "Rule 8 Violation: Payment, checkout, or billing phrase detected in temporal graph data"
            )

    def scrub_credentials(self, text: str) -> Tuple[str, int]:
        """Recursively scrubs credentials and tokens (Rule 11)."""
        count = 0

        def replace_cred(match: re.Match) -> str:
            nonlocal count
            count += 1
            key = match.group(1)
            return f"{key}: [REDACTED]"

        scrubbed = self._CREDENTIAL_PATTERN.sub(replace_cred, text)
        return scrubbed, count

    def scrub_dict(self, data: Any) -> Any:
        """Recursively scrubs sensitive keys and values from dictionaries/lists."""
        if isinstance(data, dict):
            new_dict = {}
            for k, v in data.items():
                if self._RULE_11_KEY_PATTERN.search(str(k)):
                    new_dict[k] = "[REDACTED]"
                else:
                    new_dict[k] = self.scrub_dict(v)
            return new_dict
        elif isinstance(data, list):
            return [self.scrub_dict(item) for item in data]
        elif isinstance(data, str):
            scrubbed, _ = self.scrub_credentials(data)
            return scrubbed
        return data

    def compute_temporal_score(
        self,
        base_weight: float,
        timestamp: float,
        access_count: int,
        current_time: Optional[float] = None,
    ) -> float:
        """Computes exponential half-life decay score with access frequency reinforcement."""
        now = current_time if current_time is not None else time.time()
        delta_sec = max(0.0, now - timestamp)
        decay_factor = math.exp(-self.decay_lambda * delta_sec)
        access_boost = 1.0 + self.access_boost_alpha * math.log(1.0 + access_count)
        return round(base_weight * decay_factor * access_boost, 4)

    def record_entity(
        self,
        id: str,
        name: str,
        entity_type: EntityType,
        properties: Optional[Dict[str, Any]] = None,
        timestamp: Optional[float] = None,
    ) -> GraphEntity:
        """Inserts or updates an entity node in the knowledge graph."""
        self.check_safety(f"{name} {json.dumps(properties or {})}")
        clean_name, _ = self.scrub_credentials(name)
        clean_props = self.scrub_dict(properties or {})

        now = timestamp if timestamp is not None else time.time()
        with self._lock, self._conn:
            cursor = self._conn.execute("SELECT access_count FROM graph_entities WHERE id = ?", (id,))
            row = cursor.fetchone()
            if row:
                new_access_count = row[0] + 1
                self._conn.execute(
                    """
                    UPDATE graph_entities
                    SET name = ?, entity_type = ?, properties_json = ?, updated_at = ?,
                        access_count = ?, last_accessed_at = ?
                    WHERE id = ?
                    """,
                    (clean_name, entity_type.value, json.dumps(clean_props), now, new_access_count, now, id),
                )
            else:
                new_access_count = 1
                self._conn.execute(
                    """
                    INSERT INTO graph_entities
                    (id, name, entity_type, properties_json, created_at, updated_at, access_count, last_accessed_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (id, clean_name, entity_type.value, json.dumps(clean_props), now, now, 1, now),
                )

        score = self.compute_temporal_score(1.0, now, new_access_count, current_time=now)
        return GraphEntity(
            id=id,
            name=clean_name,
            entity_type=entity_type,
            properties=clean_props,
            created_at=now,
            updated_at=now,
            access_count=new_access_count,
            last_accessed_at=now,
            current_score=score,
        )

    def record_relation(
        self,
        id: str,
        source_id: str,
        target_id: str,
        relation_type: RelationType,
        weight: float = 1.0,
        timestamp: Optional[float] = None,
    ) -> GraphRelation:
        """Links two entities with a directed, weighted relation edge."""
        self.check_safety()
        now = timestamp if timestamp is not None else time.time()
        with self._lock, self._conn:
            self._conn.execute(
                """
                INSERT OR REPLACE INTO graph_relations (id, source_id, target_id, relation_type, weight, created_at)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (id, source_id, target_id, relation_type.value, weight, now),
            )
        return GraphRelation(
            id=id,
            source_id=source_id,
            target_id=target_id,
            relation_type=relation_type,
            weight=weight,
            created_at=now,
        )

    def record_episode(
        self,
        id: str,
        session_id: str,
        episode_type: EpisodeType,
        summary: str,
        entity_ids: Optional[List[str]] = None,
        metadata: Optional[Dict[str, Any]] = None,
        timestamp: Optional[float] = None,
    ) -> GraphEpisode:
        """Indexes an episodic event (terminal execution, Git commit, Obsidian daily note)."""
        self.check_safety(f"{summary} {json.dumps(metadata or {})}")
        clean_summary, _ = self.scrub_credentials(summary)
        clean_meta = self.scrub_dict(metadata or {})

        now = timestamp if timestamp is not None else time.time()
        entities = entity_ids or []
        with self._lock, self._conn:
            self._conn.execute(
                """
                INSERT OR REPLACE INTO graph_episodes
                (id, session_id, episode_type, summary, entity_ids_json, metadata_json, timestamp)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (id, session_id, episode_type.value, clean_summary, json.dumps(entities), json.dumps(clean_meta), now),
            )

        return GraphEpisode(
            id=id,
            session_id=session_id,
            episode_type=episode_type,
            summary=clean_summary,
            entity_ids=entities,
            metadata=clean_meta,
            timestamp=now,
        )

    def query_associative_subgraph(
        self,
        query: str,
        max_hops: int = 2,
        current_time: Optional[float] = None,
    ) -> AssociativeQueryResult:
        """Traverses the associative knowledge graph up to max_hops with temporal decay scoring."""
        t0 = time.perf_counter()
        self.check_safety(query)
        now = current_time if current_time is not None else time.time()

        with self._lock:
            # 1. Find seed nodes matching query keywords or entity name
            query_terms = [q.lower() for q in query.split() if len(q) > 2]
            matched_entities_dict: Dict[str, Dict[str, Any]] = {}
            visited_nodes: Set[str] = set()

            cursor = self._conn.execute(
                "SELECT id, name, entity_type, properties_json, created_at, updated_at, access_count, last_accessed_at FROM graph_entities"
            )
            all_entities = cursor.fetchall()

            seed_ids: List[str] = []
            for row in all_entities:
                e_id, name, e_type, props_json, created_at, updated_at, access_count, last_accessed = row
                text_corpus = f"{name} {props_json}".lower()

                is_match = False
                if query.lower() in text_corpus:
                    is_match = True
                elif any(term in text_corpus for term in query_terms):
                    is_match = True

                if is_match:
                    seed_ids.append(e_id)
                    # Compute decayed score
                    score = self.compute_temporal_score(1.0, created_at, access_count, current_time=now)
                    matched_entities_dict[e_id] = {
                        "id": e_id,
                        "name": name,
                        "entity_type": e_type,
                        "properties": json.loads(props_json),
                        "decayed_score": score,
                        "hop_distance": 0,
                    }
                    visited_nodes.add(e_id)

            # 2. Associative k-hop traversal
            current_frontier = list(seed_ids)
            collected_relations: List[Dict[str, Any]] = []

            for hop in range(1, max_hops + 1):
                if not current_frontier:
                    break
                next_frontier: List[str] = []

                placeholders = ",".join("?" for _ in current_frontier)
                rel_cursor = self._conn.execute(
                    f"""
                    SELECT id, source_id, target_id, relation_type, weight, created_at
                    FROM graph_relations
                    WHERE source_id IN ({placeholders}) OR target_id IN ({placeholders})
                    """,
                    current_frontier + current_frontier,
                )
                relations_rows = rel_cursor.fetchall()

                for rel_row in relations_rows:
                    r_id, src, tgt, r_type, w, r_created = rel_row
                    neighbor_id = tgt if src in current_frontier else src

                    collected_relations.append({
                        "id": r_id,
                        "source_id": src,
                        "target_id": tgt,
                        "relation_type": r_type,
                        "weight": w,
                    })

                    if neighbor_id not in visited_nodes:
                        visited_nodes.add(neighbor_id)
                        next_frontier.append(neighbor_id)

                        # Lookup neighbor entity
                        ent_cursor = self._conn.execute(
                            "SELECT name, entity_type, properties_json, created_at, access_count FROM graph_entities WHERE id = ?",
                            (neighbor_id,),
                        )
                        ent_row = ent_cursor.fetchone()
                        if ent_row:
                            n_name, n_type, n_props_json, n_created, n_access = ent_row
                            base_score = matched_entities_dict.get(src, {}).get("decayed_score", 1.0) * w * 0.8
                            n_score = self.compute_temporal_score(base_score, n_created, n_access, current_time=now)
                            matched_entities_dict[neighbor_id] = {
                                "id": neighbor_id,
                                "name": n_name,
                                "entity_type": n_type,
                                "properties": json.loads(n_props_json),
                                "decayed_score": n_score,
                                "hop_distance": hop,
                            }

                current_frontier = next_frontier

            # 3. Retrieve linked episodes for all visited nodes
            linked_episodes: List[Dict[str, Any]] = []
            if visited_nodes:
                ep_cursor = self._conn.execute(
                    "SELECT id, session_id, episode_type, summary, entity_ids_json, metadata_json, timestamp FROM graph_episodes ORDER BY timestamp DESC"
                )
                for ep_row in ep_cursor.fetchall():
                    ep_id, sess_id, ep_type, summary, ent_ids_json, meta_json, ep_time = ep_row
                    ep_entities = set(json.loads(ent_ids_json))
                    if ep_entities.intersection(visited_nodes):
                        linked_episodes.append({
                            "id": ep_id,
                            "session_id": sess_id,
                            "episode_type": ep_type,
                            "summary": summary,
                            "entity_ids": list(ep_entities),
                            "metadata": json.loads(meta_json),
                            "timestamp": ep_time,
                        })

            # Sort entities by decayed score descending
            sorted_entities = sorted(
                matched_entities_dict.values(),
                key=lambda x: x["decayed_score"],
                reverse=True,
            )

        elapsed_ms = (time.perf_counter() - t0) * 1000.0
        return AssociativeQueryResult(
            query=query,
            matched_entities=sorted_entities,
            relations=collected_relations,
            linked_episodes=linked_episodes[:20],
            traversal_depth=max_hops,
            latency_ms=round(elapsed_ms, 3),
            status="SUCCESS",
        )

    def get_stats(self) -> Dict[str, Any]:
        """Returns knowledge graph inventory and memory statistics."""
        self.check_safety()
        with self._lock:
            cursor = self._conn.cursor()
            entity_count = cursor.execute("SELECT COUNT(*) FROM graph_entities").fetchone()[0]
            relation_count = cursor.execute("SELECT COUNT(*) FROM graph_relations").fetchone()[0]
            episode_count = cursor.execute("SELECT COUNT(*) FROM graph_episodes").fetchone()[0]
        return {
            "entity_count": entity_count,
            "relation_count": relation_count,
            "episode_count": episode_count,
            "half_life_days": self.half_life_days,
            "offline_local": True,
            "guardian_halted": guardian.is_halted,
        }


# Global singleton instance
temporal_knowledge_graph = TemporalKnowledgeGraph()
