"""Unit & Integration Test Suite for Phase 49-05: CyberHUD 3D Knowledge Graph Visualizer & Telemetry.

Tests:
1. MemoryTelemetryHub live broadcasting, subscription lifecycles, and rolling ring buffer.
2. TelegramEpisodicCardFormatter markdown generation, ASCII topology, credential redacting, and button structures.
3. Registered tools (`broadcast_choreography_telemetry`, `generate_telegram_episodic_card`).
4. 100-cycle Guardian Emergency Kill Switch SLA benchmark (< 25.0ms).
"""

import time
import pytest
from typing import Dict, Any, List

from services.backend.safety.guardian import guardian
from services.backend.safety.registry import registry
from services.backend.memory.telemetry_hub import MemoryTelemetryHub, memory_telemetry_hub
from services.backend.remote.telegram_episodic_card import TelegramEpisodicCardFormatter, telegram_episodic_card
import services.backend.tools.choreography_telemetry_tools


@pytest.fixture(autouse=True)
def reset_guardian():
    """Ensure Guardian is running before and after each test."""
    guardian.resume()
    yield
    guardian.resume()


# ============================================================================
# 1. MemoryTelemetryHub Tests
# ============================================================================

def test_telemetry_hub_broadcast_and_subscription():
    hub = MemoryTelemetryHub(buffer_size=10)
    received: List[Dict[str, Any]] = []

    def subscriber(evt: Dict[str, Any]):
        received.append(evt)

    hub.subscribe(subscriber)

    evt1 = hub.broadcast(
        event_type="CHOREOGRAPHY_STEP",
        payload={"action": "MOVE_TO", "coords": [100, 200]},
    )
    assert evt1["event_type"] == "CHOREOGRAPHY_STEP"
    assert len(received) == 1
    assert received[0]["payload"]["action"] == "MOVE_TO"

    # Test unsubscribe
    hub.unsubscribe(subscriber)
    hub.broadcast(
        event_type="FOCUS_CHANGED",
        payload={"window": "Visual Studio Code"},
    )
    assert len(received) == 1  # No new received


def test_telemetry_hub_ring_buffer_fifo():
    hub = MemoryTelemetryHub(buffer_size=5)
    for i in range(12):
        hub.broadcast(event_type="STEP", payload={"index": i})

    events = hub.get_recent_events(limit=10)
    assert len(events) == 5
    # Ring buffer keeps most recent 5
    assert events[-1]["payload"]["index"] == 11
    assert events[0]["payload"]["index"] == 7


def test_telemetry_hub_filter_by_event_type():
    hub = MemoryTelemetryHub(buffer_size=20)
    hub.broadcast(event_type="TYPE_A", payload={"v": 1})
    hub.broadcast(event_type="TYPE_B", payload={"v": 2})
    hub.broadcast(event_type="TYPE_A", payload={"v": 3})

    filtered_a = hub.get_recent_events(event_type="TYPE_A")
    assert len(filtered_a) == 2
    assert [e["payload"]["v"] for e in filtered_a] == [1, 3]

    filtered_b = hub.get_recent_events(event_type="TYPE_B")
    assert len(filtered_b) == 1
    assert filtered_b[0]["payload"]["v"] == 2


# ============================================================================
# 2. Telegram Episodic Card Formatter Tests
# ============================================================================

def test_telegram_card_markdown_generation():
    formatter = TelegramEpisodicCardFormatter()
    card = formatter.format_card(
        episode_title="Milestone 49 Phase 5 Launch",
        summary="Engineered real-time telemetry matrix and CyberHUD visualizer.",
        active_entities=["CognitiveChoreographer", "BiTemporalEngine", "BezierMotor"],
        recent_heuristics=["sig_bezier_drift_heur", "sig_focus_mismatch_heur"],
        active_window="Visual Studio Code - Phenom",
    )

    assert "text" in card
    assert "reply_markup" in card
    text = card["text"]

    # Verify Markdown elements and ASCII topology
    assert "PHENOM KNOWLEDGE MATRIX & CHOREOGRAPHER" in text
    assert "Milestone 49 Phase 5 Launch" in text
    assert "Visual Studio Code - Phenom" in text
    assert "(IMPLEMENTS)" in text
    assert "(DEPENDS_ON)" in text
    assert "CognitiveChoreographer" in text
    assert "sig_bezier_drift_heur" in text

    # Verify buttons
    keyboard = card["reply_markup"]["inline_keyboard"]
    assert len(keyboard) == 1
    assert keyboard[0][0]["text"] == "🔄 Sync Obsidian Vault"
    assert keyboard[0][0]["callback_data"] == "/sync_obsidian_vault"
    assert keyboard[0][1]["text"] == "🛑 HALT GUARDIAN"
    assert keyboard[0][1]["callback_data"] == "/guardian_halt"


