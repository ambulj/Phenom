"""
Self-Synthesizing Extension Fabric Schemas.
Pydantic v2 schemas for runtime micro-tool synthesis, AST safety validation,
and in-process dynamic hot-reloading (EXT-01, SAF-01).
"""

from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class ExtensionStatus(str, Enum):
    DRAFT = "DRAFT"
    VALIDATED = "VALIDATED"
    LOADED = "LOADED"
    FAILED = "FAILED"
    QUARANTINED = "QUARANTINED"
    UNLOADED = "UNLOADED"


class ExtensionMetadata(BaseModel):
    extension_id: str = Field(..., description="Unique extension identifier")
    name: str = Field(..., description="Tool name registered in ToolRegistry")
    description: str = Field(..., description="Human-readable tool description")
    risk_tier: int = Field(1, ge=0, le=1, description="Safety tier (0 or 1)")
    code: str = Field(..., description="Python source code of the synthesized extension")
    ast_verified: bool = Field(False, description="Whether AST safety validation passed")
    status: ExtensionStatus = Field(ExtensionStatus.DRAFT, description="Current lifecycle state")
    loaded_at: Optional[float] = Field(None, description="UNIX timestamp when hot-loaded")
    invocation_count: int = Field(0, ge=0, description="Number of times invoked")


class DynamicExtensionState(BaseModel):
    loaded_extensions_count: int = Field(0, ge=0, description="Number of active dynamic extensions")
    extensions: Dict[str, ExtensionMetadata] = Field(default_factory=dict, description="Managed extensions")
    is_active: bool = Field(True, description="Whether dynamic extension synthesis is active")


# =============================================================================
# Tool Argument Models
# =============================================================================

class ExtensionGetStatusArgs(BaseModel):
    """Arguments for querying dynamic extension manager state."""
    pass


class ExtensionSynthesizeArgs(BaseModel):
    """Arguments for synthesizing and hot-loading a Python micro-tool."""
    name: str = Field(..., description="Unique tool name (snake_case)")
    description: str = Field(..., description="Tool functionality description")
    python_code: str = Field(..., description="Self-contained Python function implementation")
    risk_tier: int = Field(1, ge=0, le=1, description="Safety tier: 0 (read-only) or 1 (reversible state change)")


class ExtensionHotReloadArgs(BaseModel):
    """Arguments for recompiling and hot-reloading an existing extension."""
    extension_id: str = Field(..., description="Extension ID to reload")


class ExtensionUnloadArgs(BaseModel):
    """Arguments for cleanly unloading an extension and unregistering it from ToolRegistry."""
    extension_id: str = Field(..., description="Extension ID to unload")
