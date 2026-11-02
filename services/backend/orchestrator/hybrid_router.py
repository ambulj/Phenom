"""
Phenom Hybrid Query Intent Router
Coordinates intelligent routing between:
1. ACTION_LOCAL: Fast system actions, media controls, volume, app launch (< 200ms via local 8B).
2. VISION_LOCAL: Quick on-screen element coordinate localization and basic OCR via local engines.
3. VISION_CLOUD: High-precision visual reasoning over screen frames via NVIDIA Nemotron Vision.

Strictly enforces Rule 4: Inputs or contexts containing sensitive/private indicators are
prohibited from cloud escalation and are retained locally.
"""

import time
import re
from enum import Enum
from typing import Optional, Dict, Any, List
from pydantic import BaseModel, Field

from services.backend.router.privacy import privacy_classifier
from services.backend.safety.action_log import action_log


class IntentCategory(str, Enum):
    ACTION_LOCAL = "action_local"
    VISION_LOCAL = "vision_local"
    VISION_CLOUD = "vision_cloud"


class IntentResult(BaseModel):
    category: IntentCategory = Field(..., description="Target routing category")
    confidence: float = Field(default=1.0, description="Confidence score between 0.0 and 1.0")
    target_model: str = Field(..., description="Target model or execution engine identifier")
    reason: str = Field(..., description="Detailed explanation of the routing decision")
    latency_ms: float = Field(..., description="Classification latency in milliseconds")
    requires_preview: bool = Field(default=False, description="Whether execution requires preview confirmation")
    privacy_status: str = Field(default="shareable", description="Privacy label of the query ('private' or 'shareable')")


# Heuristic patterns for intent classification
_ACTION_PATTERNS = [
    re.compile(r"\b(open|launch|start|run|close|kill|quit|terminate)\b\s+([a-zA-Z0-9_\-\s]+)", re.IGNORECASE),
    re.compile(r"\b(volume|mute|unmute|louder|quieter|brightness)\b", re.IGNORECASE),
    re.compile(r"\b(play|pause|stop|resume|next|previous|skip)\b(\s+song|\s+music|\s+track|\s+video|\s+spotify)?", re.IGNORECASE),
    re.compile(r"\b(schedule|remind|reminder|timer|alarm|calendar|event)\b", re.IGNORECASE),
    re.compile(r"\b(calculate|what is \d+|solve|\d+\s*[\+\-\*\/]\s*\d+)\b", re.IGNORECASE),
    re.compile(r"\b(battery|cpu|ram|memory|disk|specs|system info|uptime)\b", re.IGNORECASE),
    re.compile(r"\b(create file|write file|delete file|read file|list files|search file)\b", re.IGNORECASE),
    re.compile(r"\b(weather|temperature|forecast|news|headline)\b", re.IGNORECASE),
]

_VISION_LOCAL_PATTERNS = [
    re.compile(r"\b(where is|locate|find)\b(\s+the)?\s+(button|input|icon|tab|checkbox|field|dropdown|menu|link|submit|cancel|close|search)\b", re.IGNORECASE),
    re.compile(r"\b(coordinates of|x\s*,\s*y of)\b", re.IGNORECASE),
    re.compile(r"\b(find on screen|click on)\s+[\"']?([a-zA-Z0-9_\-\s]+)[\"']?", re.IGNORECASE),
    re.compile(r"\b(ocr|read text at|extract text)\b", re.IGNORECASE),
]

_VISION_CLOUD_PATTERNS = [
    re.compile(r"\b(explain|understand|interpret)\b(\s+this|\s+the)?\s+(diagram|chart|graph|architecture|flowchart|wireframe|layout|schema|figure)\b", re.IGNORECASE),
    re.compile(r"\b(what does|what is)\b(\s+this|\s+the)?\s+(diagram|chart|graph|architecture|flowchart|plot)\s+(show|mean|represent|indicate)\b", re.IGNORECASE),
    re.compile(r"\b(find|diagnose|spot)\b(\s+the)?\s+(bug|error|issue|stack trace|exception)\s+(in|on|from)\s+(this|my|the)?\s*(screen|code|ide|terminal)\b", re.IGNORECASE),
    re.compile(r"\b(analyze|evaluate|audit|inspect)\b(\s+my|\s+this|\s+the)?\s+(screen|diagram|ui design|mockup|code on screen|visual)\b", re.IGNORECASE),
    re.compile(r"\b(summarize|describe)\b(\s+this|\s+the)?\s+(slide|dashboard|presentation|visual|complex screen|ui)\b", re.IGNORECASE),
    re.compile(r"\b(what('s| is) wrong with)\s+(this|my)?\s*(screen|code|layout|ui)\b", re.IGNORECASE),
]


