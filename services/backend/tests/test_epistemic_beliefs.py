"""Unit & Safety Tests for Epistemic Belief Network & Contradiction Resolver (Milestone 26 Phase 2)."""

import pytest
import time
from services.backend.epistemic.belief_network import (
    EpistemicBeliefNetwork,
    EpistemicBelief,
    Rule8ViolationError,
)
from services.backend.epistemic.contradiction_resolver import ContradictionResolver
from services.backend.safety.guardian import guardian
from services.backend.safety.registry import registry
import services.backend.tools.epistemic_belief_tools  # Ensure registered


@pytest.fixture(autouse=True)
def reset_guardian():
    guardian.resume()
    yield
    guardian.resume()


def test_belief_network_initial_presets():
    net = EpistemicBeliefNetwork()
    beliefs = net.get_beliefs()
    assert len(beliefs) >= 3
    theme_belief = next(b for b in beliefs if b.predicate == "prefers_theme")
    assert theme_belief.subject == "User"
    assert theme_belief.object_value == "Dark Cyberpunk Glow"
    assert theme_belief.confidence >= 0.90


def test_update_belief_new_and_reinforce():
    net = EpistemicBeliefNetwork()
    # Add new belief
    b1 = net.update_belief("User", "favorite_language", "Python", confidence_boost=0.85)
    assert b1.object_value == "Python"
    assert b1.confidence == 0.85
    assert b1.evidence_count == 1

    # Reinforce existing belief
    b2 = net.update_belief("User", "favorite_language", "Python", confidence_boost=0.10)
    assert b2.object_value == "Python"
    assert b2.confidence > 0.85
    assert b2.evidence_count == 2


def test_update_belief_revision_log():
    net = EpistemicBeliefNetwork()
    net.update_belief("User", "ide_choice", "VSCode")
    # Change belief
    b_updated = net.update_belief("User", "ide_choice", "Antigravity IDE", confidence_boost=0.95)
    assert b_updated.object_value == "Antigravity IDE"

    revs = net.get_revisions()
    assert len(revs) == 1
    assert revs[0].old_value == "VSCode"
    assert revs[0].new_value == "Antigravity IDE"
    assert revs[0].confidence_delta != 0.0


def test_contradiction_detection():
    net = EpistemicBeliefNetwork()
    net.update_belief("User", "work_mode", "Deep Focus")
    resolver = ContradictionResolver(network=net)

    # User authoritative contradiction
    res_direct = resolver.analyze_claim("User", "work_mode", "Pair Programming", is_user_direct=True)
    assert res_direct.conflict_detected is True
    assert res_direct.resolution_strategy == "OVERWRITE_WITH_USER_CORRECTION"
    assert "User authority supersedes" in res_direct.explanation

    # Indirect contradiction
    res_indirect = resolver.analyze_claim("User", "work_mode", "Pair Programming", is_user_direct=False)
    assert res_indirect.conflict_detected is True
    assert res_indirect.resolution_strategy == "CONFIDENCE_DEGRADATION"
    assert res_indirect.confidence_shift == -0.25


def test_resolve_and_apply():
    net = EpistemicBeliefNetwork()
    net.update_belief("System", "log_level", "DEBUG")
    resolver = ContradictionResolver(network=net)

    applied = resolver.resolve_and_apply("System", "log_level", "INFO", is_user_direct=True)
    assert applied.object_value == "INFO"
    assert applied.confidence >= 0.95


def test_rule_8_enforcement_epistemic():
    net = EpistemicBeliefNetwork()
    resolver = ContradictionResolver(network=net)

    with pytest.raises(Rule8ViolationError, match="Rule 8 violation"):
        net.update_belief("User", "payment_method", "credit_card")

    with pytest.raises(Rule8ViolationError, match="Rule 8 violation"):
        net.update_belief("User", "checkout_policy", "auto_buy")

    with pytest.raises(Rule8ViolationError, match="Rule 8 violation"):
        resolver.analyze_claim("User", "pay", "order_checkout")


def test_guardian_kill_switch_sla():
    net = EpistemicBeliefNetwork()
    guardian.trigger(reason="Emergency stop")

    t0 = time.perf_counter()
    with pytest.raises(PermissionError, match="Guardian kill switch is TRIPPED"):
        net.update_belief("User", "test_subj", "test_val")
    elapsed_ms = (time.perf_counter() - t0) * 1000.0

    assert elapsed_ms < 25.0, f"Guardian SLA exceeded: {elapsed_ms:.4f}ms"


def test_tool_registry_epistemic_beliefs():
    # 1. Update Epistemic Belief (Tier 1)
    tool_update = registry.get("update_epistemic_belief")
    assert tool_update is not None
    assert tool_update.tier == 1
    prev_update = tool_update.preview_fn({
        "subject": "User",
        "predicate": "prefers_editor",
        "object_value": "Vim",
        "source": "USER_STATEMENT",
    })
    assert "[User] prefers_editor -> 'Vim'" in prev_update

    res_update = tool_update.handler_fn(
        subject="User",
        predicate="prefers_editor",
        object_value="Vim",
        confidence_boost=0.88,
        source="USER_STATEMENT",
    )
    assert res_update["status"] == "UPDATED"
    assert res_update["belief"]["object_value"] == "Vim"

    # 2. Resolve Belief Contradiction (Tier 0)
    tool_resolve = registry.get("resolve_belief_contradiction")
    assert tool_resolve is not None
    assert tool_resolve.tier == 0
    res_resolve = tool_resolve.handler_fn(
        subject="User",
        predicate="prefers_editor",
        claimed_value="Emacs",
        is_user_direct=True,
    )
    assert res_resolve["conflict_detected"] is True
    assert res_resolve["resolution_strategy"] == "OVERWRITE_WITH_USER_CORRECTION"

    # 3. Get Active Belief Network (Tier 0)
    tool_get = registry.get("get_active_belief_network")
    assert tool_get is not None
    assert tool_get.tier == 0
    res_get = tool_get.handler_fn(active_only=True)
    assert res_get["belief_count"] > 0
