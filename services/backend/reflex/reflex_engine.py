"""Reflex Reaction Engine for Real-Time Event Matching (Milestone 51 Phase 2).

Evaluates incoming ReflexEvent payloads in < 100ms, applies category-based cooldowns,
and pairs events with concise Jarvis voice commentary and suggested remediation actions.
"""

from __future__ import annotations

import collections
import time
import uuid
from typing import Any, Callable, Deque, Dict, List, Optional, Tuple
from pydantic import BaseModel, Field

from services.backend.schemas.reflex_events import (
    ReflexEvent,
    ReflexEventType,
    ReflexSeverity,
)
from services.backend.reflex.jarvis_commentator import JarvisCommentator


class SuggestedAction(BaseModel):
    """Proposed remediation tool call staged for operator authorization."""
    tool_name: str = Field(description="Safety-registered tool name")
    args: Dict[str, Any] = Field(default_factory=dict, description="Pre-computed arguments for tool")
    tier: int = Field(default=1, description="Safety tier classification (0 or 1)")
    description: str = Field(default="", description="Human-readable preview of suggested action")


class ReflexReaction(BaseModel):
    """Evaluated reflex response dispatched to CyberHUD and Voice synthesizers."""
    reaction_id: str = Field(default_factory=lambda: f"rx_{uuid.uuid4().hex[:8]}")
    event_id: str
    event_type: ReflexEventType
    severity: ReflexSeverity
    voice_commentary: str = Field(description="Spoken text constrained to <= 20 words")
    word_count: int = Field(description="Word count of voice commentary")
    suggested_action: Optional[SuggestedAction] = None
    priority: int = Field(default=50, ge=1, le=100)
    timestamp: float = Field(default_factory=time.time)
    is_suppressed: bool = False
    suppression_reason: Optional[str] = None
    evaluation_latency_ms: float = 0.0


class ReflexRule:
    """Declarative matching rule for reflex events."""

    def __init__(
        self,
        rule_id: str,
        name: str,
        event_type: Optional[ReflexEventType] = None,
        min_severity: ReflexSeverity = ReflexSeverity.INFO,
        cooldown_seconds: float = 10.0,
        priority: int = 50,
        predicate: Optional[Callable[[ReflexEvent], bool]] = None,
        action_generator: Optional[Callable[[ReflexEvent], Optional[SuggestedAction]]] = None,
    ) -> None:
        self.rule_id = rule_id
        self.name = name
        self.event_type = event_type
        self.min_severity = min_severity
        self.cooldown_seconds = cooldown_seconds
        self.priority = priority
        self.predicate = predicate
        self.action_generator = action_generator

    def matches(self, event: ReflexEvent) -> bool:
        """Evaluates whether this rule applies to the incoming event."""
        if self.event_type and event.event_type != self.event_type:
            return False

        # Severity comparison hierarchy
        sev_order = {
            ReflexSeverity.INFO: 1,
            ReflexSeverity.SUCCESS: 2,
            ReflexSeverity.WARNING: 3,
            ReflexSeverity.CRITICAL: 4,
        }
        if sev_order.get(event.severity, 1) < sev_order.get(self.min_severity, 1):
            return False

        if self.predicate and not self.predicate(event):
            return False

        return True


