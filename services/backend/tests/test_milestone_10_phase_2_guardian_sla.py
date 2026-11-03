"""
Milestone 10.0 Phase 2 Guardian Kill Switch SLA Benchmark and Verification Suite (SAF-02).
Asserts sub-25ms synchronous halt SLA (< 1ms typical), process termination,
desktop handle cleanup, and permission rejection during halt.
"""

import time
import pytest
from services.backend.safety.guardian import guardian
from services.backend.automation.virtual_desktop_backend import MockVirtualDesktopBackend
from services.backend.automation.virtual_desktop_manager import (
    VirtualDesktopManager,
    virtual_desktop_manager,
)
from services.backend.automation.virtual_desktop_driver import (
    VirtualDesktopDriver,
    virtual_desktop_driver,
)
from services.backend.automation.visual_gui_controller import (
    VisualGuiController,
    visual_gui_controller,
)
from services.backend.schemas.virtual_desktop import (
    GuiActionRequest,
    ActionType,
)


@pytest.fixture
def mock_sla_env():
    backend = MockVirtualDesktopBackend()
    manager = VirtualDesktopManager(backend=backend)
    driver = VirtualDesktopDriver(backend=backend)
    controller = VisualGuiController(driver=driver, manager=manager)

    # Wire to global manager / controller for full integration
    virtual_desktop_manager.set_backend(backend)
    virtual_desktop_driver._backend = backend
    visual_gui_controller._driver = virtual_desktop_driver
    visual_gui_controller._manager = virtual_desktop_manager

    yield manager, controller, backend

    manager.halt()
    guardian.resume()


def test_guardian_halt_sla_latency_under_25ms(mock_sla_env):
    manager, _, _ = mock_sla_env

    # 1. Create multiple active virtual desktops with simulated processes
    s1 = manager.create_desktop("desk-alpha")
    pid1, hwnd1 = manager.launch_isolated_app(s1.session_id, "proc1.exe")

    s2 = manager.create_desktop("desk-beta")
    pid2, hwnd2 = manager.launch_isolated_app(s2.session_id, "proc2.exe")

    s3 = manager.create_desktop("desk-gamma")
    pid3, hwnd3 = manager.launch_isolated_app(s3.session_id, "proc3.exe")

    assert pid1 in guardian._tracked_pids
    assert pid2 in guardian._tracked_pids
    assert pid3 in guardian._tracked_pids
    assert len(manager.list_active_sessions()) == 3

    # 2. Benchmark synchronous halt latency
    t0 = time.perf_counter()
    manager.halt()
    elapsed_ms = (time.perf_counter() - t0) * 1000.0

    # Strict SLA check: must be < 25.0ms (typical < 1.0ms)
    assert elapsed_ms < 25.0
    print(f"\n[Guardian SLA] Measured synchronous halt latency: {elapsed_ms:.4f} ms (SLA < 25.0 ms)")

    # Typical execution assertion
    assert elapsed_ms < 5.0

    # 3. Verify all processes untracked and sessions closed
    assert len(manager.list_active_sessions()) == 0
    assert pid1 not in guardian._tracked_pids
    assert pid2 not in guardian._tracked_pids
    assert pid3 not in guardian._tracked_pids


def test_guardian_trigger_integration(mock_sla_env):
    manager, _, _ = mock_sla_env

    s = manager.create_desktop("desk-live")
    pid, _ = manager.launch_isolated_app(s.session_id, "notepad.exe")

    assert pid in guardian._tracked_pids

    # Trigger guardian kill switch
    t0 = time.perf_counter()
    guardian.trigger(reason="Test SLA trigger")
    elapsed_ms = (time.perf_counter() - t0) * 1000.0

    assert elapsed_ms < 25.0
    assert guardian.is_halted is True
    assert pid not in guardian._tracked_pids


def test_operations_rejected_during_guardian_halt(mock_sla_env):
    manager, controller, _ = mock_sla_env

    guardian._halted = True
    try:
        # Create desktop rejected
        with pytest.raises(PermissionError, match="Guardian kill switch is active"):
            manager.create_desktop("blocked-desk")

        # Action execution rejected
        req = GuiActionRequest(
            session_id="blocked-sess",
            hwnd=1234,
            action_type=ActionType.CLICK,
            x=10,
            y=10,
        )
        with pytest.raises(PermissionError, match="Guardian kill switch is active"):
            controller.execute_action(req)

    finally:
        guardian.resume()


def test_clean_resumption_after_guardian_reset(mock_sla_env):
    manager, controller, _ = mock_sla_env

    # Halt and verify
    guardian._halted = True
    manager.halt()
    assert guardian.is_halted is True

    # Resume
    guardian.resume()
    manager.reset()
    assert guardian.is_halted is False

    # Verify normal operations succeed again
    new_sess = manager.create_desktop("resumed-desk")
    assert new_sess.is_active is True
    pid, hwnd = manager.launch_isolated_app(new_sess.session_id, "calc.exe")
    assert pid > 0
    assert hwnd > 0
    assert pid in guardian._tracked_pids
