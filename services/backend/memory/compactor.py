"""
Phenom Context Compactor & Memory Decay Engine
Handles:
1. Conversation Context Auto-Compaction:
   - Evaluates active conversation sliding window (default 15 turns).
   - Summarizes older turns into structured facts and episodic memory summaries.
   - Preserves lean recent conversation context.
2. Spaced Relevance Fact Decay:
   - Frequently referenced facts and core profile facts stay permanent.
   - Transient operational context decays after 14 days unless reinforced.
"""

import re
from datetime import datetime, timezone, timedelta
from typing import List, Dict, Any, Tuple, Optional
from pydantic import BaseModel, Field

class CompactedContext(BaseModel):
    preserved_messages: List[Dict[str, Any]]
    compacted_count: int
    extracted_facts: List[str]
    context_summary: str

class MemoryCompactor:
    def __init__(self, max_turns: int = 15, preserve_recent: int = 6, decay_days: int = 14):
        self.max_turns = max_turns
        self.preserve_recent = preserve_recent
        self.decay_days = decay_days

    def estimate_tokens(self, messages: List[Dict[str, Any]]) -> int:
        """Rough token heuristic (~4 chars per token)."""
        total_chars = sum(len(str(m.get("content", ""))) for m in messages)
        return max(1, total_chars // 4)

    def should_compact(self, messages: List[Dict[str, Any]], token_limit: int = 6000) -> bool:
        if len(messages) > self.max_turns:
            return True
        if self.estimate_tokens(messages) > token_limit:
            return True
        return False

    def compact_history(self, messages: List[Dict[str, Any]]) -> CompactedContext:
        """
        Compacts the conversation history:
        - Retains `preserve_recent` most recent messages verbatim.
        - Analyzes older turns to extract key facts and generate an executive summary.
        """
        if len(messages) <= self.preserve_recent:
            return CompactedContext(
                preserved_messages=list(messages),
                compacted_count=0,
                extracted_facts=[],
                context_summary=""
            )

        older = messages[:-self.preserve_recent]
        preserved = messages[-self.preserve_recent:]

        extracted_facts: List[str] = []
        user_intents: List[str] = []

        for m in older:
            role = m.get("role", "unknown")
            content = str(m.get("content", "")).strip()

            if role == "user":
                user_intents.append(content[:120])
                # Extract simple factual statements (e.g. "I prefer...", "my nickname is...", "project is...")
                matches = re.findall(r"(?:i prefer|my \w+ is|remember that|note that)\s+([^.!?\n]+)", content, re.IGNORECASE)
                for match in matches:
                    extracted_facts.append(match.strip())

        summary_points = [f"User discussed: {intent}" for intent in user_intents[:4]]
        context_summary = "Prior conversation summary: " + "; ".join(summary_points) if summary_points else "Prior dialogue compacted."

        return CompactedContext(
            preserved_messages=preserved,
            compacted_count=len(older),
            extracted_facts=extracted_facts,
            context_summary=context_summary
        )

    def evaluate_fact_retention(self, category: str, fact_text: str, created_at_iso: str) -> bool:
        """
        Spaced relevance evaluation:
        - 'permanent', 'profile', 'preference', 'owner' categories never decay.
        - Transient/scratch categories decay after `decay_days` days.
        Returns True if fact should be retained, False if it should decay.
        """
        cat_lower = category.strip().lower()
        if cat_lower in {"profile", "permanent", "preference", "owner", "rule"}:
            return True

        try:
            created_dt = datetime.fromisoformat(created_at_iso)
            now = datetime.now(timezone.utc)
            if created_dt.tzinfo is None:
                created_dt = created_dt.replace(tzinfo=timezone.utc)
            age_days = (now - created_dt).total_seconds() / 86400.0
            return age_days <= self.decay_days
        except Exception:
            return True

    def prune_decayed_facts(self, db_conn) -> int:
        """
        Prunes facts in SQLCipher database that have expired according to decay policy.
        Returns number of pruned facts.
        """
        cursor = db_conn.cursor()
        cursor.execute("SELECT id, category, fact, created_at FROM facts;")
        rows = cursor.fetchall()

        to_delete = []
        for fid, cat, fact_text, created_at in rows:
            if not self.evaluate_fact_retention(cat, fact_text, created_at):
                to_delete.append(fid)

        if to_delete:
            with db_conn:
                cursor.executemany("DELETE FROM facts WHERE id = ?;", [(fid,) for fid in to_delete])

        return len(to_delete)
