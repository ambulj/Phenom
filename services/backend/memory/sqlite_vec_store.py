"""
Encrypted SQLite Vector Store (VEC-01.1).
Stores 384-dimensional dense vectors and contextual metadata inside SQLCipher-encrypted database.
Supports fast in-memory cosine similarity search (dot product over unit L2 normalized vectors).
Enforces Rule 7 recycle bin soft-deletions.
"""

import json
import time
import uuid
from typing import Dict, Any, List, Optional
import numpy as np

from services.backend.memory.db import encrypted_db, EncryptedDatabaseManager


class SqliteVectorStore:
    """Encrypted SQLite vector store with metadata indexing and cosine similarity recall."""

    def __init__(self, db_manager: Optional[EncryptedDatabaseManager] = None):
        self.db = db_manager or encrypted_db
        self._conn = None
        self._init_table()

    def _get_conn(self):
        """Returns active encrypted connection with warm cipher key derivation."""
        if self._conn is None:
            self._conn = self.db.get_connection()
            try:
                c = self._conn.cursor()
                c.execute("SELECT 1;")
                c.fetchone()
            except Exception:
                pass
        return self._conn

    def _init_table(self):
        """Creates associative_memory table if it does not already exist."""
        conn = self._get_conn()
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS associative_memory (
                id TEXT PRIMARY KEY,
                content TEXT NOT NULL,
                metadata TEXT NOT NULL,
                embedding BLOB NOT NULL,
                source TEXT NOT NULL,
                tier INTEGER DEFAULT 0,
                tags TEXT,
                created_at REAL NOT NULL,
                is_deleted INTEGER DEFAULT 0
            );
        """)
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_assoc_mem_deleted ON associative_memory(is_deleted);
        """)
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_assoc_mem_source ON associative_memory(source);
        """)
        conn.commit()

    def insert_memory(
        self,
        content: str,
        embedding: np.ndarray,
        metadata: Optional[Dict[str, Any]] = None,
        source: str = "assistant",
        tier: int = 0,
        tags: Optional[List[str]] = None,
        memory_id: Optional[str] = None
    ) -> str:
        """Stores a vector embedding and metadata in encrypted storage."""
        mem_id = memory_id or f"mem-{uuid.uuid4().hex[:12]}"
        meta_json = json.dumps(metadata or {})
        tags_str = ",".join(tags or [])
        now = time.time()

        # Serialize float32 numpy vector to bytes
        emb_bytes = embedding.astype(np.float32).tobytes()

        conn = self._get_conn()
        cursor = conn.cursor()
        cursor.execute("""
            INSERT OR REPLACE INTO associative_memory 
            (id, content, metadata, embedding, source, tier, tags, created_at, is_deleted)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, 0);
        """, (mem_id, content, meta_json, emb_bytes, source, tier, tags_str, now))
        conn.commit()

        return mem_id

    def search_memories(
        self,
        query_embedding: np.ndarray,
        top_k: int = 5,
        min_score: float = 0.25,
        required_tags: Optional[List[str]] = None
    ) -> List[Dict[str, Any]]:
        """
        Executes sub-10ms cosine similarity search against active associative memories.
        Since vectors are pre-normalized, cosine similarity equals the dot product.
        """
        conn = self._get_conn()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT id, content, metadata, embedding, source, tier, tags, created_at 
            FROM associative_memory 
            WHERE is_deleted = 0;
        """)
        rows = cursor.fetchall()

        if not rows:
            return []

        q_vec = query_embedding.astype(np.float32)
        matches: List[Dict[str, Any]] = []

        for row in rows:
            mem_id, content, meta_json, emb_bytes, source, tier, tags_str, created_at = row

            tags = tags_str.split(",") if tags_str else []
            if required_tags and not all(rt in tags for rt in required_tags):
                continue

            # Deserialize embedding
            mem_vec = np.frombuffer(emb_bytes, dtype=np.float32)
            if len(mem_vec) != len(q_vec):
                continue

            # Dot product cosine similarity
            sim = float(np.dot(q_vec, mem_vec))
            if sim >= min_score:
                try:
                    meta = json.loads(meta_json)
                except Exception:
                    meta = {}
                matches.append({
                    "id": mem_id,
                    "content": content,
                    "similarity": round(sim, 4),
                    "metadata": meta,
                    "source": source,
                    "tier": tier,
                    "tags": tags,
                    "created_at": created_at
                })

        # Rank descending by cosine similarity
        matches.sort(key=lambda m: m["similarity"], reverse=True)
        return matches[:top_k]

    def soft_delete_memory(self, memory_id: str) -> bool:
        """
        Soft-deletes a memory entry to the recycle bin (Rule 7).
        Preserves row but sets is_deleted = 1.
        """
        conn = self._get_conn()
        cursor = conn.cursor()
        cursor.execute("""
            UPDATE associative_memory 
            SET is_deleted = 1 
            WHERE id = ?;
        """, (memory_id,))
        modified = cursor.rowcount > 0
        conn.commit()
        return modified

    def get_stats(self) -> Dict[str, Any]:
        """Returns statistics on active and recycled memories."""
        conn = self._get_conn()
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM associative_memory WHERE is_deleted = 0;")
        active_count = cursor.fetchone()[0]
        cursor.execute("SELECT COUNT(*) FROM associative_memory WHERE is_deleted = 1;")
        deleted_count = cursor.fetchone()[0]

        return {
            "active_memories": active_count,
            "recycled_memories": deleted_count,
            "dimension": 384,
            "encryption": "SQLCipher-256"
        }


# Global singleton instance
sqlite_vec_store = SqliteVectorStore()
