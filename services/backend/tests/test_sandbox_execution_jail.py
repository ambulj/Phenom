"""Unit and Safety Integration Tests for Dynamic Micro-Sandbox & Isolated AST Execution Jail.

Validates AST static security visitor, disallowed module blocking, jail escape detection,
safe sandboxed execution, timeout enforcement, Rule 8 anti-checkout defense, and Guardian SLA.
Phase 24-02 (SEC-04, ENV-02, SAF-01, SAF-02).
"""

import time
import pytest

from services.backend.sandbox.ast_security_visitor import (
    CodeSecurityAuditor,
    Rule8ViolationError as SecRule8Error,
)
from services.backend.sandbox.execution_jail import ExecutionJail
from services.backend.safety.guardian import guardian
from services.backend.safety.registry import registry
import services.backend.tools.sandbox_jail_tools  # Ensure tools are loaded


@pytest.fixture(autouse=True)
def reset_guardian():
    guardian.resume()
    yield
    guardian.resume()


def test_ast_security_visitor_detects_unsafe_code():
    """Verify AST visitor flags dangerous imports, calls, and escape vectors."""
    auditor = CodeSecurityAuditor()

    # 1. Unsafe module imports
    v1 = auditor.audit_code("import os\nprint(os.name)")
    assert not v1.is_safe
    assert "os" in v1.disallowed_imports
    assert v1.risk_level in ("HIGH", "CRITICAL")

    v2 = auditor.audit_code("from subprocess import Popen\nPopen(['calc'])")
    assert not v2.is_safe
    assert "subprocess" in v2.disallowed_imports

    v3 = auditor.audit_code("import socket\ns = socket.socket()")
    assert not v3.is_safe
    assert "socket" in v3.disallowed_imports

    # 2. Dangerous calls
    v4 = auditor.audit_code("x = eval('2 + 2')")
    assert not v4.is_safe
    assert "eval" in v4.dangerous_calls

    v5 = auditor.audit_code("f = open('secret.txt', 'w')")
    assert not v5.is_safe
    assert "open" in v5.dangerous_calls

    # 3. Jail escape vectors
    v6 = auditor.audit_code("classes = ().__class__.__bases__[0].__subclasses__()")
    assert not v6.is_safe
    assert any(attr in v6.jail_escape_vectors for attr in ("__class__", "__bases__", "__subclasses__"))
    assert v6.risk_level == "CRITICAL"

    # 4. Completely safe code
    v_safe = auditor.audit_code(
        "def compute_fib(n):\n"
        "    a, b = 0, 1\n"
        "    for _ in range(n):\n"
        "        a, b = b, a + b\n"
        "    return a\n"
        "result = compute_fib(10)\n"
        "print('Fibonacci:', result)\n"
    )
    assert v_safe.is_safe
    assert v_safe.risk_level == "SAFE"
    assert len(v_safe.disallowed_imports) == 0


def test_execution_jail_safe_code_run():
    """Verify execution jail runs safe code, captures stdout, and extracts result."""
    jail = ExecutionJail()

    code = (
        "numbers = [1, 2, 3, 4, 5]\n"
        "total = sum(numbers)\n"
        "print('Sum of array:', total)\n"
        "result = total * 2\n"
    )

    res = jail.execute_code(code)
    assert res.status == "SUCCESS"
    assert "Sum of array: 15" in res.stdout
    assert res.return_value == "30"
    assert res.execution_duration_ms > 0
    assert res.verdict.is_safe is True


def test_execution_jail_blocks_security_violations():
    """Verify execution jail halts disallowed code before execution."""
    jail = ExecutionJail()

    res = jail.execute_code("import os\nos.system('echo compromised')")
    assert res.status == "SECURITY_VIOLATION"
    assert "Security violations detected" in res.stderr
    assert res.return_value is None


def test_execution_jail_timeout_enforcement():
    """Verify execution jail enforces timeout limits on infinite loops."""
    jail = ExecutionJail()

    infinite_loop_code = "while True:\n    pass\n"

    t0 = time.perf_counter()
    res = jail.execute_code(infinite_loop_code, timeout_seconds=0.5)
    duration = time.perf_counter() - t0

    assert res.status == "TIMEOUT"
    assert "timed out after 0.5s" in res.stderr
    assert duration < 2.0  # Must terminate cleanly near timeout


def test_rule_8_anti_checkout_enforcement():
    """Verify Rule 8 payment / checkout rejection in security visitor and execution jail."""
    auditor = CodeSecurityAuditor()
    jail = ExecutionJail()

    with pytest.raises(SecRule8Error, match="Rule 8 violation"):
        auditor.audit_code("def process_checkout_payment(): pass")

    with pytest.raises(SecRule8Error, match="Rule 8 violation"):
        jail.execute_code("credit_card_cvv = '123'\nprint(credit_card_cvv)")


def test_guardian_kill_switch_sla_halt():
    """Verify Guardian kill switch halts audit and execution in < 25.0ms SLA."""
    guardian.trigger("Emergency test halt")
    assert guardian.is_halted

    auditor = CodeSecurityAuditor()
    jail = ExecutionJail()

    t0 = time.perf_counter()
    with pytest.raises(PermissionError, match="Guardian kill switch is TRIPPED"):
        auditor.audit_code("x = 1 + 1")
    t1 = time.perf_counter()
    latency_ms = (t1 - t0) * 1000.0
    assert latency_ms < 25.0, f"Halt latency {latency_ms:.4f}ms exceeded 25.0ms SLA"

    t0 = time.perf_counter()
    with pytest.raises(PermissionError, match="Guardian kill switch is TRIPPED"):
        jail.execute_code("x = 1 + 1")
    t1 = time.perf_counter()
    latency_ms = (t1 - t0) * 1000.0
    assert latency_ms < 25.0, f"Halt latency {latency_ms:.4f}ms exceeded 25.0ms SLA"

    guardian.resume()


def test_tool_registry_and_previews():
    """Verify tool registration, tier classifications, and preview generations."""
    val_tool = registry.get("validate_code_security")
    assert val_tool is not None
    assert val_tool.tier == 0
    preview_val = val_tool.generate_preview({"source_code": "import math\nprint(math.pi)"})
    assert "math" in preview_val

    exec_tool = registry.get("execute_in_sandbox_jail")
    assert exec_tool is not None
    assert exec_tool.tier == 1
    preview_exec = exec_tool.generate_preview({"source_code": "a=1", "timeout_seconds": 3.0})
    assert "3.0" in preview_exec

    telem_tool = registry.get("get_sandbox_telemetry")
    assert telem_tool is not None
    assert telem_tool.tier == 0
    preview_telem = telem_tool.generate_preview({})
    assert "metrics" in preview_telem