def test_telegram_card_sanitizes_credentials():
    formatter = TelegramEpisodicCardFormatter()
    dirty_summary = "Connected with api_key: AIzaSyD9876543210SecretToken and bearer token=secret_auth_token_xyz"
    card = formatter.format_card(
        episode_title="Secret Episode api_key: SuperSecret12345",
        summary=dirty_summary,
        active_entities=[],
        recent_heuristics=[],
    )

    text = card["text"]
    assert "AIzaSyD9876543210SecretToken" not in text
    assert "secret_auth_token_xyz" not in text
    assert "SuperSecret12345" not in text
    assert "[REDACTED]" in text


# ============================================================================
# 3. Tool Registrations & Handlers Tests
# ============================================================================

def test_broadcast_choreography_telemetry_tool():
    tool = registry.get("broadcast_choreography_telemetry")
    assert tool is not None
    assert tool.tier == 0

    preview = tool.preview_fn({"event_type": "TAKEOVER_TRIGGERED"})
    assert "TAKEOVER_TRIGGERED" in preview

    res = tool.handler_fn(
        event_type="TAKEOVER_TRIGGERED",
        payload={"displacement_px": 28.5},
    )
    assert res["status"] == "success"
    assert res["event_type"] == "TAKEOVER_TRIGGERED"
    assert "event_id" in res


def test_generate_telegram_episodic_card_tool():
    tool = registry.get("generate_telegram_episodic_card")
    assert tool is not None
    assert tool.tier == 0

    preview = tool.preview_fn({"episode_title": "Phase 49-05"})
    assert "Phase 49-05" in preview

    res = tool.handler_fn(
        episode_title="Phase 49-05 Telemetry Verified",
        summary="All systems nominal and verified.",
        active_entities=["EntityA", "EntityB"],
        recent_heuristics=["Heur1"],
        active_window="Phenom Electron",
    )
    assert res["status"] == "success"
    assert "card" in res
    assert "text" in res["card"]


# ============================================================================
# 4. Guardian Emergency Kill Switch SLA Benchmark (< 25.0ms)
# ============================================================================

def test_guardian_kill_switch_sla_benchmark():
    hub = MemoryTelemetryHub()
    formatter = TelegramEpisodicCardFormatter()

    latencies_ms: List[float] = []

    for _ in range(100):
        # 1. Normal state: passes
        guardian.resume()
        hub.broadcast(event_type="PING", payload={})

        # 2. Trip Guardian and benchmark abort latency
        t0 = time.perf_counter()
        guardian.trigger("Emergency Halt Test Triggered")

        # Telemetry Hub assert
        with pytest.raises(PermissionError, match="Guardian kill switch is active"):
            hub.broadcast(event_type="PONG", payload={})

        # Telegram Card assert
        with pytest.raises(PermissionError, match="Guardian kill switch is active"):
            formatter.format_card("Title", "Summary", [], [])

        dt_ms = (time.perf_counter() - t0) * 1000.0
        latencies_ms.append(dt_ms)

    avg_latency = sum(latencies_ms) / len(latencies_ms)
    max_latency = max(latencies_ms)

    print(f"\n[Guardian SLA Benchmark] 100 cycles: Mean = {avg_latency:.4f} ms, Max = {max_latency:.4f} ms")

    # Phenom Rule: SLA must be strictly under 25.0ms
    assert avg_latency < 25.0, f"Average Guardian halt latency {avg_latency:.2f}ms exceeded 25.0ms SLA"
    assert max_latency < 25.0, f"Max Guardian halt latency {max_latency:.2f}ms exceeded 25.0ms SLA"
