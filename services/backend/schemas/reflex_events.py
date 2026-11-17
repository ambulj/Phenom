"""Pydantic schemas for Neural Perception & Active Desktop Reflexes (Milestone 51 Phase 1).

Models:
- ReflexEventType and ReflexSeverity enums.
- VisualCueDetails and ToastNotificationDetails for raw perceptual telemetry.
- ReflexEvent: normalized event schema dispatched to reflex reaction engines.
- ReflexSentinelConfig and ReflexSentinelStatus for monitoring state.
"""

from __future__ import annotations

import time
import uuid
from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class ReflexEventType(str, Enum):
    """Types of reflex events recognized by desktop perception."""
    TERMINAL_COMPLETED = "TERMINAL_COMPLETED"
    BUILD_FAILED = "BUILD_FAILED"
    BUILD_SUCCEEDED = "BUILD_SUCCEEDED"
    TESTS_PASSED = "TESTS_PASSED"
    TESTS_FAILED = "TESTS_FAILED"
    TOAST_NOTIFICATION = "TOAST_NOTIFICATION"
    ERROR_DIALOG = "ERROR_DIALOG"
    IDLE_STATE = "IDLE_STATE"
    UNKNOWN = "UNKNOWN"


class ReflexSeverity(str, Enum):
    """Severity classification for prioritization and filtering."""
    INFO = "INFO"
    SUCCESS = "SUCCESS"
    WARNING = "WARNING"
    CRITICAL = "CRITICAL"


class VisualCueDetails(BaseModel):
    """Visual evidence captured by perceptual bounding-box diff hashing."""
    window_title: str = Field(default="", description="Foreground window title")
    process_name: str = Field(default="", description="Executable name (e.g. WindowsTerminal.exe, Code.exe)")
    bounding_box: Dict[str, int] = Field(default_factory=lambda: {"left": 0, "top": 0, "right": 0, "bottom": 0})
    perceptual_hash: str = Field(default="", description="Perceptual or difference hash of active region")
    matched_pattern: str = Field(default="", description="Regex or pattern that triggered identification")
    exit_code: Optional[int] = Field(default=None, description="Command exit code if parsed from terminal")
    raw_text: str = Field(default="", description="Extracted OCR or terminal buffer snippet")


class ToastNotificationDetails(BaseModel):
    """Details of captured system toast or notification."""
    app_name: str = Field(default="", description="Originating application name")
    title: str = Field(default="", description="Toast header / title")
    message: str = Field(default="", description="Notification body content")
    timestamp: float = Field(default_factory=time.time, description="Detection timestamp")
    urgency: str = Field(default="normal", description="Urgency: low, normal, critical")


class ReflexEvent(BaseModel):
    """Normalized reflex event dispatched through the perception bus."""
    event_id: str = Field(default_factory=lambda: f"refl_{uuid.uuid4().hex[:8]}")
    event_type: ReflexEventType = Field(default=ReflexEventType.UNKNOWN)
    severity: ReflexSeverity = Field(default=ReflexSeverity.INFO)
    source: str = Field(default="visual_sentinel", description="Source subsystem (visual_sentinel, notification_sentinel, etc.)")
    timestamp: float = Field(default_factory=time.time)
    confidence: float = Field(default=1.0, ge=0.0, le=1.0)
    visual_details: Optional[VisualCueDetails] = None
    toast_details: Optional[ToastNotificationDetails] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)

    @property
    def is_failure(self) -> bool:
        if self.severity == ReflexSeverity.CRITICAL:
            return True
        return self.event_type in (ReflexEventType.BUILD_FAILED, ReflexEventType.TESTS_FAILED, ReflexEventType.ERROR_DIALOG)

    @property
    def is_success(self) -> bool:
        if self.severity == ReflexSeverity.SUCCESS:
            return True
        return self.event_type in (ReflexEventType.BUILD_SUCCEEDED, ReflexEventType.TESTS_PASSED)


class ReflexSentinelConfig(BaseModel):
    """Configuration for low-latency visual and notification sentinels."""
    sample_rate_hz: float = Field(default=10.0, ge=1.0, le=30.0, description="Sampling rate in Hz")
    idle_sample_rate_hz: float = Field(default=2.0, ge=0.5, le=5.0, description="Sampling rate when idle")
    max_cpu_percent: float = Field(default=2.0, description="Max target CPU utilization budget")
    enable_visual_sentinel: bool = Field(default=True)
    enable_notification_sentinel: bool = Field(default=True)
    debounce_seconds: float = Field(default=3.0, description="Suppress repeated events of same type within window")


class ReflexSentinelStatus(BaseModel):
    """Current operational telemetry for reflex sentinels."""
    is_running: bool = False
    active_sample_rate_hz: float = 10.0
    recent_events_count: int = 0
    recent_events: List[ReflexEvent] = Field(default_factory=list)
    average_latency_ms: float = 0.0
    cpu_percent_estimate: float = 0.5
    last_event_timestamp: Optional[float] = None
