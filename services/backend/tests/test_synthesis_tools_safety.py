"""
Safety Governance and Hot-Loading Test Suite (SAF-01).
Tests synthesis tool registration, tiers, schemas, previews,
execution via SafetyExecutionEngine, and dynamic revocation.
"""

import pytest
from services.backend.safety.registry import registry
from services.backend.safety.engine import safety_engine
from services.backend.coding.dynamic_synthesizer import dynamic_synthesizer_manager
import services.backend.tools.synthesis_tools as st


@pytest.fixture(autouse=True)
def cleanup_tools():
    # Setup
    yield
    # Cleanup any dynamically synthesized test tools
    for tool_name in ["unit_test_flattener", "custom_adder_tool", "demo_calc"]:
        registry.unregister(tool_name)
        dynamic_synthesizer_manager.unregister_tool(tool_name)


def test_synthesis_management_tools_registered():
    expected_tools = [
        "synthesize_custom_tool",
        "run_synthesized_tool",
        "list_synthesized_tools",
        "revoke_synthesized_tool",
    ]
    for name in expected_tools:
        tool_def = registry.get(name)
        assert tool_def is not None, f"Tool '{name}' must be registered in ToolRegistry"
        assert callable(tool_def.preview_fn)
        assert tool_def.args_schema is not None

    assert registry.get_tier("synthesize_custom_tool") == 1
    assert registry.get_tier("run_synthesized_tool") == 1
    assert registry.get_tier("list_synthesized_tools") == 0
    assert registry.get_tier("revoke_synthesized_tool") == 1


def test_synthesize_custom_tool_preview():
    tool_def = registry.get("synthesize_custom_tool")
    preview = tool_def.generate_preview({
        "tool_name": "unit_test_flattener",
        "task_description": "Flatten nested JSON structures",
    })
    assert "unit_test_flattener" in preview
    assert "Flatten nested JSON structures" in preview


@pytest.mark.asyncio
async def test_end_to_end_synthesis_hot_registration_and_execution():
    # 1. Synthesize a tool
    res = st.synthesize_custom_tool(
        tool_name="unit_test_flattener",
        task_description="Flatten nested dictionaries",
        parameter_specs={"nested_dict": {"type": "dict"}},
    )
    assert res["success"] is True
    assert res["tool_name"] == "unit_test_flattener"
    assert "CAP_DATA_TRANSFORM" in res["capabilities"]

    # 2. Check hot-registered in registry
    tool_def = registry.get("unit_test_flattener")
    assert tool_def is not None
    assert tool_def.name == "unit_test_flattener"
    assert tool_def.tier == 0  # Pure transform is Tier 0 eligible

    # 3. List tools
    list_res = st.list_synthesized_tools()
    assert list_res["success"] is True
    assert any(t["tool_name"] == "unit_test_flattener" for t in list_res["tools"])

    # 4. Execute via run_synthesized_tool
    run_res = st.run_synthesized_tool(
        tool_name="unit_test_flattener",
        arguments={"nested_dict": {"x": 10, "nested": {"y": 20}}},
    )
    assert run_res["success"] is True
    assert run_res["output"]["x"] == 10
    assert run_res["output"]["nested.y"] == 20

    # 5. Revoke tool
    revoke_res = st.revoke_synthesized_tool(tool_name="unit_test_flattener", reason="Test cleanup")
    assert revoke_res["success"] is True

    # 6. Verify tool no longer exists in registry
    assert registry.get("unit_test_flattener") is None
    # Subsequent execution should report unregistered
    failed_run = st.run_synthesized_tool(tool_name="unit_test_flattener", arguments={})
    assert failed_run["success"] is False
    assert "not registered" in failed_run["error"]


@pytest.mark.asyncio
async def test_safety_engine_tier_1_confirmation_gate():
    # Set mock confirmation handler for safety engine
    async def mock_confirm(*args, **kwargs):
        return ("approved", False)

    safety_engine.set_confirmation_handler(mock_confirm)

    # Execute synthesize_custom_tool via safety engine
    exec_result = await safety_engine.execute_tool(
        tool_name="synthesize_custom_tool",
        raw_args={
            "tool_name": "custom_adder_tool",
            "task_description": "Simple adder tool",
            "parameter_specs": {"val": {"type": "int"}},
        },
        source="desktop",
    )
    assert exec_result["status"] == "success"
    assert exec_result["result"]["success"] is True
    assert registry.get("custom_adder_tool") is not None

    # Unregister
    st.revoke_synthesized_tool("custom_adder_tool")
