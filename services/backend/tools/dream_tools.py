"""
Sovereign Neuro-Symbolic Sleep & Dream Safety Tools (SAF-01).
Registers Tier 0 and Tier 1 governance tools for offline memory consolidation,
heuristic schema formation, graph compaction, and dead-link pruning.
"""

from typing import Dict, Any, Optional

from services.backend.safety.guardian import guardian
from services.backend.safety.registry import registry
from services.backend.schemas.dream import (
    DreamTriggerCycleArgs,
    DreamGetStatusArgs,
    DreamPruneStaleArgs,
)
from services.backend.memory.dream_engine import dream_engine


# ==========================================
# Tier 0 Tools (Read-Only)
# ==========================================

@registry.register(
    name="dream_get_status",
    tier=0,
    description="Queries current Neuro-Symbolic Dream Engine status, active phase, and latest consolidation report (Read-Only)",
    args_schema=DreamGetStatusArgs,
    preview_fn=lambda a: "Query Neuro-Symbolic Dream Consolidation Engine status and telemetry (Read-Only)",
)
def dream_get_status(
    include_report: bool = True,
    **kwargs,
) -> Dict[str, Any]:
    """Inspect dream engine state and telemetry."""
    status = dream_engine.get_status()
    out = status.model_dump()
    if not include_report:
        out.pop("latest_report", None)
    return {
        "status": "success",
        "engine_status": out,
    }


# ==========================================
# Tier 1 Tools (Reversible Changes with Preview)
# ==========================================

@registry.register(
    name="dream_trigger_cycle",
    tier=1,
    description="Triggers an offline Neuro-Symbolic Sleep & Dream consolidation cycle (Reversible change with preview)",
    args_schema=DreamTriggerCycleArgs,
    preview_fn=lambda a: (
        f"Trigger Neuro-Symbolic Sleep & Dream memory consolidation cycle "
        f"(force={a.get('force') if isinstance(a, dict) else getattr(a, 'force', False)}, "
        f"max_episodes={a.get('max_episodes') if isinstance(a, dict) else getattr(a, 'max_episodes', 50)})"
    ),
)
def dream_trigger_cycle(
    force: bool = False,
    max_episodes: int = 50,
    **kwargs,
) -> Dict[str, Any]:
    """Execute a dream consolidation cycle."""
    if guardian.is_halted or dream_engine.is_halted():
        raise PermissionError("Dream consolidation halted by Guardian kill switch.")

    report = dream_engine.run_dream_cycle(
        force=force,
        max_episodes=max_episodes,
    )
    return {
        "status": "completed",
        "report": report.model_dump(),
    }


@registry.register(
    name="dream_prune_stale_memory",
    tier=1,
    description="Prunes dead associative links, decayed transient edges, and consolidates duplicate entities (Reversible change with preview)",
    args_schema=DreamPruneStaleArgs,
    preview_fn=lambda a: (
        f"Prune dead links and stale graph edges "
        f"(decay threshold: {a.get('decay_days_threshold') if isinstance(a, dict) else getattr(a, 'decay_days_threshold', 14)} days, "
        f"dry_run={a.get('dry_run') if isinstance(a, dict) else getattr(a, 'dry_run', False)})"
    ),
)
def dream_prune_stale_memory(
    decay_days_threshold: int = 14,
    dry_run: bool = False,
    **kwargs,
) -> Dict[str, Any]:
    """Prunes stale or orphaned graph edges."""
    if guardian.is_halted or dream_engine.is_halted():
        raise PermissionError("Dream memory pruning halted by Guardian kill switch.")

    result = dream_engine.prune_stale_memory(
        decay_days_threshold=decay_days_threshold,
        dry_run=dry_run,
    )
    return {
        "status": "success",
        "details": result,
    }
