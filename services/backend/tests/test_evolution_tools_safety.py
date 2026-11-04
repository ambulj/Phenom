"""
Safety & Risk Tier Verification Tests for Neuro-Evolution Tools (SAF-01, SAF-02).
Verifies:
- All 5 evolution tools registered in ToolRegistry
- Tier 0 classification for evolution_get_status
- Tier 1 classification for distillation, training, activation, and rollback
- Parameter schema validation
- Guardian kill switch lockdown fails closed with PermissionError
"""

import pytest
from services.backend.safety.guardian import guardian
from services.backend.safety.registry import registry
import services.backend.tools.evolution_tools as evo_tools
from services.backend.evolution.adapter_manager import local_adapter_manager


EXPECTED_EVO_TOOLS = {
    "evolution_get_status": 0,
    "evolution_distill_instructions": 1,
    "evolution_train_adapter": 1,
    "evolution_activate_adapter": 1,
    "evolution_rollback_adapter": 1,
}


def test_evolution_tools_registered_with_correct_tiers():
    """Verify all 5 evolution tools exist in ToolRegistry with their required risk tiers."""
    for tool_name, expected_tier in EXPECTED_EVO_TOOLS.items():
        assert tool_name in registry._tools, f"Tool '{tool_name}' must be in ToolRegistry"
        meta = registry._tools[tool_name]
        assert meta.tier == expected_tier, (
            f"Tool '{tool_name}' must have Risk Tier {expected_tier}, but got {meta.tier}"
        )
        assert meta.args_schema is not None
        assert meta.preview_fn is not None


def test_evolution_get_status_tier_0():
    """Verify Tier 0 query executes cleanly."""
    res = evo_tools.evolution_get_status()
    assert res["status"] == "success"
    assert "evolution_status" in res
    assert "registered_adapters" in res["evolution_status"]


def test_evolution_tier_1_lifecycle_execution():
    """Verify training, activation, and rollback via tool invocations."""
    local_adapter_manager.reset()

    # 1. Distill
    dist_res = evo_tools.evolution_distill_instructions(domain="coding", max_pairs=5)
    assert dist_res["status"] == "success"
    assert dist_res["pairs_count"] > 0

    # 2. Train
    train_res = evo_tools.evolution_train_adapter(
        adapter_id="lora_tool_test",
        domain="coding",
        epochs=3,
    )
    assert train_res["status"] == "success"
    assert train_res["adapter"]["benchmark_score"] >= 0.85

    # 3. Activate
    act_res = evo_tools.evolution_activate_adapter(adapter_id="lora_tool_test")
    assert act_res["status"] == "success"
    assert act_res["active_adapter"]["is_active"] is True

    # 4. Rollback
    roll_res = evo_tools.evolution_rollback_adapter(reset_to_base=True)
    assert roll_res["status"] == "success"
    assert roll_res["is_base_model"] is True


def test_evolution_tools_guardian_lockdown():
    """Verify all Tier 1 evolution tools are rejected under Guardian kill switch lockdown."""
    try:
        guardian.trigger("Testing evolution tools safety lockdown")
        assert guardian.is_halted is True

        with pytest.raises(PermissionError, match="halted by Guardian kill switch"):
            evo_tools.evolution_distill_instructions(domain="coding")

        with pytest.raises(PermissionError, match="halted by Guardian kill switch"):
            evo_tools.evolution_train_adapter(adapter_id="test", domain="coding")

        with pytest.raises(PermissionError, match="halted by Guardian kill switch"):
            evo_tools.evolution_activate_adapter(adapter_id="test")

        with pytest.raises(PermissionError, match="halted by Guardian kill switch"):
            evo_tools.evolution_rollback_adapter()

    finally:
        guardian.resume()
        local_adapter_manager.reset()
        assert guardian.is_halted is False
