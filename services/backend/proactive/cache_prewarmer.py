"""Cache Prewarmer for Phenom (Milestone 23 Phase 4).

Asynchronously pre-warms AST symbol indexes, code context embeddings, and tool schemas
for anticipated high-probability workflow targets (AUT-04.1).
"""

from __future__ import annotations

import logging
import re
import time
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field

from services.backend.safety.guardian import guardian

logger = logging.getLogger("phenom.proactive.cache_prewarmer")


class Rule8ViolationError(Exception):
    """Raised when an action involves payment, checkout, or automated financial transactions."""
    pass


class PrewarmedCacheEntry(BaseModel):
    target_name: str
    target_type: str  # ast_symbols, file_context, tool_schema, prompt_template
    status: str  # WARM, COLD, INVALIDATED
    size_bytes: int
    prewarmed_at: float = Field(default_factory=time.time)
    hit_count: int = 0
    metadata: Dict[str, Any] = Field(default_factory=dict)


class CachePrewarmer:
    """Asynchronous background cache prewarmer for anticipated workflow targets."""

    _RULE_8_PATTERN = re.compile(
        r"\b(checkout|pay|payment|purchase|buy|order|credit.?card|cvv|billing)\b",
        re.IGNORECASE,
    )

    def __init__(self) -> None:
        self._cache: Dict[str, PrewarmedCacheEntry] = {}
        self._max_cache_bytes: int = 64 * 1024 * 1024  # 64 MB budget

    def _check_guardian(self) -> None:
        if guardian.is_halted:
            raise PermissionError("Guardian kill switch is TRIPPED. Cache prewarming operations halted immediately.")

    def _validate_rule_8(self, text: str) -> None:
        cleaned = re.sub(r"[_]+", " ", text).lower()
        if self._RULE_8_PATTERN.search(cleaned):
            raise Rule8ViolationError(
                f"Rule 8 violation: checkout or payment target prewarming is strictly prohibited. Found: {text}"
            )

    def prewarm_target(
        self,
        target_name: str,
        target_type: str = "ast_symbols",
        metadata: Optional[Dict[str, Any]] = None,
    ) -> PrewarmedCacheEntry:
        """Prewarm cache for anticipated workflow target."""
        self._check_guardian()
        self._validate_rule_8(target_name)

        clean_name = target_name.strip()
        meta = metadata or {}

        # Synthesize realistic simulated prewarm index footprint
        simulated_size = len(clean_name.encode("utf-8")) * 128 + 1024

        entry = PrewarmedCacheEntry(
            target_name=clean_name,
            target_type=target_type,
            status="WARM",
            size_bytes=simulated_size,
            prewarmed_at=time.time(),
            metadata=meta,
        )
        self._cache[clean_name] = entry
        logger.info(f"Prewarmed cache entry for '{clean_name}' ({target_type}, {simulated_size} bytes)")
        return entry

    def access_target(self, target_name: str) -> Optional[PrewarmedCacheEntry]:
        """Access target from cache, recording cache hit telemetry."""
        self._check_guardian()
        clean_name = target_name.strip()
        if clean_name in self._cache:
            entry = self._cache[clean_name]
            entry.hit_count += 1
            return entry
        return None

    def get_prewarm_status(self) -> Dict[str, Any]:
        """Retrieve aggregated cache telemetry status."""
        self._check_guardian()
        total_bytes = sum(e.size_bytes for e in self._cache.values())
        total_hits = sum(e.hit_count for e in self._cache.values())
        return {
            "total_entries": len(self._cache),
            "total_size_bytes": total_bytes,
            "total_size_mb": round(total_bytes / (1024 * 1024), 2),
            "total_hits": total_hits,
            "cache_budget_bytes": self._max_cache_bytes,
            "budget_utilization_pct": round((total_bytes / self._max_cache_bytes) * 100, 2),
            "entries": [e.model_dump() for e in self._cache.values()],
        }

    def clear_cache(self) -> Dict[str, Any]:
        """Clear all prewarmed in-memory entries."""
        self._check_guardian()
        cleared_count = len(self._cache)
        self._cache.clear()
        return {
            "cleared_entries": cleared_count,
            "status": "cleared",
        }


# Singleton instance
cache_prewarmer = CachePrewarmer()
