"""
Phenom Code Runner Engine (Task 7i)
Executes build, test, and script commands in an isolated workspace under strict safety constraints:
1. Hard Runtime Cap: Max 120s execution timeout per process.
2. Process Tree Cap: Maximum 4 child processes per execution tree.
3. Network Isolation: Offline test runs by default (proxies blocked, PIP_NO_INDEX).
4. Guardian Kill Switch: Registered PIDs killed recursively with SIGKILL on kill switch activation.
"""

import os
import sys
import time
import subprocess
import threading
from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field
import psutil

from services.backend.safety.guardian import GuardianKillSwitch
# Import the global guardian instance
try:
    from services.backend.safety.engine import guardian
except ImportError:
    guardian = GuardianKillSwitch()

class ExecutionResult(BaseModel):
    command: str
    exit_code: int
    stdout: str
    stderr: str
    duration_sec: float
    timed_out: bool = False
    killed_by_guardian: bool = False
    peak_child_processes: int = 0

class CodeRunner:
    MAX_TIMEOUT_SECONDS = 120.0
    MAX_CHILD_PROCESSES = 4

    def __init__(self, guardian_instance: Optional[GuardianKillSwitch] = None):
        self.guardian = guardian_instance or guardian

    def execute_in_workspace(
        self,
        command: List[str],
        cwd: str,
        timeout_seconds: float = 120.0,
        allow_network: bool = False,
        env_overrides: Optional[Dict[str, str]] = None
    ) -> ExecutionResult:
        """
        Executes a command within an isolated workspace path under strict resource & safety caps.
        """
        if self.guardian.is_halted:
            return ExecutionResult(
                command=" ".join(command),
                exit_code=-1,
                stdout="",
                stderr="Execution refused: Guardian Kill Switch is active.",
                duration_sec=0.0,
                killed_by_guardian=True
            )

        if not os.path.exists(cwd):
            raise FileNotFoundError(f"Execution directory does not exist: {cwd}")

        actual_timeout = min(timeout_seconds, self.MAX_TIMEOUT_SECONDS)

        # Build isolated environment
        env = os.environ.copy()
        if not allow_network:
            # Block outbound HTTP/HTTPS networking by routing through unreachable loopback port
            env["HTTP_PROXY"] = "http://127.0.0.1:0"
            env["HTTPS_PROXY"] = "http://127.0.0.1:0"
            env["ALL_PROXY"] = "http://127.0.0.1:0"
            env["PIP_NO_INDEX"] = "1"
            env["PHENOM_OFFLINE_MODE"] = "1"

        if env_overrides:
            env.update(env_overrides)

        start_time = time.time()
        timed_out = False
        killed_by_guardian = False
        peak_children = 0

        # Launch subprocess
        proc = subprocess.Popen(
            command,
            cwd=cwd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            env=env
        )

        # Register process PID with Guardian
        self.guardian.track_pid(proc.pid)

        # Monitor thread for timeout, process limits, and guardian halt
        monitor_stop = threading.Event()

        def monitor_process():
            nonlocal timed_out, killed_by_guardian, peak_children
            while not monitor_stop.is_set():
                if self.guardian.is_halted:
                    killed_by_guardian = True
                    self.terminate_process_tree(proc.pid)
                    break

                elapsed = time.time() - start_time
                if elapsed > actual_timeout:
                    timed_out = True
                    self.terminate_process_tree(proc.pid)
                    break

                try:
                    p = psutil.Process(proc.pid)
                    children = p.children(recursive=True)
                    count = len(children)
                    if count > peak_children:
                        peak_children = count
                    if count > self.MAX_CHILD_PROCESSES:
                        # Exceeded child process cap
                        self.terminate_process_tree(proc.pid)
                        break
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    break

                monitor_stop.wait(0.1)

        monitor_thread = threading.Thread(target=monitor_process, daemon=True)
        monitor_thread.start()

        try:
            stdout, stderr = proc.communicate(timeout=actual_timeout + 5)
        except subprocess.TimeoutExpired:
            timed_out = True
            self.terminate_process_tree(proc.pid)
            stdout, stderr = proc.communicate()
        finally:
            monitor_stop.set()
            monitor_thread.join(timeout=1.0)
            self.guardian.untrack_pid(proc.pid)

        duration = time.time() - start_time

        if self.guardian.is_halted:
            killed_by_guardian = True

        return ExecutionResult(
            command=" ".join(command),
            exit_code=proc.returncode if proc.returncode is not None else -1,
            stdout=stdout or "",
            stderr=stderr or ("Execution timed out or terminated by Guardian." if (timed_out or killed_by_guardian) else ""),
            duration_sec=duration,
            timed_out=timed_out,
            killed_by_guardian=killed_by_guardian,
            peak_child_processes=peak_children
        )

    def terminate_process_tree(self, pid: int) -> int:
        """
        Force-terminates a process and all of its descendants recursively.
        """
        killed = 0
        try:
            parent = psutil.Process(pid)
            for child in parent.children(recursive=True):
                try:
                    child.kill()
                    killed += 1
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    pass
            parent.kill()
            killed += 1
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            pass
        return killed

# Global runner instance
code_runner = CodeRunner()
