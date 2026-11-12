"""
Guardian Kill Switch Sub-25ms SLA Test Suite (SAF-02).
Benchmarks synchronous halt latency and asserts sandbox process tree termination,
PID cleanup, and execution denial while halted.
"""

import time
import psutil
import pytest
import threading
from services.backend.safety.guardian import guardian
from services.backend.coding.restricted_sandbox import restricted_sandbox
from services.backend.coding.dynamic_synthesizer import dynamic_synthesizer_manager
import services.backend.tools.synthesis_tools as st


@pytest.fixture(autouse=True)
def ensure_guardian_clean():
    # Pre-test reset
    if guardian.is_halted:
        guardian.resume()
    restricted_sandbox.reset()
    dynamic_synthesizer_manager.reset()
    yield
    # Post-test cleanup
    if guardian.is_halted:
        guardian.resume()
    restricted_sandbox.reset()
    dynamic_synthesizer_manager.reset()


def test_guardian_halt_latency_and_process_cleanup():
    # Long running function code
    code = """
def long_worker():
    import time
    for _ in range(500):
        time.sleep(0.02)
    return "done"
"""
    exec_result_box = []
    pid_box = []

    def run_in_background():
        # Hook into sandbox process launch to capture PID
        res = restricted_sandbox.execute_function(
            func_code=code,
            func_name="long_worker",
            kwargs={},
            timeout=8.0,
        )
        exec_result_box.append(res)

    worker_thread = threading.Thread(target=run_in_background, daemon=True)
    worker_thread.start()

    # Wait until process is active and tracked
    child_pid = None
    for _ in range(100):
        with restricted_sandbox._lock:
            if restricted_sandbox._active_procs:
                proc = next(iter(restricted_sandbox._active_procs))
                child_pid = proc.pid
                break
        time.sleep(0.01)

    assert child_pid is not None, "Child sandbox process failed to start in time"
    assert psutil.pid_exists(child_pid), f"Child process {child_pid} should be active"

    # Trigger Guardian kill switch and measure synchronous SLA
    t0 = time.perf_counter()
    guardian.trigger("sla_benchmark_halt")
    t1 = time.perf_counter()

    halt_latency_ms = (t1 - t0) * 1000.0

    # Assert synchronous Guardian halt SLA < 25ms (typically < 1ms)
    assert halt_latency_ms < 25.0, f"Guardian SLA breached: {halt_latency_ms:.2f}ms >= 25.0ms"

    worker_thread.join(timeout=2.0)

    # Verify process tree was terminated
    assert not psutil.pid_exists(child_pid), f"Child process {child_pid} should have been terminated"

    # Verify sandbox execution result
    if exec_result_box:
        assert exec_result_box[0].killed_by_guardian is True or exec_result_box[0].success is False


def test_operations_denied_while_halted():
    guardian.trigger("test_lockout")
    restricted_sandbox.halt()
    dynamic_synthesizer_manager.halt()

    try:
        # Attempting to synthesize while halted must raise PermissionError
        with pytest.raises(PermissionError, match="halted by Guardian kill switch"):
            st.synthesize_custom_tool(
                tool_name="illegal_tool",
                task_description="Should fail",
            )

        # Attempting to run tool while halted must raise PermissionError
        with pytest.raises(PermissionError, match="halted by Guardian kill switch"):
            st.run_synthesized_tool(
                tool_name="any_tool",
                arguments={},
            )

        # Attempting direct sandbox execution while halted must raise PermissionError
        with pytest.raises(PermissionError, match="halted by Guardian kill switch"):
            restricted_sandbox.execute_function(
                func_code="def f(): return 1",
                func_name="f",
                kwargs={},
            )
    finally:
        guardian.resume()
        restricted_sandbox.reset()
        dynamic_synthesizer_manager.reset()


def test_guardian_resume_restores_clean_execution():
    guardian.trigger("temporary_halt")
    restricted_sandbox.halt()
    dynamic_synthesizer_manager.halt()

    assert guardian.is_halted is True

    # Resume
    guardian.resume()
    restricted_sandbox.reset()
    dynamic_synthesizer_manager.reset()

    assert guardian.is_halted is False

    # Should now execute normally
    res = restricted_sandbox.execute_function(
        func_code="def multiply(x, y): return x * y",
        func_name="multiply",
        kwargs={"x": 6, "y": 7},
    )
    assert res.success is True
    assert res.output == 42
