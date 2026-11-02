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
try:
    import uiautomation as auto
except ImportError:
    auto = None

from services.backend.automation.human_takeover import takeover_manager, HumanTakeoverAbort
from services.backend.automation.limits import AutomationLimitsManager
from services.backend.voice.sound_fx import sound_fx
from services.backend.safety.guardian import guardian

class DesktopController:
    def __init__(self):
        self.limits = AutomationLimitsManager()
        self._step_history: List[Dict[str, Any]] = []
        self._overlay_callback = None
        self._start_time = 0.0

        # Register takeover callback to push UI state & halt sound
        takeover_manager.set_takeover_callback(self._on_human_takeover)

    def set_overlay_callback(self, cb):
        self._overlay_callback = cb

    def _emit_overlay_event(self, event_type: str, payload: Dict[str, Any]):
        if self._overlay_callback:
            try:
                import asyncio
                if asyncio.iscoroutinefunction(self._overlay_callback):
                    asyncio.create_task(self._overlay_callback(event_type, payload))
                else:
                    self._overlay_callback(event_type, payload)
            except Exception:
                pass

    def _on_human_takeover(self):
        sound_fx.play_automation_halt()
        self._emit_overlay_event("screen.overlay_state", {
            "state": "takeover",
            "color": "#f97316",
            "message": "User input detected. Resume automation or Stop?",
            "timeout_seconds": 10
        })

    def _format_ticker_time(self) -> str:
        elapsed = time.time() - self._start_time
        mins = int(elapsed // 60)
        secs = elapsed % 60
        return f"{mins:02d}:{secs:04.1f}"

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
        Executes a sequence of steps with live step updates, audio cues, click target rings, and takeover checks.
        Step format: {"action": "click"|"type"|"focus", "target": "...", "text": "..."}
        """
        results = []
        self._start_time = time.time()
        self.limits.start_session()
        takeover_manager.start_automation()

        # Audio cue and neon amber overlay
        sound_fx.play_automation_start()
        self._emit_overlay_event("screen.overlay_state", {
            "state": "active",
            "color": "#f59e0b"
        })

        try:
            for idx, step in enumerate(steps):
                if guardian.is_halted:
                    raise RuntimeError("Automation immediately halted by Guardian kill switch.")
                await takeover_manager.wait_if_paused()
                action = step.get("action", "")
                target = step.get("target", "")
                text = step.get("text", "")
                
                self.limits.check_limits(f"{action}:{target}")

                # Emit action ticker item
                ts = self._format_ticker_time()
                ticker_text = f"Step {idx + 1}/{len(steps)}: {action.capitalize()} '{target or text[:15]}'"
                self._emit_overlay_event("screen.action_ticker", {
                    "timestamp": ts,
                    "text": ticker_text,
                    "step": idx + 1,
                    "total": len(steps)
                })

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
                        cx, cy = None, None
                        elem = self.find_element_by_name(target) if target else None
                        if elem:
                            cx, cy = elem["center"]
                            step_record["target_rect"] = elem["rect"]
                        elif step.get("coords"):
                            cx, cy = step.get("coords")
                        elif target:
                            # Fallback to Phase 2 In-Memory Visual OCR Coordinate Locator
                            try:
                                from services.backend.vision.ocr_engine import ocr_engine
                                img = self.capture_screen_ram()
                                ocr_match = ocr_engine.find_element_coordinates(target, img)
                                if ocr_match:
                                    cx, cy = ocr_match["x"], ocr_match["y"]
                                    step_record["target_rect"] = ocr_match.get("bbox")
                            except Exception:
                                pass

                        if cx is not None and cy is not None:
                            # 300ms Click Target Highlighting Ring per Plan 7e
                            self._emit_overlay_event("screen.click_highlight", {
                                "x": cx,
                                "y": cy,
                                "duration_ms": 300
                            })
                            import asyncio
                            await asyncio.sleep(0.3)
                            pyautogui.click(cx, cy)
                            step_record["result"] = f"clicked_at_{cx}_{cy}"
                        else:
                            step_record["result"] = "target_not_found"

                    elif action == "type":
                        # Check password prohibition
                        if "pass" in target.lower() or "pwd" in target.lower():
                            raise PermissionError("Typing passwords is strictly prohibited by SAFETY.md.")
                        pyautogui.write(text, interval=0.03)
                        step_record["result"] = f"typed_{len(text)}_chars"

                    elif action in ["hotkey", "press"]:
                        keys = step.get("keys") or [step.get("key")]
                        if isinstance(keys, str):
                            keys = [keys]
                        keys = [str(k).lower().strip() for k in keys if k]
                        if keys:
                            if len(keys) == 1:
                                pyautogui.press(keys[0])
                            else:
                                pyautogui.hotkey(*keys)
                            step_record["result"] = f"pressed_{'+'.join(keys)}"
                        else:
                            step_record["result"] = "no_keys_provided"

                step_record["status"] = "done"
                results.append(step_record)
                await takeover_manager.wait_if_paused()

            # Automation completed successfully: Emerald green overlay & stop chime
            sound_fx.play_automation_stop()
            self._emit_overlay_event("screen.overlay_state", {
                "state": "success",
                "color": "#10b981"
            })
            return results
        except Exception as e:
            # Error or abort: Ruby red overlay & halt chime
            sound_fx.play_automation_halt()
            self._emit_overlay_event("screen.overlay_state", {
                "state": "error",
                "color": "#ef4444",
                "error": str(e)
            })
            raise
        finally:
            takeover_manager.end_automation()

desktop_controller = DesktopController()
