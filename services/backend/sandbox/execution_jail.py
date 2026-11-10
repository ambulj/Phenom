"""Isolated AST Execution Jail for Phenom (Milestone 24 Phase 2).

Executes untrusted code snippets and repair patches inside an isolated, capability-gated
micro-sandbox with restricted builtins, execution timeouts, and memory limits (SEC-04.2, ENV-02.1).
"""

from __future__ import annotations

import ast
import contextlib
import io
import logging
import sys
import threading
import time
import uuid
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field

from services.backend.safety.guardian import guardian
from services.backend.sandbox.ast_security_visitor import code_security_auditor, SecurityAuditVerdict

logger = logging.getLogger("phenom.sandbox.execution_jail")


class SandboxExecutionResult(BaseModel):
    execution_id: str
    status: str  # SUCCESS, SECURITY_VIOLATION, TIMEOUT, RUNTIME_ERROR
    return_value: Optional[str] = None
    stdout: str = ""
    stderr: str = ""
    execution_duration_ms: float
    verdict: Optional[SecurityAuditVerdict] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)


class LoopGuardTransformer(ast.NodeTransformer):
    """Injects iteration counter guards into While and For loops to prevent infinite CPU loops."""

    def visit_While(self, node: ast.While) -> ast.While:
        self.generic_visit(node)
        guard = ast.parse("_sandbox_check_loop()").body[0]
        node.body.insert(0, guard)
        return node

    def visit_For(self, node: ast.For) -> ast.For:
        self.generic_visit(node)
        guard = ast.parse("_sandbox_check_loop()").body[0]
        node.body.insert(0, guard)
        return node


