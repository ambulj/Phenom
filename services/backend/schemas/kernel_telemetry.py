"""
Kernel Telemetry & Autonomous Environment Self-Healing Schemas (KER-01, SAF-01, SAF-02).
Defines Pydantic v2 models for:
- Windows ETW process crash events and unhandled exceptions
- Deterministic self-healing remediation patches (pinned install, cache purge via send2trash, venv repair)
- Real-time kernel fabric telemetry and health monitoring
- Safety tool argument schemas for kernel diagnosis and remediation
"""

import time
from enum import Enum
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field, ConfigDict


class KernelCrashSeverity(str, Enum):
    INFO = "INFO"
    WARNING = "WARNING"
    CRITICAL = "CRITICAL"
    FATAL = "FATAL"


class CrashEventType(str, Enum):
    ETW_APPLICATION_CRASH = "ETW_APPLICATION_CRASH"
    UNHANDLED_EXCEPTION = "UNHANDLED_EXCEPTION"
    DEPENDENCY_MISSING = "DEPENDENCY_MISSING"
    ENVIRONMENT_CORRUPTION = "ENVIRONMENT_CORRUPTION"
    MEMORY_OVERFLOW = "MEMORY_OVERFLOW"


class SelfHealingActionType(str, Enum):
    INSTALL_PINNED_PACKAGE = "INSTALL_PINNED_PACKAGE"
    PURGE_CORRUPT_CACHE = "PURGE_CORRUPT_CACHE"
    RELOAD_VENV_MANIFEST = "RELOAD_VENV_MANIFEST"
    RESTART_SUBPROCESS_DAEMON = "RESTART_SUBPROCESS_DAEMON"


class SelfHealingRemediationPatch(BaseModel):
    """A deterministic, verifiable remediation patch for system or venv discrepancies."""
    model_config = ConfigDict(use_enum_values=True)

    patch_id: str = Field(..., description="Unique remediation patch identifier")
    action_type: SelfHealingActionType = Field(..., description="Type of healing action")
    target_entity: str = Field(..., description="Package name, cache folder, or service name")
    proposed_command: str = Field(..., description="Deterministic command to execute (no arbitrary shell injection)")
    requires_tier_1_confirmation: bool = Field(default=True, description="Enforces Rule 1 confirmation gate")
    is_applied: bool = Field(default=False, description="Whether the patch has been successfully applied")
    applied_at: Optional[float] = Field(default=None, description="Epoch timestamp when applied")
    result_message: Optional[str] = Field(default=None, description="Execution outcome or error summary")


class KernelCrashEvent(BaseModel):
    """Diagnosed kernel crash or unhandled system exception event."""
    model_config = ConfigDict(use_enum_values=True)

    event_id: str = Field(..., description="Unique crash event identifier")
    timestamp: float = Field(default_factory=time.time, description="Detection epoch timestamp")
    event_type: CrashEventType = Field(default=CrashEventType.UNHANDLED_EXCEPTION, description="Classification of crash")
    severity: KernelCrashSeverity = Field(default=KernelCrashSeverity.WARNING, description="Severity tier")
    process_name: str = Field(..., description="Name of the affected executable or module")
    pid: Optional[int] = Field(default=None, description="Process ID if available")
    exception_code: Optional[str] = Field(default=None, description="Hex exception code (e.g. 0xC0000005, ImportError)")
    stack_trace: str = Field(default="", description="Sanitized traceback (scrubbed of sensitive credentials)")
    root_cause_diagnosis: str = Field(default="", description="Inferred diagnosis explaining the breakdown")
    remediation_patch: Optional[SelfHealingRemediationPatch] = Field(default=None, description="Suggested self-healing patch")
    is_resolved: bool = Field(default=False, description="Whether the crash condition has been remediated")


class KernelFabricState(BaseModel):
    """Aggregated health and state of the deep kernel telemetry fabric."""
    model_config = ConfigDict(use_enum_values=True)

    is_monitoring: bool = Field(default=True, description="Whether ETW and exception listeners are active")
    total_crashes_diagnosed: int = Field(default=0, description="Total crashes detected across session")
    active_crashes: List[KernelCrashEvent] = Field(default_factory=list, description="Currently unresolved crashes")
    pending_patches: List[SelfHealingRemediationPatch] = Field(default_factory=list, description="Patches awaiting Tier 1 approval")
    remediation_success_rate: float = Field(default=1.0, ge=0.0, le=1.0, description="Successful patch ratio")
    last_scan_timestamp: float = Field(default_factory=time.time, description="Last venv/system health scan timestamp")


# ==========================================
# Tool Argument Schemas (SAF-01)
# ==========================================

class KernelGetTelemetryStatusArgs(BaseModel):
    """Arguments for querying kernel telemetry state and recent crashes (Tier 0)."""
    model_config = ConfigDict(extra="forbid")


class KernelDiagnoseCrashArgs(BaseModel):
    """Arguments for triaging a crash stack trace and generating a remediation patch (Tier 0)."""
    model_config = ConfigDict(extra="forbid")

    process_name: str = Field(..., min_length=1, max_length=100, description="Executable name (e.g. python.exe, uvicorn.exe)")
    exception_code: str = Field(..., min_length=1, max_length=50, description="Exception code or type (e.g. ModuleNotFoundError, 0xC0000005)")
    stack_trace: str = Field(default="", description="Error traceback string")


class KernelScanVenvDiscrepanciesArgs(BaseModel):
    """Arguments for scanning virtual environment packages against requirements (Tier 0)."""
    model_config = ConfigDict(extra="forbid")


class KernelApplyHealingPatchArgs(BaseModel):
    """Arguments for applying a deterministic self-healing remediation patch (Tier 1)."""
    model_config = ConfigDict(extra="forbid")

    patch_id: str = Field(..., min_length=1, max_length=64, description="ID of the validated remediation patch to execute")
