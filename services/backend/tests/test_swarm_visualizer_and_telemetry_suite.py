"""Comprehensive Unit Test Suite for CyberHUD Multi-Agent Visualizer & Swarm Telemetry.

Phase 48-05: TELE-01, TELE-02, TELE-03, TELE-04.
Tests SwarmTelemetryHub broadcasting, dynamic TelegramSwarmCard generation,
ToolRegistry integrations, and executes the Master Guardian Kill Switch SLA Benchmark (<25ms SLA).
"""

import time
import pytest
from typing import Dict, Any, List

from services.backend.schemas.swarm_auction import AgentRole
from services.backend.swarm.telemetry_hub import SwarmTelemetryHub
from services.backend.remote.telegram_swarm_card import TelegramSwarmCard
from services.backend.swarm.scheduler import SwarmScheduler, SwarmTaskStatus
import services.backend.tools.swarm_telemetry_tools
from services.backend.safety.registry import registry


# ============================================================================
# 1. Swarm Telemetry WebSocket Hub (TELE-02)
# ============================================================================

def test_swarm_telemetry_hub_broadcast_and_subscription():
    """Verify event publishing, subscriber callbacks, and event buffering."""
    hub = SwarmTelemetryHub(max_history=10)
    received_events: List[Dict[str, Any]] = []

    def mock_subscriber(event: Dict[str, Any]):
        received_events.append(event)

    # Subscribe
    hub.subscribe(mock_subscriber)

    # Broadcast event 1: Auction update
    e1 = hub.broadcast_event(
        event_type="auction_update",
        payload={"node_id": "step_1", "winning_role": "coder", "fitness": 0.92},
    )
    assert len(received_events) == 1
    assert received_events[0]["event_type"] == "auction_update"
    assert received_events[0]["payload"]["winning_role"] == "coder"

    # Broadcast event 2: Consensus update
    e2 = hub.broadcast_event(
        event_type="consensus_update",
        payload={"state": "quorum_reached", "is_approved": True},
    )
    assert len(received_events) == 2

    # Verify history retrieval
    recent = hub.get_recent_events(limit=5)
    assert len(recent) == 2

    # Unsubscribe test
    assert hub.unsubscribe(mock_subscriber) is True
    hub.broadcast_event("test_after_unsub", {})
    assert len(received_events) == 2  # No new events received


# ============================================================================
# 2. Dynamic Telegram Swarm Card Generator (TELE-03)
# ============================================================================

def test_telegram_swarm_card_formatting():
    """Verify ASCII quorum indicators, VRAM gauge calculation, and markdown structure."""
    # 1. VRAM Gauge test
    gauge = TelegramSwarmCard.generate_vram_gauge(used_mb=4800.0, max_mb=5632.0, width=10)
    assert "GB" in gauge
    assert "%" in gauge
    assert "█" in gauge

    # 2. Quorum indicator test: Pass
    q_pass = TelegramSwarmCard.generate_quorum_indicator(
        coder_signed=True,
        security_signed=True,
        architect_arbitrated=False,
        state="quorum_reached",
    )
    assert "[CODER: ✅]" in q_pass
    assert "[SECURITY: ✅]" in q_pass
    assert "[QUORUM: PASS]" in q_pass

    # 3. Quorum indicator test: Vetoed
    q_veto = TelegramSwarmCard.generate_quorum_indicator(
        coder_signed=True,
        security_signed=False,
        architect_arbitrated=False,
        state="vetoed",
    )
    assert "[SECURITY: 🛑 VETOED]" in q_veto

    # 4. Full card generation
    card = TelegramSwarmCard.format_swarm_card(
        mission_id="mission_alpha",
        active_role="security_auditor",
        current_task_title="Path and Secret Audit",
        quorum_state="quorum_reached",
        coder_signed=True,
        security_signed=True,
        architect_arbitrated=False,
        vram_mb=4850.0,
        max_vram_mb=5632.0,
        elapsed_seconds=135.0,
    )
    assert "PHENOM MULTI-AGENT SWARM" in card
    assert "mission_alpha" in card
    assert "SECURITY AUDITOR" in card
    assert "/approve" in card
    assert "/halt" in card
    assert "02:15" in card  # 135 seconds formatted


# ============================================================================
# 3. Tool Registry Integration
# ============================================================================

def test_swarm_telemetry_tools_registry():
    """Verify tool registration, tier numbers, preview generation, and execution."""
    tool_bcast = registry.get("broadcast_swarm_telemetry")
    tool_card = registry.get("generate_telegram_swarm_card")

    assert tool_bcast is not None
    assert tool_bcast.tier == 0  # Tier 0 read-only
    assert tool_card is not None
    assert tool_card.tier == 0  # Tier 0 read-only

    # Execute broadcast_swarm_telemetry
    res_bcast = tool_bcast.handler_fn(
        event_type="vram_telemetry",
        payload={"used_mb": 4850.0, "is_safe": True},
    )
    assert res_bcast["event_type"] == "vram_telemetry"
    assert res_bcast["payload"]["is_safe"] is True

    # Execute generate_telegram_swarm_card
    res_card = tool_card.handler_fn(
        mission_id="m_test",
        active_role="coder",
        current_task_title="Compile isolated workspace diff",
    )
    assert res_card["mission_id"] == "m_test"
    assert "PHENOM MULTI-AGENT SWARM" in res_card["markdown_card"]


# ============================================================================
# 4. Master Safety Battery: 100-Cycle Guardian Kill Switch Benchmark (TELE-04)
# ============================================================================

def test_master_guardian_emergency_kill_switch_sla_benchmark():
    """100-cycle emergency halt benchmark verifying hard SLA < 25.0ms under task load."""
    scheduler = SwarmScheduler()
    latencies_ms: List[float] = []

    for cycle in range(100):
        # Reset scheduler state for benchmark cycle
        scheduler._is_halted = False
        scheduler._queue.clear()
        scheduler._history.clear()

        # Enqueue 10 mock tasks across agent roles
        for i in range(10):
            scheduler.enqueue_task(
                node_id=f"node_{cycle}_{i}",
                tool_name="validate_ast_syntax",
                arguments={"idx": i},
                assigned_role=AgentRole.CODER if i % 2 == 0 else AgentRole.SECURITY_AUDITOR,
            )

        # Trigger emergency halt and measure latency
        t_start = time.perf_counter()
        cancelled = scheduler.halt()
        elapsed_ms = (time.perf_counter() - t_start) * 1000.0

        latencies_ms.append(elapsed_ms)
        assert cancelled == 10
        assert len(scheduler.get_queue_status()) == 0
        assert all(t.status == SwarmTaskStatus.HALTED for t in scheduler.get_history())

    max_latency = max(latencies_ms)
    avg_latency = sum(latencies_ms) / len(latencies_ms)

    print(f"\n[BENCHMARK] Guardian Kill Switch (100 cycles): Max={max_latency:.3f}ms, Avg={avg_latency:.3f}ms")

    # Hard SLA Invariant: Max latency must be < 25.0 ms
    assert max_latency < 25.0, f"Max latency {max_latency:.2f}ms exceeded 25.0ms SLA"
    assert avg_latency < 5.0, f"Average latency {avg_latency:.2f}ms exceeded 5.0ms target"
