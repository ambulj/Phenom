"""Execution Telemetry Bus Tools for Phenom (Milestone 29 Phase 4).

Registers 3 execution telemetry tools in ToolRegistry:
1. record_execution_telemetry_event (Tier 1)
2. query_execution_telemetry_history (Tier 0)
3. get_active_telemetry_bus_stats (Tier 0)
"""

from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field

from services.backend.safety.registry import registry
from services.backend.telemetry.execution_telemetry_bus import (
    execution_telemetry_bus,
)


# ==========================================
# 1. Record Execution Telemetry Event (Tier 1)
# ==========================================

class RecordExecutionTelemetryEventArgs(BaseModel):
    tool_name: str = Field(..., description="Name of the executed tool.")
    status: str = Field(default="COMPLETED", description="Execution status: 'STARTED', 'COMPLETED', 'FAILED', or 'CANCELLED'.")
    duration_ms: float = Field(default=0.0, ge=0.0, description="Observed runtime latency in milliseconds.")
    tier: int = Field(default=0, ge=0, le=3, description="Risk tier of the executed tool.")
    arguments: Dict[str, Any] = Field(default_factory=dict, description="Execution arguments (credentials will be automatically scrubbed).")
    result_summary: Optional[str] = Field(default=None, description="Short human-readable result synopsis.")


def preview_record_execution_telemetry_event(args: Dict[str, Any]) -> str:
    tool_name = args.get("tool_name", "unknown")
    status = args.get("status", "COMPLETED")
    dur = args.get("duration_ms", 0.0)
    return f"Record telemetry event for '{tool_name}' ({status}, {dur:.2f}ms)."


@registry.register(
    name="record_execution_telemetry_event",
    tier=1,
    description="Buffers a background tool execution telemetry event into the circular in-memory telemetry ring buffer.",
    args_schema=RecordExecutionTelemetryEventArgs,
    preview_fn=preview_record_execution_telemetry_event,
    can_remember_per_folder=False,
)
def handle_record_execution_telemetry_event(
    tool_name: str,
    status: str = "COMPLETED",
    duration_ms: float = 0.0,
    tier: int = 0,
    arguments: Optional[Dict[str, Any]] = None,
    result_summary: Optional[str] = None,
) -> Dict[str, Any]:
    event = execution_telemetry_bus.record_event(
        tool_name=tool_name,
        status=status,
        duration_ms=duration_ms,
        tier=tier,
        args=arguments or {},
        result_summary=result_summary,
    )
    return event.model_dump()


# ==========================================
# 2. Query Execution Telemetry History (Tier 0)
# ==========================================

class QueryExecutionTelemetryHistoryArgs(BaseModel):
    tool_name: Optional[str] = Field(default=None, description="Optional tool name filter.")
    limit: int = Field(default=50, ge=1, le=200, description="Maximum number of recent telemetry events to retrieve.")


def preview_query_execution_telemetry_history(args: Dict[str, Any]) -> str:
    tool_name = args.get("tool_name")
    filter_str = f" for '{tool_name}'" if tool_name else ""
    return f"Query recent background tool execution telemetry events{filter_str}."


@registry.register(
    name="query_execution_telemetry_history",
    tier=0,
    description="Retrieves buffered background tool execution events, execution latencies, and scrubbed arguments.",
    args_schema=QueryExecutionTelemetryHistoryArgs,
    preview_fn=preview_query_execution_telemetry_history,
    can_remember_per_folder=False,
)
def handle_query_execution_telemetry_history(
    tool_name: Optional[str] = None,
    limit: int = 50,
) -> Dict[str, Any]:
    events = execution_telemetry_bus.query_history(tool_name=tool_name, limit=limit)
    return {
        "events": [e.model_dump() for e in events],
        "count": len(events),
    }


# ==========================================
# 3. Get Active Telemetry Bus Stats (Tier 0)
# ==========================================

class GetActiveTelemetryBusStatsArgs(BaseModel):
    pass


def preview_get_active_telemetry_bus_stats(args: Dict[str, Any]) -> str:
    return "Retrieve cumulative execution telemetry stats, averages, and tool call distribution."


@registry.register(
    name="get_active_telemetry_bus_stats",
    tier=0,
    description="Returns aggregate execution statistics, average latency, and tool invocation breakdown from the telemetry bus.",
    args_schema=GetActiveTelemetryBusStatsArgs,
    preview_fn=preview_get_active_telemetry_bus_stats,
    can_remember_per_folder=False,
)
def handle_get_active_telemetry_bus_stats() -> Dict[str, Any]:
    stats = execution_telemetry_bus.get_stats()
    return stats.model_dump()
