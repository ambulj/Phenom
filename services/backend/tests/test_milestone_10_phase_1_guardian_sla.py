"""
Sub-25ms Synchronous Guardian Kill Switch SLA & Recovery Tests (SAF-02, SWM-01)
Measures and validates:
1. Synchronous halt() SLA < 25ms (with typical execution < 1ms).
2. Cancellation of active debate tasks and futures.
3. Strict rejection of operations while halted.
4. Resumption and state recovery upon reset().
"""

import time
import asyncio
import pytest

from services.backend.main import on_guardian_state_change
from services.backend.safety.guardian import guardian
from services.backend.schemas.swarm_debate import (
    SwarmProposal,
    ConsensusReport,
    ConsensusVerdict,
)
from services.backend.swarm.specialist_orchestrator import (
    SpecialistSwarmOrchestrator,
    specialist_swarm_orchestrator,
)


@pytest.fixture(autouse=True)
def reset_milestone_10_phase_1_components():
    """Ensure clean state before and after each test."""
    guardian.resume()
    specialist_swarm_orchestrator.reset()
    yield
    guardian.resume()
    specialist_swarm_orchestrator.reset()


def test_synchronous_halt_sla_benchmark():
    """Verify orchestrator halt() executes well within the 25ms SLA (assert < 25ms, verify < 1ms typical)."""
    orchestrator = SpecialistSwarmOrchestrator()

    # Prepopulate with dummy debate records
    for i in range(50):
        report = ConsensusReport(
            proposal_title=f"Debate {i}",
            proposal_description="Background review",
            risk_tier=1,
            verdict=ConsensusVerdict.ESCALATED_TO_USER
        )
        orchestrator._debates[report.debate_id] = report

    # High-precision timer benchmark
    start_time = time.perf_counter()
    orchestrator.halt()
    elapsed_ms = (time.perf_counter() - start_time) * 1000.0

    print(f"\n[Guardian SLA Benchmark] orchestrator.halt() elapsed: {elapsed_ms:.4f} ms")
    assert elapsed_ms < 25.0, f"Halt exceeded 25ms SLA! Took {elapsed_ms:.4f} ms"
    assert orchestrator.is_halted is True


@pytest.mark.asyncio
async def test_active_debate_cancellation_on_halt():
    """Verify in-flight debate asyncio tasks are immediately canceled on halt()."""
    orchestrator = SpecialistSwarmOrchestrator()

    # Create an artificial slow debate proposal
    proposal = SwarmProposal(
        title="Long debate",
        description="Complex proposal [simulate_block]",
        risk_tier=2
    )

    # Spawn an asynchronous debate task
    task = asyncio.create_task(orchestrator.dispatch_debate(proposal, max_rounds=3))
    # Give the task a moment to register in _active_tasks
    await asyncio.sleep(0.001)

    # Trigger halt
    start = time.perf_counter()
    orchestrator.halt()
    elapsed_ms = (time.perf_counter() - start) * 1000.0

    assert elapsed_ms < 25.0
    assert orchestrator.is_halted is True

    # The task should be cancelled or done
    with pytest.raises((asyncio.CancelledError, Exception)):
        await task


@pytest.mark.asyncio
async def test_pending_escalations_rejected_on_halt():
    """Verify pending escalations waiting for user decisions fail immediately with PermissionError."""
    orchestrator = SpecialistSwarmOrchestrator()

    proposal = SwarmProposal(
        title="Escalated proposal",
        description="Requires user sign-off [simulate_block]",
        risk_tier=2
    )

    # Dispatch debate (will escalate to user)
    report = await orchestrator.dispatch_debate(proposal, max_rounds=1)
    assert report.verdict in [ConsensusVerdict.GATED_PENDING_UNANIMOUS, ConsensusVerdict.ESCALATED_TO_USER]
    assert report.debate_id in orchestrator._pending_escalations

    # Trigger halt
    orchestrator.halt()

    # Pending escalations dict is cleared and reports marked HALTED
    assert len(orchestrator._pending_escalations) == 0
    status = orchestrator.get_debate_status(report.debate_id)
    assert status["debate"]["verdict"] == ConsensusVerdict.HALTED.value

    # Subsequent dispatch or decision submission raises PermissionError
    with pytest.raises(PermissionError):
        orchestrator.submit_user_decision(report.debate_id, "approve")

    with pytest.raises(PermissionError):
        await orchestrator.dispatch_debate(proposal)


@pytest.mark.asyncio
async def test_recovery_and_resumption_after_reset():
    """Verify orchestrator recovers cleanly upon reset() and accepts new debates."""
    orchestrator = SpecialistSwarmOrchestrator()
    orchestrator.halt()
    assert orchestrator.is_halted is True

    # Reset
    orchestrator.reset()
    assert orchestrator.is_halted is False

    # Dispatch a new debate - should succeed
    proposal = SwarmProposal(
        title="Clean post-halt patch",
        description="Add simple math function with tests",
        diff="def test_clean(): assert True",
        risk_tier=1
    )
    report = await orchestrator.dispatch_debate(proposal, max_rounds=1)
    assert report.verdict == ConsensusVerdict.APPROVED_AUTONOMOUS


def test_guardian_singleton_integration():
    """Verify global guardian trigger invokes specialist_swarm_orchestrator.halt() and reset()."""
    # Ensure idle state first
    guardian.resume()
    assert specialist_swarm_orchestrator.is_halted is False

    # Trigger Guardian
    guardian.trigger("Test Guardian Kill Switch SLA")
    assert specialist_swarm_orchestrator.is_halted is True

    # Resume Guardian
    guardian.resume()
    assert specialist_swarm_orchestrator.is_halted is False
