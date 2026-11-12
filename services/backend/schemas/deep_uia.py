"""
Deep Windows UIAutomation (UIA) & Self-Healing Workflow Schemas.
Pydantic v2 schemas for non-intrusive accessibility tree inspection,
background pattern invocation, and fuzzy self-healing workflows (RPA-01).
"""

from enum import Enum
from typing import Any, Dict, List, Optional, Tuple
from pydantic import BaseModel, Field


class UIElementType(str, Enum):
    BUTTON = "BUTTON"
    EDIT = "EDIT"
    TEXT = "TEXT"
    WINDOW = "WINDOW"
    MENU_ITEM = "MENU_ITEM"
    CHECKBOX = "CHECKBOX"
    COMBOBOX = "COMBOBOX"
    TREE_ITEM = "TREE_ITEM"
    TAB_ITEM = "TAB_ITEM"
    UNKNOWN = "UNKNOWN"


class UIPatternType(str, Enum):
    INVOKE = "INVOKE"
    VALUE = "VALUE"
    TOGGLE = "TOGGLE"
    SELECTION = "SELECTION"
    EXPAND_COLLAPSE = "EXPAND_COLLAPSE"
    SCROLL = "SCROLL"


class UIElementNode(BaseModel):
    element_id: str = Field(..., description="Unique in-memory element reference ID")
    name: str = Field("", description="Accessible element name or label")
    automation_id: str = Field("", description="Windows UIAutomation AutomationId")
    control_type: UIElementType = Field(UIElementType.UNKNOWN, description="Classified control type")
    bounding_rect: Tuple[int, int, int, int] = Field(
        (0, 0, 0, 0), description="Bounding rectangle: (left, top, width, height)"
    )
    supported_patterns: List[UIPatternType] = Field(default_factory=list, description="Available UIA patterns")
    is_enabled: bool = Field(True, description="Whether control is enabled and interactive")
    is_offscreen: bool = Field(False, description="Whether control is scrolled off-screen")
    is_password: bool = Field(False, description="Whether control is a password or PIN field (Rule 8/11)")
    value: Optional[str] = Field(None, description="Current value if ValuePattern supported")
    children: List["UIElementNode"] = Field(default_factory=list, description="Child accessibility elements")


class UIWorkflowStep(BaseModel):
    step_id: str = Field(..., description="Step sequence identifier")
    action_type: str = Field(..., description="Action: 'CLICK', 'SET_VALUE', 'SELECT', 'EXPAND'")
    target_query: str = Field(..., description="Target name or automation_id query")
    control_type: Optional[UIElementType] = Field(None, description="Optional expected control type filter")
    value_payload: Optional[str] = Field(None, description="Input text value for SET_VALUE")
    verification_expected: Optional[str] = Field(None, description="Expected text or state post-action")
    status: str = Field("PENDING", description="Step status: PENDING, EXECUTING, VERIFIED, HEALED, FAILED")
    healing_applied: bool = Field(False, description="Whether fuzzy self-healing resolution was utilized")


class UIWorkflowExecutionResult(BaseModel):
    workflow_id: str = Field(..., description="Workflow execution identifier")
    total_steps: int = Field(0, description="Total planned steps")
    successful_steps: int = Field(0, description="Successfully completed and verified steps")
    healed_steps: int = Field(0, description="Steps recovered via fuzzy self-healing")
    is_success: bool = Field(False, description="Whether all steps succeeded")
    elapsed_ms: float = Field(0.0, description="Execution time in milliseconds")
    log: List[str] = Field(default_factory=list, description="Execution telemetry log")


# =============================================================================
# Tool Argument Models
# =============================================================================

class UIAGetTreeArgs(BaseModel):
    """Arguments for querying the native accessibility tree of a window."""
    window_title: Optional[str] = Field(None, description="Optional window title filter (substring)")
    max_depth: int = Field(3, ge=1, le=10, description="Maximum tree traversal depth")


class UIAFindElementArgs(BaseModel):
    """Arguments for finding elements by name, automation_id, or fuzzy similarity."""
    name_query: str = Field(..., description="Element name or text label to match")
    automation_id: Optional[str] = Field(None, description="Exact or partial AutomationId")
    control_type: Optional[UIElementType] = Field(None, description="Expected control type")
    fuzzy_threshold: float = Field(0.70, ge=0.5, le=1.0, description="Fuzzy matching confidence threshold")


class UIAInvokeElementArgs(BaseModel):
    """Arguments for non-intrusive background element invocation (InvokePattern)."""
    element_id: str = Field(..., description="Target element ID")
    non_intrusive: bool = Field(True, description="Strictly preserve foreground focus (no mouse cursor movement)")


class UIASetValueArgs(BaseModel):
    """Arguments for non-intrusive background text input (ValuePattern)."""
    element_id: str = Field(..., description="Target element ID")
    value: str = Field(..., description="Text value to set")
    non_intrusive: bool = Field(True, description="Strictly preserve foreground focus")


class UIAExecuteWorkflowArgs(BaseModel):
    """Arguments for executing a multi-step self-healing desktop workflow."""
    workflow_id: Optional[str] = Field(None, description="Optional workflow ID")
    steps: List[UIWorkflowStep] = Field(..., description="List of sequential workflow steps")
    auto_heal: bool = Field(True, description="Enable fuzzy matching self-healing if exact match fails")