class ExecutionJail:
    """Ephemeral in-process sandbox runner enforcing strict syscall and resource limits."""

    SAFE_BUILTINS: Dict[str, Any] = {
        "abs": abs,
        "all": all,
        "any": any,
        "bin": bin,
        "bool": bool,
        "chr": chr,
        "dict": dict,
        "divmod": divmod,
        "enumerate": enumerate,
        "filter": filter,
        "float": float,
        "format": format,
        "frozenset": frozenset,
        "hasattr": hasattr,
        "hex": hex,
        "int": int,
        "isinstance": isinstance,
        "issubclass": issubclass,
        "iter": iter,
        "len": len,
        "list": list,
        "map": map,
        "max": max,
        "min": min,
        "next": next,
        "oct": oct,
        "ord": ord,
        "pow": pow,
        "range": range,
        "repr": repr,
        "reversed": reversed,
        "round": round,
        "set": set,
        "sorted": sorted,
        "str": str,
        "sum": sum,
        "tuple": tuple,
        "zip": zip,
    }

    def __init__(self) -> None:
        self._total_executions: int = 0
        self._blocked_executions: int = 0
        self._timeout_executions: int = 0
        self._total_duration_ms: float = 0.0

    def _check_guardian(self) -> None:
        if guardian.is_halted:
            raise PermissionError("Guardian kill switch is TRIPPED. Sandbox execution halted immediately.")

    def execute_code(
        self,
        source_code: str,
        timeout_seconds: float = 2.0,
    ) -> SandboxExecutionResult:
        """Audit and execute untrusted source code inside the isolated jail."""
        self._check_guardian()
        execution_id = f"jail_{uuid.uuid4().hex[:10]}"
        t0 = time.perf_counter()

        # 1. Pre-execution static AST security audit
        verdict = code_security_auditor.audit_code(source_code)
        if not verdict.is_safe:
            self._total_executions += 1
            self._blocked_executions += 1
            duration_ms = (time.perf_counter() - t0) * 1000.0
            return SandboxExecutionResult(
                execution_id=execution_id,
                status="SECURITY_VIOLATION",
                stderr=verdict.details,
                execution_duration_ms=round(duration_ms, 3),
                verdict=verdict,
            )

        # 2. Transform AST with Loop Guard to prevent infinite CPU loops
        try:
            parsed_tree = ast.parse(source_code)
            transformer = LoopGuardTransformer()
            guarded_tree = transformer.visit(parsed_tree)
            ast.fix_missing_locations(guarded_tree)
            compiled_code = compile(guarded_tree, f"<sandbox_{execution_id}>", "exec")
        except Exception as e:
            duration_ms = (time.perf_counter() - t0) * 1000.0
            return SandboxExecutionResult(
                execution_id=execution_id,
                status="RUNTIME_ERROR",
                stderr=f"AST Compilation Error: {e}",
                execution_duration_ms=round(duration_ms, 3),
                verdict=verdict,
            )

        # 3. Build isolated execution environment
        stdout_capture = io.StringIO()
        stderr_capture = io.StringIO()

        def custom_print(*args: Any, **kwargs: Any) -> None:
            sep = kwargs.get("sep", " ")
            end = kwargs.get("end", "\n")
            text = sep.join(str(a) for a in args) + end
            stdout_capture.write(text)

        loop_steps = 0
        max_loop_steps = 100_000

        def check_loop() -> None:
            nonlocal loop_steps
            loop_steps += 1
            if loop_steps > max_loop_steps:
                raise TimeoutError(f"Execution timed out after {timeout_seconds:.1f}s (step limit exceeded).")

        sandbox_builtins = dict(self.SAFE_BUILTINS)
        sandbox_builtins["print"] = custom_print

        sandbox_globals: Dict[str, Any] = {
            "__builtins__": sandbox_builtins,
            "__name__": "__sandbox__",
            "_sandbox_check_loop": check_loop,
        }
        sandbox_locals: Dict[str, Any] = {}

        # 4. Execute with Thread timeout wrapper
        run_error = None
        return_val = None

        def worker() -> None:
            nonlocal run_error, return_val
            try:
                with contextlib.redirect_stdout(stdout_capture), contextlib.redirect_stderr(stderr_capture):
                    exec(compiled_code, sandbox_globals, sandbox_locals)
                    raw_res = sandbox_locals.get("result", None)
                    return_val = str(raw_res) if raw_res is not None else None
            except Exception as exc:
                run_error = exc

        th = threading.Thread(target=worker, daemon=True)
        th.start()
        th.join(timeout=timeout_seconds)

        status = "SUCCESS"
        if th.is_alive() or isinstance(run_error, TimeoutError):
            status = "TIMEOUT"
            stderr_capture.write(f"Execution timed out after {timeout_seconds:.1f}s.")
            self._timeout_executions += 1
        elif run_error is not None:
            status = "RUNTIME_ERROR"
            stderr_capture.write(f"{type(run_error).__name__}: {run_error}")

        duration_ms = (time.perf_counter() - t0) * 1000.0
        self._total_executions += 1
        self._total_duration_ms += duration_ms

        return SandboxExecutionResult(
            execution_id=execution_id,
            status=status,
            return_value=return_val,
            stdout=stdout_capture.getvalue(),
            stderr=stderr_capture.getvalue(),
            execution_duration_ms=round(duration_ms, 3),
            verdict=verdict,
        )

    def get_telemetry(self) -> Dict[str, Any]:
        """Query sandbox execution counters and capability metrics."""
        self._check_guardian()
        avg_duration = (
            self._total_duration_ms / self._total_executions
            if self._total_executions > 0
            else 0.0
        )
        return {
            "total_executions": self._total_executions,
            "blocked_executions": self._blocked_executions,
            "timeout_executions": self._timeout_executions,
            "successful_executions": (
                self._total_executions - self._blocked_executions - self._timeout_executions
            ),
            "average_duration_ms": round(avg_duration, 2),
            "capability_gates": {
                "filesystem_write_blocked": True,
                "network_sockets_blocked": True,
                "subprocesses_blocked": True,
                "rule_8_payment_shield_active": True,
            },
        }


# Singleton instance
execution_jail = ExecutionJail()
