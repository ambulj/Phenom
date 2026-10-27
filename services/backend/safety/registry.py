"""
Phenom Tool Registry & Declaration
Safety Rule: No tool can be registered without a tier, a human-readable preview function,
and a valid Pydantic argument schema.
"""

from typing import Callable, Any, Dict, Optional, Type
from pydantic import BaseModel
from services.backend.schemas.protocol import RiskTier

class ToolDefinition:
    def __init__(
        self,
        name: str,
        tier: RiskTier,
        description: str,
        args_schema: Type[BaseModel],
        preview_fn: Callable[[Dict[str, Any]], str],
        handler_fn: Callable[..., Any],
        undo_fn: Optional[Callable[[Dict[str, Any], Any], Any]] = None,
        can_remember_per_folder: bool = False
    ):
        if tier not in (0, 1, 2, 3):
            raise ValueError(f"Invalid risk tier {tier}. Must be 0, 1, 2, or 3.")
        if not preview_fn or not callable(preview_fn):
            raise ValueError(f"Tool {name} must declare a callable preview function.")
        if not args_schema or not issubclass(args_schema, BaseModel):
            raise ValueError(f"Tool {name} must declare a Pydantic argument schema.")
            
        self.name = name
        self.tier = tier
        self.description = description
        self.args_schema = args_schema
        self.preview_fn = preview_fn
        self.handler_fn = handler_fn
        self.undo_fn = undo_fn
        self.can_remember_per_folder = can_remember_per_folder and (tier == 1)

    def generate_preview(self, args: Dict[str, Any]) -> str:
        return self.preview_fn(args)

class ToolRegistry:
    def __init__(self):
        self._tools: Dict[str, ToolDefinition] = {}

    def register(
        self,
        name: str,
        tier: RiskTier,
        description: str,
        args_schema: Type[BaseModel],
        preview_fn: Callable[[Dict[str, Any]], str],
        undo_fn: Optional[Callable[[Dict[str, Any], Any], Any]] = None,
        can_remember_per_folder: bool = False
    ):
        """Decorator to register a tool with strict safety contract."""
        def decorator(handler_fn: Callable[..., Any]):
            tool_def = ToolDefinition(
                name=name,
                tier=tier,
                description=description,
                args_schema=args_schema,
                preview_fn=preview_fn,
                handler_fn=handler_fn,
                undo_fn=undo_fn,
                can_remember_per_folder=can_remember_per_folder
            )
            self._tools[name] = tool_def
            return handler_fn
        return decorator

    def get(self, name: str) -> Optional[ToolDefinition]:
        return self._tools.get(name)

    def list_all(self) -> Dict[str, ToolDefinition]:
        return dict(self._tools)

    def get_tier(self, name: str) -> RiskTier:
        tool = self.get(name)
        if tool is None:
            # Unknown tools default to Tier 3 per SAFETY.md
            return 3
        return tool.tier

# Global Tool Registry
registry = ToolRegistry()
