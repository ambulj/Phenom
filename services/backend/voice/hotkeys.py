"""
Phenom Hotkeys Manager with Conflict Detection
Configures, validates, and registers system-wide keyboard shortcuts.
Default shortcuts:
- Push-to-Talk: alt+space
- Toggle Phenom Window: ctrl+alt+p
- Guardian Kill Switch: ctrl+alt+pause
"""

from typing import Dict, Optional, Tuple, Callable, Any
import keyboard

DEFAULT_HOTKEYS = {
    "push_to_talk": "alt+space",
    "toggle_phenom": "ctrl+alt+p",
    "kill_switch": "ctrl+alt+pause"
}

class HotkeyManager:
    def __init__(self, initial_hotkeys: Optional[Dict[str, str]] = None):
        self._hotkeys: Dict[str, str] = dict(initial_hotkeys or DEFAULT_HOTKEYS)
        self._hooks: Dict[str, Any] = {}
        self._callbacks: Dict[str, Callable[[], None]] = {}

    def get_hotkeys(self) -> Dict[str, str]:
        return dict(self._hotkeys)

    def validate_and_detect_conflicts(self, proposed_hotkeys: Dict[str, str]) -> Tuple[bool, Optional[str]]:
        """
        Validates hotkey syntax and checks for duplicates/conflicts among actions.
        Returns (is_valid, error_message).
        """
        seen_keys: Dict[str, str] = {}
        for action, key_combo in proposed_hotkeys.items():
            norm_key = key_combo.strip().lower().replace(" ", "")
            if not norm_key:
                return False, f"Hotkey for '{action}' cannot be empty."

            # Check for conflict
            if norm_key in seen_keys:
                conflicting_action = seen_keys[norm_key]
                return False, f"Hotkey conflict: '{key_combo}' is assigned to both '{conflicting_action}' and '{action}'."
            seen_keys[norm_key] = action

            # Validate syntax by parsing with keyboard module
            try:
                keyboard.parse_hotkey(norm_key)
            except Exception as e:
                return False, f"Invalid key combination '{key_combo}' for '{action}': {e}"

        return True, None

    def update_hotkey(self, action: str, new_key_combo: str) -> Tuple[bool, Optional[str]]:
        proposed = dict(self._hotkeys)
        proposed[action] = new_key_combo
        valid, err = self.validate_and_detect_conflicts(proposed)
        if not valid:
            return False, err
        self._hotkeys[action] = new_key_combo.strip().lower()
        self.rebind_all()
        return True, None

    def register_callback(self, action: str, callback: Callable[[], None]):
        self._callbacks[action] = callback
        self.rebind_action(action)

    def rebind_action(self, action: str):
        if action in self._hooks:
            try:
                keyboard.remove_hotkey(self._hooks[action])
            except Exception:
                pass
            self._hooks.pop(action, None)

        key_combo = self._hotkeys.get(action)
        cb = self._callbacks.get(action)
        if key_combo and cb:
            try:
                hook = keyboard.add_hotkey(key_combo, cb)
                self._hooks[action] = hook
            except Exception:
                pass

    def rebind_all(self):
        for action in self._callbacks:
            self.rebind_action(action)

hotkey_manager = HotkeyManager()
