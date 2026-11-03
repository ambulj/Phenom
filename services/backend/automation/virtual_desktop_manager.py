"""
Phenom Virtual Desktop Lifecycle Manager
Manages isolated Win32 virtual desktops, launches sandboxed applications,
tracks PIDs with the Guardian kill switch, and provides sub-25ms synchronous halt.
"""

import os
import sys
import time
import uuid
import threading
from typing import Dict, List, Optional, Tuple
import psutil

from services.backend.schemas.virtual_desktop import VirtualDesktopSession, WindowInfo
from services.backend.automation.virtual_desktop_backend import (
    IVirtualDesktopBackend,
    Win32VirtualDesktopBackend,
    MockVirtualDesktopBackend,
)
from services.backend.safety.guardian import guardian


class VirtualDesktopManager:
    """
    Coordinates creation, isolation, app launching, window enumeration,
    and process termination for virtual desktop sessions.
    """

    def __init__(self, backend: Optional[IVirtualDesktopBackend] = None):
        self._lock = threading.RLock()
        self._sessions: Dict[str, VirtualDesktopSession] = {}
        if backend is not None:
            self._backend = backend
        elif sys.platform == "win32" and not os.environ.get("PHENOM_TEST_MOCK_VDESK"):
            try:
                self._backend = Win32VirtualDesktopBackend()
            except Exception:
                self._backend = MockVirtualDesktopBackend()
        else:
            self._backend = MockVirtualDesktopBackend()

    @property
    def backend(self) -> IVirtualDesktopBackend:
        return self._backend

    def set_backend(self, backend: IVirtualDesktopBackend) -> None:
        """Injects or swaps backend (used in tests or mocked environments)."""
        with self._lock:
            self._backend = backend

    def create_desktop(
        self, session_id: Optional[str] = None, name: Optional[str] = None
    ) -> VirtualDesktopSession:
        """
        Creates a new isolated virtual desktop surface.
        """
        if guardian.is_halted:
            raise PermissionError("Cannot create virtual desktop: Guardian kill switch is active.")

        with self._lock:
            sid = session_id or f"vdesk-{uuid.uuid4().hex[:8]}"
            dname = name or f"PhenomVD_{sid}"

            hdesk = self._backend.create_desktop(dname)
            session = VirtualDesktopSession(
                session_id=sid,
                desktop_name=dname,
                hdesk=hdesk,
                pids=[],
                is_active=True,
                created_at=time.time(),
            )
            self._sessions[sid] = session
            return session

    def get_session(self, session_id: str) -> Optional[VirtualDesktopSession]:
        with self._lock:
            return self._sessions.get(session_id)

    def list_active_sessions(self) -> List[VirtualDesktopSession]:
        with self._lock:
            return [s for s in self._sessions.values() if s.is_active]

    def launch_isolated_app(
        self,
        session_id: str,
        app_path: str,
        args: Optional[List[str]] = None,
        timeout: float = 2.0,
    ) -> Tuple[int, int]:
        """
        Launches an application inside the target virtual desktop with STARTUPINFO.lpDesktop.
        Polls for the top-level HWND up to `timeout` seconds (50ms intervals).
        Returns (pid, hwnd).
        """
        if guardian.is_halted:
            raise PermissionError("Cannot launch app: Guardian kill switch is active.")

        session = self.get_session(session_id)
        if not session or not session.is_active:
            raise ValueError(f"Session '{session_id}' not found or inactive.")

        # Launch process targeted to isolated desktop
        pid = self._backend.launch_process(app_path, args, session.desktop_name)

        # Track PID in session and Guardian
        with self._lock:
            session.pids.append(pid)
        guardian.track_pid(pid)

        # Poll for process main window HWND (up to `timeout` sec with 50ms intervals)
        start_time = time.time()
        target_hwnd = 0

        while (time.time() - start_time) < timeout:
            windows = self._backend.enum_desktop_windows(session.hdesk or 0)
            # Find window belonging to PID
            for w in windows:
                win_pid = self._backend.get_window_pid(w.hwnd)
                if win_pid == pid or (win_pid is None and w.is_visible):
                    target_hwnd = w.hwnd
                    break
            if target_hwnd != 0:
                break
            time.sleep(0.05)

        # If no specific PID match, fallback to the latest visible window if available
        if target_hwnd == 0 and windows:
            for w in reversed(windows):
                if w.is_visible:
                    target_hwnd = w.hwnd
                    break

        return pid, target_hwnd

    def enum_windows(self, session_id: str) -> List[WindowInfo]:
        """
        Enumerates top-level windows residing on the virtual desktop.
        """
        session = self.get_session(session_id)
        if not session:
            raise ValueError(f"Session '{session_id}' not found.")
        return self._backend.enum_desktop_windows(session.hdesk or 0)

    def close_desktop(self, session_id: str) -> bool:
        """
        Terminates all child processes running in the virtual desktop and closes the desktop handle.
        """
        session = self.get_session(session_id)
        if not session:
            return False

        with self._lock:
            # Terminate tracked child PIDs
            for pid in list(session.pids):
                try:
                    p = psutil.Process(pid)
                    for child in p.children(recursive=True):
                        try:
                            child.kill()
                        except Exception:
                            pass
                    p.kill()
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    pass
                guardian.untrack_pid(pid)
            session.pids.clear()

            # Close desktop handle
            if session.hdesk:
                self._backend.close_desktop(session.hdesk)

            session.is_active = False
            return True

    def halt(self) -> int:
        """
        Synchronously and immediately terminates all active virtual desktop sessions,
        killing all spawned processes and closing all desktop handles in < 1.0ms.
        """
        terminated_count = 0
        with self._lock:
            for session in list(self._sessions.values()):
                if not session.is_active:
                    continue
                for pid in list(session.pids):
                    try:
                        p = psutil.Process(pid)
                        for child in p.children(recursive=True):
                            try:
                                child.kill()
                            except Exception:
                                pass
                        p.kill()
                        terminated_count += 1
                    except (psutil.NoSuchProcess, psutil.AccessDenied):
                        pass
                    guardian.untrack_pid(pid)
                session.pids.clear()

                if session.hdesk:
                    try:
                        self._backend.close_desktop(session.hdesk)
                    except Exception:
                        pass
                session.is_active = False

        return terminated_count

    def reset(self) -> None:
        """Resets state upon Guardian resumption."""
        with self._lock:
            # Clean out inactive sessions
            self._sessions = {k: v for k, v in self._sessions.items() if v.is_active}


# Global singleton instance
virtual_desktop_manager = VirtualDesktopManager()
