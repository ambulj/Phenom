"""
Phenom Encrypted Cognitive Mirror Database (SQLCipher v4, AES-256)
Stores personalized cognitive profiles, learned feature representations, and synthesis logs (MIR-01, SAF-01).
Key stored securely in Windows Credential Manager under 'Phenom/cognitive-mirror-key' (Rule 4, Rule 11).
Zero cloud exfiltration.
"""

import os
import json
import secrets
import sqlcipher3
from typing import Optional, List, Dict, Any
from datetime import datetime, timezone

try:
    import win32cred
except ImportError:
    win32cred = None

CRED_TARGET = "Phenom/cognitive-mirror-key"
DEFAULT_COGNITIVE_DB_PATH = os.path.abspath("services/backend/data/cognitive_profile.db")


def get_or_create_mirror_key() -> str:
    """Retrieves 256-bit encryption key from Windows Credential Manager, or generates one."""
    if win32cred is None:
        return os.environ.get("PHENOM_COGNITIVE_MIRROR_KEY", "c09n1t1v3m1rr0rk3yf4llb4ck9876543210abcdef0123456789abcdef01234567")
    try:
        cred = win32cred.CredRead(CRED_TARGET, win32cred.CRED_TYPE_GENERIC)
        blob = cred["CredentialBlob"]
        if isinstance(blob, bytes):
            try:
                return blob.decode("utf-16le")
            except UnicodeDecodeError:
                return blob.decode("utf-8", errors="ignore")
        return str(blob)
    except Exception:
        # Check environment variable before generating new one
        env_key = os.environ.get("PHENOM_COGNITIVE_MIRROR_KEY")
        if env_key:
            new_key = env_key
        else:
            new_key = secrets.token_hex(32)

        try:
            cred = {
                "Type": win32cred.CRED_TYPE_GENERIC,
                "TargetName": CRED_TARGET,
                "CredentialBlob": new_key,
                "Persist": win32cred.CRED_PERSIST_LOCAL_MACHINE,
                "Comment": "Phenom Cognitive Mirror SQLCipher Key",
            }
            win32cred.CredWrite(cred, 0)
        except Exception:
            pass
        return new_key


