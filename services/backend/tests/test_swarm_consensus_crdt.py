"""Unit & Safety Tests for Swarm CRDT State Consensus & Reconciler (Milestone 27 Phase 3)."""

import pytest
import time
from services.backend.swarm.crdt_consensus_engine import (
    VectorClock,
    CRDTStateRegister,
    Rule8ViolationError,
)
from services.backend.swarm.state_reconciler import StateReconciler
from services.backend.safety.guardian import guardian
from services.backend.safety.registry import registry
import services.backend.tools.swarm_consensus_tools  # Ensure registered


@pytest.fixture(autouse=True)
def reset_guardian():
    guardian.resume()
    yield
    guardian.resume()


def test_vector_clock_ticks_and_dominance():
    vc1 = VectorClock(clocks={"agent_a": 1, "agent_b": 2})
    vc2 = VectorClock(clocks={"agent_a": 2, "agent_b": 2})

    assert vc2.dominates(vc1) is True
    assert vc1.dominates(vc2) is False

    # Tick
    vc1.tick("agent_a")
    assert vc1.clocks["agent_a"] == 2

    # Merge
    vc3 = VectorClock(clocks={"agent_c": 3})
    vc1.merge(vc3)
    assert vc1.clocks["agent_c"] == 3


def test_crdt_delta_application_and_lww():
    reg = CRDTStateRegister()
    # Apply delta from agent_a
    d1 = reg.apply_delta("agent_codearchitect", "target_branch", "feat/phase-3")
    assert d1.value == "feat/phase-3"
    state = reg.get_converged_state()
    assert state["target_branch"]["value"] == "feat/phase-3"
    assert state["target_branch"]["author"] == "agent_codearchitect"

    # Newer delta from agent_securityauditor overrides (LWW)
    time.sleep(0.005)
    d2 = reg.apply_delta("agent_securityauditor", "target_branch", "hardening/pass-1")
    state2 = reg.get_converged_state()
    assert state2["target_branch"]["value"] == "hardening/pass-1"
    assert state2["target_branch"]["author"] == "agent_securityauditor"


def test_state_reconciler_proposals_batch():
    reconciler = StateReconciler()
    proposals = [
        {"agent_id": "agent_codearchitect", "key": "build_tool", "value": "vite"},
        {"agent_id": "agent_testorchestrator", "key": "test_runner", "value": "pytest"},
    ]
    res = reconciler.reconcile_proposals(proposals)
    assert res["status"] == "CONVERGED"
    assert res["applied_delta_count"] == 2
    assert res["converged_state"]["build_tool"]["value"] == "vite"
    assert res["converged_state"]["test_runner"]["value"] == "pytest"


def test_state_reconciler_rollback():
    reg = CRDTStateRegister()
    reconciler = StateReconciler(register=reg)

    reconciler.reconcile_proposals([{"agent_id": "agent_a", "key": "config_mode", "value": "DEBUG"}])
    assert reg.get_converged_state()["config_mode"]["value"] == "DEBUG"

    # Mutate
    time.sleep(0.005)
    reconciler.reconcile_proposals([{"agent_id": "agent_b", "key": "config_mode", "value": "PRODUCTION"}])
    assert reg.get_converged_state()["config_mode"]["value"] == "PRODUCTION"

    # Rollback (Rule 7)
    time.sleep(0.005)
    assert reconciler.rollback_last_reconciliation() is True
    assert reg.get_converged_state()["config_mode"]["value"] == "DEBUG"


def test_rule_8_anti_checkout_consensus():
    reg = CRDTStateRegister()

    with pytest.raises(Rule8ViolationError, match="Rule 8 violation"):
        reg.apply_delta("agent_a", "payment_policy", "auto_buy")

    with pytest.raises(Rule8ViolationError, match="Rule 8 violation"):
        reg.apply_delta("agent_a", "credit_card_vault", "4111222233334444")


def test_guardian_kill_switch_sla_consensus():
    reg = CRDTStateRegister()
    guardian.trigger(reason="Safety test")

    t0 = time.perf_counter()
    with pytest.raises(PermissionError, match="Guardian kill switch is TRIPPED"):
        reg.get_converged_state()
    elapsed_ms = (time.perf_counter() - t0) * 1000.0
    assert elapsed_ms < 25.0, f"Guardian SLA exceeded: {elapsed_ms:.4f}ms"

    t1 = time.perf_counter()
    with pytest.raises(PermissionError, match="Guardian kill switch is TRIPPED"):
        reg.apply_delta("agent_a", "test_key", "test_val")
    elapsed_ms2 = (time.perf_counter() - t1) * 1000.0
    assert elapsed_ms2 < 25.0, f"Guardian SLA exceeded: {elapsed_ms2:.4f}ms"


def test_tool_registry_swarm_consensus_tools():
    # 1. propose_state_crdt_delta (Tier 1)
    tool_prop = registry.get("propose_state_crdt_delta")
    assert tool_prop is not None
    assert tool_prop.tier == 1
    prev_prop = tool_prop.preview_fn({"agent_id": "agent_a", "key": "port", "value": "8000"})
    assert "Propose CRDT state delta from 'agent_a': [port] -> '8000'" in prev_prop

    res_prop = tool_prop.handler_fn(agent_id="agent_codearchitect", key="active_compiler", value="tsc")
    assert res_prop["status"] == "APPLIED"
    assert res_prop["converged_entry"]["value"] == "tsc"

    # 2. reconcile_swarm_consensus (Tier 0)
    tool_rec = registry.get("reconcile_swarm_consensus")
    assert tool_rec is not None
    assert tool_rec.tier == 0
    res_rec = tool_rec.handler_fn()
    assert res_rec["status"] == "CONVERGED"
    assert "active_compiler" in res_rec["state"]

    # 3. get_lamport_vector_clocks (Tier 0)
    tool_clocks = registry.get("get_lamport_vector_clocks")
    assert tool_clocks is not None
    assert tool_clocks.tier == 0
    res_clocks = tool_clocks.handler_fn()
    assert "clocks" in res_clocks
    assert res_clocks["total_deltas"] > 0
