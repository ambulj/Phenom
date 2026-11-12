"""
Unit tests for Virtual Desktop Backend and Lifecycle Manager.
"""

import time
import pytest
from services.backend.automation.virtual_desktop_backend import (
    MockVirtualDesktopBackend,
    IVirtualDesktopBackend,
)
from services.backend.automation.virtual_desktop_manager import (
    VirtualDesktopManager,
)
from services.backend.safety.guardian import guardian


@pytest.fixture
def mock_backend():
    return MockVirtualDesktopBackend()


@pytest.fixture
def vdesk_manager(mock_backend):
    mgr = VirtualDesktopManager(backend=mock_backend)
    yield mgr
    mgr.halt()


def test_mock_backend_implements_interface(mock_backend):
    assert isinstance(mock_backend, IVirtualDesktopBackend)
    hdesk = mock_backend.create_desktop("TestDesktop")
    assert hdesk > 0

    pid = mock_backend.launch_process("notepad.exe", None, "TestDesktop")
    assert pid > 0

    windows = mock_backend.enum_desktop_windows(hdesk)
    assert len(windows) == 1
    assert windows[0].title.startswith("Mock")
    assert windows[0].is_visible is True

    rect = mock_backend.get_window_rect(windows[0].hwnd)
    assert rect == (100, 100, 900, 700)

    closed = mock_backend.close_desktop(hdesk)
    assert closed is True


def test_manager_create_and_get_session(vdesk_manager):
    session = vdesk_manager.create_desktop(session_id="test-session-1")
    assert session.session_id == "test-session-1"
    assert session.is_active is True
    assert session.desktop_name == "PhenomVD_test-session-1"

    retrieved = vdesk_manager.get_session("test-session-1")
    assert retrieved is not None
    assert retrieved.session_id == session.session_id

    active = vdesk_manager.list_active_sessions()
    assert len(active) == 1
    assert active[0].session_id == "test-session-1"


def test_manager_launch_isolated_app_and_pid_tracking(vdesk_manager):
    session = vdesk_manager.create_desktop()
    pid, hwnd = vdesk_manager.launch_isolated_app(session.session_id, "calc.exe")

    assert pid > 0
    assert hwnd > 0
    assert pid in session.pids
    # Verify PID is registered with Guardian
    assert pid in guardian._tracked_pids

    windows = vdesk_manager.enum_windows(session.session_id)
    assert any(w.hwnd == hwnd for w in windows)


def test_manager_close_desktop_cleans_up(vdesk_manager):
    session = vdesk_manager.create_desktop()
    pid, _ = vdesk_manager.launch_isolated_app(session.session_id, "notepad.exe")

    assert pid in guardian._tracked_pids
    assert session.is_active is True

    success = vdesk_manager.close_desktop(session.session_id)
    assert success is True
    assert session.is_active is False
    assert len(session.pids) == 0
    # Verified untracked from guardian
    assert pid not in guardian._tracked_pids


def test_manager_synchronous_halt_latency(vdesk_manager):
    # Spawn multiple sessions with simulated processes
    s1 = vdesk_manager.create_desktop("s1")
    pid1, _ = vdesk_manager.launch_isolated_app("s1", "app1.exe")

    s2 = vdesk_manager.create_desktop("s2")
    pid2, _ = vdesk_manager.launch_isolated_app("s2", "app2.exe")

    assert len(vdesk_manager.list_active_sessions()) == 2
    assert pid1 in guardian._tracked_pids
    assert pid2 in guardian._tracked_pids

    # Measure synchronous halt latency
    t0 = time.perf_counter()
    vdesk_manager.halt()
    elapsed_ms = (time.perf_counter() - t0) * 1000.0

    # Must be well below 25ms SLA (typically < 1ms)
    assert elapsed_ms < 25.0
    assert len(vdesk_manager.list_active_sessions()) == 0
    assert pid1 not in guardian._tracked_pids
    assert pid2 not in guardian._tracked_pids


def test_manager_rejects_when_guardian_halted(vdesk_manager):
    guardian._halted = True
    try:
        with pytest.raises(PermissionError, match="Guardian kill switch is active"):
            vdesk_manager.create_desktop("blocked")

        # Create session before halt
        guardian._halted = False
        s = vdesk_manager.create_desktop("s-temp")
        guardian._halted = True

        with pytest.raises(PermissionError, match="Guardian kill switch is active"):
            vdesk_manager.launch_isolated_app("s-temp", "cmd.exe")
    finally:
        guardian._halted = False
