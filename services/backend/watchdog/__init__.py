"""Phenom Desktop Watchdog Subsystem (Milestone 25 Phase 4).

Proactive Context-Aware Desktop Watchdog & Autonomous Task Interceptor (DOG-01, INT-03).
"""

from services.backend.watchdog.desktop_watchdog import (
    WatchdogIncident,
    DesktopWatchdog,
    desktop_watchdog,
)
from services.backend.watchdog.proactive_task_interceptor import (
    ProactiveInterventionCard,
    ProactiveTaskInterceptor,
    proactive_task_interceptor,
)

__all__ = [
    "WatchdogIncident",
    "DesktopWatchdog",
    "desktop_watchdog",
    "ProactiveInterventionCard",
    "ProactiveTaskInterceptor",
    "proactive_task_interceptor",
]
