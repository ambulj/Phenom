"""
Phenom Ambient Vision & Resource Governor Schemas
Pydantic schemas for continuous ambient screen vision, copilot configuration,
and adaptive resource governance state.
"""

from typing import List, Optional
from pydantic import BaseModel, Field


class AmbientScreenContext(BaseModel):
    """
    Sanitized screen vision context captured in RAM.
    Zero disk storage; captures foreground window context, visual summary,
    detected error popups, and change delta.
    """
    timestamp: float = Field(..., description="UNIX epoch timestamp of the capture")
    window_title: str = Field(default="", description="Foreground window title")
    process_name: str = Field(default="", description="Foreground executable process name")
    is_sensitive: bool = Field(default=False, description="Whether any sensitive region was detected or masked")
    is_blacklisted: bool = Field(default=False, description="Whether foreground window is blacklisted (capture skipped)")
    scene_summary: str = Field(default="", description="High-level visual summary from local VLM or blackout notice")
    detected_errors: List[str] = Field(default_factory=list, description="Extracted error popups, tracebacks, or alerts")
    detected_text_snippets: List[str] = Field(default_factory=list, description="Prominent UI text or code snippets")
    delta_score: float = Field(default=0.0, description="Normalized perceptual difference from previous frame")
    has_changed: bool = Field(default=True, description="Whether screen change exceeded delta threshold")
    vlm_model: str = Field(default="moondream", description="Name of local VLM used for inference")
    inference_latency_ms: float = Field(default=0.0, description="Inference latency in milliseconds")
    is_suspended: bool = Field(default=False, description="Whether vision loop is currently paused by governor")
    suspension_reason: Optional[str] = Field(default=None, description="Reason for suspension (e.g. 3D gaming, high GPU load)")


class AmbientCopilotConfig(BaseModel):
    """
    Configuration parameters for AmbientVisionCopilot.
    """
    is_enabled: bool = Field(default=True, description="Whether continuous ambient vision loop is running")
    interval_seconds: float = Field(default=3.0, ge=1.0, le=60.0, description="Loop sampling interval in seconds")
    delta_threshold: float = Field(default=0.02, ge=0.001, le=1.0, description="Perceptual change threshold to trigger VLM (default 2%)")
    custom_blacklists: List[str] = Field(default_factory=list, description="User-specified regex patterns or titles to blacklist")


class ResourceGovernorState(BaseModel):
    """
    Performance and hardware load state emitted by AdaptiveResourceGovernor.
    """
    timestamp: float = Field(..., description="UNIX epoch timestamp of metric sampling")
    is_gaming: bool = Field(default=False, description="True if a 3D DirectX/Vulkan game is active")
    active_game: Optional[str] = Field(default=None, description="Executable name of active 3D game if detected")
    gpu_load_percent: float = Field(default=0.0, ge=0.0, le=100.0, description="Current GPU 3D engine utilization percentage")
    vram_used_mb: float = Field(default=0.0, ge=0.0, description="Current VRAM utilization in MB")
    cpu_load_percent: float = Field(default=0.0, ge=0.0, le=100.0, description="Current CPU utilization percentage")
    is_throttled: bool = Field(default=False, description="True if background workloads are throttled due to high load")
    throttling_reason: Optional[str] = Field(default=None, description="Detailed explanation if throttled or gaming")
    vision_suspended: bool = Field(default=False, description="True if ambient screen vision capture is currently suspended")
    swarms_suspended: bool = Field(default=False, description="True if background worker swarms are currently suspended")
