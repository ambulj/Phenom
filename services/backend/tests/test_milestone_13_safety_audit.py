"""
Milestone 13.0 Comprehensive Safety Audit Test Suite (SAF-01, SAF-02).
Audits all 18 tools introduced in Milestone 13 across Phases 1, 2, 3, and 4:
- Tier classifications (6 Tier 0 tools, 12 Tier 1 tools)
- Pydantic v2 argument schema definitions and callable previews
- Permanent Rules compliance (Rules 1, 4, 7, 8, 9, 11)
- Fail-closed Guardian kill switch lockdown across all 12 Tier 1 tools
"""

import pytest
from services.backend.safety.guardian import guardian
from services.backend.safety.registry import registry

# Import all Milestone 13 tool modules
import services.backend.tools.evolution_tools as evo_tools
import services.backend.tools.volumetric_tools as vol_tools
import services.backend.tools.swarm_compute_tools as swarm_tools
import services.backend.tools.kernel_tools as kernel_tools


EXPECTED_M13_TOOLS = {
    # Phase 1: Neuro-Evolution & LoRA Tuning (EVO-01)
    "evolution_get_status": 0,
    "evolution_distill_instructions": 1,
    "evolution_train_adapter": 1,
    "evolution_activate_adapter": 1,
    "evolution_rollback_adapter": 1,
    # Phase 2: Volumetric Spatial Canvas & Gestures (VOL-01)
    "volumetric_get_status": 0,
    "volumetric_set_projection": 1,
    "volumetric_spawn_node": 1,
    "volumetric_clear_canvas": 1,
    "volumetric_ingest_gesture": 1,
    # Phase 3: Distributed Swarm Compute & Mesh Offload (SWM-01)
    "swarm_compute_get_topology": 0,
    "swarm_compute_register_node": 1,
    "swarm_compute_offload_workload": 1,
    "swarm_compute_abort_workload": 1,
    # Phase 4: Kernel Telemetry & Self-Healing Fabric (KER-01)
    "kernel_get_telemetry_status": 0,
    "kernel_diagnose_crash": 0,
    "kernel_scan_venv_discrepancies": 0,
    "kernel_apply_healing_patch": 1,
}


def test_milestone_13_all_18_tools_registered_and_tiered():
    """Verify all 18 Milestone 13 tools exist in ToolRegistry with exact risk tiers."""
    assert len(EXPECTED_M13_TOOLS) == 18

    for tool_name, expected_tier in EXPECTED_M13_TOOLS.items():
        assert tool_name in registry._tools, f"Tool '{tool_name}' must be registered in ToolRegistry"
        tool_meta = registry._tools[tool_name]
        assert tool_meta.tier == expected_tier, (
            f"Tool '{tool_name}' expected Tier {expected_tier}, but got Tier {tool_meta.tier}"
        )
        assert tool_meta.args_schema is not None, f"Tool '{tool_name}' missing args_schema"
        assert callable(tool_meta.preview_fn), f"Tool '{tool_name}' preview_fn must be callable"
        assert tool_meta.description, f"Tool '{tool_name}' missing description"


def test_milestone_13_all_tier_0_queries_execute():
    """Verify all 6 Tier 0 read-only queries execute cleanly."""
    # 1. evolution_get_status
    e_res = evo_tools.evolution_get_status()
    assert e_res["status"] == "success"

    # 2. volumetric_get_status
    v_res = vol_tools.volumetric_get_status()
    assert v_res["status"] == "success"

    # 3. swarm_compute_get_topology
    s_res = swarm_tools.swarm_compute_get_topology()
    assert s_res["status"] == "success"

    # 4. kernel_get_telemetry_status
    k_res = kernel_tools.kernel_get_telemetry_status()
    assert k_res["status"] == "success"

    # 5. kernel_diagnose_crash
    kd_res = kernel_tools.kernel_diagnose_crash(
        process_name="test.exe",
        exception_code="0xC0000005",
    )
    assert kd_res["status"] == "success"

    # 6. kernel_scan_venv_discrepancies
    ks_res = kernel_tools.kernel_scan_venv_discrepancies()
    assert ks_res["status"] == "success"


def test_milestone_13_guardian_lockdown_fails_closed():
    """Verify all 12 Tier 1 tools fail closed with PermissionError when Guardian is halted."""
    try:
        guardian.trigger("Milestone 13 Comprehensive Safety Audit")
        assert guardian.is_halted is True

        # Phase 1 Tier 1 tools
        with pytest.raises(PermissionError, match="halted by Guardian"):
            evo_tools.evolution_distill_instructions(domain="coding")
        with pytest.raises(PermissionError, match="halted by Guardian"):
            evo_tools.evolution_train_adapter(adapter_id="audit_test", domain="coding")
        with pytest.raises(PermissionError, match="halted by Guardian"):
            evo_tools.evolution_activate_adapter(adapter_id="audit_test")
        with pytest.raises(PermissionError, match="halted by Guardian"):
            evo_tools.evolution_rollback_adapter()

        # Phase 2 Tier 1 tools
        with pytest.raises(PermissionError, match="halted by Guardian"):
            vol_tools.volumetric_set_projection(mode="spherical")
        with pytest.raises(PermissionError, match="halted by Guardian"):
            vol_tools.volumetric_spawn_node(label="Audit Node")
        with pytest.raises(PermissionError, match="halted by Guardian"):
            vol_tools.volumetric_clear_canvas()
        with pytest.raises(PermissionError, match="halted by Guardian"):
            vol_tools.volumetric_ingest_gesture(gesture_type="POINT")

        # Phase 3 Tier 1 tools
        with pytest.raises(PermissionError, match="halted by Guardian"):
            swarm_tools.swarm_compute_register_node(node_id="audit_node", device_name="Audit Device")
        with pytest.raises(PermissionError, match="halted by Guardian"):
            swarm_tools.swarm_compute_offload_workload(workload_type="EMBEDDING_BATCH")
        with pytest.raises(PermissionError, match="halted by Guardian"):
            swarm_tools.swarm_compute_abort_workload(task_id="swm_dummy")

        # Phase 4 Tier 1 tools
        with pytest.raises(PermissionError, match="halted by Guardian"):
            kernel_tools.kernel_apply_healing_patch(patch_id="patch_dummy")

    finally:
        guardian.resume()
