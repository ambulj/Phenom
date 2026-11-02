"""
Phenom Encrypted Visual Store
Provides persistent, encrypted vector storage for continuous desktop screen history.
Uses sqlcipher3 / sqlite3 with custom vectorized cosine similarity scalar function.
Strictly local, bounded with rolling retention pruning.
"""

import os
import json
import sqlite3
import logging
from typing import List, Dict, Any, Optional, Tuple
import numpy as np

logger = logging.getLogger("phenom.visual_store")

try:
    import sqlcipher3
    HAS_SQLCIPHER = True
except ImportError:
    sqlcipher3 = None
    HAS_SQLCIPHER = False


def cosine_similarity_blob(b1: bytes, b2: bytes) -> float:
    """
    SQLite scalar function to compute cosine similarity between two float32 BLOB vectors.
    """
    if not b1 or not b2:
        return 0.0
    try:
        v1 = np.frombuffer(b1, dtype=np.float32)
        v2 = np.frombuffer(b2, dtype=np.float32)
        dot = float(np.dot(v1, v2))
        norm1 = float(np.linalg.norm(v1))
        norm2 = float(np.linalg.norm(v2))
        denom = norm1 * norm2
        return float(dot / denom) if denom > 1e-6 else 0.0
    except Exception:
        return 0.0


class EncryptedVisualStore:
    """
    Encrypted SQLite / SQLCipher vector store for screen text history.
    """

    def __init__(self, db_path: Optional[str] = None, encryption_key: Optional[str] = None):
        if db_path is None:
            base_dir = os.path.dirname(os.path.abspath(__file__))
            self.db_path = os.path.join(base_dir, "visual_history.db")
        else:
            self.db_path = db_path

        self.encryption_key = encryption_key
        self._conn = None
        self._init_db()

    def _get_connection(self):
        if self._conn is None:
            if HAS_SQLCIPHER and self.encryption_key:
                conn = sqlcipher3.connect(self.db_path)
                conn.execute(f"PRAGMA key = '{self.encryption_key}';")
            else:
                conn = sqlite3.connect(self.db_path, check_same_thread=False)

            # Register custom vectorized scalar function
            conn.create_function("cosine_sim", 2, cosine_similarity_blob)
            conn.row_factory = sqlite3.Row
            self._conn = conn
        return self._conn

    def _init_db(self):
        """Initializes tables and indices."""
        conn = self._get_connection()
        with conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS visual_timeline (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp REAL NOT NULL,
                    iso_time TEXT NOT NULL,
                    process_name TEXT NOT NULL,
                    window_title TEXT NOT NULL,
                    text_content TEXT NOT NULL,
                    bbox_json TEXT,
                    embedding BLOB
                );
            """)
            conn.execute("CREATE INDEX IF NOT EXISTS idx_visual_timeline_ts ON visual_timeline(timestamp);")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_visual_timeline_proc ON visual_timeline(process_name);")

    def insert_chunks(self, chunks: List[Dict[str, Any]], embeddings: np.ndarray) -> int:
        """
        Inserts a batch of extracted screen text chunks and corresponding embedding vectors.
        Returns the number of rows inserted.
        """
        if not chunks or len(embeddings) != len(chunks):
            return 0

        conn = self._get_connection()
        rows_to_insert = []
        for chunk, emb in zip(chunks, embeddings):
            emb_bytes = emb.astype(np.float32).tobytes()
            bbox_str = json.dumps(chunk.get("bbox") or [])
            rows_to_insert.append((
                float(chunk.get("timestamp", 0.0)),
                str(chunk.get("iso_time", "")),
                str(chunk.get("process_name", "unknown")),
                str(chunk.get("window_title", "")),
                str(chunk.get("text_content", "")),
                bbox_str,
                emb_bytes
            ))

        with conn:
            conn.executemany("""
                INSERT INTO visual_timeline (
                    timestamp, iso_time, process_name, window_title, text_content, bbox_json, embedding
                ) VALUES (?, ?, ?, ?, ?, ?, ?);
            """, rows_to_insert)

        return len(rows_to_insert)

    def search_similar_chunks(
        self,
        query_vector: np.ndarray,
        start_time: Optional[float] = None,
        end_time: Optional[float] = None,
        process_filter: Optional[str] = None,
        limit: int = 10,
        min_score: float = 0.1
    ) -> List[Dict[str, Any]]:
        """
        Searches visual history using cosine similarity against the query vector,
        filtered by optional time bounds and process name.
        """
        conn = self._get_connection()
        query_bytes = query_vector.astype(np.float32).tobytes()

        conditions = []
        params = [query_bytes]

        if start_time is not None:
            conditions.append("timestamp >= ?")
            params.append(start_time)
        if end_time is not None:
            conditions.append("timestamp <= ?")
            params.append(end_time)
        if process_filter:
            conditions.append("process_name = ?")
            params.append(process_filter.lower())

        where_clause = f"WHERE {' AND '.join(conditions)}" if conditions else ""

        sql = f"""
            SELECT id, timestamp, iso_time, process_name, window_title, text_content, bbox_json,
                   cosine_sim(embedding, ?) AS score
            FROM visual_timeline
            {where_clause}
            ORDER BY score DESC, timestamp DESC
            LIMIT ?;
        """
        params.append(limit * 2)  # retrieve extra to filter min_score

        cursor = conn.execute(sql, params)
        results = []
        for row in cursor.fetchall():
            score = float(row["score"])
            if score >= min_score:
                bbox = []
                try:
                    bbox = json.loads(row["bbox_json"]) if row["bbox_json"] else []
                except Exception:
                    pass

                results.append({
                    "id": row["id"],
                    "timestamp": row["timestamp"],
                    "iso_time": row["iso_time"],
                    "process_name": row["process_name"],
                    "window_title": row["window_title"],
                    "text_content": row["text_content"],
                    "bbox": bbox,
                    "score": score
                })
            if len(results) >= limit:
                break

        return results

    def prune_older_than(self, days: int = 7) -> int:
        """Prunes historical records older than the specified retention window in days."""
        import time
        cutoff_ts = time.time() - (days * 86400.0)
        conn = self._get_connection()
        with conn:
            cursor = conn.execute("DELETE FROM visual_timeline WHERE timestamp < ?;", (cutoff_ts,))
            deleted = cursor.rowcount
        return deleted

    def get_timeline_stats(self) -> Dict[str, Any]:
        """Returns row count and time range of stored visual history."""
        conn = self._get_connection()
        cursor = conn.execute("""
            SELECT COUNT(*) AS total_records,
                   MIN(timestamp) AS earliest_ts,
                   MAX(timestamp) AS latest_ts
            FROM visual_timeline;
        """)
        row = cursor.fetchone()
        return {
            "total_records": row["total_records"] if row else 0,
            "earliest_ts": row["earliest_ts"] if row else None,
            "latest_ts": row["latest_ts"] if row else None
        }

    def close(self):
        """Closes the underlying connection."""
        if self._conn:
            try:
                self._conn.close()
            except Exception:
                pass
            self._conn = None


# Global singleton
visual_store = EncryptedVisualStore()
