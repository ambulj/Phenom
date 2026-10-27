"""
Phenom Automation Limits & Stuck Detector
Enforces:
1. Maximum step limit (default: 25 steps per automated session)
2. Total execution timeout (default: 120 seconds)
3. Stuck-loop detector: triggers when consecutive steps perform identical actions without state change
"""

import time
import hashlib
from typing import Optional, List, Dict, Any

class AutomationLimitExceeded(Exception):
    pass

class AutomationStuckError(Exception):
    pass

class AutomationLimitsManager:
    def __init__(self, max_steps: int = 25, timeout_seconds: float = 120.0, max_repeats: int = 3):
        self.max_steps = max_steps
        self.timeout_seconds = timeout_seconds
        self.max_repeats = max_repeats
        self.step_count = 0
        self.start_time: Optional[float] = None
        self._action_history: List[str] = []
        self._state_hashes: List[str] = []

    def start_session(self):
        self.step_count = 0
        self.start_time = time.time()
        self._action_history.clear()
        self._state_hashes.clear()

    def check_limits(self, action_signature: str, state_repr: str = ""):
        """
        Validates step count, elapsed time, and stuck loops.
        Raises AutomationLimitExceeded or AutomationStuckError if bounds are breached.
        """
        if self.start_time is None:
            self.start_session()

        self.step_count += 1
        elapsed = time.time() - (self.start_time or 0)

        # 1. Step Limit
        if self.step_count > self.max_steps:
            raise AutomationLimitExceeded(
                f"Automation step limit reached ({self.step_count}/{self.max_steps} steps). Halted for user safety."
            )

        # 2. Timeout
        if elapsed > self.timeout_seconds:
            raise AutomationLimitExceeded(
                f"Automation session timed out ({round(elapsed, 1)}s elapsed > {self.timeout_seconds}s limit). Halted for user safety."
            )

        # 3. Stuck Detector
        self._action_history.append(action_signature)
        state_hash = hashlib.md5(state_repr.encode("utf-8")).hexdigest() if state_repr else ""
        self._state_hashes.append(state_hash)

        if len(self._action_history) >= self.max_repeats:
            last_actions = self._action_history[-self.max_repeats:]
            # Check if all last N actions are identical
            if len(set(last_actions)) == 1:
                # Check if state also remained unchanged
                if state_hash and len(set(self._state_hashes[-self.max_repeats:])) == 1:
                    raise AutomationStuckError(
                        f"Stuck loop detected: Action '{action_signature}' was repeated {self.max_repeats} times without state progress. Halted."
                    )
