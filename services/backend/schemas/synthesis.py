"""
Dynamic Runtime Tool Synthesis & Sandboxed Micro-Plugins Schemas.
Part of Phenom Milestone 11.0 Phase 1 (SYN-01, SAF-01, SAF-02).
"""

from typing import List, Dict, Any, Optional, Literal
from pydantic import BaseModel, Field

ToolCapability = Literal[
    "CAP_MATH",
    "CAP_DATA_TRANSFORM",
    "CAP_FILE_READ",
    "CAP_FILE_WRITE",
]


class ASTViolation(BaseModel):
    violation_type: str = Field(..., description="Type of violation, e.g. BANNED_BUILTIN, BANNED_MODULE, RULE_4_NETWORK, RULE_7_DELETE, RULE_8_PAYMENT, REFLECTION_ESCAPE")
    node_type: str = Field(..., description="AST node type where violation was detected, e.g. Call, Import, Attribute")
    line_number: int = Field(default=1, description="Line number of violation")
    description: str = Field(..., description="Human-readable explanation of why this construct is prohibited")
    offending_symbol: str = Field(..., description="Specific symbol or token that triggered the violation")


class ASTInspectionReport(BaseModel):
    is_safe: bool = Field(..., description="True if no safety violations were detected")
    violations: List[ASTViolation] = Field(default_factory=list, description="List of detected AST violations")
    risk_tier: int = Field(default=0, description="Inferred risk tier: 0 for pure computation/transform, 1 for file IO, 3 for dangerous")
    detected_capabilities: List[str] = Field(default_factory=list, description="Detected tool capabilities")
    imported_modules: List[str] = Field(default_factory=list, description="List of imported module names")
    analyzed_functions: List[str] = Field(default_factory=list, description="Names of analyzed top-level functions")


class ToolSynthesisRequest(BaseModel):
    tool_name: str = Field(..., description="Proposed identifier for the micro-tool")
    task_description: str = Field(..., description="Natural language specification of what the tool should do")
    parameter_specs: Dict[str, Any] = Field(default_factory=dict, description="Dictionary mapping parameter names to types or descriptions")
    return_type_spec: str = Field(default="Any", description="Expected return type")
    required_capabilities: List[str] = Field(default_factory=list, description="Capabilities explicitly requested")


class SynthesizedToolProposal(BaseModel):
    tool_name: str = Field(..., description="Normalized snake_case identifier")
    description: str = Field(..., description="Docstring and tool description")
    function_code: str = Field(..., description="Executable Python function code")
    schema_code: str = Field(..., description="Pydantic argument schema definition code")
    test_code: str = Field(..., description="Self-contained unit test assertions")
    declared_tier: int = Field(default=0, description="Assigned safety risk tier (0 or 1)")
    capabilities: List[str] = Field(default_factory=list, description="Associated capabilities")


class SandboxExecutionResult(BaseModel):
    success: bool = Field(..., description="True if execution finished with exit code 0 and valid output")
    output: Any = Field(default=None, description="Returned result from the function or test")
    stdout: str = Field(default="", description="Captured standard output")
    stderr: str = Field(default="", description="Captured standard error")
    duration_ms: float = Field(default=0.0, description="Subprocess execution duration in milliseconds")
    peak_memory_mb: float = Field(default=0.0, description="Peak RSS memory consumption in MB")
    timed_out: bool = Field(default=False, description="True if process exceeded the timeout limit")
    killed_by_guardian: bool = Field(default=False, description="True if process was halted by Guardian kill switch")
    killed_by_oom: bool = Field(default=False, description="True if process exceeded memory cap")
    error: Optional[str] = Field(default=None, description="Error message if execution failed")


class SynthesizedToolMetadata(BaseModel):
    tool_name: str = Field(..., description="Tool name registered in ToolRegistry")
    description: str = Field(..., description="Tool description")
    tier: int = Field(..., description="Assigned risk tier")
    capabilities: List[str] = Field(default_factory=list, description="Detected capabilities")
    created_at: str = Field(..., description="ISO 8601 creation timestamp")
    invocation_count: int = Field(default=0, description="Number of times executed")
    avg_duration_ms: float = Field(default=0.0, description="Average execution duration in ms")
    last_status: str = Field(default="registered", description="Status: registered, active, error, revoked")


class SynthesizeCustomToolArgs(BaseModel):
    tool_name: str = Field(..., description="Unique snake_case identifier for the micro-tool")
    task_description: str = Field(..., description="Detailed description of what the custom micro-tool must compute or perform")
    parameter_specs: Dict[str, Any] = Field(default_factory=dict, description="Dictionary of parameter names and type descriptions")
    expected_output_type: str = Field(default="Any", description="Expected return type or description of the output")


class RunSynthesizedToolArgs(BaseModel):
    tool_name: str = Field(..., description="Name of the synthesized tool to execute")
    arguments: Dict[str, Any] = Field(default_factory=dict, description="Arguments to pass to the tool function")


class ListSynthesizedToolsArgs(BaseModel):
    capability_filter: Optional[str] = Field(default=None, description="Optional capability filter: CAP_MATH, CAP_DATA_TRANSFORM, CAP_FILE_READ, CAP_FILE_WRITE")


class RevokeSynthesizedToolArgs(BaseModel):
    tool_name: str = Field(..., description="Name of the synthesized tool to revoke/unregister")
    reason: Optional[str] = Field(default=None, description="Optional reason for revocation")
