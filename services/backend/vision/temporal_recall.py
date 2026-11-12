"""
Phenom Temporal Recall Engine
Translates natural language temporal queries ("What command failed 15 minutes ago?",
"Find that CUDA chart from earlier today") into time-bounded semantic vector queries
against EncryptedVisualStore.
"""

import re
import time
import logging
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional, Tuple
import numpy as np

from services.backend.memory.embeddings import LocalEmbeddingPipeline, embedding_pipeline as default_embedding_pipeline
from services.backend.memory.visual_store import EncryptedVisualStore, visual_store as default_visual_store

logger = logging.getLogger("phenom.temporal_recall")


class TemporalRecallEngine:
    """
    Parses conversational time expressions and executes hybrid temporal + vector search.
    """

    def __init__(
        self,
        visual_st: Optional[EncryptedVisualStore] = None,
        embed_pipe: Optional[LocalEmbeddingPipeline] = None
    ):
        self.visual_store = visual_st or default_visual_store
        self.embedding_pipeline = embed_pipe or default_embedding_pipeline

    def parse_temporal_query(
        self,
        query: str,
        now_ts: Optional[float] = None
    ) -> Tuple[str, Optional[float], Optional[float]]:
        """
        Parses time expressions and returns (cleaned_query, start_ts, end_ts).
        """
        now = now_ts if now_ts is not None else time.time()
        start_ts: Optional[float] = None
        end_ts: Optional[float] = None
        clean_query = query.strip()

        # Pattern 1: N minutes ago / last N minutes
        m_mins = re.search(r"\b(?:last\s+)?(\d+)\s*(?:mins?|minutes?)(?:\s+ago)?\b", clean_query, re.IGNORECASE)
        if m_mins:
            mins = int(m_mins.group(1))
            start_ts = now - (mins * 60.0)
            end_ts = now
            clean_query = clean_query[:m_mins.start()] + " " + clean_query[m_mins.end():]

        # Pattern 2: N hours ago / last N hours
        m_hrs = re.search(r"\b(?:last\s+)?(\d+)\s*(?:hours?|hrs?)(?:\s+ago)?\b", clean_query, re.IGNORECASE)
        if m_hrs and start_ts is None:
            hrs = int(m_hrs.group(1))
            start_ts = now - (hrs * 3600.0)
            end_ts = now
            clean_query = clean_query[:m_hrs.start()] + " " + clean_query[m_hrs.end():]

        # Pattern 3: past hour / last hour
        if re.search(r"\b(?:past|last)\s+hour\b", clean_query, re.IGNORECASE) and start_ts is None:
            start_ts = now - 3600.0
            end_ts = now
            clean_query = re.sub(r"\b(?:past|last)\s+hour\b", "", clean_query, flags=re.IGNORECASE)

        # Pattern 4: today
        if re.search(r"\btoday\b", clean_query, re.IGNORECASE) and start_ts is None:
            dt_now = datetime.fromtimestamp(now)
            dt_today_start = datetime(dt_now.year, dt_now.month, dt_now.day, 0, 0, 0)
            start_ts = dt_today_start.timestamp()
            end_ts = now
            clean_query = re.sub(r"\btoday\b", "", clean_query, flags=re.IGNORECASE)

        # Pattern 5: yesterday
        if re.search(r"\byesterday\b", clean_query, re.IGNORECASE) and start_ts is None:
            dt_now = datetime.fromtimestamp(now)
            dt_yest = dt_now - timedelta(days=1)
            start_ts = datetime(dt_yest.year, dt_yest.month, dt_yest.day, 0, 0, 0).timestamp()
            end_ts = datetime(dt_yest.year, dt_yest.month, dt_yest.day, 23, 59, 59).timestamp()
            clean_query = re.sub(r"\byesterday\b", "", clean_query, flags=re.IGNORECASE)

        # Clean multiple spaces and punctuation artifacts
        clean_query = re.sub(r"\s+", " ", clean_query).strip()
        # Remove lingering conversational lead-ins like "what was that", "find that", "where did i see"
        clean_query = re.sub(r"^(?:where\s+did\s+i\s+see|find\s+(?:the|that)?|what\s+was\s+(?:the|that)?|show\s+me)\s+", "", clean_query, flags=re.IGNORECASE).strip()

        return clean_query or query, start_ts, end_ts

    def recall(
        self,
        query: str,
        limit: int = 5,
        min_score: float = 0.1,
        now_ts: Optional[float] = None
    ) -> List[Dict[str, Any]]:
        """
        Executes natural language temporal recall across encrypted visual memory.
        """
        now = now_ts if now_ts is not None else time.time()
        clean_text, start_ts, end_ts = self.parse_temporal_query(query, now_ts=now)

        query_vec = self.embedding_pipeline.embed_query(clean_text)
        raw_results = self.visual_store.search_similar_chunks(
            query_vector=query_vec,
            start_time=start_ts,
            end_time=end_ts,
            limit=limit,
            min_score=min_score
        )

        formatted_matches = []
        for r in raw_results:
            diff_sec = max(0, int(now - r["timestamp"]))
            if diff_sec < 60:
                rel_time = f"{diff_sec}s ago"
            elif diff_sec < 3600:
                rel_time = f"{diff_sec // 60}m ago"
            else:
                rel_time = f"{diff_sec // 3600}h ago"

            formatted_matches.append({
                "id": r["id"],
                "timestamp": r["timestamp"],
                "relative_time": rel_time,
                "process_name": r["process_name"],
                "window_title": r["window_title"],
                "text_content": r["text_content"],
                "similarity_score": round(r["score"], 4),
                "bbox": r["bbox"]
            })

        return formatted_matches


# Global singleton
temporal_recall_engine = TemporalRecallEngine()
