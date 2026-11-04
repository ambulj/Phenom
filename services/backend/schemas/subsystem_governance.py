from enum import Enum
from typing import Dict, List, Optional
from pydantic import BaseModel, Field


class CircuitBreakerStatus(str, Enum):
    NORMAL = "normal"
    DEGRADED = "degraded"
    TRIPPED = "tripped"
    HEALING = "healing"


class RemediationActionType(str, Enum):
    RECYCLE_WORKER = "recycle_worker"
    FLUSH_STALE_BUFFERS = "flush_stale_buffers"
    TRIM_GPU_CACHE = "trim_gpu_cache"
    RESET_CIRCUIT_BREAKER = "reset_circuit_breaker"


class SubsystemTelemetry(BaseModel):
    subsystem_name: str
    health_score: float = Field(..., ge=0.0, le=1.0)
    circuit_status: CircuitBreakerStatus
    memory_mb: float = Field(..., ge=0.0)
    vram_mb: float = Field(..., ge=0.0)
    last_heartbeat: float
    error_count: int = Field(0, ge=0)


class RemediationResult(BaseModel):
    remediation_id: str
    subsystem_name: str
    action_type: RemediationActionType
    success: bool
    message: str
    timestamp: float


class GovernanceWatchdogState(BaseModel):
    is_active: bool
    subsystems: Dict[str, SubsystemTelemetry]
    overall_health: float = Field(..., ge=0.0, le=1.0)
    active_anomalies: List[str] = []
    recent_remediations: List[RemediationResult] = []


class SubsystemGetHealthArgs(BaseModel):
    subsystem_name: Optional[str] = Field(None, description="Optional specific subsystem name to filter")


class SubsystemTriggerRemediationArgs(BaseModel):
    subsystem_name: str = Field(..., description="Target subsystem to remediate")
    action_type: RemediationActionType = Field(..., description="Remediation action to execute")


class SubsystemResetCircuitBreakerArgs(BaseModel):
    subsystem_name: str = Field(..., description="Target subsystem circuit breaker to reset to NORMAL")


class SubsystemConfigureThresholdsArgs(BaseModel):
    max_error_count: Optional[int] = Field(None, ge=1, le=100, description="Max consecutive errors before tripping breaker")
    max_memory_mb: Optional[float] = Field(None, ge=50.0, le=32768.0, description="Max memory threshold in MB")
    max_vram_mb: Optional[float] = Field(None, ge=50.0, le=24576.0, description="Max VRAM threshold in MB")
