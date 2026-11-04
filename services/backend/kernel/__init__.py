"""Milestone 13 Phase 4: Deep OS Telemetry, Self-Healing Kernel Fabric & Production Release.
Exports KernelTelemetryFabric and kernel_telemetry_fabric singleton.
"""

from services.backend.kernel.telemetry_listener import (
    KernelTelemetryFabric,
    kernel_telemetry_fabric,
)

__all__ = [
    "KernelTelemetryFabric",
    "kernel_telemetry_fabric",
]
