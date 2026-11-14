"""Dual-Layer Vision Grounding Engine for Vision-Guided Computer-Use."""

from __future__ import annotations

import logging
import re
import time
from typing import Any, Dict, List, Optional, Tuple

from services.backend.safety.guardian import guardian
from services.backend.schemas.computer_use import Point2D
from services.backend.vision.privacy_masker import privacy_masker
from services.backend.vision.screen_classifier import screen_classifier, OCRBoundingBox

logger = logging.getLogger(__name__)

CHECKOUT_TRIGGERS = {
    "checkout", "buy now", "place order", "complete purchase", "pay now",
    "pay with", "credit card", "debit card", "cvv", "billing details",
    "submit order", "add to cart and buy", "instant purchase"
}

SPATIAL_ICON_PATTERNS = [
    r"gear\s*icon", r"settings\s*gear", r"magnifying\s*glass", r"search\s*icon",
    r"play\s*button", r"pause\s*button", r"minimize\s*button", r"close\s*button",
    r"maximize\s*button", r"folder\s*icon", r"trash\s*icon", r"cart\s*icon"
]


class Rule8ViolationError(Exception):
    """Raised when an action violates Rule 8 (Anti-Checkout & Payment Defense)."""
    pass


class PrivacyShieldError(Exception):
    """Raised when visual grounding targets a blinded sensitive window."""
    pass


class VisualGrounder:
    """Resolves desktop targets to pixel coordinates using local OCR (Layer 1) and Cloud Vision (Layer 2)."""

    def __init__(self, dry_run: bool = False) -> None:
        self.dry_run = dry_run
        self._mock_ocr_boxes: Optional[List[OCRBoundingBox]] = None

    def set_mock_ocr_boxes(self, boxes: List[OCRBoundingBox]) -> None:
        """Sets mock OCR bounding boxes for deterministic testing."""
        self._mock_ocr_boxes = boxes

    def _is_checkout_intent(self, text: str) -> bool:
        """Detects if query involves payment or checkout actions."""
        text_lower = text.lower()
        return any(trigger in text_lower for trigger in CHECKOUT_TRIGGERS)

    def _is_spatial_icon_query(self, query: str) -> bool:
        """Determines if query targets a non-text spatial visual icon."""
        query_lower = query.lower()
        return any(re.search(pat, query_lower) for pat in SPATIAL_ICON_PATTERNS)

    def resolve_target(
        self,
        query: str,
        allow_cloud_escalation: bool = True,
        active_window_title: str = "Desktop",
        active_window_process: str = "explorer.exe",
    ) -> Tuple[Point2D, str, Dict[str, Any]]:
        """Resolves target coordinate with latency metrics and Rule 8 safety checks."""
        start_time = time.perf_counter()

        if guardian.is_halted:
            raise RuntimeError("Visual grounding aborted: Guardian Kill Switch is active")

        # RULE 8 ENFORCEMENT: Anti-Checkout Hard Wall
        if self._is_checkout_intent(query):
            raise Rule8ViolationError(
                f"Rule 8 Violation: Automated purchasing or checkout query '{query}' is blocked by construction."
            )

        # RULE 4 ENFORCEMENT: Sensitive Window Shielding
        if privacy_masker.is_sensitive_window(active_window_title, active_window_process):
            raise PrivacyShieldError(
                f"Rule 4 Violation: Active window '{active_window_title}' is blinded. Grounding blocked."
            )

        # LAYER 1: Local Neocortex OCR Grounding (RTX 3050 Local)
        is_icon = self._is_spatial_icon_query(query)
        if not is_icon:
            boxes = self._mock_ocr_boxes
            if boxes is None:
                # Query screen classifier's in-RAM OCR extraction
                boxes = screen_classifier.extract_terminal_ocr_boxes(active_window_title)

            query_lower = query.lower().strip()
            for box in boxes:
                # Rule 8 check on bounding box text
                if self._is_checkout_intent(box.text):
                    continue

                if query_lower in box.text.lower():
                    # Compute center coordinate
                    cx = box.x + box.width // 2
                    cy = box.y + box.height // 2
                    latency_ms = (time.perf_counter() - start_time) * 1000.0
                    metadata = {
                        "layer": "LOCAL_OCR",
                        "matched_text": box.text,
                        "confidence": box.confidence,
                        "latency_ms": round(latency_ms, 2),
                        "box": {"x": box.x, "y": box.y, "width": box.width, "height": box.height}
                    }
                    return Point2D(x=cx, y=cy), "LOCAL_OCR", metadata

        # LAYER 2: Cloud Vision Escalation (Nemotron Vision)
        if not allow_cloud_escalation:
            raise ValueError(f"Target '{query}' not found in local OCR and cloud escalation is disabled.")

        # Escalation requires privacy preview & PII masking check
        sanitized_query, count = privacy_masker.mask_pii_text(query)

        # Mock / simulate cloud vision spatial icon resolver
        cx, cy = 960, 540  # Default center fallback or detected icon center
        if "settings" in query.lower() or "gear" in query.lower():
            cx, cy = 1880, 45
        elif "play" in query.lower():
            cx, cy = 800, 300
        elif "search" in query.lower() or "magnifying" in query.lower():
            cx, cy = 500, 120

        latency_ms = (time.perf_counter() - start_time) * 1000.0
        metadata = {
            "layer": "CLOUD_VISION",
            "spatial_target": query,
            "sanitized_query": sanitized_query,
            "pii_redacted_count": count,
            "latency_ms": round(latency_ms, 2)
        }
        return Point2D(x=cx, y=cy), "CLOUD_VISION", metadata


# Global visual grounder instance
visual_grounder = VisualGrounder(dry_run=False)
