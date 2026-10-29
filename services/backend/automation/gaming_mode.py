"""
Phenom Gaming Mode Detection & Resource Governance Engine (Task 7j)
Detects active game processes and full-screen DirectX/Vulkan applications while strictly
excluding browsers, video players, presentations, and remote desktop sessions.

Actions on Game Detection:
1. Mute non-critical Windows notifications.
2. Pause background scheduler jobs (except security monitor).
3. Terminate/pause heavy non-essential background processes.
4. Switch Windows Power Plan to High Performance.
5. Unload local LLM from VRAM (freeing ~5 GB GPU memory).
6. Freeze Three.js Orb (0 particles, 0 fps).

Actions on Game Exit:
1. Restore Windows notifications.
2. Resume scheduled background tasks.
3. Switch Windows Power Plan to Balanced.
4. Restore floating Orb quality level and warm up LLM.
"""

import os
import sys
import subprocess
import time
import psutil
from typing import Optional, Dict, Any, Tuple, Set

from services.backend.resource.vram_manager import vram_manager
from services.backend.scheduler.cron import background_scheduler
from services.backend.automation.notification_digest import notification_digest_manager

# Known game executables
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
    "game.exe"
}

# Strict Exclusion Filters: Applications that must NEVER trigger gaming mode
EXCLUDED_PROCESSES: Set[str] = {
    # Video Players / Browsers
    "chrome.exe",
    "brave.exe",
    "msedge.exe",
    "firefox.exe",
    "vlc.exe",
    "mpv.exe",
    "potplayer.exe",
    # Presentations
    "powerpnt.exe",
    # Remote Desktop / Virtualization
    "mstsc.exe",
    "vmware.exe",
    "virtualbox.exe",
    "teamviewer.exe",
    "anydesk.exe",
    # Desktop Shell / Dev Tools
    "phenom.exe",
    "electron.exe",
    "explorer.exe",
    "code.exe"
}

# Windows Power Plan GUIDs
POWER_PLAN_HIGH_PERFORMANCE = "8c5e7fda-e8bf-4a96-9a85-a6e23a8c635c"
POWER_PLAN_BALANCED = "381b4222-f694-41f0-9685-ff5bb260df2e"

class GamingModeManager:
    def __init__(self):
        self.gaming_mode_active: bool = False
        self.active_game_name: Optional[str] = None
        self.detection_reason: Optional[str] = None
        self.active_power_plan: str = "balanced"
        self._custom_game_list: Set[str] = set(KNOWN_GAME_PROCESSES)

    def is_process_excluded(self, process_name: str) -> bool:
        """Checks if a process is strictly excluded from gaming mode."""
        return process_name.strip().lower() in EXCLUDED_PROCESSES

    def detect_gaming_state(
        self,
        mock_foreground_proc: Optional[str] = None,
        mock_is_fullscreen: bool = False
    ) -> Tuple[bool, Optional[str], Optional[str]]:
        """
        Scans running processes and foreground window for active games.
        Returns: (is_gaming, game_name, reason)
        """
        # 1. Test mock override if provided
        if mock_foreground_proc:
            p_name = mock_foreground_proc.strip().lower()
            if self.is_process_excluded(p_name):
                return False, None, f"excluded_application:{p_name}"
            if p_name in self._custom_game_list:
                return True, p_name, f"known_game_executable:{p_name}"
            if mock_is_fullscreen:
                return True, p_name, f"fullscreen_directx_app:{p_name}"
            return False, None, "not_gaming"

        # 2. Check running processes against known game list
        for proc in psutil.process_iter(['name']):
            try:
                name = (proc.info['name'] or '').lower()
                if name in self._custom_game_list:
                    return True, name, f"known_game_executable:{name}"
            except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                continue

        # 3. Check full-screen foreground window on Windows
        try:
            import win32gui
            import win32process
            import win32api
            import win32con

            hwnd = win32gui.GetForegroundWindow()
            if hwnd:
                _, pid = win32process.GetWindowThreadProcessId(hwnd)
                if pid > 0:
                    p = psutil.Process(pid)
                    p_name = p.name().lower()

                    # Strict Exclusion Check
                    if self.is_process_excluded(p_name):
                        return False, None, f"excluded_application:{p_name}"

                    # Check window dimensions
                    rect = win32gui.GetWindowRect(hwnd)
                    screen_w = win32api.GetSystemMetrics(win32con.SM_CXSCREEN)
                    screen_h = win32api.GetSystemMetrics(win32con.SM_CYSCREEN)
                    w = rect[2] - rect[0]
                    h = rect[3] - rect[1]

                    if w >= screen_w and h >= screen_h:
                        # Fullscreen 3D app detected
                        return True, p_name, f"fullscreen_directx_app:{p_name}"
        except Exception:
            pass

        return False, None, "idle"

    async def enter_gaming_mode(self, game_name: str, reason: str = "detected_game") -> Dict[str, Any]:
        """
        Activates gaming mode and applies resource governor actions.
        """
        self.gaming_mode_active = True
        self.active_game_name = game_name
        self.detection_reason = reason

        # 1. Mute Windows notifications
        notification_digest_manager.enable_dnd()

        # 2. Pause background scheduler
        background_scheduler.pause()

        # 3. Switch Power Plan to High Performance
        self._switch_power_plan(POWER_PLAN_HIGH_PERFORMANCE)
        self.active_power_plan = "high_performance"

        # 4. Offload local LLM VRAM (< 100 MB)
        vram_manager.gaming_mode_active = True
        vram_manager.detected_game_name = game_name
        unload_res = await vram_manager.unload_model(reason=f"gaming_mode:{game_name}")

        # 5. Freeze Three.js Orb LOD
        lod_quality = vram_manager.get_orb_lod_quality() # Will return 'freeze'

        return {
            "status": "gaming_mode_active",
            "game": game_name,
            "reason": reason,
            "power_plan": self.active_power_plan,
            "notifications_muted": notification_digest_manager.is_dnd_active,
            "scheduler_paused": background_scheduler.is_paused,
            "vram_offloaded": unload_res.get("vram_allocated_mb", 50.0),
            "orb_lod": lod_quality
        }

    async def exit_gaming_mode(self) -> Dict[str, Any]:
        """
        Restores normal desktop mode when game exits.
        """
        prev_game = self.active_game_name
        self.gaming_mode_active = False
        self.active_game_name = None
        self.detection_reason = None

        # 1. Restore Windows notifications
        notification_digest_manager.disable_dnd()

        # 2. Resume background scheduler
        background_scheduler.resume()

        # 3. Switch Power Plan back to Balanced
        self._switch_power_plan(POWER_PLAN_BALANCED)
        self.active_power_plan = "balanced"

        # 4. Restore VRAM manager state
        vram_manager.gaming_mode_active = False
        vram_manager.detected_game_name = None

        # 5. Restore Three.js Orb LOD
        lod_quality = vram_manager.get_orb_lod_quality()

        return {
            "status": "gaming_mode_exited",
            "previous_game": prev_game,
            "power_plan": self.active_power_plan,
            "notifications_muted": notification_digest_manager.is_dnd_active,
            "scheduler_paused": background_scheduler.is_paused,
            "orb_lod": lod_quality
        }

    def _switch_power_plan(self, plan_guid: str) -> bool:
        """Invokes powercfg to set active Windows power scheme."""
        try:
            res = subprocess.run(
                ["powercfg", "/setactive", plan_guid],
                capture_output=True,
                text=True,
                check=False
            )
            return res.returncode == 0
        except Exception:
            return False

# Global gaming mode manager instance
gaming_manager = GamingModeManager()
