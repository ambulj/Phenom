"""
Safety & ToolRegistry Governance Tests for Sovereign Dream Engine (SAF-01).
Validates:
- Tool registration in ToolRegistry
- Risk tier classifications (Tier 0 & Tier 1)
- Pydantic argument schemas and non-empty preview generation
- Guardian kill switch fail-closed enforcement
"""

import pytest
from pydantic import BaseModel
import services.backend.tools.dream_tools
from services.backend.safety.registry import registry
from services.backend.safety.guardian import guardian

EXPECTED_DREAM_TOOLS = {
    "dream_get_status": 0,
    "dream_trigger_cycle": 1,
    "dream_prune_stale_memory": 1,
}


def test_dream_tools_registration_and_tiers():
    """Assert all dream tools are registered with expected risk tiers."""
    tools = registry.list_all()

    for tool_name, expected_tier in EXPECTED_DREAM_TOOLS.items():
        assert tool_name in tools, f"Tool '{tool_name}' must be registered in ToolRegistry"
        tool_def = tools[tool_name]

        assert tool_def.tier == expected_tier, (
            f"Tool '{tool_name}' tier mismatch: expected {expected_tier}, got {tool_def.tier}"
        )
        assert tool_def.args_schema is not None
        assert issubclass(tool_def.args_schema, BaseModel)
        assert callable(tool_def.preview_fn)

        # Verify preview generation
        preview = tool_def.generate_preview({})
        assert isinstance(preview, str)
        assert len(preview) > 0


def test_dream_tools_execution_via_registry():
    """Assert dream tools execute safely through ToolRegistry."""
    # Tier 0 status inspect
    status_def = registry.get("dream_get_status")
    assert status_def is not None
    res = status_def.handler_fn(include_report=True)
    assert res["status"] == "success"
    assert "engine_status" in res

    # Tier 1 prune in dry_run mode
    prune_def = registry.get("dream_prune_stale_memory")
    assert prune_def is not None
    prune_res = prune_def.handler_fn(decay_days_threshold=14, dry_run=True)
    assert prune_res["status"] == "success"
    assert prune_res["details"]["dry_run"] is True


def test_dream_tools_guardian_lockdown():
    """Assert all Tier 1 dream tools fail closed when Guardian is halted."""
    if not guardian.is_halted:
        guardian.trigger("Dream tools safety test")

    try:
        assert guardian.is_halted

        with pytest.raises(PermissionError):
            services.backend.tools.dream_tools.dream_trigger_cycle(force=True)

        with pytest.raises(PermissionError):
            services.backend.tools.dream_tools.dream_prune_stale_memory(dry_run=True)
    finally:
        guardian.resume()
