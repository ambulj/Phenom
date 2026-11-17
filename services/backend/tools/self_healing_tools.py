"""
Phenom Self-Healing & Hybrid Grounding Tool Registrations (WKF-02)
Registers:
- detect_and_resolve_obstacles (Tier 1)
- ground_element_hybrid (Tier 0)
"""

from typing import Dict, Any, Optional
from pydantic import BaseModel, Field

from services.backend.safety.registry import registry
from services.backend.automation.self_healing_resolver import self_healing_resolver
from services.backend.automation.hybrid_grounding import hybrid_grounder, GroundingStrategy


class DetectAndResolveObstaclesArgs(BaseModel):
    window_title: Optional[str] = Field(default=None, description="Target window title to inspect for obstacles")


class GroundElementHybridArgs(BaseModel):
    target_label: str = Field(description="Name, label, or text of the target element to ground")
    window_title: Optional[str] = Field(default=None, description="Optional target window title")
    preferred_strategy: Optional[str] = Field(
        default=None,
        description="Preferred strategy: 'UIA_ACCESSIBILITY' or 'VISUAL_OCR'"
    )


@registry.register(
    name="detect_and_resolve_obstacles",
    tier=1,
    description="Detects unexpected on-screen dialogs (cookies, tips, notices) and auto-dismisses safe barriers within < 500ms.",
    args_schema=DetectAndResolveObstaclesArgs,
    preview_fn=lambda a: f"Detect and auto-resolve interstitial obstacles in window '{a.get('window_title') or 'active'}'"
)
async def detect_and_resolve_obstacles(window_title: Optional[str] = None) -> Dict[str, Any]:
    res = await self_healing_resolver.inspect_and_resolve(window_title=window_title)
    return res.model_dump()


@registry.register(
    name="ground_element_hybrid",
    tier=0,
    description="Resolves element coordinates using high-speed native UIA (<15ms) with visual OCR fallback.",
    args_schema=GroundElementHybridArgs,
    preview_fn=lambda a: f"Ground element coordinates for '{a.get('target_label')}' via hybrid UIA/vision"
)
def ground_element_hybrid(
    target_label: str,
    window_title: Optional[str] = None,
    preferred_strategy: Optional[str] = None
) -> Dict[str, Any]:
    strategy = None
    if preferred_strategy:
        try:
            strategy = GroundingStrategy(preferred_strategy)
        except ValueError:
            pass

    grounded = hybrid_grounder.ground(
        target_label=target_label,
        window_title=window_title,
        preferred_strategy=strategy
    )
    return grounded.model_dump()
