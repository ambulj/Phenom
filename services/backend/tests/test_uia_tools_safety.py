"""
Tests for Deep UIAutomation Tool Safety Governance (SAF-01, SAF-02).
Verifies ToolRegistry registration, preview outputs, and Guardian kill switch lockdown.
"""

import pytest
from services.backend.automation.deep_uia_engine import deep_uia_engine
from services.backend.safety.guardian import guardian
from services.backend.safety.registry import registry
from services.backend.schemas.deep_uia import (
    UIElementType,
    UIWorkflowStep,
)
import services.backend.tools.uia_tools as uia_tools


def test_uia_tools_registered_in_registry():
    expected_tools = {
        "uia_get_tree": 0,
        "uia_find_element": 0,
        "uia_invoke_element": 1,
        "uia_set_value": 1,
        "uia_execute_workflow": 1,
    }

    for tool_name, expected_tier in expected_tools.items():
        assert tool_name in registry._tools, f"Tool {tool_name} not registered in ToolRegistry"
        assert registry._tools[tool_name].tier == expected_tier, (
            f"Tool {tool_name} has tier {registry._tools[tool_name].tier}, expected {expected_tier}"
        )


def test_uia_tier_0_queries_execute():
    tree_res = uia_tools.uia_get_tree()
    assert tree_res["status"] == "success"
    assert "tree" in tree_res

    find_res = uia_tools.uia_find_element(name_query="Save")
    assert find_res["status"] == "success"
    assert find_res["element"]["name"] == "Save"


def test_uia_tier_1_controls_with_preview():
    # Verify previews
    inv_tool = registry._tools["uia_invoke_element"]
    preview_inv = inv_tool.preview_fn({"element_id": "elem-btn-save-01", "non_intrusive": True})
    assert "Invoke UI element 'elem-btn-save-01'" in preview_inv
    assert "zero cursor stealing" in preview_inv

    set_tool = registry._tools["uia_set_value"]
    preview_set = set_tool.preview_fn({"element_id": "elem-edit-title-02", "value": "New Title"})
    assert "Set value on UI element 'elem-edit-title-02' to 'New Title'" in preview_set

    wf_tool = registry._tools["uia_execute_workflow"]
    preview_wf = wf_tool.preview_fn({"steps": [{}, {}], "auto_heal": True})
    assert "Execute 2-step UIAutomation desktop workflow" in preview_wf

    # Execute Tier 1 calls
    inv_res = uia_tools.uia_invoke_element(element_id="elem-btn-save-01")
    assert inv_res["status"] == "success"

    set_res = uia_tools.uia_set_value(element_id="elem-edit-title-02", value="Updated via Tool")
    assert set_res["status"] == "success"

    wf_res = uia_tools.uia_execute_workflow(
        steps=[
            UIWorkflowStep(step_id="s1", action_type="CLICK", target_query="Save"),
        ]
    )
    assert wf_res["status"] == "success"


def test_uia_tools_fail_closed_under_guardian_halt():
    try:
        guardian.trigger("UIA Safety Test Halt")

        with pytest.raises(PermissionError, match="Guardian kill switch is active"):
            uia_tools.uia_invoke_element(element_id="elem-btn-save-01")

        with pytest.raises(PermissionError, match="Guardian kill switch is active"):
            uia_tools.uia_set_value(element_id="elem-edit-title-02", value="Halted Value")

        with pytest.raises(PermissionError, match="Guardian kill switch is active"):
            uia_tools.uia_execute_workflow(
                steps=[UIWorkflowStep(step_id="s1", action_type="CLICK", target_query="Save")]
            )
    finally:
        guardian.resume()
        deep_uia_engine.resume()