class HybridRouter:
    """
    High-speed deterministic query intent classifier.
    Directs queries across local fast-path actions, on-device UI locators, and cloud vision.
    """

    def __init__(
        self,
        local_model_name: str = "phenom-jarvis:latest",
        cloud_vision_model: str = "nvidia/neva-22b"
    ):
        self.local_model_name = local_model_name
        self.cloud_vision_model = cloud_vision_model

    def classify_intent(
        self,
        query: str,
        context_files: Optional[List[str]] = None,
        context: Optional[Dict[str, Any]] = None
    ) -> IntentResult:
        """
        Classifies incoming query intent in < 5ms.
        Enforces privacy boundaries and returns structured IntentResult.
        """
        t0 = time.perf_counter()
        query_clean = query.strip()
        context_files = context_files or []
        context = context or {}

        # 1. Privacy Safety Verification (Rule 4)
        # Check if query contains hard PII, credentials, or private paths that can NEVER leave the machine
        privacy_label, privacy_reason = privacy_classifier.classify(
            query_clean, file_paths=context_files, manual_override="shareable"
        )
        has_pii_or_secrets = (privacy_label == "private")

        # 2. Check for Deep Cloud Vision Patterns
        matched_cloud_pattern = any(p.search(query_clean) for p in _VISION_CLOUD_PATTERNS)
        if matched_cloud_pattern:
            if has_pii_or_secrets:
                # Privacy constraint: Force local
                elapsed_ms = (time.perf_counter() - t0) * 1000.0
                reason = f"Visual reasoning query contains sensitive/private data ({privacy_reason}). Cloud escalation prohibited; retained local."
                result = IntentResult(
                    category=IntentCategory.VISION_LOCAL,
                    confidence=0.95,
                    target_model="local_vlm_moondream",
                    reason=reason,
                    latency_ms=round(elapsed_ms, 3),
                    requires_preview=False,
                    privacy_status="private"
                )
                self._log_routing(query_clean, result)
                return result
            else:
                elapsed_ms = (time.perf_counter() - t0) * 1000.0
                reason = "Complex visual reasoning query matched. Routed to NVIDIA Nemotron Vision API."
                result = IntentResult(
                    category=IntentCategory.VISION_CLOUD,
                    confidence=0.98,
                    target_model=self.cloud_vision_model,
                    reason=reason,
                    latency_ms=round(elapsed_ms, 3),
                    requires_preview=True,  # Tier 2 approval required for cloud vision
                    privacy_status="shareable"
                )
                self._log_routing(query_clean, result)
                return result

        # 3. Check for Local Vision / Coordinate Locator Patterns
        matched_local_vision = any(p.search(query_clean) for p in _VISION_LOCAL_PATTERNS)
        if matched_local_vision:
            elapsed_ms = (time.perf_counter() - t0) * 1000.0
            reason = "UI element localization / OCR request. Routed to local ScreenOCREngine & UI Automation."
            result = IntentResult(
                category=IntentCategory.VISION_LOCAL,
                confidence=0.95,
                target_model="local_ocr_uia",
                reason=reason,
                latency_ms=round(elapsed_ms, 3),
                requires_preview=False,
                privacy_status="private" if has_pii_or_secrets else "shareable"
            )
            self._log_routing(query_clean, result)
            return result

        # 4. Check for Fast OS Action Patterns
        matched_action = any(p.search(query_clean) for p in _ACTION_PATTERNS)
        elapsed_ms = (time.perf_counter() - t0) * 1000.0

        if matched_action:
            reason = "Fast OS system / automation command. Routed to local 8B model for sub-200ms execution."
        else:
            reason = "General conversational or factual query. Handled by local 8B model."

        result = IntentResult(
            category=IntentCategory.ACTION_LOCAL,
            confidence=0.92 if matched_action else 0.85,
            target_model=self.local_model_name,
            reason=reason,
            latency_ms=round(elapsed_ms, 3),
            requires_preview=False,
            privacy_status="private" if has_pii_or_secrets else "shareable"
        )
        self._log_routing(query_clean, result)
        return result

    def _log_routing(self, query: str, result: IntentResult) -> None:
        """Records routing metadata to the persistent action log."""
        try:
            action_log.log_action(
                tool_name="hybrid_intent_router",
                args={
                    "query_preview": query[:80] + ("..." if len(query) > 80 else ""),
                    "category": result.category.value,
                    "target_model": result.target_model,
                    "latency_ms": result.latency_ms,
                    "requires_preview": result.requires_preview,
                    "privacy_status": result.privacy_status
                },
                tier=2 if result.category == IntentCategory.VISION_CLOUD else 0,
                result={"reason": result.reason}
            )
        except Exception:
            pass


hybrid_router = HybridRouter()
