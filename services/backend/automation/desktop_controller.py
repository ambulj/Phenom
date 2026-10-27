"""
Phenom Desktop Controller
Handles:
1. In-memory screenshot capture (mss), strictly retained in RAM.
2. Windows UI Automation (uiautomation) element inspection with coordinate fallback.
3. Mouse, keyboard, and window focus execution.
4. Step plan generation and live target highlight bounding boxes.
5. Human takeover pause checking before and after each action.
"""

import io
import time
import base64
from typing import Optional, Dict, Any, List, Tuple
from PIL import Image
import mss
import pyautogui
import uiautomation as auto

from services.backend.automation.human_takeover import takeover_manager
from services.backend.automation.limits import AutomationLimitsManager

class DesktopController:
    def __init__(self):
        self.limits = AutomationLimitsManager()
        self._step_history: List[Dict[str, Any]] = []

    def capture_screen_ram(self) -> Image.Image:
        """
        Captures the primary monitor into an in-memory PIL Image.
        Never written to disk per screen privacy rule.
        """
        try:
            with mss.mss() as sct:
                monitor = sct.monitors[1] # Primary monitor
                sct_img = sct.grab(monitor)
                img = Image.frombytes("RGB", sct_img.size, sct_img.bgra, "raw", "BGRX")
                return img
        except Exception:
            try:
                from PIL import ImageGrab
                return ImageGrab.grab()
            except Exception:
                # In headless or non-interactive service sessions where GDI BitBlt is unavailable,
                # provide an in-memory canvas so pipeline never crashes or writes to disk
                return Image.new("RGB", (1920, 1080), color=(15, 23, 42))

    def capture_screen_base64(self) -> str:
        img = self.capture_screen_ram()
        img.thumbnail((1280, 720)) # Lightweight size for UI live stream
        buf = io.BytesIO()
        img.save(buf, format="JPEG", quality=50)
        return base64.b64encode(buf.getvalue()).decode("utf-8")

    def find_element_by_name(self, name: str, control_type: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """
        Locates a UI control using Windows UI Automation accessibility tree.
        Returns element metadata and bounding box.
        """
        root = auto.GetRootControl()
        target = None
        
        # Search visible controls
        for ctrl, depth in auto.WalkControl(root, maxDepth=3):
            if name.lower() in ctrl.Name.lower():
                target = ctrl
                break

        if target:
            rect = target.BoundingRectangle
            return {
                "name": target.Name,
                "control_type": target.ControlTypeName,
                "rect": {
                    "left": rect.left,
                    "top": rect.top,
                    "right": rect.right,
                    "bottom": rect.bottom,
                    "width": rect.width(),
                    "height": rect.height()
                },
                "center": (rect.xcenter(), rect.ycenter())
            }
        return None

    def focus_window(self, title_substr: str) -> bool:
        """Focuses a window matching title_substr."""
        win = auto.WindowControl(searchDepth=1, SubName=title_substr)
        if win.Exists(maxSearchSeconds=1):
            win.SetActive()
            win.SetTopmost(True)
            win.SetTopmost(False)
            return True
        return False

    async def execute_step_plan(self, steps: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Executes a sequence of steps with live step updates and takeover checks.
        Step format: {"action": "click"|"type"|"focus", "target": "...", "text": "..."}
        """
        results = []
        self.limits.start_session()
        takeover_manager.start_automation()

        try:
            for idx, step in enumerate(steps):
                await takeover_manager.wait_if_paused()
                action = step.get("action", "")
                target = step.get("target", "")
                text = step.get("text", "")
                
                self.limits.check_limits(f"{action}:{target}")

                # Step status
                step_record = {
                    "step_number": idx + 1,
                    "action": action,
                    "target": target,
                    "status": "current"
                }

                # Execute action
                with takeover_manager.synthetic_action():
                    if action == "focus":
                        success = self.focus_window(target)
                        step_record["result"] = "focused" if success else "window_not_found"

                    elif action == "click":
                        elem = self.find_element_by_name(target)
                        if elem:
                            cx, cy = elem["center"]
                            pyautogui.click(cx, cy)
                            step_record["result"] = f"clicked_element_at_{cx}_{cy}"
                            step_record["target_rect"] = elem["rect"]
                        else:
                            # Fallback if coordinates specified
                            coords = step.get("coords")
                            if coords:
                                pyautogui.click(coords[0], coords[1])
                                step_record["result"] = f"clicked_coords_{coords}"
                            else:
                                step_record["result"] = "element_not_found"

                    elif action == "type":
                        # Check password prohibition
                        if "pass" in target.lower() or "pwd" in target.lower():
                            raise PermissionError("Typing passwords is strictly prohibited by SAFETY.md.")
                        pyautogui.write(text, interval=0.03)
                        step_record["result"] = f"typed_{len(text)}_chars"

                step_record["status"] = "done"
                results.append(step_record)
                await takeover_manager.wait_if_paused()

            return results
        finally:
            takeover_manager.end_automation()

desktop_controller = DesktopController()
