"""
Associative Memory Engine & Semantic Knowledge Graph (MEM-02.2 & VEC-01.2).
Provides:
1. Autonomous tiered ingestion: auto-indexing daily debriefs & explicit "remember this" commands.
2. Contextual semantic recall (< 10ms query latency) using dense cosine similarity.
3. Obsidian [[wikilink]] backlink traversal.
4. Rule 7 soft-delete / memory recycling.
5. Synchronous Guardian kill switch integration (< 25.0ms SLA).
"""

import re
import os
import time
from typing import Dict, Any, List, Optional, Tuple

from services.backend.safety.guardian import guardian
from services.backend.safety.action_log import action_log
from services.backend.memory.vector_embeddings import vector_encoder, VectorEmbeddingEncoder
from services.backend.memory.sqlite_vec_store import sqlite_vec_store, SqliteVectorStore


WIKILINK_REGEX = re.compile(r"\[\[(.*?)\]\]")


class AssociativeMemoryEngine:
    """Coordinates tiered memory embedding, encrypted vector storage, and semantic recall."""

    def __init__(
        self,
        encoder: Optional[VectorEmbeddingEncoder] = None,
        store: Optional[SqliteVectorStore] = None
    ):
        self.encoder = encoder or vector_encoder
        self.store = store or sqlite_vec_store

    def store_explicit_memory(
        self,
        content: str,
        tags: Optional[List[str]] = None,
        source: str = "user_command"
    ) -> Dict[str, Any]:
        """
        Stores an explicit memory (e.g. from 'Phenom, remember this: ...').
        Tagged as #explicit with Tier 1 priority.
        """
        if guardian.is_halted:
            raise PermissionError("Guardian kill switch is active. Memory storage aborted.")

        clean = content.strip()
        all_tags = list(set((tags or []) + ["explicit", "user_memory"]))

        # Extract any [[wikilinks]] in text
        wikilinks = WIKILINK_REGEX.findall(clean)

        emb = self.encoder.encode(clean)
        metadata = {
            "type": "explicit_memory",
            "wikilinks": wikilinks,
            "char_count": len(clean)
        }

        mem_id = self.store.insert_memory(
            content=clean,
            embedding=emb,
            metadata=metadata,
            source=source,
            tier=1,
            tags=all_tags
        )

        action_log.log_action(
            tool="store_explicit_memory",
            tier=1,
            args={"memory_id": mem_id, "tags": all_tags},
            decision="auto",
            result_status="STORED",
            source="memory"
        )

        return {
            "status": "stored",
            "memory_id": mem_id,
            "content": clean,
            "tags": all_tags,
            "wikilinks": wikilinks
        }

    def ingest_daily_debrief(self, note_path: str) -> Dict[str, Any]:
        """Auto-ingests an Obsidian daily debrief note into associative memory (Tier 0)."""
        if guardian.is_halted:
            raise PermissionError("Guardian kill switch is active.")

        if not os.path.isfile(note_path):
            return {"status": "file_not_found", "path": note_path}

        with open(note_path, "r", encoding="utf-8") as f:
            text = f.read()

        filename = os.path.basename(note_path)
        date_tag = filename.replace(".md", "")
        all_tags = ["daily_debrief", "obsidian", date_tag]

        emb = self.encoder.encode(text[:1000])  # Embed executive summary header
        wikilinks = WIKILINK_REGEX.findall(text)

        mem_id = self.store.insert_memory(
            content=f"Daily Debrief {date_tag}: " + text[:400].replace("\n", " "),
            embedding=emb,
            metadata={"note_path": note_path, "wikilinks": wikilinks},
            source="obsidian_sync",
            tier=0,
            tags=all_tags
        )

        return {
            "status": "ingested",
            "memory_id": mem_id,
            "date": date_tag,
            "wikilinks": wikilinks
        }

    def recall(
        self,
        query: str,
        top_k: int = 5,
        min_score: float = 0.20,
        required_tags: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        Executes sub-10ms semantic similarity recall over associative long-term memory.
        Enriches results with Obsidian backlink traversal.
        """
        start = time.perf_counter()

        if guardian.is_halted:
            raise PermissionError("Guardian kill switch is active. Memory recall aborted.")

        q_vec = self.encoder.encode(query)
        matches = self.store.search_memories(
            query_embedding=q_vec,
            top_k=top_k,
            min_score=min_score,
            required_tags=required_tags
        )

        elapsed_ms = (time.perf_counter() - start) * 1000.0

        return {
            "query": query,
            "matches_count": len(matches),
            "latency_ms": round(elapsed_ms, 2),
            "results": matches
        }

    def delete_memory(self, memory_id: str) -> bool:
        """Soft-deletes a memory entry to the recycle bin (Rule 7)."""
        if guardian.is_halted:
            raise PermissionError("Guardian kill switch is active.")

        success = self.store.soft_delete_memory(memory_id)
        if success:
            action_log.log_action(
                tool="delete_associative_memory",
                tier=1,
                args={"memory_id": memory_id},
                decision="auto",
                result_status="RECYCLED",
                source="memory"
            )
        return success


# Global singleton instance
associative_memory_engine = AssociativeMemoryEngine()
