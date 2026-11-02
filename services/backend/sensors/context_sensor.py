"""Active Foreground Window Context Sensor for Phenom.

Uses Win32 APIs (win32gui, win32process) to track active application context
with automatic redaction for sensitive windows (passwords, banking, chat) (SEN-02).
"""

from __future__ import annotations

import asyncio
import inspect
import logging
import time
from typing import Any, Awaitable, Callable, List, Optional, Union

import psutil
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)

# Try importing win32gui and win32process
try:
    import win32gui
    import win32process
    HAS_WIN32 = True
except ImportError:
    HAS_WIN32 = False
    logger.warning("pywin32 not available; Win32ContextSensor will run in fallback mock mode.")

SENSITIVE_KEYWORDS: List[str] = [
    "bitwarden",
    "keepass",
    "1password",
    "lastpass",
    "dashlane",
    "whatsapp",
    "telegram",
    "signal",
    "banking",
    "login",
    "sign in",
    "signin",
    "password",
    "credential",
    "authenticator",
    "password vault",
]


class ForegroundContext(BaseModel):
    """Snapshot of active foreground desktop context."""

    hwnd: int = Field(default=0, description="Window handle")
    title: str = Field(default="", description="Sanitized window title")
    app_name: str = Field(default="", description="Process executable name (e.g. Code.exe)")
    pid: int = Field(default=0, description="Process ID")
    is_sensitive: bool = Field(default=False, description="True if window matched privacy filters")
    timestamp: float = Field(default_factory=time.time, description="Unix timestamp of query")


ContextCallbackType = Union[Callable[[ForegroundContext], Any], Callable[[ForegroundContext], Awaitable[Any]]]


class Win32ContextSensor:
    """Monitors Windows 11 foreground application context and redacts sensitive data."""

    def __init__(
        self,
        poll_interval: float = 2.0,
        on_context_change_callback: Optional[ContextCallbackType] = None,
        sensitive_keywords: Optional[List[str]] = None,
    ) -> None:
        self.poll_interval = poll_interval
        self.on_context_change_callback = on_context_change_callback
        self.sensitive_keywords = sensitive_keywords or SENSITIVE_KEYWORDS

        self._current_context = ForegroundContext()
        self._running = False
        self._monitor_task: Optional[asyncio.Task] = None

    @property
    def current_context(self) -> ForegroundContext:
        """Return the current foreground context snapshot."""
        return self._current_context

    def check_sensitivity(self, title: str, app_name: str) -> bool:
        """Evaluate whether window title or process name is privacy-sensitive."""
        low_title = title.lower()
        low_app = app_name.lower()
        for kw in self.sensitive_keywords:
            if kw in low_title or kw in low_app:
                return True
        return False

    def query_context(self, redact_sensitive: bool = True) -> ForegroundContext:
        """Query foreground window context synchronously."""
        if not HAS_WIN32:
            ctx = ForegroundContext(
                hwnd=0,
                title="Mock Desktop",
                app_name="mock_explorer.exe",
                pid=0,
                is_sensitive=False,
                timestamp=time.time(),
            )
            self._current_context = ctx
            return ctx

        try:
            hwnd = win32gui.GetForegroundWindow()
            if not hwnd:
                ctx = ForegroundContext(
                    hwnd=0,
                    title="Desktop",
                    app_name="explorer.exe",
                    pid=0,
                    is_sensitive=False,
                    timestamp=time.time(),
                )
                self._current_context = ctx
                return ctx

            raw_title = win32gui.GetWindowText(hwnd) or ""
            _, pid = win32process.GetWindowThreadProcessId(hwnd)

            app_name = "unknown"
            if pid > 0:
                try:
                    proc = psutil.Process(pid)
                    app_name = proc.name()
                except Exception:
                    pass

            is_sensitive = self.check_sensitivity(raw_title, app_name)
            display_title = "[REDACTED_SENSITIVE_APP]" if (is_sensitive and redact_sensitive) else raw_title

            ctx = ForegroundContext(
                hwnd=hwnd,
                title=display_title,
                app_name=app_name,
                pid=pid,
                is_sensitive=is_sensitive,
                timestamp=time.time(),
            )
            self._current_context = ctx
            return ctx
        except Exception as exc:
            logger.debug("Win32 context query failed: %s", exc)
            return self._current_context

    async def _invoke_callback(self, ctx: ForegroundContext) -> None:
        """Safely execute context transition callback."""
        if not self.on_context_change_callback:
            return
        try:
            cb = self.on_context_change_callback
            if inspect.iscoroutinefunction(cb):
                await cb(ctx)
            else:
                res = cb(ctx)
                if inspect.isawaitable(res):
                    await res
        except Exception as exc:
            logger.error("Error in context callback %s: %s", cb, exc)

    async def _run_loop(self) -> None:
        """Background context change detection loop."""
        logger.info("Win32ContextSensor polling loop started (interval=%.1fs)", self.poll_interval)
        last_hwnd = -1
        last_title = ""

        while self._running:
            try:
                ctx = self.query_context(redact_sensitive=True)
                if ctx.hwnd != last_hwnd or ctx.title != last_title:
                    last_hwnd = ctx.hwnd
                    last_title = ctx.title
                    logger.debug("Foreground window changed: [%s] %s", ctx.app_name, ctx.title)
                    await self._invoke_callback(ctx)

                await asyncio.sleep(self.poll_interval)
            except asyncio.CancelledError:
                break
            except Exception as exc:
                logger.error("Win32ContextSensor loop exception: %s", exc)
                await asyncio.sleep(self.poll_interval)

    def start(self) -> None:
        """Start the background context sensor loop."""
        if self._running:
            return
        self._running = True
        try:
            loop = asyncio.get_running_loop()
            self._monitor_task = loop.create_task(self._run_loop())
        except RuntimeError:
            logger.debug("No running event loop; context sensor will start when loop runs.")

    def stop(self) -> None:
        """Gracefully stop background context monitoring."""
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


context_sensor = Win32ContextSensor()

