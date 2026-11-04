import pytest
from services.backend.safety.guardian import guardian
from services.backend.safety.registry import registry
import services.backend.tools.subsystem_governance_tools as sgt
from services.backend.schemas.subsystem_governance import RemediationActionType


def test_subsystem_governance_tools_registered_in_registry():
    expected_tools = [
        ("subsystem_get_health", 0),
        ("subsystem_trigger_remediation", 1),
        ("subsystem_reset_circuit_breaker", 1),
        ("subsystem_configure_thresholds", 1),
    ]

    for tool_name, expected_tier in expected_tools:
        tool_def = registry.get(tool_name)
        assert tool_def is not None, f"Tool {tool_name} not registered in ToolRegistry"
        assert tool_def.tier == expected_tier, f"Tool {tool_name} tier mismatch"


def test_subsystem_governance_tier_0_queries_execute():
    if guardian.is_halted:
        guardian.resume()

    res = sgt.subsystem_get_health()
    assert "is_active" in res
    assert "subsystems" in res
    assert "overall_health" in res


def test_subsystem_governance_tier_1_controls_with_preview():
    if guardian.is_halted:
        guardian.resume()

    # Trigger remediation preview
    tool_rem = registry.get("subsystem_trigger_remediation")
    preview_rem = tool_rem.preview_fn({"subsystem_name": "voice_action", "action_type": "recycle_worker"})
    assert "recycle_worker" in preview_rem
    assert "voice_action" in preview_rem

    res_rem = sgt.subsystem_trigger_remediation(
        subsystem_name="voice_action",
        action_type=RemediationActionType.RECYCLE_WORKER,
    )
    assert res_rem["success"]

    # Reset circuit breaker preview
    tool_rst = registry.get("subsystem_reset_circuit_breaker")
    preview_rst = tool_rst.preview_fn({"subsystem_name": "voice_action"})
    assert "voice_action" in preview_rst

    res_rst = sgt.subsystem_reset_circuit_breaker(subsystem_name="voice_action")
    assert res_rst["success"]


def test_subsystem_governance_tools_fail_closed_under_guardian_halt():
    try:
        guardian.trigger("Governance Safety Test Halt")
        assert guardian.is_halted

        with pytest.raises(PermissionError):
            sgt.subsystem_get_health()

        with pytest.raises(PermissionError):
            sgt.subsystem_trigger_remediation(
                subsystem_name="telepresence",
                action_type=RemediationActionType.FLUSH_STALE_BUFFERS,
            )

        with pytest.raises(PermissionError):
            sgt.subsystem_reset_circuit_breaker(subsystem_name="telepresence")

        with pytest.raises(PermissionError):
            sgt.subsystem_configure_thresholds(max_error_count=10)
    finally:
        guardian.resume()
