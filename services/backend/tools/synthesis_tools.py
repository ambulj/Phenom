"""
Dynamic Runtime Micro-Tool Synthesis Safety Tools (SAF-01).
Registers Tier 0 and Tier 1 management tools for dynamic synthesis,
sandboxed execution, listing, and revocation of bespoke micro-tools.
"""

from typing import Dict, Any, Optional
from pydantic import BaseModel, ConfigDict, create_model

from services.backend.safety.guardian import guardian
from services.backend.safety.registry import registry, ToolDefinition
from services.backend.coding.restricted_sandbox import restricted_sandbox
from services.backend.coding.dynamic_synthesizer import (
    dynamic_synthesizer,
    dynamic_synthesizer_manager,
    sanitize_schema_name,
)
from services.backend.schemas.synthesis import (
    ToolSynthesisRequest,
    SynthesizedToolProposal,
    SynthesizeCustomToolArgs,
    RunSynthesizedToolArgs,
    ListSynthesizedToolsArgs,
    RevokeSynthesizedToolArgs,
)


class _DynamicArgsBase(BaseModel):
    model_config = ConfigDict(extra="allow")


def hot_register_micro_tool(proposal: SynthesizedToolProposal) -> ToolDefinition:
    """
    Dynamically register a validated synthesized micro-tool proposal into the ToolRegistry.
    Enforces strict typing, Pydantic schema generation, preview rendering, and sandbox routing.
    """
    model_name = sanitize_schema_name(proposal.tool_name)
    dynamic_schema = create_model(model_name, __base__=_DynamicArgsBase)

    def dynamic_preview(args: Dict[str, Any]) -> str:
        return f"Execute sandboxed micro-tool '{proposal.tool_name}' with arguments: {args}"

    def dynamic_handler(**kwargs) -> Dict[str, Any]:
        if guardian.is_halted:
            raise PermissionError("Execution halted by Guardian kill switch.")

        res = restricted_sandbox.execute_function(
            func_code=proposal.function_code,
            func_name=proposal.tool_name,
            kwargs=kwargs,
        )
        dynamic_synthesizer_manager.record_execution(
            proposal.tool_name,
            duration_ms=res.duration_ms,
            success=res.success,
        )
        if not res.success:
            return {
                "success": False,
                "error": res.error or res.stderr or "Execution failed in sandbox",
                "duration_ms": res.duration_ms,
            }
        return {
            "success": True,
            "output": res.output,
            "duration_ms": res.duration_ms,
            "peak_memory_mb": res.peak_memory_mb,
        }

    tool_def = ToolDefinition(
        name=proposal.tool_name,
        tier=proposal.declared_tier,
        description=proposal.description,
        args_schema=dynamic_schema,
        preview_fn=dynamic_preview,
        handler_fn=dynamic_handler,
    )

    registry.register_tool_def(tool_def)
    dynamic_synthesizer_manager.register_synthesized_tool(proposal)
    return tool_def


# ==========================================
# Synthesis Management Tools (SAF-01)
# ==========================================

@registry.register(
    name="synthesize_custom_tool",
    tier=1,
    description="Synthesize, AST-inspect, test, and hot-register a bespoke Python micro-tool in the restricted sandbox (Tier 1 Reversible)",
    args_schema=SynthesizeCustomToolArgs,
    preview_fn=lambda a: (
        f"Synthesize, AST-inspect, and test custom micro-tool '{a.get('tool_name') if isinstance(a, dict) else getattr(a, 'tool_name', '')}' "
        f"for task: '{a.get('task_description') if isinstance(a, dict) else getattr(a, 'task_description', '')}'"
    ),
)
def synthesize_custom_tool(
    tool_name: str,
    task_description: str,
    parameter_specs: Optional[Dict[str, Any]] = None,
    expected_output_type: str = "Any",
    **kwargs,
) -> Dict[str, Any]:
    if guardian.is_halted:
        raise PermissionError("Tool synthesis halted by Guardian kill switch.")

    req = ToolSynthesisRequest(
        tool_name=tool_name,
        task_description=task_description,
        parameter_specs=parameter_specs or {},
        return_type_spec=expected_output_type,
    )

    proposal = dynamic_synthesizer.synthesize_and_verify(req)
    tool_def = hot_register_micro_tool(proposal)

    return {
        "success": True,
        "tool_name": proposal.tool_name,
        "tier": proposal.declared_tier,
        "capabilities": proposal.capabilities,
        "description": proposal.description,
        "message": f"Micro-tool '{proposal.tool_name}' successfully synthesized, AST-verified, sandbox-tested, and hot-registered in ToolRegistry.",
    }


