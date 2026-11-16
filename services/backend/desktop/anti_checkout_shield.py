"""Anti-Checkout & Financial Protection Shield for Desktop Automation (Milestone 49 Phase 3, GUI-03).

Enforces Rule 8 (payments/checkout impossible by construction) and Rule 5 (finance informational only).
Scans window titles, URL bars, and UI element descriptors, aborting automation before clicking.
"""

from __future__ import annotations

import logging
import re
from typing import Any, Dict, List, Optional

from services.backend.schemas.semantic_focus import (
    UIAElementDescriptor,
    WindowContext,
)
from services.backend.memory.temporal_graph_engine import Rule8ViolationError
from services.backend.safety.guardian import guardian

logger = logging.getLogger("phenom.desktop.anti_checkout_shield")


class AntiCheckoutShield:
    """Blocks desktop automation from interacting with checkout, payment, or trading screens."""

    _CHECKOUT_KEYWORDS = [
        "checkout",
        "pay now",
        "payment",
        "order summary",
        "place order",
        "buy now",
        "complete purchase",
        "credit card",
        "debit card",
        "cvv",
        "billing address",
        "card number",
        "paypal checkout",
        "upi pay",
        "place trade",
        "buy order",
        "sell order",
    ]

    _REGEX_PATTERN = re.compile(
        r"(?i)\b(" + "|".join(re.escape(k) for k in _CHECKOUT_KEYWORDS) + r")\b"
    )

    def inspect_window_title(self, window_title: str) -> None:
        """Raises Rule8ViolationError if window title indicates a checkout or payment view."""
        if guardian.is_halted:
            raise PermissionError("Guardian kill switch is active. Anti-checkout inspection aborted.")

        match = self._REGEX_PATTERN.search(window_title)
        if match:
            trigger = match.group(0)
            raise Rule8ViolationError(
                f"Rule 8 Violation: Desktop automation blocked on payment/checkout screen (trigger: '{trigger}')."
            )

    def inspect_element(self, element: UIAElementDescriptor) -> None:
        """Inspects element text, name, and automation ID for financial or checkout triggers."""
        if guardian.is_halted:
            raise PermissionError("Guardian kill switch is active. Anti-checkout inspection aborted.")

        combined = f"{element.name} {element.automation_id} {element.control_type}"
        match = self._REGEX_PATTERN.search(combined)
        if match:
            trigger = match.group(0)
            raise Rule8ViolationError(
                f"Rule 8 Violation: Interaction blocked on financial or checkout element (trigger: '{trigger}')."
            )

    def is_safe_context(self, context: WindowContext) -> bool:
        """Returns True if window context is free of checkout and trading triggers."""
        try:
            self.inspect_window_title(context.title)
            if context.uia_root:
                self.inspect_element(context.uia_root)
            return True
        except Rule8ViolationError:
            return False
