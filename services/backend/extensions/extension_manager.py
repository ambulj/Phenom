"""
Dynamic Extension Manager & In-Process Hot-Reloader (EXT-01, SAF-01, SAF-02).
Manages runtime compilation, ToolRegistry dynamic hot-registration,
and sub-10ms Guardian lockdown disengagement.
"""

import time
import uuid
from typing import Any, Callable, Dict, List, Optional, Tuple

from pydantic import BaseModel
from services.backend.extensions.ast_auditor import ASTSafetyAuditor
from services.backend.safety.registry import ToolDefinition, registry
from services.backend.schemas.extensions import (
    DynamicExtensionState,
    ExtensionMetadata,
    ExtensionStatus,
)


class DynamicExtensionManager:
    """Coordinates runtime micro-tool synthesis, AST safety validation, and hot-loading."""

    def __init__(self) -> None:
        self._auditor: ASTSafetyAuditor = ASTSafetyAuditor()
        self._extensions: Dict[str, ExtensionMetadata] = {}
        self._halted: bool = False
        self._change_callbacks: List[Callable[[DynamicExtensionState], None]] = []

    def register_change_callback(self, callback: Callable[[DynamicExtensionState], None]) -> None:
        """Register a subscriber callback for state updates."""
        self._change_callbacks.append(callback)

    def _notify(self) -> None:
        state = self.get_state()
        for cb in self._change_callbacks:
            try:
                cb(state)
            except Exception:
                pass

    def synthesize_extension(
        self,
        name: str,
        description: str,
        python_code: str,
        risk_tier: int = 1,
    ) -> Tuple[str, ExtensionMetadata]:
        """
        Validate, compile, and hot-load a Python micro-tool into ToolRegistry.
        """
        if self._halted:
            raise PermissionError("Guardian kill switch is active: extension synthesis blocked.")

        extension_id = f"ext-{uuid.uuid4().hex[:8]}"

        # 1. AST Safety Validation
        is_safe, violations = self._auditor.audit_code(python_code)
        if not is_safe:
            meta = ExtensionMetadata(
                extension_id=extension_id,
                name=name,
                description=description,
                risk_tier=risk_tier,
                code=python_code,
                ast_verified=False,
                status=ExtensionStatus.FAILED,
            )
            self._extensions[extension_id] = meta
            self._notify()
            raise ValueError(f"AST Safety Violation(s): {'; '.join(violations)}")

        # 2. In-Process Compilation in safe namespace
        safe_builtins = {
            "abs": abs,
            "all": all,
            "any": any,
            "bool": bool,
            "dict": dict,
            "enumerate": enumerate,
            "float": float,
            "int": int,
            "len": len,
            "list": list,
            "max": max,
            "min": min,
            "range": range,
            "round": round,
            "set": set,
            "str": str,
            "sum": sum,
            "tuple": tuple,
            "zip": zip,
        }
        exec_globals: Dict[str, Any] = {"__builtins__": safe_builtins}

        try:
            compiled = compile(python_code, f"<extension-{name}>", "exec")
            exec(compiled, exec_globals)
        except Exception as e:
            meta = ExtensionMetadata(
                extension_id=extension_id,
                name=name,
                description=description,
                risk_tier=risk_tier,
                code=python_code,
                ast_verified=True,
                status=ExtensionStatus.FAILED,
            )
            self._extensions[extension_id] = meta
            self._notify()
            raise RuntimeError(f"Compilation error for extension '{name}': {e}")

        # 3. Locate callable function
        func = exec_globals.get(name)
        if not callable(func):
            # Fallback: find any callable defined in exec_globals
            for k, v in exec_globals.items():
                if callable(v) and k != "__builtins__":
                    func = v
                    break

        if not callable(func):
            raise ValueError(f"No callable function named '{name}' found in synthesized code.")

        # 4. Hot-register into ToolRegistry
        class DynamicToolArgs(BaseModel):
            pass

        tool = ToolDefinition(
            name=name,
            tier=risk_tier,
            description=description,
            args_schema=DynamicToolArgs,
            preview_fn=lambda a: f"Execute dynamic extension '{name}' (Tier {risk_tier})",
            handler_fn=func,
        )
        registry._tools[name] = tool

        meta = ExtensionMetadata(
            extension_id=extension_id,
            name=name,
            description=description,
            risk_tier=risk_tier,
            code=python_code,
            ast_verified=True,
            status=ExtensionStatus.LOADED,
            loaded_at=time.time(),
            invocation_count=0,
        )
        self._extensions[extension_id] = meta
        self._notify()
        return extension_id, meta

    def unload_extension(self, extension_id: str) -> bool:
        """
        Unload an extension and cleanly deregister it from ToolRegistry.
        """
        meta = self._extensions.get(extension_id)
        if not meta:
            return False

        # Deregister from ToolRegistry
        if meta.name in registry._tools:
            del registry._tools[meta.name]

        meta.status = ExtensionStatus.UNLOADED
        self._notify()
        return True

    def hot_reload_extension(self, extension_id: str) -> ExtensionMetadata:
        """
        Recompile and hot-reload an existing extension.
        """
        meta = self._extensions.get(extension_id)
        if not meta:
            raise KeyError(f"Extension ID {extension_id} not found.")

        # Unload previous
        self.unload_extension(extension_id)

        # Re-synthesize
        _, new_meta = self.synthesize_extension(
            name=meta.name,
            description=meta.description,
            python_code=meta.code,
            risk_tier=meta.risk_tier,
        )
        return new_meta

    def get_state(self) -> DynamicExtensionState:
        """Return the current dynamic extension state."""
        loaded_count = sum(1 for m in self._extensions.values() if m.status == ExtensionStatus.LOADED)
        return DynamicExtensionState(
            loaded_extensions_count=loaded_count,
            extensions={k: v.model_copy() for k, v in self._extensions.items()},
            is_active=not self._halted,
        )

    # =========================================================================
    # Guardian Kill Switch Sub-10ms SLA Hooks
    # =========================================================================

    def halt(self) -> None:
        """
        Synchronously halt dynamic extensions.
        Immediately unregisters all dynamically synthesized tools from ToolRegistry.
        """
        self._halted = True

        # Unregister all loaded tools from registry
        for ext in list(self._extensions.values()):
            if ext.status == ExtensionStatus.LOADED:
                if ext.name in registry._tools:
                    del registry._tools[ext.name]
                ext.status = ExtensionStatus.UNLOADED

        self._notify()

    def resume(self) -> None:
        """Resume dynamic extension manager."""
        self._halted = False
        self._notify()

    def reset(self) -> None:
        """Alias for resume."""
        self.resume()
