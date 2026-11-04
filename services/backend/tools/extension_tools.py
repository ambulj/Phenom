"""
Self-Synthesizing Extension Tools (EXT-01, SAF-01, SAF-02).
Registers Tier 0 and Tier 1 tools for inspecting, synthesizing, hot-reloading,
and unloading dynamic micro-extensions.
"""

from typing import Any, Dict, Optional

from services.backend.extensions import dynamic_extension_manager
from services.backend.safety.guardian import guardian
from services.backend.safety.registry import registry
from services.backend.schemas.extensions import (
    ExtensionGetStatusArgs,
    ExtensionHotReloadArgs,
    ExtensionSynthesizeArgs,
    ExtensionUnloadArgs,
)


# ==========================================
# Tier 0 Tools (Read-Only)
# ==========================================

@registry.register(
    name="extension_get_status",
    tier=0,
    description="Inspects active dynamically synthesized extensions, status, and AST metrics (Read-Only)",
    args_schema=ExtensionGetStatusArgs,
    preview_fn=lambda a: "Inspect dynamic extension state and loaded micro-tools (Read-Only)",
)
def extension_get_status(**kwargs) -> Dict[str, Any]:
    """Inspect dynamic extension state."""
    state = dynamic_extension_manager.get_state()
    return {
        "status": "success",
        "extension_state": state.model_dump(),
    }


# ==========================================
# Tier 1 Tools (Reversible Changes with Preview)
# ==========================================

def _preview_synthesize(args: Dict[str, Any]) -> str:
    name = args.get("name", "tool")
    desc = args.get("description", "")
    tier = args.get("risk_tier", 1)
    return f"Synthesize and hot-load Python micro-tool '{name}' (Tier {tier}): {desc}"


@registry.register(
    name="extension_synthesize",
    tier=1,
    description="Synthesizes, AST-audits, compiles, and hot-registers a Python micro-tool into ToolRegistry (Tier 1 Preview)",
    args_schema=ExtensionSynthesizeArgs,
    preview_fn=_preview_synthesize,
)
def extension_synthesize(
    name: str,
    description: str,
    python_code: str,
    risk_tier: int = 1,
    **kwargs,
) -> Dict[str, Any]:
    """Synthesize and hot-register dynamic tool."""
    if guardian.is_halted:
        raise PermissionError("Guardian kill switch is active: extension synthesis blocked.")

    ext_id, meta = dynamic_extension_manager.synthesize_extension(
        name=name,
        description=description,
        python_code=python_code,
        risk_tier=risk_tier,
    )
    return {
        "status": "success",
        "action": "synthesize",
        "extension_id": ext_id,
        "metadata": meta.model_dump(),
    }


def _preview_hot_reload(args: Dict[str, Any]) -> str:
    ext_id = args.get("extension_id", "")
    return f"Recompile and hot-reload dynamic extension '{ext_id}' in-process"


@registry.register(
    name="extension_hot_reload",
    tier=1,
    description="Recompiles and hot-reloads an active dynamic extension without server restart (Tier 1 Preview)",
    args_schema=ExtensionHotReloadArgs,
    preview_fn=_preview_hot_reload,
)
def extension_hot_reload(extension_id: str, **kwargs) -> Dict[str, Any]:
    """Hot-reload dynamic extension."""
    if guardian.is_halted:
        raise PermissionError("Guardian kill switch is active: extension reloading blocked.")

    meta = dynamic_extension_manager.hot_reload_extension(extension_id=extension_id)
    return {
        "status": "success",
        "action": "hot_reload",
        "extension_id": extension_id,
        "metadata": meta.model_dump(),
    }


def _preview_unload(args: Dict[str, Any]) -> str:
    ext_id = args.get("extension_id", "")
    return f"Unload dynamic extension '{ext_id}' and unregister tool from ToolRegistry"


@registry.register(
    name="extension_unload",
    tier=1,
    description="Unloads a dynamic extension and deregisters it cleanly from ToolRegistry (Tier 1 Preview)",
    args_schema=ExtensionUnloadArgs,
    preview_fn=_preview_unload,
)
def extension_unload(extension_id: str, **kwargs) -> Dict[str, Any]:
    """Unload dynamic extension."""
    if guardian.is_halted:
        raise PermissionError("Guardian kill switch is active: extension unloading blocked.")

    unloaded = dynamic_extension_manager.unload_extension(extension_id=extension_id)
    return {
        "status": "success",
        "action": "unload",
        "extension_id": extension_id,
        "unloaded": unloaded,
    }
