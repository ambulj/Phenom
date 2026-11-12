"""Unit and Safety Integration Tests for Semantic Grounding & Visual Element Segmenter.

Validates multi-modal visual segmentation, natural language semantic grounding accuracy,
spatial directional disambiguation, Rule 8 payment screening, and Guardian SLA.
Phase 25-01 (ACT-01, VIS-04, SAF-01, SAF-02).
"""

import time
import pytest

from services.backend.grounding.visual_segmenter import (
    VisualSegmenter,
    SegmentedUIElement,
    UIElementBoundingBox,
    Rule8ViolationError as SegmenterR8,
    visual_segmenter,
)
from services.backend.grounding.semantic_grounding_engine import (
    SemanticGroundingEngine,
    Rule8ViolationError as GroundingR8,
    semantic_grounding_engine,
)
from services.backend.safety.guardian import guardian
from services.backend.safety.registry import registry
import services.backend.tools.semantic_grounding_tools  # Ensure tools are loaded


@pytest.fixture(autouse=True)
def reset_guardian_and_segmenter():
    guardian.resume()
    visual_segmenter.reset_elements()
    yield
    guardian.resume()
    visual_segmenter.reset_elements()


def test_visual_segmenter_screen_parsing():
    """Verify visual segmenter parses interactive elements and bounding boxes."""
    segmenter = VisualSegmenter()
    elements = segmenter.segment_screen()

    assert len(elements) >= 5
    roles = {e.role for e in elements}
    assert "BUTTON" in roles
    assert "INPUT" in roles
    assert "MENU_ITEM" in roles

    for elem in elements:
        assert elem.bounding_box.width > 0
        assert elem.bounding_box.height > 0
        assert elem.bounding_box.center_x == elem.bounding_box.x + (elem.bounding_box.width // 2)
        assert elem.bounding_box.center_y == elem.bounding_box.y + (elem.bounding_box.height // 2)
        assert elem.confidence > 0.80


def test_semantic_grounding_query_accuracy():
    """Verify queries resolve to the expected UI element with high confidence."""
    engine = SemanticGroundingEngine()

    # 1. Save button
    m1 = engine.ground_query("click the save changes button")
    assert m1.matched_element.label == "Save Changes"
    assert m1.matched_element.role == "BUTTON"
    assert m1.match_score >= 0.85
    assert m1.target_coordinates == (910, 638)
    assert m1.latency_ms < 50.0

    # 2. Search input
    m2 = engine.ground_query("find the search box to find files")
    assert "Search" in m2.matched_element.label
    assert m2.matched_element.role == "INPUT"
    assert m2.match_score >= 0.85

    # 3. Settings gear
    m3 = engine.ground_query("open settings gear icon")
    assert "Settings" in m3.matched_element.label
    assert m3.matched_element.role == "ICON"
    assert m3.match_score >= 0.85

    # 4. Run tests button
    m4 = engine.ground_query("press run tests")
    assert m4.matched_element.label == "Run Tests"
    assert m4.matched_element.role == "BUTTON"


def test_spatial_directional_disambiguation():
    """Verify directional cues ('top', 'bottom', 'left', 'right') guide grounding."""
    engine = SemanticGroundingEngine()

    # Both are INPUT: search is at top (y=48), prompt input is at bottom (y=980)
    m_top = engine.ground_query("type into the top input")
    assert m_top.matched_element.bounding_box.center_y < 200

    m_bottom = engine.ground_query("enter text into the bottom input message box")
    assert m_bottom.matched_element.bounding_box.center_y > 800


def test_rule_8_anti_checkout_enforcement():
    """Verify payment and checkout operations are blocked with Rule8ViolationError."""
    engine = SemanticGroundingEngine()
    segmenter = VisualSegmenter()

    with pytest.raises(GroundingR8, match="Rule 8"):
        engine.ground_query("click the checkout payment button")

    with pytest.raises(GroundingR8, match="Rule 8"):
        engine.ground_query("enter credit card number into billing form")

    bad_elem = SegmentedUIElement(
        role="BUTTON",
        label="Complete Checkout and Pay Now",
        bounding_box=UIElementBoundingBox(x=100, y=100, width=100, height=30),
    )
    with pytest.raises(SegmenterR8, match="Rule 8"):
        segmenter.inject_elements_for_testing([bad_elem])


def test_guardian_kill_switch_sla_halt():
    """Verify Guardian kill switch synchronously interrupts grounding in < 25.0ms SLA."""
    guardian.trigger("Emergency Grounding Halt")
    assert guardian.is_halted

    t0 = time.perf_counter()
    with pytest.raises(PermissionError, match="Guardian kill switch"):
        semantic_grounding_engine.ground_query("find save button")
    halt_duration_ms = (time.perf_counter() - t0) * 1000.0

    assert halt_duration_ms < 25.0, f"Halt latency {halt_duration_ms:.4f}ms exceeded 25.0ms SLA"

    with pytest.raises(PermissionError, match="Guardian kill switch"):
        visual_segmenter.segment_screen()

    guardian.resume()
    assert not guardian.is_halted


def test_tool_registry_and_previews():
    """Verify tool registration, tier classifications, and preview generations."""
    ground_tool = registry.get("ground_screen_elements")
    assert ground_tool is not None
    assert ground_tool.tier == 0
    preview_ground = ground_tool.generate_preview({"query": "save button"})
    assert "save button" in preview_ground

    anchor_tool = registry.get("locate_gui_visual_anchor")
    assert anchor_tool is not None
    assert anchor_tool.tier == 0
    preview_anchor = anchor_tool.generate_preview({"anchor_name": "settings_gear"})
    assert "settings_gear" in preview_anchor

    map_tool = registry.get("get_visual_grounding_map")
    assert map_tool is not None
    assert map_tool.tier == 0
    preview_map = map_tool.generate_preview({})
    assert "visual grounding map" in preview_map
