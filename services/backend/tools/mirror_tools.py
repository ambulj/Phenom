"""
Phenom Cognitive Mirror Safety Tools (SAF-01)
Registers Tier 0 and Tier 1 tools in the Safety ToolRegistry for cognitive profile statistics,
incremental learning from local sources, synthetic twin generation, and profile resets.
"""

from typing import Dict, Any, Optional, List
from services.backend.safety.registry import registry
from services.backend.schemas.cognitive_mirror import (
    MirrorDimension,
    SynthesisTaskType,
    MirrorGetProfileStatsArgs,
    MirrorLearnFromSourcesArgs,
    MirrorSynthesizeTextArgs,
    MirrorResetProfileArgs,
    MirrorSynthesisResult,
)
from services.backend.personality.cognitive_mirror import cognitive_mirror


# ==========================================
# Tier 0 Tools (Read-Only)
# ==========================================

@registry.register(
    name="mirror_get_profile_stats",
    tier=0,
    description="Retrieves learned cognitive profile statistics, confidence scores, and sample counts (Read-Only)",
    args_schema=MirrorGetProfileStatsArgs,
    preview_fn=lambda a: (
        f"Retrieve cognitive mirror profile statistics"
        + (f" for {a.get('dimension') if isinstance(a, dict) else getattr(a, 'dimension', '')}"
           if (a.get('dimension') if isinstance(a, dict) else getattr(a, 'dimension', None)) else "")
        + " (Read-Only)"
    ),
)
async def mirror_get_profile_stats(args: MirrorGetProfileStatsArgs) -> Dict[str, Any]:
    stats = cognitive_mirror.get_stats(dimension=args.dimension)
    return {
        "status": "success",
        "stats": stats,
    }


@registry.register(
    name="mirror_synthesize_text",
    tier=0,
    description="Synthesizes text matching the user's authentic personal style for commits, comments, emails, or notes (Read-Only)",
    args_schema=MirrorSynthesizeTextArgs,
    preview_fn=lambda a: (
        f"Synthesize {a.get('task') if isinstance(a, dict) else getattr(a, 'task', 'text')} "
        f"in user's authentic style (Read-Only)"
    ),
)
async def mirror_synthesize_text(args: MirrorSynthesizeTextArgs) -> Dict[str, Any]:
    res: MirrorSynthesisResult = cognitive_mirror.synthesize_text(
        task=args.task,
        context_prompt=args.context_prompt,
        metadata=args.metadata,
    )
    return {
        "status": "success",
        "task": res.task.value,
        "synthesized_text": res.synthesized_text,
        "applied_style_traits": res.applied_style_traits,
        "confidence": res.confidence,
        "duration_ms": res.duration_ms,
    }


# ==========================================
# Tier 1 Tools (Reversible Changes)
# ==========================================

@registry.register(
    name="mirror_learn_from_sources",
    tier=1,
    description="Learns personal coding and communication style traits from local git, obsidian, emails, or activity logs",
    args_schema=MirrorLearnFromSourcesArgs,
    preview_fn=lambda a: (
        f"Learn personal style from sources: "
        f"{', '.join(a.get('sources', [])) if isinstance(a, dict) else ', '.join(getattr(a, 'sources', []))} "
        f"(max {a.get('max_items', 100) if isinstance(a, dict) else getattr(a, 'max_items', 100)} items)"
    ),
)
async def mirror_learn_from_sources(args: MirrorLearnFromSourcesArgs) -> Dict[str, Any]:
    res = cognitive_mirror.learn_from_sources(
        sources=args.sources,
        repo_path=args.repo_path,
        vault_path=args.vault_path,
        max_items=args.max_items or 100,
    )
    return res


@registry.register(
    name="mirror_reset_profile",
    tier=1,
    description="Resets one or more cognitive mirror dimensions or clears all learned profiles",
    args_schema=MirrorResetProfileArgs,
    preview_fn=lambda a: (
        f"Reset cognitive mirror dimensions: "
        f"{[d.value if hasattr(d, 'value') else str(d) for d in a.get('dimensions', [])] if isinstance(a, dict) else (getattr(a, 'dimensions') or 'all')}"
    ),
)
async def mirror_reset_profile(args: MirrorResetProfileArgs) -> Dict[str, Any]:
    res = cognitive_mirror.reset_profile(dimensions=args.dimensions)
    return res
