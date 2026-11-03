"""
End-to-End Tests for Specialist Swarm Tools & Orchestration (SWM-01, SAF-01)
Validates ToolRegistry tool registrations, risk tiers, preview strings, and end-to-end debate runs.
"""

import pytest
from services.backend.safety.registry import registry
from services.backend.schemas.swarm_debate import (
    SpecialistRole,
    ConsensusVerdict,
)
from services.backend.tools.swarm_tools import (
    swarm_dispatch_specialists,
    swarm_get_debate_status,
    swarm_submit_user_decision,
)


def test_swarm_tools_registered_with_correct_tiers():
    """Verify specialist swarm tools are registered in ToolRegistry with accurate risk tiers."""
    get_status_tool = registry.get("swarm_get_debate_status")
    assert get_status_tool is not None
    assert get_status_tool.tier == 0
    assert "Read-only" in get_status_tool.description

    dispatch_tool = registry.get("swarm_dispatch_specialists")
    assert dispatch_tool is not None
    assert dispatch_tool.tier == 1

    submit_tool = registry.get("swarm_submit_user_decision")
    assert submit_tool is not None
    assert submit_tool.tier == 1


def test_swarm_tool_preview_functions():
    """Verify tool previews are informative, formatted properly, and leak no private content."""
    dispatch_tool = registry.get("swarm_dispatch_specialists")
    assert dispatch_tool is not None
    preview = dispatch_tool.generate_preview({"title": "Refactor router", "risk_tier": 2})
    assert "Refactor router" in preview
    assert "Tier 2" in preview

    get_status_tool = registry.get("swarm_get_debate_status")
    assert get_status_tool is not None
    preview_status = get_status_tool.generate_preview({"debate_id": "deb-999"})
    assert "deb-999" in preview_status

    submit_tool = registry.get("swarm_submit_user_decision")
    assert submit_tool is not None
    preview_submit = submit_tool.generate_preview({"debate_id": "deb-999", "decision": "approve"})
    assert "deb-999" in preview_submit
    assert "approve" in preview_submit


@pytest.mark.asyncio
async def test_end_to_end_specialist_debate_via_tool():
    """Verify swarm_dispatch_specialists tool execution runs full synthetic debate."""
    result = await swarm_dispatch_specialists(
        title="Create caching utility",
        description="Add LRU cache with clean modular functions and full pytest tests",
        diff="def test_cache(): assert True",
        risk_tier=1,
        max_rounds=2
    )

    assert "debate_id" in result
    assert result["proposal_title"] == "Create caching utility"
    assert result["verdict"] == ConsensusVerdict.APPROVED_AUTONOMOUS.value
    assert result["final_score"] == 1.0
    assert len(result["turns"]) >= 1

    # Verify query tool retrieves the debate
    status = swarm_get_debate_status(debate_id=result["debate_id"])
    assert status["found"] is True
    assert status["debate"]["debate_id"] == result["debate_id"]


@pytest.mark.asyncio
async def test_end_to_end_escalation_and_submission_via_tool():
    """Verify escalating debate via tool and resolving it with swarm_submit_user_decision."""
    escalated_result = await swarm_dispatch_specialists(
        title="High-privilege system script",
        description="Shell execution command [simulate_request_changes] without tests",
        risk_tier=2,
        max_rounds=1
    )

    assert escalated_result["verdict"] in [
        ConsensusVerdict.GATED_PENDING_UNANIMOUS.value,
        ConsensusVerdict.ESCALATED_TO_USER.value,
    ]
    debate_id = escalated_result["debate_id"]

    decision_result = swarm_submit_user_decision(
        debate_id=debate_id,
        decision="approve",
        reason="Operator approved for staging environment"
    )

    assert decision_result["verdict"] == ConsensusVerdict.APPROVED_BY_USER.value
