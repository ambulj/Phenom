"""Win32 User Inactivity Sensor for Phenom.

Uses ctypes.windll.user32.GetLastInputInfo and kernel32.GetTickCount64 to
measure user inactivity without invasive keyboard/mouse hooks (SEN-01).
"""

from __future__ import annotations

import asyncio
import ctypes
import inspect
import logging
from typing import Any, Awaitable, Callable, Optional, Union

logger = logging.getLogger(__name__)


class LASTINPUTINFO(ctypes.Structure):
    _fields_ = [
        ("cbSize", ctypes.c_uint),
        ("dwTime", ctypes.c_uint),
    ]


def default_get_idle_seconds() -> float:
    """Retrieve elapsed seconds since the last user mouse/keyboard input."""
    try:
        lii = LASTINPUTINFO()
        lii.cbSize = ctypes.sizeof(LASTINPUTINFO)
        if not ctypes.windll.user32.GetLastInputInfo(ctypes.byref(lii)):
            return 0.0

        # Get system uptime in milliseconds
        if hasattr(ctypes.windll.kernel32, "GetTickCount64"):
            tick_count = ctypes.windll.kernel32.GetTickCount64()
        else:
            tick_count = ctypes.windll.kernel32.GetTickCount()

        # lii.dwTime is a 32-bit millisecond value. Handle wrap-around arithmetic:
        diff_ms = (tick_count & 0xFFFFFFFF) - lii.dwTime
        if diff_ms < 0:
            diff_ms += 0x100000000

        return max(0.0, float(diff_ms) / 1000.0)
    except Exception as exc:
        logger.debug("Win32 GetLastInputInfo query failed: %s", exc)
        return 0.0


CallbackType = Union[Callable[[float], Any], Callable[[float], Awaitable[Any]]]


class Win32IdleDetector:
    """Monitors Windows 11 user inactivity and triggers state transition callbacks."""

    def __init__(
        self,
        idle_threshold_seconds: float = 300.0,
        on_idle_callback: Optional[CallbackType] = None,
        on_returned_callback: Optional[CallbackType] = None,
        poll_interval_active: float = 2.0,
        poll_interval_idle: float = 5.0,
        get_idle_seconds_fn: Optional[Callable[[], float]] = None,
    ) -> None:
        self.idle_threshold_seconds = max(1.0, float(idle_threshold_seconds))
        self.on_idle_callback = on_idle_callback
        self.on_returned_callback = on_returned_callback
        self.poll_interval_active = poll_interval_active
        self.poll_interval_idle = poll_interval_idle
        self._get_idle_seconds = get_idle_seconds_fn or default_get_idle_seconds

        self._is_idle = False
        self._running = False
        self._monitor_task: Optional[asyncio.Task] = None
        self._last_idle_duration: float = 0.0

    @property
    def is_idle(self) -> bool:
        """Return True if currently in idle state."""
        return self._is_idle

    @property
    def last_idle_duration(self) -> float:
        """Return the most recently measured idle duration in seconds."""
        return self._last_idle_duration

    def get_current_idle_seconds(self) -> float:
        """Query current idle duration directly."""
        dur = self._get_idle_seconds()
        self._last_idle_duration = dur
        return dur

    def set_threshold(self, threshold_seconds: float) -> None:
        """Update idle duration threshold."""
        self.idle_threshold_seconds = max(1.0, float(threshold_seconds))

    async def _invoke_callback(self, cb: Optional[CallbackType], duration: float) -> None:
        """Safely invoke sync or async callback."""
        if not cb:
            return
        try:
            if inspect.iscoroutinefunction(cb):
                await cb(duration)
            else:
                res = cb(duration)
                if inspect.isawaitable(res):
                    await res
        except Exception as exc:
            logger.error("Error executing idle callback %s: %s", cb, exc)

    async def _run_loop(self) -> None:
        """Background monitoring loop."""
        logger.info(
            "Win32IdleDetector started with threshold=%.1fs (active_poll=%.1fs, idle_poll=%.1fs)",
            self.idle_threshold_seconds,
            self.poll_interval_active,
            self.poll_interval_idle,
        )
        while self._running:
            try:
                duration = self.get_current_idle_seconds()

                if not self._is_idle and duration >= self.idle_threshold_seconds:
                    self._is_idle = True
                    logger.info("User is now IDLE (elapsed=%.1fs >= threshold=%.1fs)", duration, self.idle_threshold_seconds)
                    await self._invoke_callback(self.on_idle_callback, duration)
                elif self._is_idle and duration < self.idle_threshold_seconds:
                    self._is_idle = False
                    logger.info("User RETURNED from idle (duration was %.1fs)", duration)
                    await self._invoke_callback(self.on_returned_callback, duration)

                sleep_time = self.poll_interval_idle if self._is_idle else self.poll_interval_active
                await asyncio.sleep(sleep_time)
            except asyncio.CancelledError:
                break
            except Exception as exc:
                logger.error("Win32IdleDetector loop exception: %s", exc)
                await asyncio.sleep(self.poll_interval_active)

    def start(self) -> None:
        """Start the background monitoring task."""
        if self._running:
            return
        self._running = True
        try:
            loop = asyncio.get_running_loop()
            self._monitor_task = loop.create_task(self._run_loop())
        except RuntimeError:
            logger.debug("No running event loop; idle monitor will start when event loop runs.")

    def stop(self) -> None:
        """Gracefully stop background monitoring."""
        self._running = False
        if self._monitor_task and not self._monitor_task.done():
            self._monitor_task.cancel()
            self._monitor_task = None

    def halt(self) -> None:
        """Synchronous Guardian halt callback (< 5ms SLA)."""
        self._running = False
        if self._monitor_task and not self._monitor_task.done():
            self._monitor_task.cancel()
            self._monitor_task = None


idle_detector = Win32IdleDetector()

