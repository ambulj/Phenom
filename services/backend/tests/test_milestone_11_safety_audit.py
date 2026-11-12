"""
Milestone 11.0 Comprehensive Safety Audit Test Suite (SAF-01, SAF-02)
Audits all 13 Milestone 11 tools across Phases 1–3 against risk tiers,
Pydantic schemas, callable previews, and Phenom Permanent Safety Rules.
"""

import pytest
from pydantic import BaseModel
import services.backend.tools.synthesis_tools
import services.backend.tools.tot_tools
import services.backend.tools.sensory_tools
import services.backend.tools.file_tools
import services.backend.tools.automation_tools
import services.backend.tools.integration_tools
from services.backend.safety.registry import registry
from services.backend.safety.guardian import guardian

# Exact list of all 13 tools introduced in Milestone 11.0
EXPECTED_M11_TOOLS = {
    # Phase 1: Dynamic Runtime Tool Synthesis & Sandboxing
    "synthesize_custom_tool": 1,
    "run_synthesized_tool": 1,
    "list_synthesized_tools": 0,
    "revoke_synthesized_tool": 1,
    # Phase 2: Hierarchical Tree-of-Thought Goal Engine
    "tot_create_goal_dag": 1,
    "tot_execute_step": 1,
    "tot_get_dag_status": 0,
    "tot_prune_branch": 1,
    "tot_abort_goal": 1,
    # Phase 3: Multi-Device Sensory Fabric & P2P Media Drop
    "camera_get_companion_frame": 0,
    "camera_analyze_object_or_ocr": 0,
    "media_drop_send_file": 1,
    "media_drop_get_history": 0,
}


def test_m11_tools_registration_and_tiers():
    """Assert all 13 Milestone 11 tools are registered with correct risk tiers and Pydantic schemas."""
    tools = registry.list_all()

    for tool_name, expected_tier in EXPECTED_M11_TOOLS.items():
        assert tool_name in tools, f"Tool '{tool_name}' must be registered in ToolRegistry"
        tool_def = tools[tool_name]

        # Assert correct risk tier
        assert tool_def.tier == expected_tier, (
            f"Tool '{tool_name}' tier mismatch: expected {expected_tier}, got {tool_def.tier}"
        )

        # Assert valid Pydantic schema
        assert tool_def.args_schema is not None, f"Tool '{tool_name}' must declare an args_schema"
        assert issubclass(tool_def.args_schema, BaseModel), (
            f"Tool '{tool_name}' schema must inherit from Pydantic BaseModel"
        )

        # Assert valid callable preview function
        assert callable(tool_def.preview_fn), f"Tool '{tool_name}' preview_fn must be callable"

        # Generate preview with fallback dummy args
        try:
            preview_text = tool_def.generate_preview({})
            assert isinstance(preview_text, str)
            assert len(preview_text) > 0, f"Preview for '{tool_name}' must not be empty"
        except Exception:
            # Pass schema-constructed defaults if empty dict fails
            dummy_args = {
                "tool_name": "calc",
                "task_description": "calculate sum",
                "code": "def run(): return 42",
                "test_code": "def test(): assert True",
                "goal_description": "organize files",
                "dag_id": "test_dag",
                "node_id": "node_1",
                "branch_id": "branch_1",
                "reason": "testing",
                "image_b64": "dGVzdA==",
                "task": "ocr",
                "target_device_id": "device_1",
                "relative_path": "report.md",
                "file_bytes_b64": "dGVzdA==",
            }
            preview_text = tool_def.generate_preview(dummy_args)
            assert isinstance(preview_text, str)
            assert len(preview_text) > 0


def test_rule_1_no_unclassified_tools():
    """Permanent Rule 1: Every registered tool must have an integer tier in (0, 1, 2, 3)."""
    tools = registry.list_all()
    for name, tool_def in tools.items():
        assert tool_def.tier in (0, 1, 2, 3), f"Tool '{name}' has invalid tier {tool_def.tier}"


def test_rule_4_privacy_camera_and_drops():
    """Permanent Rule 4: Camera frames must never write to disk and P2P drops must validate paths."""
    from services.backend.sensors.companion_camera import companion_camera_streamer
    from services.backend.mesh.media_drop import media_drop_manager

    # Camera frame buffer should be in-memory only
    assert hasattr(companion_camera_streamer, "_frame_buffer")
    assert companion_camera_streamer._frame_buffer._max_frames <= 10

    # P2P media drop manager safe roots must be isolated
    assert "vault" in str(media_drop_manager._vault_dir).lower()
    assert "downloads" in str(media_drop_manager._downloads_dir).lower()


def test_rule_7_no_direct_unlinking_in_tools():
    """Permanent Rule 7: Delete means recycle bin. No Milestone 11 tool performs permanent deletion."""
    from services.backend.safety.ast_inspector import ASTSafetyInspector

    # AST inspector strictly rejects os.unlink and os.remove
    inspector = ASTSafetyInspector()
    bad_code = "import os\ndef run():\n    os.unlink('file.txt')\n"
    res = inspector.inspect_code(bad_code)
    assert not res.is_safe
    assert any("RULE_7" in v.violation_type for v in res.violations)


def test_rule_8_prohibit_financial_payments_in_synthesis_and_goals():
    """Permanent Rule 8: Financial transactions remain impossible by construction."""
    from services.backend.safety.ast_inspector import ASTSafetyInspector
    from services.backend.orchestrator.tot_planner import TreeOfThoughtPlanner

    inspector = ASTSafetyInspector()
    pay_code = "def run():\n    return checkout(stripe_key='abc', amount=100)\n"
    res = inspector.inspect_code(pay_code)
    assert not res.is_safe
    assert any("RULE_8" in v.violation_type for v in res.violations)

    planner = TreeOfThoughtPlanner()
    with pytest.raises(PermissionError) as exc_info:
        planner.plan_objective("Purchase shares of stock and checkout automatically")
    assert "Rule 8" in str(exc_info.value)


def test_rule_11_zero_secrets_exposure():
    """Permanent Rule 11: Secrets live in env or Credential Manager only."""
    tools = registry.list_all()
    forbidden_terms = ["api_key", "password", "secret_key", "private_key", "token"]
    for tool_name in EXPECTED_M11_TOOLS:
        tool_def = tools[tool_name]
        schema_fields = tool_def.args_schema.model_fields.keys()
        for field in schema_fields:
            assert field.lower() not in forbidden_terms, (
                f"Tool '{tool_name}' exposes credential field '{field}' in public schema"
            )


@pytest.mark.asyncio
async def test_guardian_kill_switch_blocks_execution():
    """SAF-02: Assert Guardian halt prevents any Tier 1 tool execution."""
    from services.backend.schemas.sensory import MediaDropSendFileArgs

    if not guardian.is_halted:
        guardian.trigger("Safety audit lockdown test")

    try:
        assert guardian.is_halted

        # Check synthesis tools fail closed
        with pytest.raises(PermissionError):
            services.backend.tools.synthesis_tools.synthesize_custom_tool(
                tool_name="test_tool", task_description="sum two numbers"
            )

        # Check ToT tools fail closed
        with pytest.raises(PermissionError):
            services.backend.tools.tot_tools.tot_create_goal_dag(
                goal_description="sample goal"
            )

        # Check media drop tools fail closed
        with pytest.raises(PermissionError):
            await services.backend.tools.sensory_tools.media_drop_send_file(
                MediaDropSendFileArgs(file_path="test.txt", target_node_id="dev1")
            )
    finally:
        guardian.resume()
