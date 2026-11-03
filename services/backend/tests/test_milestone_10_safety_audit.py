"""
Milestone 10.0 Comprehensive Safety Audit Test Suite (SAF-01, SAF-02)
Audits all 15 Milestone 10 tools across Phases 1–4 against risk tiers,
Pydantic schemas, callable previews, and Phenom Permanent Safety Rules.
"""

import pytest
from pydantic import BaseModel
import services.backend.tools.swarm_tools
import services.backend.tools.virtual_gui_tools
import services.backend.tools.mirror_tools
import services.backend.tools.mesh_tools
import services.backend.tools.file_tools
import services.backend.tools.automation_tools
import services.backend.tools.integration_tools
from services.backend.safety.registry import registry

# Exact list of all 15 tools introduced in Milestone 10.0
EXPECTED_M10_TOOLS = {
    # Phase 1: Swarm Debate
    "swarm_dispatch_specialists": 1,
    "swarm_get_debate_status": 0,
    "swarm_submit_user_decision": 1,
    # Phase 2: Virtual Desktop GUI Automation
    "gui_capture_virtual_screen": 0,
    "gui_launch_app_isolated": 1,
    "gui_execute_action": 1,
    "gui_close_isolated_desktop": 1,
    # Phase 3: Cognitive Mirror & Twin
    "mirror_get_profile_stats": 0,
    "mirror_synthesize_text": 0,
    "mirror_learn_from_sources": 1,
    "mirror_reset_profile": 1,
    # Phase 4: P2P Local Mesh
    "mesh_get_paired_devices": 0,
    "mesh_generate_pairing_qr": 1,
    "mesh_sync_push": 1,
    "mesh_unpair_device": 1,
}


def test_m10_tools_registration_and_tiers():
    """Assert all 15 tools are registered with correct risk tiers and Pydantic schemas."""
    tools = registry.list_all()

    for tool_name, expected_tier in EXPECTED_M10_TOOLS.items():
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

        # Generate preview with empty/default args
        try:
            preview_text = tool_def.generate_preview({})
            assert isinstance(preview_text, str)
            assert len(preview_text) > 0, f"Preview for '{tool_name}' must not be empty"
        except Exception as e:
            # If empty dict lacks required field, pass schema-constructed defaults
            preview_text = tool_def.generate_preview({"node_id": "test_node", "session_id": "test_session", "hwnd": 1234})
            assert isinstance(preview_text, str)
            assert len(preview_text) > 0


def test_rule_1_no_unclassified_tools():
    """Permanent Rule 1: Every registered tool must have an integer tier in (0, 1, 2, 3)."""
    tools = registry.list_all()
    for name, tool_def in tools.items():
        assert tool_def.tier in (0, 1, 2, 3), f"Tool '{name}' has invalid tier {tool_def.tier}"


def test_rule_4_zero_cloud_exfiltration_invariants():
    """
    Permanent Rule 4: Private data, virtual desktop frames, cognitive mirror traits,
    and mesh sync payloads must NEVER be routed to external cloud endpoints.
    """
    from services.backend.personality.cognitive_mirror import CognitiveMirrorEngine
    from services.backend.mesh.p2p_mesh_engine import P2PMeshEngine
    from services.backend.automation.virtual_desktop_manager import VirtualDesktopManager

    # Inspect class attributes and method names for forbidden cloud exfiltration
    for cls in [CognitiveMirrorEngine, P2PMeshEngine, VirtualDesktopManager]:
        method_names = [m for m in dir(cls) if not m.startswith("__")]
        for m in method_names:
            assert "upload_to_cloud" not in m.lower()
            assert "send_to_telemetry" not in m.lower()


def test_rule_7_and_8_recycle_bin_and_zero_payments():
    """
    Permanent Rule 7: Delete operations must use Send2Trash.
    Permanent Rule 8: Zero payment or financial checkout tools by construction.
    """
    import inspect
    from services.backend.tools import file_tools
    source = inspect.getsource(file_tools)
    assert "send2trash" in source, "File deletions must use send2trash for recycle bin safety"

    # Rule 8: Ensure payment tools are strictly Tier 3 (blocked) and raise PermissionError
    checkout_tool = registry.get("checkout_pay")
    assert checkout_tool is not None
    assert checkout_tool.tier == 3

    from services.backend.tools.automation_tools import checkout_pay
    with pytest.raises(PermissionError) as exc_info:
        checkout_pay()
    assert "strictly prohibited" in str(exc_info.value).lower()

    # Verify no Milestone 10.0 tool enables payments
    for tool_name in EXPECTED_M10_TOOLS:
        name_lower = tool_name.lower()
        for kw in ["pay", "checkout", "buy", "place_order", "purchase"]:
            assert kw not in name_lower, f"Violates Rule 8: {tool_name}"


def test_rule_9_email_and_calendar_invariants():
    """
    Permanent Rule 9: Email is drafts-only (no direct send).
    Calendar: create events only, never delete or edit others' events.
    """
    # Ensure send_email is strictly Tier 3 (blocked)
    send_tool = registry.get("send_email")
    assert send_tool is not None
    assert send_tool.tier == 3

    # Verify Milestone 10.0 tools do not perform email sending or calendar event deletions
    for tool_name in EXPECTED_M10_TOOLS:
        assert "send_email" not in tool_name.lower(), f"Violates Rule 9: {tool_name}"
        assert "delete_calendar" not in tool_name.lower(), f"Violates Rule 9: {tool_name}"
