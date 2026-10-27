"""
Phenom Encrypted Vector Store & Local Embeddings
Uses all-MiniLM-L6-v2 sentence embeddings.
Embeddings are stored encrypted at rest inside the SQLCipher database.
Features:
- Incremental indexing based on file mtime
- Multi-format document chunking and indexing
- Fast in-memory cosine similarity search with exact source attribution
- Search across documents, notes, and conversation turns
"""

import os
import uuid
from typing import List, Dict, Any, Optional
import numpy as np
from sentence_transformers import SentenceTransformer

from services.backend.memory.db import encrypted_db
from services.backend.memory.doc_reader import doc_reader

SUPPORTED_EXTENSIONS = {".txt", ".md", ".pdf", ".docx", ".pptx", ".xlsx"}

class VectorStore:
    def __init__(self):
        self._model: Optional[SentenceTransformer] = None

    def _get_model(self) -> SentenceTransformer:
        if self._model is None:
            self._model = SentenceTransformer("all-MiniLM-L6-v2")
        return self._model

    def embed_text(self, text: str) -> np.ndarray:
        model = self._get_model()
        vec = model.encode(text, normalize_embeddings=True)
        return np.array(vec, dtype=np.float32)

    def index_file(self, file_path: str) -> int:
        """
        Incrementally indexes a single document file.
        Returns number of chunks indexed (0 if skipped because unmodified).
        """
        abs_path = os.path.abspath(file_path)
        if not os.path.isfile(abs_path):
            return 0

        ext = os.path.splitext(abs_path)[1].lower()
        if ext not in SUPPORTED_EXTENSIONS:
            return 0

        current_mtime = os.path.getmtime(abs_path)

        # Check existing mtime in SQLCipher
        conn = encrypted_db.get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT mtime FROM embeddings WHERE doc_path = ? LIMIT 1;", (abs_path,))
        row = cursor.fetchone()

        if row is not None and abs(row[0] - current_mtime) < 0.001:
            conn.close()
            return 0  # Unmodified, skip

        # Extract text and split into chunks
        try:
            full_text = doc_reader.read_document(abs_path)
        except Exception:
            conn.close()
            return 0

        chunks = doc_reader.chunk_text(full_text, chunk_size=350, overlap=50)
        if not chunks:
            conn.close()
            return 0

        # Remove previous chunks for this file
        with conn:
            conn.execute("DELETE FROM embeddings WHERE doc_path = ?;", (abs_path,))

            for idx, chunk in enumerate(chunks):
                emb = self.embed_text(chunk)
                chunk_id = f"emb-{uuid.uuid4().hex[:12]}"
                conn.execute(
                    "INSERT INTO embeddings (id, doc_path, chunk_index, chunk_text, mtime, embedding_blob) "
                    "VALUES (?, ?, ?, ?, ?, ?);",
                    (chunk_id, abs_path, idx, chunk, current_mtime, emb.tobytes())
                )

        conn.close()
        return len(chunks)

    def index_folder(self, folder_path: str, recursive: bool = True) -> Dict[str, Any]:
        """Indexes all supported documents in a folder incrementally."""
        abs_folder = os.path.abspath(folder_path)
        if not os.path.isdir(abs_folder):
            raise FileNotFoundError(f"Folder not found: {folder_path}")

        files_indexed = 0
        chunks_indexed = 0
        files_skipped = 0

        for root, _, files in os.walk(abs_folder):
            for file in files:
                ext = os.path.splitext(file)[1].lower()
                if ext in SUPPORTED_EXTENSIONS:
                    file_path = os.path.join(root, file)
                    c_count = self.index_file(file_path)
                    if c_count > 0:
                        files_indexed += 1
                        chunks_indexed += c_count
                    else:
                        files_skipped += 1
            if not recursive:
                break

        return {
            "folder": abs_folder,
            "files_indexed": files_indexed,
            "chunks_indexed": chunks_indexed,
            "files_unmodified": files_skipped
        }

    def search(self, query: str, top_k: int = 5, folder_filter: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Executes semantic cosine similarity search across all indexed chunks.
        Shows exact source document, chunk snippet, and similarity score.
        """
        query_vec = self.embed_text(query)

        conn = encrypted_db.get_connection()
        cursor = conn.cursor()
        
        if folder_filter:
            norm_filter = os.path.abspath(folder_filter)
            cursor.execute(
                "SELECT id, doc_path, chunk_index, chunk_text, embedding_blob FROM embeddings WHERE doc_path LIKE ?;",
                (f"{norm_filter}%",)
            )
        else:
            cursor.execute("SELECT id, doc_path, chunk_index, chunk_text, embedding_blob FROM embeddings;")

        rows = cursor.fetchall()
        conn.close()

        if not rows:
            return []

        scored_results = []
        for r_id, path, c_idx, text, blob in rows:
            emb = np.frombuffer(blob, dtype=np.float32)
            # Dot product for normalized vectors = cosine similarity
            sim = float(np.dot(query_vec, emb))
            scored_results.append({
                "score": round(sim, 4),
                "source": path,
                "filename": os.path.basename(path),
                "chunk_index": c_idx,
                "snippet": text[:400]
            })

        scored_results.sort(key=lambda x: x["score"], reverse=True)
        return scored_results[:top_k]

    def search_conversations(self, query: str, limit: int = 5) -> List[Dict[str, Any]]:
        """Searches past conversation turns in the encrypted messages table."""
        conn = encrypted_db.get_connection()
        cursor = conn.cursor()
        cursor.execute(
            "SELECT id, role, content, timestamp FROM messages WHERE content LIKE ? ORDER BY timestamp DESC LIMIT ?;",
            (f"%{query}%", limit)
        )
        rows = cursor.fetchall()
        conn.close()

        return [
            {
                "id": r[0],
                "role": r[1],
                "content": r[2],
                "timestamp": r[3],
                "source": "conversation_history"
            }
            for r in rows
        ]

vector_store = VectorStore()
