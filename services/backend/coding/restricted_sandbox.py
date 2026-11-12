"""
Restricted Subprocess Sandbox for Synthesized Micro-Plugins.
Part of Phenom Milestone 11.0 Phase 1 (SYN-01, SAF-01, SAF-02).

Enforces:
- In-memory execution over stdio without temporary disk scripts
- 256 MB RSS memory ceiling
- 5.0s default timeout (10.0s hard maximum)
- Network isolation (offline proxies)
- Synchronous sub-25ms Guardian kill switch SLA with process tree cleanup
"""

import os
import sys
import json
import time
import psutil
import subprocess
import threading
from typing import Dict, Any, Optional, Set
from services.backend.safety.guardian import guardian
from services.backend.schemas.synthesis import SandboxExecutionResult

DEFAULT_TIMEOUT_SEC: float = 5.0
MAX_TIMEOUT_SEC: float = 10.0
DEFAULT_MAX_MEMORY_BYTES: int = 256 * 1024 * 1024  # 256 MB

RUNNER_BOOTSTRAP = r'''
import sys
import json
import traceback

def main():
    try:
        raw_input = sys.stdin.read()
        if not raw_input or not raw_input.strip():
            print(json.dumps({"success": False, "error": "Empty execution payload"}))
            return
        payload = json.loads(raw_input)
        mode = payload.get("mode")
        
        namespace = {"__builtins__": __builtins__}
        
        if mode == "function":
            code = payload["code"]
            func_name = payload["func_name"]
            kwargs = payload.get("kwargs", {})
            exec(compile(code, "<sandboxed_tool>", "exec"), namespace)
            if func_name not in namespace:
                print(json.dumps({"success": False, "error": f"Function '{func_name}' was not defined in submitted code"}))
                return
            fn = namespace[func_name]
            result = fn(**kwargs)
            try:
                serialized = json.dumps({"success": True, "output": result})
            except (TypeError, ValueError):
                serialized = json.dumps({"success": True, "output": str(result)})
            print(serialized)
            
        elif mode == "test":
            test_code = payload["test_code"]
            exec(compile(test_code, "<sandboxed_test>", "exec"), namespace)
            print(json.dumps({"success": True, "output": "Tests passed successfully"}))
            
        else:
            print(json.dumps({"success": False, "error": f"Unknown sandbox execution mode: {mode}"}))
            
    except Exception as e:
        err_msg = traceback.format_exc()
        err_str = str(e).strip() or e.__class__.__name__
        print(json.dumps({"success": False, "error": err_str, "traceback": err_msg}))

if __name__ == "__main__":
    main()
'''


def _kill_process_tree(pid: int):
    """Recursively terminate all child processes then the parent process on Windows."""
    try:
        parent = psutil.Process(pid)
        children = parent.children(recursive=True)
        for child in children:
            try:
                child.kill()
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                pass
        try:
            parent.kill()
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            pass
    except (psutil.NoSuchProcess, psutil.AccessDenied):
        pass


