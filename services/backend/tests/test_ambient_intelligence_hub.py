"""
Tests for Proactive Ambient Intelligence Daemon & Context-Aware Notification Hub.
Part of Phenom 22.0 Sovereign Swarm Intelligence (AMB-02, NOT-02, SAF-01, SAF-02).
"""

import time
import pytest
from typing import Dict, Any

from services.backend.ambient.ambient_intelligence_daemon import (
    AmbientIntelligenceDaemon,
    AmbientAlertItem,
    ambient_daemon,
)
from services.backend.ambient.notification_priority_hub import (
    NotificationPriorityHub,
    priority_hub,
)
from services.backend.safety.guardian import guardian
from services.backend.safety.registry import registry
import services.backend.tools.ambient_intelligence_tools as ambient_tools


@pytest.fixture(autouse=True)
def reset_guardian():
    guardian.resume()
    yield
    guardian.resume()


def test_ambient_alert_addition_and_urgency_ordering():
    """Verify ambient alert creation and sorted urgency retrieval."""
    daemon = AmbientIntelligenceDaemon()
    a1 = daemon.add_alert(title="Low Warning", summary="Low", urgency=0.2)
    a2 = daemon.add_alert(title="High Warning", summary="High", urgency=0.9)
    a3 = daemon.add_alert(title="Medium Warning", summary="Medium", urgency=0.5)

    active = daemon.get_active_alerts(min_urgency=0.0)
    assert len(active) >= 3

    # Check top alert is the highest urgency
    assert active[0].urgency >= active[1].urgency >= active[2].urgency
    assert any(a.alert_id == a2.alert_id for a in active[:2])


def test_soft_dismissal_rule_7_non_destructibility():
    """Verify Rule 7: dismissing an alert soft-marks it without deleting historical record."""
    daemon = AmbientIntelligenceDaemon()
    alert = daemon.add_alert(title="Dismissible Alert", summary="Testing soft dismissal", urgency=0.4)

    assert alert.is_dismissed is False
    assert alert.dismissed_at is None

    dismissed = daemon.dismiss_alert(alert.alert_id)
    assert dismissed is True
    assert alert.is_dismissed is True
    assert alert.dismissed_at is not None

    # Alert should no longer appear in get_active_alerts()
    active_ids = [a.alert_id for a in daemon.get_active_alerts()]
    assert alert.alert_id not in active_ids


def test_focus_mode_filtering_and_suppression():
    """Verify notification priority hub suppresses low-priority alerts in deep focus mode."""
    hub = NotificationPriorityHub()

    # 1. Balanced mode (0.40)
    hub.set_mode("balanced")
    assert hub.get_effective_threshold() == 0.40

    low_alert = AmbientAlertItem(alert_id="a_low", title="Low", summary="...", urgency=0.30)
    high_alert = AmbientAlertItem(alert_id="a_high", title="High", summary="...", urgency=0.85)

    eval_low = hub.evaluate_delivery(low_alert)
    eval_high = hub.evaluate_delivery(high_alert)

    assert eval_low["delivered"] is False
    assert eval_high["delivered"] is True

    # 2. Deep Focus mode (0.75)
    hub.set_mode("deep_focus")
    assert hub.get_effective_threshold() == 0.75

    med_alert = AmbientAlertItem(alert_id="a_med", title="Med", summary="...", urgency=0.60)
    assert hub.evaluate_delivery(med_alert)["delivered"] is False
    assert hub.evaluate_delivery(high_alert)["delivered"] is True

    # 3. Ambient mode (0.00)
    hub.set_mode("ambient")
    assert hub.get_effective_threshold() == 0.00
    assert hub.evaluate_delivery(low_alert)["delivered"] is True


def test_proactive_briefing_synthesis():
    """Verify natural-language proactive briefing generation with count metrics."""
    daemon = AmbientIntelligenceDaemon()
    daemon.add_alert(title="GPU Test", summary="GPU OK", urgency=0.3)
    daemon.add_alert(title="Security Event", summary="Sandbox check", urgency=0.85)

    briefing = daemon.synthesize_proactive_briefing()
    assert "Phenom Ambient Status" in briefing["briefing"]
    assert briefing["total_active"] >= 2
    assert briefing["critical_count"] >= 1
    assert len(briefing["top_alerts"]) >= 1


def test_guardian_kill_switch_sla_halt():
    """Guardian trigger must synchronously interrupt ambient intelligence in < 25.0ms SLA."""
    guardian.trigger()
    t0 = time.perf_counter()
    with pytest.raises(PermissionError, match="Guardian kill switch"):
        ambient_daemon.get_active_alerts()
    latency_ms = (time.perf_counter() - t0) * 1000.0

    assert latency_ms < 25.0, f"Guardian SLA exceeded: {latency_ms:.4f}ms >= 25.0ms"


def test_tool_registry_and_previews():
    """Verify tool registration and preview generator functions in ToolRegistry."""
    tool_names = [
        "get_ambient_intelligence_feed",
        "configure_notification_filter",
        "dismiss_ambient_alert",
        "synthesize_proactive_briefing",
    ]
    for name in tool_names:
        tool = registry.get(name)
        assert tool is not None, f"Tool {name} is not registered in ToolRegistry"
        assert callable(tool.handler_fn)

    # Preview generators
    preview_feed = registry.get("get_ambient_intelligence_feed").generate_preview({"min_urgency": 0.5})
    assert "min urgency 0.5" in preview_feed

    preview_config = registry.get("configure_notification_filter").generate_preview({"mode": "deep_focus"})
    assert "deep_focus" in preview_config

    preview_brief = registry.get("synthesize_proactive_briefing").generate_preview({})
    assert "conversational overview" in preview_brief.lower()
