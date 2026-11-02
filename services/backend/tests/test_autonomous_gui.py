"""
Tests for Phenom Phase 3: Autonomous GUI Automation & Safety Interrupter
Verifies:
1. Tool registration & Tier 1 classification.
2. Multi-step macro progression (clicks, hotkeys, window focus).
3. Strict password typing prohibition.
4. Immediate Guardian kill switch halt.
5. Human-takeover interrupt & pause mechanism.
6. Visual target fallback to OCR.
"""

import pytest
from unittest.mock import patch, MagicMock
from services.backend.safety.registry import registry
from services.backend.safety.engine import safety_engine
from services.backend.safety.guardian import guardian
from services.backend.automation.desktop_controller import desktop_controller
from services.backend.automation.human_takeover import takeover_manager
import services.backend.tools.desktop_macro_tools


@pytest.fixture(autouse=True)
def reset_safety_states():
    """Ensure clean safety and takeover states before and after each test."""
    guardian.resume()
    takeover_manager.end_automation()
    yield
    guardian.resume()
    takeover_manager.end_automation()


def test_desktop_macro_tools_registered():
    macro_tools = ["execute_desktop_macro", "click_screen", "type_keyboard", "press_key_combination"]
    for t_name in macro_tools:
        tool_def = registry.get(t_name)
        assert tool_def is not None, f"Tool {t_name} must be registered"
        assert tool_def.tier == 1, f"Tool {t_name} must be Tier 1 (Reversible UI Automation)"


@pytest.mark.asyncio
async def test_execute_macro_progression():
    steps = [
        {"action": "focus", "target": "Desktop"},
        {"action": "click", "coords": (300, 400)},
        {"action": "hotkey", "keys": ["ctrl", "c"]}
    ]
    with patch("pyautogui.click") as mock_click, patch("pyautogui.hotkey") as mock_hotkey, patch.object(desktop_controller, "focus_window", return_value=True):
        res = await desktop_controller.execute_step_plan(steps)
        assert len(res) == 3
        assert res[0]["status"] == "done"
        assert res[1]["status"] == "done"
        assert res[2]["status"] == "done"
        assert mock_click.called
        assert mock_hotkey.called


@pytest.mark.asyncio
async def test_password_typing_prohibited():
    steps = [{"action": "type", "text": "secret123", "target": "password_input"}]
    with pytest.raises(PermissionError, match="Typing passwords is strictly prohibited"):
        await desktop_controller.execute_step_plan(steps)


@pytest.mark.asyncio
async def test_guardian_halt_stops_macro():
    guardian.trigger("test_halt")
    assert guardian.is_halted
    steps = [{"action": "click", "coords": (100, 100)}]
    with pytest.raises(RuntimeError, match="Automation immediately halted by Guardian kill switch"):
        await desktop_controller.execute_step_plan(steps)


@pytest.mark.asyncio
async def test_human_takeover_detection_pauses():
    takeover_manager.start_automation()
    assert not takeover_manager.is_paused
    # Trigger user physical movement
    takeover_manager._trigger_pause("test_mouse_move")
    assert takeover_manager.is_paused
    # Resuming clears pause
    takeover_manager.resolve_takeover("continue")
    assert not takeover_manager.is_paused


@pytest.mark.asyncio
async def test_visual_target_fallback_to_ocr():
    with patch("services.backend.vision.ocr_engine.ocr_engine.find_element_coordinates") as mock_find, patch("pyautogui.click") as mock_click:
        mock_find.return_value = {"x": 550, "y": 650, "bbox": [500, 630, 100, 40]}
        steps = [{"action": "click", "target": "UnlabeledSubmitButton"}]
        res = await desktop_controller.execute_step_plan(steps)
        assert len(res) == 1
        assert res[0]["status"] == "done"
        assert res[0]["result"] == "clicked_at_550_650"
        mock_click.assert_called_with(550, 650)


@pytest.mark.asyncio
async def test_tools_execute_via_safety_engine():
    async def mock_handler(*args, **kwargs):
        return ("approved", False)

    safety_engine.set_confirmation_handler(mock_handler)
    with patch("pyautogui.click"):
        res = await safety_engine.execute_tool("click_screen", {"x": 200, "y": 300})
        assert res["status"] == "success"
        assert res["result"]["status"] == "success"