class CognitiveDatabaseManager:
    """Manages encrypted SQLCipher database for Cognitive Mirror storage."""

    def __init__(self, db_path: Optional[str] = None, encryption_key: Optional[str] = None):
        self.db_path = db_path or DEFAULT_COGNITIVE_DB_PATH
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        self.key = encryption_key or get_or_create_mirror_key()
        self._init_schema()

    def get_connection(self):
        conn = sqlcipher3.connect(self.db_path, timeout=30.0)
        conn.execute(f"PRAGMA key = '{self.key}';")
        conn.execute("PRAGMA cipher_compatibility = 4;")
        conn.execute("PRAGMA busy_timeout = 30000;")
        return conn

    def _init_schema(self):
        conn = self.get_connection()
        with conn:
            conn.execute("""
            CREATE TABLE IF NOT EXISTS dimension_profiles (
                dimension TEXT PRIMARY KEY,
                profile_json TEXT NOT NULL,
                confidence REAL NOT NULL,
                sample_count INTEGER NOT NULL,
                updated_at TEXT NOT NULL
            );
            """)
            conn.execute("""
            CREATE TABLE IF NOT EXISTS learned_samples (
                sample_id TEXT PRIMARY KEY,
                dimension TEXT NOT NULL,
                source_type TEXT NOT NULL,
                features_json TEXT NOT NULL,
                created_at TEXT NOT NULL
            );
            """)
            conn.execute("""
            CREATE TABLE IF NOT EXISTS synthesis_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                task_type TEXT NOT NULL,
                prompt_summary TEXT NOT NULL,
                applied_traits TEXT NOT NULL,
                duration_ms REAL NOT NULL,
                created_at TEXT NOT NULL
            );
            """)
            conn.execute("""
            CREATE TABLE IF NOT EXISTS mirror_metadata (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL
            );
            """)
        conn.close()

    def save_dimension_profile(
        self, dimension: str, profile_json: str, confidence: float, sample_count: int
    ):
        updated_at = datetime.now(timezone.utc).isoformat()
        conn = self.get_connection()
        with conn:
            conn.execute("""
            INSERT INTO dimension_profiles (dimension, profile_json, confidence, sample_count, updated_at)
            VALUES (?, ?, ?, ?, ?)
            ON CONFLICT(dimension) DO UPDATE SET
                profile_json = excluded.profile_json,
                confidence = excluded.confidence,
                sample_count = excluded.sample_count,
                updated_at = excluded.updated_at;
            """, (dimension, profile_json, confidence, sample_count, updated_at))
        conn.close()

    def get_dimension_profile(self, dimension: str) -> Optional[Dict[str, Any]]:
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute(
            "SELECT dimension, profile_json, confidence, sample_count, updated_at FROM dimension_profiles WHERE dimension = ?",
            (dimension,)
        )
        row = cursor.fetchone()
        conn.close()
        if not row:
            return None
        return {
            "dimension": row[0],
            "profile_json": row[1],
            "confidence": row[2],
            "sample_count": row[3],
            "updated_at": row[4],
        }

    def save_learned_sample(
        self, sample_id: str, dimension: str, source_type: str, features_json: str
    ):
        created_at = datetime.now(timezone.utc).isoformat()
        conn = self.get_connection()
        with conn:
            conn.execute("""
            INSERT OR REPLACE INTO learned_samples (sample_id, dimension, source_type, features_json, created_at)
            VALUES (?, ?, ?, ?, ?);
            """, (sample_id, dimension, source_type, features_json, created_at))
        conn.close()

    def get_samples_for_dimension(self, dimension: str) -> List[Dict[str, Any]]:
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute(
            "SELECT sample_id, dimension, source_type, features_json, created_at FROM learned_samples WHERE dimension = ? ORDER BY created_at DESC",
            (dimension,)
        )
        rows = cursor.fetchall()
        conn.close()
        results = []
        for r in rows:
            results.append({
                "sample_id": r[0],
                "dimension": r[1],
                "source_type": r[2],
                "features_json": r[3],
                "created_at": r[4],
            })
        return results

    def log_synthesis(
        self, task_type: str, prompt_summary: str, applied_traits: List[str], duration_ms: float
    ):
        created_at = datetime.now(timezone.utc).isoformat()
        conn = self.get_connection()
        with conn:
            conn.execute("""
            INSERT INTO synthesis_history (task_type, prompt_summary, applied_traits, duration_ms, created_at)
            VALUES (?, ?, ?, ?, ?);
            """, (task_type, prompt_summary, json.dumps(applied_traits), duration_ms, created_at))
        conn.close()

    def get_synthesis_history(self, limit: int = 50) -> List[Dict[str, Any]]:
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute(
            "SELECT id, task_type, prompt_summary, applied_traits, duration_ms, created_at FROM synthesis_history ORDER BY id DESC LIMIT ?",
            (limit,)
        )
        rows = cursor.fetchall()
        conn.close()
        results = []
        for r in rows:
            results.append({
                "id": r[0],
                "task_type": r[1],
                "prompt_summary": r[2],
                "applied_traits": json.loads(r[3]),
                "duration_ms": r[4],
                "created_at": r[5],
            })
        return results

    def reset_dimension(self, dimension: Optional[str] = None):
        conn = self.get_connection()
        with conn:
            if dimension:
                conn.execute("DELETE FROM dimension_profiles WHERE dimension = ?", (dimension,))
                conn.execute("DELETE FROM learned_samples WHERE dimension = ?", (dimension,))
            else:
                conn.execute("DELETE FROM dimension_profiles;")
                conn.execute("DELETE FROM learned_samples;")
                conn.execute("DELETE FROM synthesis_history;")
        conn.close()
