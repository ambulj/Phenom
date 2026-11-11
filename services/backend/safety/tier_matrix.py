"""Safety Tier Matrix Manager for Phenom (Milestone 29 Phase 2).

Manages pragmatic auto-execution policies, risk tier matrix evaluation, and
high-risk confirmation gates (TIER-01.1, TIER-01.2, AUTO-02.1).
"""

from __future__ import annotations

import logging
import re
import time
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field

from services.backend.safety.guardian import guardian
from services.backend.safety.registry import registry

logger = logging.getLogger("phenom.safety.tier_matrix")


class Rule8ViolationError(Exception):
    """Raised when policy evaluation or reclassification touches payment or checkout operations."""
    pass


class ToolPolicyDefinition(BaseModel):
    tool_name: str
    tier: int
    auto_executable: bool
    requires_confirmation: bool
    is_blocked: bool
    category: str
    description: str = ""


class TierReclassificationRecord(BaseModel):
    tool_name: str
    previous_tier: int
    new_tier: int
    reason: str
    timestamp: float = Field(default_factory=time.time)


class SafetyTierMatrixReport(BaseModel):
    total_tools: int
    tier_counts: Dict[int, int]
    auto_executable_count: int
    high_risk_confirmation_count: int
    blocked_count: int
    auto_execute_tier1_enabled: bool
    tools: List[ToolPolicyDefinition] = Field(default_factory=list)


class SafetyTierMatrixManager:
    """Evaluates and manages zero-friction auto-execution matrix for registered tools."""

    _RULE_8_PATTERN = re.compile(
        r"(?:\b|_)(checkout|pay|payment|purchase|buy|order|credit.?card|cvv|billing)(?:\b|_)",
        re.IGNORECASE,
    )

    # Known high-risk tools requiring explicit user confirmation (Tier 2)
    _HIGH_RISK_TOOLS = {
        "send_email",
        "send_email_draft",
        "telegram_broadcast",
        "telegram_send_remote",
        "export_credentials",
        "modify_registry_key",
        "set_system_password",
        "grant_admin_privileges",
        "wipe_memory_vault",
    }

    def __init__(self, auto_execute_tier1: bool = True) -> None:
        self.auto_execute_tier1 = auto_execute_tier1
        self._custom_reclassifications: Dict[str, int] = {}
        self._history: List[TierReclassificationRecord] = []

    def check_safety(self, text: str) -> None:
        """Enforces Guardian kill switch and Rule 8 payment defenses."""
        if guardian.is_halted:
            raise RuntimeError("Execution halted by Guardian kill switch (SAFETY_MATRIX_HALTED)")

        if self._RULE_8_PATTERN.search(text):
            raise Rule8ViolationError(
                "Rule 8 Violation: Payment, checkout, or billing directives detected in safety matrix"
            )

    def classify_tool_category(self, tool_name: str) -> str:
        """Heuristically categorizes tools for UI and policy analysis."""
        name_lower = tool_name.lower()
        if any(w in name_lower for w in ["email", "telegram", "broadcast", "notify"]):
            return "COMMUNICATION"
        if any(w in name_lower for w in ["credential", "password", "token", "auth", "secret", "registry"]):
            return "SECURITY"
        if any(w in name_lower for w in ["file", "folder", "directory", "pdf", "recycle", "path"]):
            return "FILESYSTEM"
        if any(w in name_lower for w in ["app", "window", "volume", "audio", "macro", "screen"]):
            return "DESKTOP"
        if any(w in name_lower for w in ["plan", "tree", "branch", "heal", "meta"]):
            return "PLANNING"
        return "GENERAL"

    def evaluate_tool_policy(self, tool_name: str, args: Optional[Dict[str, Any]] = None) -> ToolPolicyDefinition:
        """Evaluates active auto-execution policy for a given tool."""
        self.check_safety(f"{tool_name} {args or ''}")

        tool_def = registry.get(tool_name)
        if tool_def is None:
            return ToolPolicyDefinition(
                tool_name=tool_name,
                tier=3,
                auto_executable=False,
                requires_confirmation=False,
                is_blocked=True,
                category="UNKNOWN",
                description="Unregistered tool (Default Blocked)",
            )

        # Check if there is an active custom reclassification
        if tool_name in self._custom_reclassifications:
            effective_tier = self._custom_reclassifications[tool_name]
        else:
            effective_tier = tool_def.get_tier(args or {})

        category = self.classify_tool_category(tool_name)

        # Force Tier 2 confirmation for known high-risk tools unless explicitly overridden
        if tool_name in self._HIGH_RISK_TOOLS and effective_tier < 2:
            effective_tier = 2

        auto_executable = (effective_tier == 0) or (effective_tier == 1 and self.auto_execute_tier1)
        requires_confirmation = (effective_tier == 2)
        is_blocked = (effective_tier == 3)

        return ToolPolicyDefinition(
            tool_name=tool_name,
            tier=effective_tier,
            auto_executable=auto_executable,
            requires_confirmation=requires_confirmation,
            is_blocked=is_blocked,
            category=category,
            description=tool_def.description or "",
        )

    def reclassify_tool(self, tool_name: str, new_tier: int, reason: str = "") -> TierReclassificationRecord:
        """Reclassifies a tool's safety tier dynamically with record keeping."""
        self.check_safety(f"{tool_name} {reason}")

        if new_tier not in (0, 1, 2, 3):
            raise ValueError(f"Invalid tier {new_tier}. Must be 0, 1, 2, or 3.")

        tool_def = registry.get(tool_name)
        if tool_def is None:
            raise ValueError(f"Cannot reclassify unregistered tool '{tool_name}'.")

        previous_tier = self._custom_reclassifications.get(tool_name, tool_def.tier)
        self._custom_reclassifications[tool_name] = new_tier

        # Also update underlying ToolDefinition tier if applicable
        tool_def.tier = new_tier

        record = TierReclassificationRecord(
            tool_name=tool_name,
            previous_tier=previous_tier,
            new_tier=new_tier,
            reason=reason or f"Dynamic reclassification to Tier {new_tier}",
        )
        self._history.append(record)
        logger.info(
            "Reclassified tool %s from Tier %d to Tier %d (Reason: %s)",
            tool_name,
            previous_tier,
            new_tier,
            record.reason,
        )
        return record

    def get_matrix_report(self) -> SafetyTierMatrixReport:
        """Generates comprehensive safety tier matrix report across all registered tools."""
        self.check_safety("matrix_report")

        tier_counts = {0: 0, 1: 0, 2: 0, 3: 0}
        tool_policies: List[ToolPolicyDefinition] = []
        auto_count = 0
        confirm_count = 0
        blocked_count = 0

        for name in sorted(registry._tools.keys()):
            policy = self.evaluate_tool_policy(name)
            tool_policies.append(policy)
            tier_counts[policy.tier] = tier_counts.get(policy.tier, 0) + 1
            if policy.auto_executable:
                auto_count += 1
            if policy.requires_confirmation:
                confirm_count += 1
            if policy.is_blocked:
                blocked_count += 1

        return SafetyTierMatrixReport(
            total_tools=len(tool_policies),
            tier_counts=tier_counts,
            auto_executable_count=auto_count,
            high_risk_confirmation_count=confirm_count,
            blocked_count=blocked_count,
            auto_execute_tier1_enabled=self.auto_execute_tier1,
            tools=tool_policies,
        )


# Global singleton instance
safety_tier_matrix_manager = SafetyTierMatrixManager()
