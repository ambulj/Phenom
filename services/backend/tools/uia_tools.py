"""
Deep Windows UIAutomation (UIA) Tools (RPA-01, SAF-01, SAF-02).
Registers Tier 0 and Tier 1 tools for inspecting accessibility trees,
invoking background patterns without focus stealing, and running self-healing workflows.
"""

from typing import Any, Dict, List, Optional

from services.backend.automation.deep_uia_engine import deep_uia_engine
from services.backend.safety.guardian import guardian
from services.backend.safety.registry import registry
from services.backend.schemas.deep_uia import (
    UIAExecuteWorkflowArgs,
    UIAFindElementArgs,
    UIAGetTreeArgs,
    UIAInvokeElementArgs,
    UIASetValueArgs,
    UIElementType,
    UIWorkflowStep,
)


# ==========================================
# Tier 0 Tools (Read-Only)
# ==========================================

@registry.register(
    name="uia_get_tree",
    tier=0,
    description="Inspects the native Windows UIAutomation accessibility tree for desktop windows (Read-Only)",
    args_schema=UIAGetTreeArgs,
    preview_fn=lambda a: "Inspect Windows UIAutomation accessibility tree hierarchy (Read-Only)",
)
def uia_get_tree(window_title: Optional[str] = None, max_depth: int = 3, **kwargs) -> Dict[str, Any]:
    """Inspect accessibility tree."""
    if guardian.is_halted:
        raise PermissionError("Guardian kill switch is active: UIA tree query blocked.")

    tree = deep_uia_engine.get_tree(window_title=window_title, max_depth=max_depth)
    return {
        "status": "success",
        "tree": tree.model_dump(),
    }


@registry.register(
    name="uia_find_element",
    tier=0,
    description="Finds a UI element in the accessibility tree with fuzzy matching support (Read-Only)",
    args_schema=UIAFindElementArgs,
    preview_fn=lambda a: f"Find UI element matching query '{a.get('name_query', '')}' (Read-Only)",
)
def uia_find_element(
    name_query: str,
    automation_id: Optional[str] = None,
    control_type: Optional[UIElementType] = None,
    fuzzy_threshold: float = 0.70,
    **kwargs,
) -> Dict[str, Any]:
    """Find element by name or automation_id with fuzzy fallback."""
    if guardian.is_halted:
        raise PermissionError("Guardian kill switch is active: element lookup blocked.")

    res = deep_uia_engine.find_element(
        name_query=name_query,
        automation_id=automation_id,
        control_type=control_type,
        fuzzy_threshold=fuzzy_threshold,
    )
    if not res:
        return {
            "status": "not_found",
            "message": f"Element matching query '{name_query}' not found.",
        }

    element, is_healed = res
    return {
        "status": "success",
        "element": element.model_dump(),
        "is_healed": is_healed,
    }


# ==========================================
# Tier 1 Tools (Reversible Changes with Preview)
# ==========================================

def _preview_invoke(args: Dict[str, Any]) -> str:
    elem_id = args.get("element_id", "")
    non_intrusive = args.get("non_intrusive", True)
    return f"Invoke UI element '{elem_id}' (non_intrusive: {non_intrusive}, zero cursor stealing)"


@registry.register(
    name="uia_invoke_element",
    tier=1,
    description="Invokes an element (InvokePattern) in the background without stealing foreground focus (Tier 1 Preview)",
    args_schema=UIAInvokeElementArgs,
    preview_fn=_preview_invoke,
)
def uia_invoke_element(element_id: str, non_intrusive: bool = True, **kwargs) -> Dict[str, Any]:
    """Invoke element via InvokePattern."""
    if guardian.is_halted:
        raise PermissionError("Guardian kill switch is active: element invocation blocked.")

    res = deep_uia_engine.invoke_element(element_id=element_id, non_intrusive=non_intrusive)
    return {
        "status": "success",
        "result": res,
    }


def _preview_set_value(args: Dict[str, Any]) -> str:
    elem_id = args.get("element_id", "")
    val = args.get("value", "")
    return f"Set value on UI element '{elem_id}' to '{val}' (ValuePattern)"


@registry.register(
    name="uia_set_value",
    tier=1,
    description="Sets text on an editable control without stealing user keyboard focus (Tier 1 Preview)",
    args_schema=UIASetValueArgs,
    preview_fn=_preview_set_value,
)
def uia_set_value(element_id: str, value: str, non_intrusive: bool = True, **kwargs) -> Dict[str, Any]:
    """Set value on element via ValuePattern."""
    if guardian.is_halted:
        raise PermissionError("Guardian kill switch is active: value pattern blocked.")

    res = deep_uia_engine.set_value(element_id=element_id, value=value, non_intrusive=non_intrusive)
    return {
        "status": "success",
        "result": res,
    }


def _preview_execute_workflow(args: Dict[str, Any]) -> str:
    steps = args.get("steps", [])
    auto_heal = args.get("auto_heal", True)
    return f"Execute {len(steps)}-step UIAutomation desktop workflow (auto_heal={auto_heal})"


@registry.register(
    name="uia_execute_workflow",
    tier=1,
    description="Executes a multi-step self-healing desktop workflow with verification checkpoints (Tier 1 Preview)",
    args_schema=UIAExecuteWorkflowArgs,
    preview_fn=_preview_execute_workflow,
)
def uia_execute_workflow(
    steps: List[UIWorkflowStep],
    auto_heal: bool = True,
    workflow_id: Optional[str] = None,
    **kwargs,
) -> Dict[str, Any]:
    """Execute desktop workflow."""
    if guardian.is_halted:
        raise PermissionError("Guardian kill switch is active: workflow execution blocked.")

    res = deep_uia_engine.execute_workflow(steps=steps, auto_heal=auto_heal, workflow_id=workflow_id)
    return {
        "status": "success" if res.is_success else "partial_failure",
        "workflow_result": res.model_dump(),
    }