class RestrictedToolSandbox:
    """
    Subprocess execution sandbox providing process, memory, network, and timeout isolation.
    """

    def __init__(self):
        self._halted: bool = False
        self._active_procs: Set[subprocess.Popen] = set()
        self._lock = threading.Lock()

    def halt(self):
        """Immediately halts all running sandbox subprocesses."""
        self._halted = True
        with self._lock:
            for proc in list(self._active_procs):
                _kill_process_tree(proc.pid)

    def reset(self):
        """Resets the sandbox from halted state."""
        self._halted = False

    def _sanitize_env(self) -> Dict[str, str]:
        """Strip sensitive credentials and enforce offline network proxies."""
        clean_env = os.environ.copy()
        for k in list(clean_env.keys()):
            upper_k = k.upper()
            if any(term in upper_k for term in ("KEY", "TOKEN", "SECRET", "PASSWORD", "CREDENTIAL", "AUTH", "CIPHER")):
                del clean_env[k]

        clean_env["HTTP_PROXY"] = "http://127.0.0.1:0"
        clean_env["HTTPS_PROXY"] = "http://127.0.0.1:0"
        clean_env["ALL_PROXY"] = "http://127.0.0.1:0"
        clean_env["PIP_NO_INDEX"] = "1"
        clean_env["PHENOM_OFFLINE_MODE"] = "1"
        clean_env["PYTHONUNBUFFERED"] = "1"
        return clean_env

    def _run_subprocess(
        self,
        payload: Dict[str, Any],
        timeout: float,
        max_memory_bytes: int,
    ) -> SandboxExecutionResult:
        if self._halted or guardian.is_halted:
            raise PermissionError("Subprocess sandbox execution halted by Guardian kill switch.")

        timeout = min(max(0.1, timeout), MAX_TIMEOUT_SEC)
        start_time = time.perf_counter()
        clean_env = self._sanitize_env()
        payload_bytes = json.dumps(payload).encode("utf-8")

        proc = subprocess.Popen(
            [sys.executable, "-u", "-c", RUNNER_BOOTSTRAP],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            env=clean_env,
        )

        with self._lock:
            self._active_procs.add(proc)
        guardian.track_pid(proc.pid)

        monitor_flags = {
            "killed_by_oom": False,
            "killed_by_guardian": False,
            "peak_memory_mb": 0.0,
        }
        stop_monitoring = threading.Event()

        def _monitor_loop():
            try:
                p = psutil.Process(proc.pid)
                while not stop_monitoring.is_set():
                    if guardian.is_halted or self._halted:
                        monitor_flags["killed_by_guardian"] = True
                        _kill_process_tree(proc.pid)
                        break

                    try:
                        mem = p.memory_info().rss
                        for child in p.children(recursive=True):
                            try:
                                mem += child.memory_info().rss
                            except (psutil.NoSuchProcess, psutil.AccessDenied):
                                pass
                        mem_mb = mem / (1024 * 1024)
                        if mem_mb > monitor_flags["peak_memory_mb"]:
                            monitor_flags["peak_memory_mb"] = mem_mb

                        if mem > max_memory_bytes:
                            monitor_flags["killed_by_oom"] = True
                            _kill_process_tree(proc.pid)
                            break
                    except (psutil.NoSuchProcess, psutil.AccessDenied):
                        break

                    time.sleep(0.02)
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                pass

        monitor_thread = threading.Thread(target=_monitor_loop, daemon=True)
        monitor_thread.start()

        timed_out = False
        stdout_data = ""
        stderr_data = ""

        try:
            # Use proc.communicate to prevent pipe deadlock
            raw_stdout, raw_stderr = proc.communicate(input=payload_bytes, timeout=timeout)
            stdout_data = raw_stdout.decode("utf-8", errors="replace")
            stderr_data = raw_stderr.decode("utf-8", errors="replace")
        except subprocess.TimeoutExpired:
            timed_out = True
            _kill_process_tree(proc.pid)
            try:
                raw_stdout, raw_stderr = proc.communicate(timeout=0.5)
                stdout_data = raw_stdout.decode("utf-8", errors="replace")
                stderr_data = raw_stderr.decode("utf-8", errors="replace")
            except Exception:
                pass
        finally:
            stop_monitoring.set()
            monitor_thread.join(timeout=0.5)
            with self._lock:
                self._active_procs.discard(proc)
            guardian.untrack_pid(proc.pid)

        duration_ms = (time.perf_counter() - start_time) * 1000.0

        if monitor_flags["killed_by_guardian"]:
            return SandboxExecutionResult(
                success=False,
                output=None,
                stdout=stdout_data,
                stderr=stderr_data,
                duration_ms=duration_ms,
                peak_memory_mb=monitor_flags["peak_memory_mb"],
                killed_by_guardian=True,
                error="Process terminated by Guardian kill switch.",
            )

        if monitor_flags["killed_by_oom"]:
            return SandboxExecutionResult(
                success=False,
                output=None,
                stdout=stdout_data,
                stderr=stderr_data,
                duration_ms=duration_ms,
                peak_memory_mb=monitor_flags["peak_memory_mb"],
                killed_by_oom=True,
                error=f"Process terminated: memory limit exceeded ({monitor_flags['peak_memory_mb']:.1f} MB > {max_memory_bytes / (1024*1024):.1f} MB)",
            )

        if timed_out:
            return SandboxExecutionResult(
                success=False,
                output=None,
                stdout=stdout_data,
                stderr=stderr_data,
                duration_ms=duration_ms,
                peak_memory_mb=monitor_flags["peak_memory_mb"],
                timed_out=True,
                error=f"Process execution timed out after {timeout:.1f}s",
            )

        # Parse response from runner stdout
        if not stdout_data.strip():
            return SandboxExecutionResult(
                success=False,
                output=None,
                stdout=stdout_data,
                stderr=stderr_data,
                duration_ms=duration_ms,
                peak_memory_mb=monitor_flags["peak_memory_mb"],
                error=f"Empty process output. Stderr: {stderr_data}",
            )

        try:
            res_json = json.loads(stdout_data.strip())
            is_success = res_json.get("success", False)
            err_msg = res_json.get("error")
            if not is_success and not err_msg:
                err_msg = res_json.get("traceback") or "Execution failed"
            return SandboxExecutionResult(
                success=is_success,
                output=res_json.get("output"),
                stdout=stdout_data,
                stderr=stderr_data,
                duration_ms=duration_ms,
                peak_memory_mb=monitor_flags["peak_memory_mb"],
                error=err_msg,
            )
        except json.JSONDecodeError:
            return SandboxExecutionResult(
                success=False,
                output=None,
                stdout=stdout_data,
                stderr=stderr_data,
                duration_ms=duration_ms,
                peak_memory_mb=monitor_flags["peak_memory_mb"],
                error=f"Invalid JSON from sandbox runner: {stdout_data[:200]}",
            )

    def execute_function(
        self,
        func_code: str,
        func_name: str,
        kwargs: Dict[str, Any],
        timeout: float = DEFAULT_TIMEOUT_SEC,
        max_memory_mb: float = 256.0,
    ) -> SandboxExecutionResult:
        payload = {
            "mode": "function",
            "code": func_code,
            "func_name": func_name,
            "kwargs": kwargs,
        }
        return self._run_subprocess(
            payload=payload,
            timeout=timeout,
            max_memory_bytes=int(max_memory_mb * 1024 * 1024),
        )

    def execute_unit_test(
        self,
        test_code: str,
        timeout: float = DEFAULT_TIMEOUT_SEC,
    ) -> SandboxExecutionResult:
        payload = {
            "mode": "test",
            "test_code": test_code,
        }
        return self._run_subprocess(
            payload=payload,
            timeout=timeout,
            max_memory_bytes=DEFAULT_MAX_MEMORY_BYTES,
        )


# Global singleton instance
restricted_sandbox = RestrictedToolSandbox()