@registry.register(
    name="run_synthesized_tool",
    tier=1,
    description="Execute an active synthesized micro-tool inside the restricted subprocess sandbox (Tier 1 Reversible)",
    args_schema=RunSynthesizedToolArgs,
    preview_fn=lambda a: (
        f"Execute sandboxed micro-tool '{a.get('tool_name') if isinstance(a, dict) else getattr(a, 'tool_name', '')}' with provided arguments"
    ),
)
def run_synthesized_tool(
    tool_name: str,
    arguments: Optional[Dict[str, Any]] = None,
    **kwargs,
) -> Dict[str, Any]:
    if guardian.is_halted:
        raise PermissionError("Tool execution halted by Guardian kill switch.")

    args = arguments or {}
    tool_def = registry.get(tool_name)
    if not tool_def:
        return {
            "success": False,
            "error": f"Tool '{tool_name}' is not registered in ToolRegistry.",
        }

    proposal = dynamic_synthesizer_manager.get_proposal(tool_name)
    if not proposal:
        # Fallback to direct tool handler if registered outside manager
        return tool_def.handler_fn(**args)

    res = restricted_sandbox.execute_function(
        func_code=proposal.function_code,
        func_name=proposal.tool_name,
        kwargs=args,
    )
    dynamic_synthesizer_manager.record_execution(
        proposal.tool_name,
        duration_ms=res.duration_ms,
        success=res.success,
    )

    if not res.success:
        return {
            "success": False,
            "error": res.error or res.stderr or "Sandboxed execution failed",
            "duration_ms": res.duration_ms,
            "peak_memory_mb": res.peak_memory_mb,
        }

    return {
        "success": True,
        "output": res.output,
        "duration_ms": res.duration_ms,
        "peak_memory_mb": res.peak_memory_mb,
    }


@registry.register(
    name="list_synthesized_tools",
    tier=0,
    description="List currently active synthesized micro-tools and their capabilities (Read-Only)",
    args_schema=ListSynthesizedToolsArgs,
    preview_fn=lambda a: "List currently active synthesized micro-tools (Read-Only)",
)
def list_synthesized_tools(
    capability_filter: Optional[str] = None,
    **kwargs,
) -> Dict[str, Any]:
    tools = dynamic_synthesizer_manager.list_tools(capability_filter=capability_filter)
    return {
        "success": True,
        "count": len(tools),
        "tools": [t.model_dump() for t in tools],
    }


@registry.register(
    name="revoke_synthesized_tool",
    tier=1,
    description="Revoke and unregister a synthesized micro-tool from ToolRegistry (Tier 1 Reversible)",
    args_schema=RevokeSynthesizedToolArgs,
    preview_fn=lambda a: (
        f"Revoke and unregister synthesized micro-tool '{a.get('tool_name') if isinstance(a, dict) else getattr(a, 'tool_name', '')}'"
    ),
)
def revoke_synthesized_tool(
    tool_name: str,
    reason: Optional[str] = None,
    **kwargs,
) -> Dict[str, Any]:
    if guardian.is_halted:
        raise PermissionError("Tool revocation halted by Guardian kill switch.")

    unregistered_registry = registry.unregister(tool_name)
    unregistered_manager = dynamic_synthesizer_manager.unregister_tool(tool_name)

    removed = unregistered_registry or unregistered_manager
    return {
        "success": removed,
        "tool_name": tool_name,
        "reason": reason,
        "message": f"Micro-tool '{tool_name}' was {'successfully revoked' if removed else 'not found'}.",
    }
