"""
Hybrid Model Mission Router with Automatic Privacy Defense (Phase 47-05, ROUTER-01, ROUTER-02).
Routes mission tasks between local Llama 3.1 8B (on RTX 3050 GPU) and cloud Nemotron/Groq.
Invariants:
1. Local-first priority: Simple tool calls, file edits, and DAG execution run locally (ROUTER-01).
2. Pre-flight privacy defense: Outbound cloud payloads pass through PrivacySanitizer (ROUTER-02).
3. Zero unredacted PII or credentials leave the local PC (Rule 4).
"""

from enum import Enum
from typing import Dict, Any, Optional, List
from pydantic import BaseModel, Field

from services.backend.router.privacy_sanitizer import privacy_sanitizer, SanitizationResult


class TargetModel(str, Enum):
    LOCAL_8B = "local_llama_3.1_8b"
    CLOUD_NEMOTRON = "cloud_nemotron"
    CLOUD_GROQ = "cloud_groq"


class RoutingDecision(BaseModel):
    """Routing choice and sanitized payload for a task step."""
    target_model: TargetModel = Field(..., description="Selected model engine")
    is_cloud: bool = Field(..., description="True if dispatched to an external cloud endpoint")
    reason: str = Field(..., description="Technical rationale for the routing decision")
    sanitized_prompt: str = Field(..., description="PII-scrubbed prompt safe for target model")
    redactions_count: int = Field(default=0, description="Count of sensitive items masked")
    redacted_types: List[str] = Field(default_factory=list, description="Categories of masked tokens")


class HybridMissionRouter:
    """Classifies task complexity and routes between sovereign local and cloud AI models."""

    DEEP_REASONING_KEYWORDS = [
        "deep architectural synthesis",
        "cross-module refactoring",
        "complex mathematical derivation",
        "synthesize multi-paper meta-analysis",
        "heavy reasoning",
        "meta-cognitive reflection",
        "novel algorithm design"
    ]

    LOCAL_MAX_CHAR_CAP = 8000  # Context boundary for local 8B

    def __init__(self):
        pass

    def evaluate_task(self, prompt: str, task_context: Optional[Dict[str, Any]] = None) -> RoutingDecision:
        """
        Determines the optimal model target for a given task prompt and ensures privacy scrubbing.
        """
        clean_prompt = prompt.strip()
        ctx = task_context or {}
        lower_prompt = clean_prompt.lower()

        # Check explicit cloud requirement
        is_deep_reasoning = any(kw in lower_prompt for kw in self.DEEP_REASONING_KEYWORDS)
        is_oversized_context = len(clean_prompt) > self.LOCAL_MAX_CHAR_CAP
        force_cloud = ctx.get("force_cloud", False)

        if is_deep_reasoning or is_oversized_context or force_cloud:
            target = TargetModel.CLOUD_NEMOTRON
            is_cloud = True
            if is_deep_reasoning:
                reason = "Task matches deep reasoning and complex architecture synthesis patterns"
            elif is_oversized_context:
                reason = f"Context size ({len(clean_prompt)} chars) exceeds local 8B optimal window"
            else:
                reason = "Cloud dispatch explicitly requested by context policy"
        else:
            target = TargetModel.LOCAL_8B
            is_cloud = False
            reason = "Task is suited for sovereign local 8B model (RTX 3050 GPU)"

        # Apply pre-flight privacy sanitization
        # Rule 4: If routing to cloud, ensure 100% redaction
        if is_cloud:
            sanitization: SanitizationResult = privacy_sanitizer.sanitize(clean_prompt)
            sanitized_text = sanitization.sanitized_text
            redactions_cnt = sanitization.redactions_count
            redacted_types = sanitization.redacted_types
        else:
            # Local model keeps unredacted text for sovereign execution
            sanitized_text = clean_prompt
            redactions_cnt = 0
            redacted_types = []

        return RoutingDecision(
            target_model=target,
            is_cloud=is_cloud,
            reason=reason,
            sanitized_prompt=sanitized_text,
            redactions_count=redactions_cnt,
            redacted_types=redacted_types
        )


# Global singleton instance
hybrid_mission_router = HybridMissionRouter()
