"""Unit and Safety Integration Tests for Proactive Context-Aware Desktop Watchdog & Autonomous Task Interceptor.

Validates incident tracking, system health ratings, intervention card synthesis,
1-click remediation, soft dismissal (Rule 7), Rule 8 payment defenses, and Guardian SLA halt.
Phase 25-04 (DOG-01, INT-03, SAF-01, SAF-02).
"""

import time
import pytest

from services.backend.watchdog.desktop_watchdog import (
    DesktopWatchdog,
    WatchdogIncident,
    Rule8ViolationError as WatchdogR8,
    desktop_watchdog,
)
from services.backend.watchdog.proactive_task_interceptor import (
    ProactiveTaskInterceptor,
    ProactiveInterventionCard,
    Rule8ViolationError as InterceptorR8,
    proactive_task_interceptor,
)
from services.backend.safety.guardian import guardian
from services.backend.safety.registry import registry
import services.backend.tools.desktop_watchdog_tools  # Ensure tools are loaded


@pytest.fixture(autouse=True)
def reset_state():
    guardian.resume()
    yield
    guardian.resume()


def test_watchdog_incident_logging_and_health_scoring():
    """Verify watchdog logs incidents and calculates dynamic system health score."""
    watchdog = DesktopWatchdog()

    # Initial state should be healthy
    h0 = watchdog.get_system_health()
    assert h0["status"] == "HEALTHY"
    assert h0["health_score"] == 1.0

    # Record warning
    watchdog.record_incident(
        severity="WARNING",
        incident_type="BUILD_FAILURE",
        process_name="vite.exe",
        details="TypeScript compilation error in App.tsx",
    )
    h1 = watchdog.get_system_health()
    assert h1["status"] == "DEGRADED"
    assert h1["health_score"] < 1.0

    # Record critical
    inc_crit = watchdog.record_incident(
        severity="CRITICAL",
        incident_type="HUNG_PROCESS",
        process_name="Code.exe",
        details="Editor thread frozen for 15.2s",
    )
    h2 = watchdog.get_system_health()
    assert h2["status"] == "CRITICAL"
    assert h2["health_score"] <= 0.4

    # Resolve critical
    watchdog.resolve_incident(inc_crit.incident_id)
    h3 = watchdog.get_system_health()
    assert h3["status"] == "DEGRADED"


def test_proactive_task_interception_and_execution():
    """Verify task interceptor formulates 1-click remediation cards and executes fixes."""
    watchdog = DesktopWatchdog()
    interceptor = ProactiveTaskInterceptor(watchdog=watchdog)

    inc = watchdog.record_incident(
        severity="WARNING",
        incident_type="BUILD_FAILURE",
        process_name="pytest.exe",
        details="SyntaxError in module tests",
    )

    cards = interceptor.synthesize_interventions()
    assert len(cards) >= 1
    target_card = next(c for c in cards if c.incident_id == inc.incident_id)
    assert target_card.action_type == "APPLY_REPAIR_PATCH"
    assert "pytest.exe" in target_card.title

    # Execute remediation
    res = interceptor.execute_intervention(target_card.card_id)
    assert res["status"] == "REMEDIATED"
    assert res["action_executed"] == "APPLY_REPAIR_PATCH"

    # Incident should now be resolved in watchdog
    active_incidents = watchdog.get_active_incidents(unresolved_only=True)
    assert inc.incident_id not in [i.incident_id for i in active_incidents]


def test_soft_dismissal_rule_7():
    """Verify soft dismissal marks cards dismissed without destroying incident history."""
    watchdog = DesktopWatchdog()
    interceptor = ProactiveTaskInterceptor(watchdog=watchdog)

    inc = watchdog.record_incident(
        severity="INFO",
        incident_type="SYSTEM_ALERT",
        process_name="Notepad.exe",
        details="Unsaved backup buffer",
    )

    cards = interceptor.synthesize_interventions()
    card = next(c for c in cards if c.incident_id == inc.incident_id)

    # Soft dismiss
    dismissed = interceptor.dismiss_intervention(card.card_id)
    assert dismissed is True

    # Card is not returned in active cards
    active = interceptor.get_active_cards()
    assert card.card_id not in [c.card_id for c in active]

    # But incident still exists in watchdog logs
    all_incidents = watchdog.get_active_incidents(unresolved_only=False)
    assert inc.incident_id in [i.incident_id for i in all_incidents]


def test_rule_8_anti_checkout_enforcement():
    """Verify payment and checkout alerts are blocked with Rule8ViolationError."""
    watchdog = DesktopWatchdog()

    with pytest.raises(WatchdogR8, match="Rule 8"):
        watchdog.record_incident(
            severity="ERROR",
            incident_type="CRASH_DIALOG",
            process_name="checkout_service.exe",
            details="Crash during credit card payment processing",
        )

    with pytest.raises(WatchdogR8, match="Rule 8"):
        watchdog.record_incident(
            severity="WARNING",
            incident_type="SYSTEM_ALERT",
            process_name="browser.exe",
            details="Complete order and buy now popup",
        )


def test_guardian_kill_switch_sla_halt():
    """Verify Guardian kill switch synchronously interrupts watchdog operations in < 25.0ms SLA."""
    guardian.trigger("Emergency Watchdog Abort")
    assert guardian.is_halted

    t0 = time.perf_counter()
    with pytest.raises(PermissionError, match="Guardian kill switch"):
        desktop_watchdog.get_system_health()
    halt_duration_ms = (time.perf_counter() - t0) * 1000.0

    assert halt_duration_ms < 25.0, f"Halt latency {halt_duration_ms:.4f}ms exceeded 25.0ms SLA"

    with pytest.raises(PermissionError, match="Guardian kill switch"):
        proactive_task_interceptor.synthesize_interventions()

    guardian.resume()
    assert not guardian.is_halted


def test_tool_registry_and_previews():
    """Verify tool registration, tier classifications, and preview generations."""
    inspect_tool = registry.get("inspect_desktop_watchdog_events")
    assert inspect_tool is not None
    assert inspect_tool.tier == 0
    preview_inspect = inspect_tool.generate_preview({"unresolved_only": True})
    assert "watchdog incident" in preview_inspect

    resolve_tool = registry.get("resolve_proactive_alert")
    assert resolve_tool is not None
    assert resolve_tool.tier == 1
    preview_resolve = resolve_tool.generate_preview({"card_id": "card_01", "action": "EXECUTE"})
    assert "card_01" in preview_resolve

    config_tool = registry.get("configure_watchdog_policies")
    assert config_tool is not None
    assert config_tool.tier == 1
    preview_config = config_tool.generate_preview({"sensitivity_mode": "AGGRESSIVE"})
    assert "AGGRESSIVE" in preview_config
