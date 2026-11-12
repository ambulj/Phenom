"""Phenom Predictive Resource Governor & Heterogeneous CUDA/RAM Dynamic Balancer Subsystem.

Provides host CPU/RAM/VRAM telemetry monitoring, composite load rating calculation,
adaptive subagent concurrency throttling, and memory headroom balancing (GOV-03, RES-02).
"""

from services.backend.governor.resource_governor import (
    ResourceGovernor,
    resource_governor,
    HostResourceTelemetry,
)
from services.backend.governor.adaptive_throttler import (
    AdaptiveThrottler,
    adaptive_throttler,
    ThrottleConfiguration,
    Rule8ViolationError,
)

__all__ = [
    "ResourceGovernor",
    "resource_governor",
    "HostResourceTelemetry",
    "AdaptiveThrottler",
    "adaptive_throttler",
    "ThrottleConfiguration",
    "Rule8ViolationError",
]
