"""
Phenom Encrypted Memory Database (SQLCipher)
Key stored securely in Windows Credential Manager under 'Phenom/db-key'.
Manages: messages, facts, learned_rules, approvals_remembered, action_log, settings.
"""

import os
import secrets
import sqlcipher3
import win32cred
from typing import Optional, List, Dict, Any
from datetime import datetime, timezone

CRED_TARGET = "Phenom/db-key"
DEFAULT_DB_PATH = os.path.abspath("services/backend/data/phenom_encrypted.db")

def get_or_create_master_key() -> str:
    """Retrieves 256-bit encryption key from Windows Credential Manager, or creates one."""
    try:
        cred = win32cred.CredRead(CRED_TARGET, win32cred.CRED_TYPE_GENERIC)
        blob = cred["CredentialBlob"]
        if isinstance(blob, bytes):
            return blob.decode("utf-16le")
        return str(blob)
    except Exception:
        # Generate new 256-bit key
        new_key = secrets.token_hex(32)
        cred = {
            "Type": win32cred.CRED_TYPE_GENERIC,
            "TargetName": CRED_TARGET,
            "CredentialBlob": new_key,
            "Persist": win32cred.CRED_PERSIST_LOCAL_MACHINE,
            "Comment": "Phenom Encrypted Database Master Key"
        }
        win32cred.CredWrite(cred, 0)
        return new_key

class EncryptedDatabaseManager:
    def __init__(self, db_path: Optional[str] = None, encryption_key: Optional[str] = None):
        self.db_path = db_path or DEFAULT_DB_PATH
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        self.key = encryption_key or get_or_create_master_key()
        self._init_schema()

    def get_connection(self):
        conn = sqlcipher3.connect(self.db_path)
        conn.execute(f"PRAGMA key = '{self.key}';")
        conn.execute("PRAGMA cipher_compatibility = 4;")
        return conn

    def _init_schema(self):
        conn = self.get_connection()
        with conn:
            conn.execute("""
            CREATE TABLE IF NOT EXISTS messages (
                id TEXT PRIMARY KEY,
                role TEXT NOT NULL,
                content TEXT NOT NULL,
                timestamp TEXT NOT NULL,
                model TEXT,
                tokens INTEGER
            );
            """)
            conn.execute("""
            CREATE TABLE IF NOT EXISTS facts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                category TEXT NOT NULL,
                fact TEXT NOT NULL,
                created_at TEXT NOT NULL
            );
            """)
            conn.execute("""
            CREATE TABLE IF NOT EXISTS learned_rules (
                id TEXT PRIMARY KEY,
                rule_text TEXT NOT NULL,
                created_at TEXT NOT NULL,
                enabled INTEGER DEFAULT 1
            );
            """)
            conn.execute("""
            CREATE TABLE IF NOT EXISTS settings (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL
            );
            """)
            conn.execute("""
            CREATE TABLE IF NOT EXISTS embeddings (
                id TEXT PRIMARY KEY,
                doc_path TEXT NOT NULL,
                chunk_index INTEGER NOT NULL,
                chunk_text TEXT NOT NULL,
                mtime REAL NOT NULL,
                embedding_blob BLOB NOT NULL
            );
            """)
            conn.execute("CREATE INDEX IF NOT EXISTS idx_embeddings_path ON embeddings(doc_path);")
            conn.execute("""
            CREATE TABLE IF NOT EXISTS photo_index (
                id TEXT PRIMARY KEY,
                file_path TEXT NOT NULL UNIQUE,
                filename TEXT NOT NULL,
                tags TEXT NOT NULL,
                caption TEXT NOT NULL,
                mtime REAL NOT NULL,
                metadata_json TEXT NOT NULL
            );
            """)
        conn.close()

    def add_message(self, msg_id: str, role: str, content: str, model: Optional[str] = None, tokens: Optional[int] = None):
        ts = datetime.now(timezone.utc).isoformat()
        conn = self.get_connection()
        with conn:
            conn.execute(
                "INSERT INTO messages (id, role, content, timestamp, model, tokens) VALUES (?, ?, ?, ?, ?, ?);",
                (msg_id, role, content, ts, model, tokens)
            )
        conn.close()

    def get_recent_messages(self, limit: int = 20) -> List[Dict[str, Any]]:
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT id, role, content, timestamp, model, tokens FROM messages ORDER BY timestamp DESC LIMIT ?;", (limit,))
        rows = cursor.fetchall()
        conn.close()
        return [
            {"id": r[0], "role": r[1], "content": r[2], "timestamp": r[3], "model": r[4], "tokens": r[5]}
            for r in reversed(rows)
        ]

    def add_fact(self, category: str, fact: str):
        ts = datetime.now(timezone.utc).isoformat()
        conn = self.get_connection()
        with conn:
            conn.execute("INSERT INTO facts (category, fact, created_at) VALUES (?, ?, ?);", (category, fact, ts))
        conn.close()

    def list_facts(self) -> List[Dict[str, Any]]:
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT id, category, fact, created_at FROM facts ORDER BY created_at DESC;")
        rows = cursor.fetchall()
        conn.close()
        return [{"id": r[0], "category": r[1], "fact": r[2], "created_at": r[3]} for r in rows]

# Global Encrypted DB Manager
encrypted_db = EncryptedDatabaseManager()