class ReflexEngine:
    """Sub-100ms in-memory reflex matching engine."""

    def __init__(self, commentator: Optional[JarvisCommentator] = None) -> None:
        self.commentator = commentator or JarvisCommentator()
        self.rules: List[ReflexRule] = []
        self._last_triggered: Dict[str, float] = {}
        self._recent_reactions: Deque[ReflexReaction] = collections.deque(maxlen=100)
        self._register_default_rules()

    def register_rule(self, rule: ReflexRule) -> None:
        """Registers a reflex matching rule and sorts by priority descending."""
        self.rules.append(rule)
        self.rules.sort(key=lambda r: r.priority, reverse=True)

    def set_rule_cooldown(self, rule_id: str, cooldown_seconds: float) -> bool:
        """Updates cooldown threshold for a specific rule."""
        for r in self.rules:
            if r.rule_id == rule_id:
                r.cooldown_seconds = max(0.0, cooldown_seconds)
                return True
        return False

    def evaluate_event(self, event: ReflexEvent) -> Tuple[Optional[ReflexReaction], float]:
        """Matches an incoming ReflexEvent against registered rules in < 100ms.
        
        Returns:
            Tuple of (Optional[ReflexReaction], evaluation_latency_ms).
        """
        t0 = time.perf_counter()
        now = time.time()

        matched_rule: Optional[ReflexRule] = None
        for rule in self.rules:
            if rule.matches(event):
                matched_rule = rule
                break

        if not matched_rule:
            elapsed_ms = (time.perf_counter() - t0) * 1000.0
            return None, elapsed_ms

        # Cooldown verification
        last_time = self._last_triggered.get(matched_rule.rule_id, 0.0)
        in_cooldown = (now - last_time) < matched_rule.cooldown_seconds

        # Generate Jarvis spoken commentary (<= 20 words)
        voice_text, word_count = self.commentator.format_commentary(event)

        # Generate suggested action if rule defines generator
        suggested_action: Optional[SuggestedAction] = None
        if matched_rule.action_generator:
            try:
                suggested_action = matched_rule.action_generator(event)
            except Exception:
                suggested_action = None

        elapsed_ms = (time.perf_counter() - t0) * 1000.0

        reaction = ReflexReaction(
            event_id=event.event_id,
            event_type=event.event_type,
            severity=event.severity,
            voice_commentary=voice_text,
            word_count=word_count,
            suggested_action=suggested_action,
            priority=matched_rule.priority,
            timestamp=now,
            is_suppressed=in_cooldown,
            suppression_reason=f"Rule '{matched_rule.rule_id}' in cooldown" if in_cooldown else None,
            evaluation_latency_ms=round(elapsed_ms, 3),
        )

        if not in_cooldown:
            self._last_triggered[matched_rule.rule_id] = now
            self._recent_reactions.append(reaction)

        return reaction, elapsed_ms

    def get_recent_reactions(self, limit: int = 10) -> List[ReflexReaction]:
        """Returns the most recent dispatched reactions."""
        return list(self._recent_reactions)[-limit:]

    def _register_default_rules(self) -> None:
        """Initializes default curated reflex rules."""
        # 1. Critical Build Failures
        self.register_rule(ReflexRule(
            rule_id="rule_build_failed",
            name="Build Failure Immediate Alert",
            event_type=ReflexEventType.BUILD_FAILED,
            min_severity=ReflexSeverity.CRITICAL,
            cooldown_seconds=5.0,
            priority=90,
            action_generator=lambda ev: SuggestedAction(
                tool_name="read_file",
                args={"path": "services/backend/main.py"},
                tier=0,
                description="Inspect file containing compilation errors",
            )
        ))

        # 2. Test Suite Failures
        self.register_rule(ReflexRule(
            rule_id="rule_tests_failed",
            name="Test Failure Alert",
            event_type=ReflexEventType.TESTS_FAILED,
            min_severity=ReflexSeverity.CRITICAL,
            cooldown_seconds=10.0,
            priority=85,
            action_generator=lambda ev: SuggestedAction(
                tool_name="simulate_reflex_event",
                args={"event_type": "TESTS_FAILED", "message": "Investigate regression"},
                tier=0,
                description="Isolate test failures",
            )
        ))

        # 3. Test Suite Success
        self.register_rule(ReflexRule(
            rule_id="rule_tests_passed",
            name="Test Success Debrief",
            event_type=ReflexEventType.TESTS_PASSED,
            min_severity=ReflexSeverity.SUCCESS,
            cooldown_seconds=15.0,
            priority=70,
        ))

        # 4. Terminal Clean Completion
        self.register_rule(ReflexRule(
            rule_id="rule_terminal_completed",
            name="Terminal Execution Completed",
            event_type=ReflexEventType.TERMINAL_COMPLETED,
            min_severity=ReflexSeverity.INFO,
            cooldown_seconds=5.0,
            priority=60,
        ))

        # 5. Error Dialog / System Exception
        self.register_rule(ReflexRule(
            rule_id="rule_error_dialog",
            name="System Error Dialog Detection",
            event_type=ReflexEventType.ERROR_DIALOG,
            min_severity=ReflexSeverity.CRITICAL,
            cooldown_seconds=8.0,
            priority=95,
        ))

        # 6. Toast Notifications
        self.register_rule(ReflexRule(
            rule_id="rule_toast_notification",
            name="Ambient Toast Alert",
            event_type=ReflexEventType.TOAST_NOTIFICATION,
            min_severity=ReflexSeverity.INFO,
            cooldown_seconds=10.0,
            priority=40,
        ))
