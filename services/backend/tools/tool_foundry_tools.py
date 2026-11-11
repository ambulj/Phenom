"""Dynamic Micro-Tool Synthesis & Sandbox Foundry Tools for Phenom (Milestone 32 Phase 3).

Registers 6 specialized tools in ToolRegistry:
1. synthesize_python_micro_tool (Tier 1)
2. validate_tool_ast_security (Tier 0)
3. test_micro_tool_in_sandbox (Tier 1)
4. hot_load_synthetic_micro_tool (Tier 1)
5. unload_synthetic_micro_tool (Tier 1)
6. list_synthetic_micro_tools (Tier 0)
"""

from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field

from services.backend.safety.registry import registry
from services.backend.evolution.tool_foundry import tool_foundry


# ==========================================
# 1. Synthesize Python Micro-Tool (Tier 1)
# ==========================================

class SynthesizeMicroToolArgs(BaseModel):
    name: str = Field(..., description="Tool name identifier (e.g. 'calculate_fibonacci' or 'parse_csv_header').")
    description: str = Field(..., description="Detailed description of tool capability and use case.")
    parameters: Dict[str, str] = Field(default_factory=dict, description="Dictionary mapping parameter names to Python types (e.g. {'n': 'int'}).")
    logic_body: str = Field(..., description="Indented Python function body returning a Dict[str, Any].")
    test_assertions: List[str] = Field(default_factory=list, description="List of assert statements validating tool output.")
    tier: int = Field(0, description="Risk tier: 0 for read-only computational, 1 for side-effect.")


def preview_synthesize_micro_tool(args: Dict[str, Any]) -> str:
    name = args.get("name", "tool")
    tier = args.get("tier", 0)
    return f"Synthesize Python micro-tool '{name}' (Tier {tier})"


@registry.register(
    name="synthesize_python_micro_tool",
    tier=1,
    description="Synthesizes typed Python micro-tool code, Pydantic args schema, preview function, and unit tests (Tier 1 staging).",
    args_schema=SynthesizeMicroToolArgs,
    preview_fn=preview_synthesize_micro_tool,
    can_remember_per_folder=False,
)
def handle_synthesize_python_micro_tool(
    name: str,
    description: str,
    parameters: Dict[str, str],
    logic_body: str,
    test_assertions: List[str],
    tier: int = 0,
) -> Dict[str, Any]:
    tool_def = tool_foundry.synthesize_tool(
        name=name,
        description=description,
        parameters=parameters,
        logic_body=logic_body,
        test_assertions=test_assertions,
        tier=tier,
    )
    return tool_def.model_dump()


# ==========================================
# 2. Validate Tool AST Security (Tier 0)
# ==========================================

class ValidateASTSecurityArgs(BaseModel):
    code: str = Field(..., description="Python source code to statically inspect.")


def preview_validate_ast_security(args: Dict[str, Any]) -> str:
    code = args.get("code", "")
    return f"Run static AST security analysis on code snippet ({len(code)} bytes)"


@registry.register(
    name="validate_tool_ast_security",
    tier=0,
    description="Statically inspects Python code for forbidden imports, dangerous builtins, and Rule 8 violations (Tier 0 read-only).",
    args_schema=ValidateASTSecurityArgs,
    preview_fn=preview_validate_ast_security,
    can_remember_per_folder=False,
)
def handle_validate_tool_ast_security(code: str) -> Dict[str, Any]:
    report = tool_foundry.validate_ast_security(code)
    return report.model_dump()


# ==========================================
# 3. Test Micro-Tool in Sandbox (Tier 1)
# ==========================================

class TestMicroToolInSandboxArgs(BaseModel):
    tool_id: str = Field(..., description="ID of the synthesized micro-tool to test.")


def preview_test_micro_tool_in_sandbox(args: Dict[str, Any]) -> str:
    t_id = args.get("tool_id", "")
    return f"Execute unit tests for synthetic tool '{t_id}' in isolated sandbox"


@registry.register(
    name="test_micro_tool_in_sandbox",
    tier=1,
    description="Runs synthesized tool code and unit test suite inside an isolated restricted sandbox (Tier 1 verification).",
    args_schema=TestMicroToolInSandboxArgs,
    preview_fn=preview_test_micro_tool_in_sandbox,
    can_remember_per_folder=False,
)
def handle_test_micro_tool_in_sandbox(tool_id: str) -> Dict[str, Any]:
    results = tool_foundry.test_in_sandbox(tool_id)
    return results


# ==========================================
# 4. Hot-Load Synthetic Micro-Tool (Tier 1)
# ==========================================

class HotLoadSyntheticToolArgs(BaseModel):
    tool_id: str = Field(..., description="ID of the verified synthetic tool to register.")


def preview_hot_load_synthetic_tool(args: Dict[str, Any]) -> str:
    t_id = args.get("tool_id", "")
    return f"Hot-load verified synthetic tool '{t_id}' into ToolRegistry"


@registry.register(
    name="hot_load_synthetic_micro_tool",
    tier=1,
    description="Dynamically registers a verified synthetic micro-tool into ToolRegistry for runtime dispatch (Tier 1 registration).",
    args_schema=HotLoadSyntheticToolArgs,
    preview_fn=preview_hot_load_synthetic_tool,
    can_remember_per_folder=False,
)
def handle_hot_load_synthetic_micro_tool(tool_id: str) -> Dict[str, Any]:
    load_res = tool_foundry.hot_load_tool(tool_id)
    return load_res


# ==========================================
# 5. Unload Synthetic Micro-Tool (Tier 1)
# ==========================================

class UnloadSyntheticToolArgs(BaseModel):
    name_or_id: str = Field(..., description="Name or ID of synthetic tool to unregister.")


def preview_unload_synthetic_tool(args: Dict[str, Any]) -> str:
    t = args.get("name_or_id", "")
    return f"Unload synthetic tool '{t}' from ToolRegistry"


@registry.register(
    name="unload_synthetic_micro_tool",
    tier=1,
    description="Unregisters a previously hot-loaded synthetic tool from ToolRegistry (Tier 1 unregistration).",
    args_schema=UnloadSyntheticToolArgs,
    preview_fn=preview_unload_synthetic_tool,
    can_remember_per_folder=False,
)
def handle_unload_synthetic_micro_tool(name_or_id: str) -> Dict[str, Any]:
    success = tool_foundry.unload_tool(name_or_id)
    return {"name_or_id": name_or_id, "unloaded": success}


# ==========================================
# 6. List Synthetic Micro-Tools (Tier 0)
# ==========================================

class ListSyntheticToolsArgs(BaseModel):
    pass


def preview_list_synthetic_tools(args: Dict[str, Any]) -> str:
    return "List all synthesized tools and their verification states"


@registry.register(
    name="list_synthetic_micro_tools",
    tier=0,
    description="Returns read-only inventory of synthesized micro-tools and their verification states (Tier 0 read-only).",
    args_schema=ListSyntheticToolsArgs,
    preview_fn=preview_list_synthetic_tools,
    can_remember_per_folder=False,
)
def handle_list_synthetic_micro_tools() -> List[Dict[str, Any]]:
    return tool_foundry.list_synthetic_tools()
