"""
Phenom Desktop Macro Tools
Provides multi-step GUI automation, mouse clicking, typing, and keyboard hotkeys.
Strictly conforms to SAFETY.md Tier 1 (Reversible UI automation) with immediate human takeover and Guardian halt.
"""

from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field
from services.backend.safety.registry import registry
from services.backend.automation.desktop_controller import desktop_controller


class ExecuteDesktopMacroArgs(BaseModel):
    steps: List[Dict[str, Any]] = Field(
        description="List of sequential step dictionaries. Example: [{'action': 'focus', 'target': 'Notepad'}, {'action': 'type', 'text': 'Hello'}]"
    )
    description: Optional[str] = Field(
        default="Execute multi-step desktop workflow",
        description="Human-readable explanation of what this workflow achieves"
    )


class ClickScreenArgs(BaseModel):
    x: Optional[int] = Field(default=None, description="Screen X coordinate")
    y: Optional[int] = Field(default=None, description="Screen Y coordinate")
    target_name: Optional[str] = Field(default=None, description="Name or label of UI element/button to click")
    clicks: int = Field(default=1, description="Number of clicks (1 for single, 2 for double click)")
    button: str = Field(default="left", description="Mouse button: 'left', 'right', or 'middle'")


class TypeKeyboardArgs(BaseModel):
    text: str = Field(description="Text characters to type into the active or target window")
    target: Optional[str] = Field(default=None, description="Target field description (must not be a password field)")


class PressKeyCombinationArgs(BaseModel):
    keys: List[str] = Field(description="List of keys to press together. Example: ['ctrl', 's'], ['enter'], ['alt', 'tab']")


@registry.register(
    name="execute_desktop_macro",
    tier=1,
    description="Executes a multi-step desktop macro (focus window, click, type text, press hotkeys) with live screen overlay and takeover pause.",
    args_schema=ExecuteDesktopMacroArgs,
    preview_fn=lambda a: f"Execute desktop macro ({len(a.get('steps', []))} steps): {a.get('description', 'Workflow')}"
)
async def execute_desktop_macro(steps: List[Dict[str, Any]], description: Optional[str] = None) -> Dict[str, Any]:
    """Runs a multi-step GUI automation plan with active safety gates."""
    step_results = await desktop_controller.execute_step_plan(steps)
    return {
        "status": "success",
        "description": description or "Desktop macro completed",
        "steps_executed": len(step_results),
        "details": step_results,
        "message": f"Successfully executed desktop macro ({len(step_results)} steps)."
    }


@registry.register(
    name="click_screen",
    tier=1,
    description="Clicks at specific screen coordinates (x, y) or finds and clicks a UI button by name/label.",
    args_schema=ClickScreenArgs,
    preview_fn=lambda a: f"Click {'at (' + str(a.get('x')) + ', ' + str(a.get('y')) + ')' if a.get('x') is not None else 'on ' + str(a.get('target_name'))} [{a.get('button', 'left')} click]"
)
async def click_screen(x: Optional[int] = None, y: Optional[int] = None, target_name: Optional[str] = None, clicks: int = 1, button: str = "left") -> Dict[str, Any]:
    """Clicks at coordinates or on a named target."""
    step = {"action": "click", "button": button, "clicks": clicks}
    if x is not None and y is not None:
        step["coords"] = (x, y)
    if target_name:
        step["target"] = target_name

    results = await desktop_controller.execute_step_plan([step])
    return {
        "status": "success",
        "clicked": True,
        "result": results[0] if results else {},
        "message": f"Clicked on {target_name or f'({x}, {y})'}."
    }


@registry.register(
    name="type_keyboard",
    tier=1,
    description="Types text into the currently active or specified input field (strictly prohibits passwords per SAFETY.md).",
    args_schema=TypeKeyboardArgs,
    preview_fn=lambda a: f"Type text: '{a.get('text', '')[:20]}' into '{a.get('target', 'focused window')}'"
)
async def type_keyboard(text: str, target: Optional[str] = None) -> Dict[str, Any]:
    """Types text characters with human-like intervals."""
    step = {"action": "type", "text": text, "target": target or ""}
    results = await desktop_controller.execute_step_plan([step])
    return {
        "status": "success",
        "typed_chars": len(text),
        "result": results[0] if results else {},
        "message": f"Typed {len(text)} characters into {target or 'active window'}."
    }


@registry.register(
    name="press_key_combination",
    tier=1,
    description="Presses a keyboard shortcut or key combination (e.g. ['ctrl', 's'], ['enter'], ['alt', 'f4']).",
    args_schema=PressKeyCombinationArgs,
    preview_fn=lambda a: f"Press key combination: {'+'.join(a.get('keys', []))}"
)
async def press_key_combination(keys: List[str]) -> Dict[str, Any]:
    """Presses key combination or single special key."""
    step = {"action": "hotkey", "keys": keys}
    results = await desktop_controller.execute_step_plan([step])
    return {
        "status": "success",
        "keys": keys,
        "result": results[0] if results else {},
        "message": f"Pressed key combination: {'+'.join(keys)}."
    }
