"""
Phenom Adaptive Performance & Resource Governor (GOV-01)
Monitors 3D gaming, GPU utilization, VRAM usage, and CPU pressure.
Automatically suspends continuous ambient screen vision loops and background worker swarms
during high-load scenarios to preserve 60+ FPS in games and prevent VRAM exhaustion.
Seamlessly resumes background tasks once the system returns to desktop idle.
Provides sub-1ms synchronous kill switch integration (SAF-02).
"""

import asyncio
import inspect
import os
import subprocess
import time
from typing import Callable, List, Optional, Set, Tuple

import psutil

from services.backend.schemas.ambient_vision import ResourceGovernorState

# Processes that should never be classified as 3D games
EXCLUDED_PROCESSES: Set[str] = {
    "chrome.exe",
    "brave.exe",
    "msedge.exe",
    "firefox.exe",
    "vlc.exe",
    "mpv.exe",
    "potplayer.exe",
    "powerpnt.exe",
    "mstsc.exe",
    "vmware.exe",
    "virtualbox.exe",
    "teamviewer.exe",
    "anydesk.exe",
    "phenom.exe",
    "electron.exe",
    "explorer.exe",
    "code.exe",
}

# Known 3D game executables
KNOWN_GAME_PROCESSES: Set[str] = {
    "cs2.exe",
    "valorant.exe",
    "steam.exe",
    "dota2.exe",
    "cyberpunk2077.exe",
    "gta5.exe",
    "starfield.exe",
    "witcher3.exe",
    "overwatch.exe",
    "fortniteclient-win64-shipping.exe",
    "directx_game.exe",
    "game.exe",
}


