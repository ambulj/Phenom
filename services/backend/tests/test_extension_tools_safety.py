"""
Tests for Extension Tools Safety Governance (SAF-01, SAF-02).
Verifies ToolRegistry registration, preview outputs, and Guardian kill switch lockdown.
"""

import pytest
from services.backend.extensions import dynamic_extension_manager
from services.backend.safety.guardian import guardian
from services.backend.safety.registry import registry
import services.backend.tools.extension_tools as ext_tools


def test_extension_tools_registered_in_registry():
    expected_tools = {
        "extension_get_status": 0,
        "extension_synthesize": 1,
        "extension_hot_reload": 1,
        "extension_unload": 1,
    }

    for tool_name, expected_tier in expected_tools.items():
        assert tool_name in registry._tools, f"Tool {tool_name} not registered in ToolRegistry"
        assert registry._tools[tool_name].tier == expected_tier, (
            f"Tool {tool_name} has tier {registry._tools[tool_name].tier}, expected {expected_tier}"
        )


def test_extension_tier_0_queries_execute():
    res = ext_tools.extension_get_status()
    assert res["status"] == "success"
    assert "extension_state" in res


def test_extension_tier_1_controls_with_preview():
    # Verify previews
    syn_tool = registry._tools["extension_synthesize"]
    preview_syn = syn_tool.preview_fn({"name": "mock_tool", "description": "A test tool", "risk_tier": 1})
    assert "Synthesize and hot-load Python micro-tool 'mock_tool'" in preview_syn

    reload_tool = registry._tools["extension_hot_reload"]
    preview_rel = reload_tool.preview_fn({"extension_id": "ext-123"})
    assert "Recompile and hot-reload dynamic extension 'ext-123'" in preview_rel

    unload_tool = registry._tools["extension_unload"]
    preview_unl = unload_tool.preview_fn({"extension_id": "ext-123"})
    assert "Unload dynamic extension 'ext-123'" in preview_unl

    # Execute Tier 1 synthesize
    safe_code = """
def sample_calculator(x: int = 5) -> int:
    return x * x
"""
    syn_res = ext_tools.extension_synthesize(
        name="sample_calculator",
        description="Squares input number",
        python_code=safe_code,
        risk_tier=1,
    )
    assert syn_res["status"] == "success"
    ext_id = syn_res["extension_id"]
    assert "sample_calculator" in registry._tools

    # Execute Tier 1 reload
    rel_res = ext_tools.extension_hot_reload(extension_id=ext_id)
    assert rel_res["status"] == "success"

    # Execute Tier 1 unload
    unl_res = ext_tools.extension_unload(extension_id=ext_id)
    assert unl_res["status"] == "success"
    assert "sample_calculator" not in registry._tools


def test_extension_tools_fail_closed_under_guardian_halt():
    try:
        guardian.trigger("Extension Safety Test Halt")

        with pytest.raises(PermissionError, match="Guardian kill switch is active"):
            ext_tools.extension_synthesize(
                name="illegal_tool",
                description="test",
                python_code="def f(): pass",
            )

        with pytest.raises(PermissionError, match="Guardian kill switch is active"):
            ext_tools.extension_hot_reload(extension_id="fake-id")

        with pytest.raises(PermissionError, match="Guardian kill switch is active"):
            ext_tools.extension_unload(extension_id="fake-id")
    finally:
        guardian.resume()
        dynamic_extension_manager.resume()
