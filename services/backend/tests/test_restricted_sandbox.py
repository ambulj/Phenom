"""
Unit tests for Restricted Subprocess Sandbox (SYN-01, SAF-02).
Tests memory ceiling, execution timeouts, offline network flags,
and Guardian kill switch integration.
"""

import time
import pytest
from services.backend.safety.guardian import guardian
from services.backend.coding.restricted_sandbox import restricted_sandbox


def test_sandbox_safe_execution():
    code = """
def compute_stats(numbers: list) -> dict:
    total = sum(numbers)
    count = len(numbers)
    avg = total / count if count > 0 else 0
    return {"total": total, "count": count, "avg": avg}
"""
    result = restricted_sandbox.execute_function(
        func_code=code,
        func_name="compute_stats",
        kwargs={"numbers": [10, 20, 30, 40]},
    )
    assert result.success is True
    assert result.output["total"] == 100
    assert result.output["count"] == 4
    assert result.output["avg"] == 25.0
    assert result.duration_ms > 0
    assert result.timed_out is False
    assert result.killed_by_oom is False
    assert result.killed_by_guardian is False


def test_sandbox_timeout_enforcement():
    # Infinite loop code with short timeout (1.0s)
    infinite_loop_code = """
def runaway_task() -> int:
    import time
    while True:
        time.sleep(0.05)
    return 0
"""
    start = time.perf_counter()
    result = restricted_sandbox.execute_function(
        func_code=infinite_loop_code,
        func_name="runaway_task",
        kwargs={},
        timeout=1.0,
    )
    elapsed = time.perf_counter() - start

    assert result.success is False
    assert result.timed_out is True
    assert "timed out" in (result.error or "").lower()
    assert elapsed < 3.0  # Must terminate promptly


def test_sandbox_memory_cap_enforcement():
    # Allocate large memory block exceeding max_memory_mb
    memory_hog_code = """
def allocate_huge_block() -> int:
    data = []
    for _ in range(200):
        data.append(bytearray(2 * 1024 * 1024))  # Allocate 400 MB
    return len(data)
"""
    result = restricted_sandbox.execute_function(
        func_code=memory_hog_code,
        func_name="allocate_huge_block",
        kwargs={},
        timeout=5.0,
        max_memory_mb=100.0,  # 100 MB cap
    )
    assert result.success is False
    assert result.killed_by_oom is True
    assert "memory limit exceeded" in (result.error or "").lower()


def test_sandbox_offline_env_sanitization():
    check_env_code = """
def check_env() -> dict:
    import os
    return {
        "offline_mode": os.environ.get("PHENOM_OFFLINE_MODE"),
        "pip_no_index": os.environ.get("PIP_NO_INDEX"),
        "http_proxy": os.environ.get("HTTP_PROXY"),
    }
"""
    result = restricted_sandbox.execute_function(
        func_code=check_env_code,
        func_name="check_env",
        kwargs={},
    )
    assert result.success is True
    assert result.output["offline_mode"] == "1"
    assert result.output["pip_no_index"] == "1"
    assert "127.0.0.1:0" in result.output["http_proxy"]


def test_sandbox_unit_test_execution():
    test_code = """
def add(a, b): return a + b
assert add(2, 3) == 5
assert add(-1, 1) == 0
"""
    result = restricted_sandbox.execute_unit_test(test_code)
    assert result.success is True
    assert "Tests passed" in str(result.output)

    bad_test_code = """
assert 2 + 2 == 5
"""
    bad_result = restricted_sandbox.execute_unit_test(bad_test_code)
    assert bad_result.success is False
    assert "AssertionError" in str(bad_result.stderr) or "AssertionError" in str(bad_result.error)


def test_sandbox_guardian_halt():
    restricted_sandbox.halt()
    try:
        with pytest.raises(PermissionError, match="halted by Guardian kill switch"):
            restricted_sandbox.execute_function(
                func_code="def f(): return 1",
                func_name="f",
                kwargs={},
            )
    finally:
        restricted_sandbox.reset()