class AdaptiveResourceGovernor:
    def __init__(
        self,
        gpu_throttle_threshold: float = 85.0,
        gpu_resume_threshold: float = 60.0,
        cpu_throttle_threshold: float = 90.0,
        recovery_cycles_required: int = 2,
    ):
        self.gpu_throttle_threshold = gpu_throttle_threshold
        self.gpu_resume_threshold = gpu_resume_threshold
        self.cpu_throttle_threshold = cpu_throttle_threshold
        self.recovery_cycles_required = recovery_cycles_required

        self._is_halted: bool = False
        self._is_running: bool = False
        self._monitor_task: Optional[asyncio.Task] = None

        # State tracking
        self.is_gaming: bool = False
        self.active_game: Optional[str] = None
        self.gpu_load_percent: float = 0.0
        self.vram_used_mb: float = 0.0
        self.cpu_load_percent: float = 0.0
        self.is_throttled: bool = False
        self.throttling_reason: Optional[str] = None
        self.vision_suspended: bool = False
        self.swarms_suspended: bool = False

        self._consecutive_idle_cycles: int = 0
        self._pause_callbacks: List[Callable] = []
        self._resume_callbacks: List[Callable] = []

        # Mock override for testing / headless CI
        self._mock_override: bool = False
        self._mock_gaming: bool = False
        self._mock_game_name: Optional[str] = None
        self._mock_gpu_load: float = 0.0
        self._mock_vram_mb: float = 0.0
        self._mock_cpu_load: float = 0.0

    @property
    def is_halted(self) -> bool:
        return self._is_halted

    def register_pause_callback(self, cb: Callable):
        """Registers a callback invoked when governor suspends background workloads."""
        if cb not in self._pause_callbacks:
            self._pause_callbacks.append(cb)

    def register_resume_callback(self, cb: Callable):
        """Registers a callback invoked when governor resumes background workloads."""
        if cb not in self._resume_callbacks:
            self._resume_callbacks.append(cb)

    def set_mock_state(
        self,
        is_gaming: Optional[bool] = None,
        active_game: Optional[str] = None,
        gpu_load: Optional[float] = None,
        vram_used_mb: Optional[float] = None,
        cpu_load: Optional[float] = None,
    ):
        """Overrides metrics for deterministic unit and integration testing."""
        self._mock_override = True
        if is_gaming is not None:
            self._mock_gaming = is_gaming
        if active_game is not None:
            self._mock_game_name = active_game
        if gpu_load is not None:
            self._mock_gpu_load = gpu_load
        if vram_used_mb is not None:
            self._mock_vram_mb = vram_used_mb
        if cpu_load is not None:
            self._mock_cpu_load = cpu_load

    def clear_mock_state(self):
        """Clears test overrides."""
        self._mock_override = False
        self._mock_gaming = False
        self._mock_game_name = None
        self._mock_gpu_load = 0.0
        self._mock_vram_mb = 0.0
        self._mock_cpu_load = 0.0

    def query_gpu_metrics(self) -> Tuple[float, float]:
        """
        Queries GPU 3D engine utilization and VRAM usage via nvidia-smi.
        Returns: (gpu_load_percent, vram_used_mb).
        Gracefully falls back to (0.0, 0.0) if unavailable or in CI.
        """
        if self._mock_override:
            return self._mock_gpu_load, self._mock_vram_mb

        try:
            result = subprocess.run(
                ["nvidia-smi", "--query-gpu=utilization.gpu,memory.used", "--format=csv,noheader,nounits"],
                capture_output=True,
                text=True,
                timeout=1.5,
                creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0,
            )
            if result.returncode == 0 and result.stdout.strip():
                parts = result.stdout.strip().split("\n")[0].split(",")
                gpu_util = float(parts[0].strip())
                vram_mb = float(parts[1].strip())
                return gpu_util, vram_mb
        except Exception:
            pass

        return 0.0, 0.0

    def query_cpu_load(self) -> float:
        """Queries total system CPU load percentage."""
        if self._mock_override:
            return self._mock_cpu_load
        try:
            return float(psutil.cpu_percent(interval=None))
        except Exception:
            return 0.0

    def detect_3d_gaming(self) -> Tuple[bool, Optional[str]]:
        """
        Detects active full-screen 3D games or graphics applications.
        Excludes browsers, dev tools, and desktop media players.
        """
        if self._mock_override:
            return self._mock_gaming, self._mock_game_name

        # 1. Process scan
        try:
            for proc in psutil.process_iter(["name"]):
                try:
                    name = (proc.info["name"] or "").lower()
                    if name in KNOWN_GAME_PROCESSES:
                        return True, name
                except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                    continue
        except Exception:
            pass

        # 2. Windows foreground fullscreen check
        if os.name == "nt":
            try:
                import win32api
                import win32con
                import win32gui
                import win32process

                hwnd = win32gui.GetForegroundWindow()
                if hwnd:
                    _, pid = win32process.GetWindowThreadProcessId(hwnd)
                    if pid > 0:
                        p = psutil.Process(pid)
                        p_name = p.name().lower()
                        if p_name not in EXCLUDED_PROCESSES:
                            rect = win32gui.GetWindowRect(hwnd)
                            screen_w = win32api.GetSystemMetrics(win32con.SM_CXSCREEN)
                            screen_h = win32api.GetSystemMetrics(win32con.SM_CYSCREEN)
                            w = rect[2] - rect[0]
                            h = rect[3] - rect[1]
                            if w >= screen_w and h >= screen_h:
                                return True, p_name
            except Exception:
                pass

        return False, None

    def poll_metrics(self) -> ResourceGovernorState:
        """
        Evaluates current system load and applies suspension or resumption rules.
        """
        if self._is_halted:
            return self.get_state()

        is_game, game_name = self.detect_3d_gaming()
        gpu_load, vram_mb = self.query_gpu_metrics()
        cpu_load = self.query_cpu_load()

        self.is_gaming = is_game
        self.active_game = game_name
        self.gpu_load_percent = gpu_load
        self.vram_used_mb = vram_mb
        self.cpu_load_percent = cpu_load

        # Determine if resource throttling condition is met
        should_throttle = False
        reason = None

        if is_game:
            should_throttle = True
            reason = f"3D game active: {game_name or 'fullscreen_app'}"
        elif gpu_load >= self.gpu_throttle_threshold:
            should_throttle = True
            reason = f"High GPU load ({gpu_load:.1f}% >= {self.gpu_throttle_threshold}%)"
        elif cpu_load >= self.cpu_throttle_threshold:
            should_throttle = True
            reason = f"High CPU load ({cpu_load:.1f}% >= {self.cpu_throttle_threshold}%)"

        if should_throttle:
            self._consecutive_idle_cycles = 0
            if not self.vision_suspended:
                self.is_throttled = True
                self.throttling_reason = reason
                self.vision_suspended = True
                self.swarms_suspended = True
                self._dispatch_pause(reason or "governor_throttle")
        else:
            # Check for recovery conditions (GPU < resume threshold and not gaming)
            if self.vision_suspended:
                if gpu_load <= self.gpu_resume_threshold and cpu_load < self.cpu_throttle_threshold:
                    self._consecutive_idle_cycles += 1
                    if self._consecutive_idle_cycles >= self.recovery_cycles_required:
                        self.is_throttled = False
                        self.throttling_reason = None
                        self.vision_suspended = False
                        self.swarms_suspended = False
                        self._consecutive_idle_cycles = 0
                        self._dispatch_resume()
            else:
                self.is_throttled = False
                self.throttling_reason = None
                self._consecutive_idle_cycles = 0

        return self.get_state()

    def _dispatch_pause(self, reason: str):
        for cb in self._pause_callbacks:
            try:
                sig = inspect.signature(cb)
                if len(sig.parameters) > 0:
                    res = cb(reason)
                else:
                    res = cb()
                if inspect.iscoroutine(res):
                    try:
                        loop = asyncio.get_running_loop()
                        if loop.is_running():
                            loop.create_task(res)
                    except RuntimeError:
                        pass
            except Exception:
                pass

    def _dispatch_resume(self):
        for cb in self._resume_callbacks:
            try:
                res = cb()
                if inspect.iscoroutine(res):
                    try:
                        loop = asyncio.get_running_loop()
                        if loop.is_running():
                            loop.create_task(res)
                    except RuntimeError:
                        pass
            except Exception:
                pass

    def get_state(self) -> ResourceGovernorState:
        """Returns the current snapshot as a typed Pydantic model."""
        return ResourceGovernorState(
            timestamp=time.time(),
            is_gaming=self.is_gaming,
            active_game=self.active_game,
            gpu_load_percent=self.gpu_load_percent,
            vram_used_mb=self.vram_used_mb,
            cpu_load_percent=self.cpu_load_percent,
            is_throttled=self.is_throttled,
            throttling_reason=self.throttling_reason,
            vision_suspended=self.vision_suspended,
            swarms_suspended=self.swarms_suspended,
        )

    def halt(self):
        """
        Synchronous sub-1ms Guardian kill switch halt.
        Immediately stops background monitoring and suspends all managed tasks.
        """
        self._is_halted = True
        self.vision_suspended = True
        self.swarms_suspended = True
        self.is_throttled = True
        self.throttling_reason = "guardian_killswitch_halt"

        if self._monitor_task and not self._monitor_task.done():
            self._monitor_task.cancel()

        self._dispatch_pause("guardian_killswitch_halt")

    def reset(self):
        """
        Resets governor after Guardian resume or test reset.
        """
        self._is_halted = False
        self.is_throttled = False
        self.throttling_reason = None
        self.vision_suspended = False
        self.swarms_suspended = False
        self._consecutive_idle_cycles = 0
        self.clear_mock_state()
        self._dispatch_resume()

    async def start(self, poll_interval_seconds: float = 3.0):
        """Starts asynchronous periodic monitoring loop."""
        if self._is_running:
            return
        self._is_running = True
        self._monitor_task = asyncio.create_task(self._run_loop(poll_interval_seconds))

    async def stop(self):
        """Stops asynchronous monitoring loop."""
        self._is_running = False
        if self._monitor_task and not self._monitor_task.done():
            self._monitor_task.cancel()
            try:
                await self._monitor_task
            except asyncio.CancelledError:
                pass

    async def _run_loop(self, poll_interval_seconds: float):
        while self._is_running and not self._is_halted:
            try:
                self.poll_metrics()
            except Exception:
                pass
            await asyncio.sleep(poll_interval_seconds)


resource_governor = AdaptiveResourceGovernor()
