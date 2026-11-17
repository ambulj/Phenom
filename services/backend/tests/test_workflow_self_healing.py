"""
Unit tests for Self-Healing UI Resilience & Hybrid Grounding Engine (Phase 50-02)
Tests:
1. Dialog classification (cookies, tips, updates vs. destructive confirmation)
2. Safe non-destructive dismissal (< 500ms SLA)
3. Destructive dialog pause and operator escalation
4. High-speed UIA element grounding (< 15ms SLA)
5. Visual OCR fallback for canvas and custom Electron components
6. Tool registry verification (Tier 1 for dismissal, Tier 0 for grounding)
"""

import pytest
import asyncio
import time
from services.backend.automation.self_healing_resolver import (
    SelfHealingObstacleResolver,
    DialogCategory,
    ObstacleDetection,
    ResolutionResult,
)
from services.backend.automation.hybrid_grounding import (
    HybridElementGrounder,
    GroundingStrategy,
    GroundedElement,
)
from services.backend.tools.self_healing_tools import (
    detect_and_resolve_obstacles,
    ground_element_hybrid,
)
from services.backend.safety.registry import registry


def test_dialog_classification():
    """Verify on-screen modals are accurately classified and safety gates applied."""
    resolver = SelfHealingObstacleResolver()

    # 1. Cookie Banner
    d_cookie = resolver.classify_dialog(
        title="Privacy Preferences",
        text_content="We use cookies to improve your browsing experience. Accept all cookies to continue.",
        buttons=["Accept All", "Customize Settings"]
    )
    assert d_cookie.detected is True
    assert d_cookie.dialog_type == DialogCategory.COOKIE_BANNER
    assert d_cookie.is_safe_to_dismiss is True
    assert d_cookie.dismiss_action_label == "Accept All"

    # 2. Promotional Tip
    d_tip = resolver.classify_dialog(
        title="Welcome Tour",
        text_content="Did you know? You can now use shortcuts to execute faster macros.",
        buttons=["Got it", "Skip Tour"]
    )
    assert d_tip.detected is True
    assert d_tip.dialog_type == DialogCategory.PROMOTIONAL_TIP
    assert d_tip.is_safe_to_dismiss is True
    assert d_tip.dismiss_action_label in ["Got it", "Skip Tour"]

    # 3. Update Notice
    d_update = resolver.classify_dialog(
        title="Software Update",
        text_content="A new version 2.4 is ready to install.",
        buttons=["Restart Now", "Remind Me Later"]
    )
    assert d_update.detected is True
    assert d_update.dialog_type == DialogCategory.UPDATE_NOTICE
    assert d_update.is_safe_to_dismiss is True
    assert "Later" in (d_update.dismiss_action_label or "")

    # 4. Destructive Confirmation (MUST NEVER BE AUTO-DISMISSED)
    d_destruct = resolver.classify_dialog(
        title="Confirm Permanent Deletion",
        text_content="Are you sure you want to permanently delete 45 items from this repository?",
        buttons=["Delete", "Cancel"]
    )
    assert d_destruct.detected is True
    assert d_destruct.dialog_type == DialogCategory.DESTRUCTIVE_CONFIRMATION
    assert d_destruct.is_safe_to_dismiss is False


@pytest.mark.asyncio
async def test_non_destructive_auto_dismissal_sla():
    """Verify non-destructive interstitial is auto-dismissed within < 500ms SLA."""
    cookie_state = {
        "title": "Cookie Consent",
        "text": "Please accept our cookie policy to continue.",
        "buttons": ["Accept Cookies", "Decline"],
        "button_coords": {"Accept Cookies": (400, 500)}
    }
    resolver = SelfHealingObstacleResolver()

    start = time.perf_counter()
    result = await resolver.inspect_and_resolve(context_override=cookie_state)
    elapsed_ms = (time.perf_counter() - start) * 1000

    assert result.resolved is True
    assert result.operator_escalation_required is False
    assert "Accept Cookies" in result.action_taken
    assert result.latency_ms < 500.0
    assert elapsed_ms < 500.0


@pytest.mark.asyncio
async def test_destructive_dialog_pause_and_escalation():
    """Verify destructive modal halts macro and requires operator confirmation."""
    destructive_state = {
        "title": "Discard Changes",
        "text": "Are you sure you want to discard all unsaved work?",
        "buttons": ["Discard", "Keep Editing"],
        "button_coords": {"Discard": (300, 400)}
    }
    resolver = SelfHealingObstacleResolver()

    result = await resolver.inspect_and_resolve(context_override=destructive_state)
    assert result.resolved is False
    assert result.operator_escalation_required is True
    assert result.action_taken == "paused_for_operator"
    assert "Destructive or critical prompt detected" in result.message


def test_hybrid_grounding_uia_fast_path():
    """Verify primary UIA element resolution achieves < 15ms SLA."""
    mock_uia = lambda label, win: {
        "bounding_box": (100, 200, 80, 30),
        "confidence": 0.99
    }
    grounder = HybridElementGrounder(uia_provider=mock_uia)

    start = time.perf_counter()
    elem = grounder.ground("Save Button", window_title="VS Code")
    elapsed_ms = (time.perf_counter() - start) * 1000

    assert elem.strategy_used == GroundingStrategy.UIA_ACCESSIBILITY
    assert elem.is_fallback is False
    assert elem.center_x == 140
    assert elem.center_y == 215
    assert elem.resolution_latency_ms < 15.0
    assert elapsed_ms < 15.0


def test_hybrid_grounding_visual_fallback():
    """Verify visual OCR fallback engages when UIA accessibility is detached/canvas."""
    mock_vision = lambda label, win: {
        "bounding_box": (500, 600, 150, 40),
        "confidence": 0.89
    }
    # UIA provider returns None (Canvas app)
    grounder = HybridElementGrounder(uia_provider=lambda l, w: None, vision_provider=mock_vision)

    elem = grounder.ground("Submit Order", window_title="Figma Canvas")

    assert elem.strategy_used == GroundingStrategy.VISUAL_OCR
    assert elem.is_fallback is True
    assert elem.center_x == 575
    assert elem.center_y == 620
    assert elem.confidence == 0.89


def test_self_healing_tool_registrations():
    """Verify tool safety tiers, argument schemas, and preview generators."""
    t_resolve = registry.get("detect_and_resolve_obstacles")
    assert t_resolve is not None
    assert t_resolve.tier == 1
    assert callable(t_resolve.preview_fn)
    preview = t_resolve.preview_fn({"window_title": "Browser"})
    assert "Browser" in preview

    t_ground = registry.get("ground_element_hybrid")
    assert t_ground is not None
    assert t_ground.tier == 0
    assert callable(t_ground.preview_fn)
    preview = t_ground.preview_fn({"target_label": "Search Box"})
    assert "Search Box" in preview
