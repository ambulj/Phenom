"""
Unit & Integration Test Suite for Milestone 40 Phase 2: Headless Binary Reverse-Engineering & Dynamic Frida DBI Engine
Validates:
- Binary disassembly & mitigation checking on PE & ELF binaries.
- Return-Oriented Programming (ROP) gadget extraction.
- Dynamic Binary Instrumentation (DBI) via Frida on active processes.
- Sub-25ms Universal Guardian Kill Switch enforcement.
- ToolRegistry registration audit for binary RE tools.
"""

import os
import sys
import time
import pytest

from services.backend.safety.guardian import guardian
from services.backend.safety.registry import registry
from services.backend.cyber.binary_analyzer import binary_analyzer
from services.backend.cyber.frida_instrumentation import frida_engine
import services.backend.tools.binary_re_tools


@pytest.fixture(autouse=True)
def reset_binary_test_state():
    guardian.resume()
    frida_engine.clear_sessions()
    yield
    guardian.resume()
    frida_engine.clear_sessions()


def test_binary_disassembly_pe_executable():
    """Verify disassembly of active Python executable identifies PE format, mitigations, and instructions."""
    python_exe = sys.executable
    assert os.path.exists(python_exe)

    res = binary_analyzer.disassemble_binary(python_exe, max_instructions=20)
    assert res["file_name"] == os.path.basename(python_exe)
    assert "PE" in res["binary_format"] or "ELF" in res["binary_format"]
    assert "entry_point" in res
    assert "security_mitigations" in res
    assert len(res["instructions"]) >= 1
    assert "mnemonic" in res["instructions"][0]
    assert "bytes" in res["instructions"][0]


def test_binary_rop_gadget_extraction():
    """Verify ROP gadget scanning identifies gadgets and calculates chain viability."""
    python_exe = sys.executable
    res = binary_analyzer.scan_rop_gadgets(python_exe, max_gadgets=15)

    assert res["file_name"] == os.path.basename(python_exe)
    assert "total_gadgets_found" in res
    assert "rop_chain_viability" in res
    assert isinstance(res["gadgets"], list)


def test_frida_process_instrumentation_current_pid():
    """Verify Frida DBI attaches non-destructive telemetry hooks to active test process."""
    current_pid = os.getpid()
    res = frida_engine.instrument_process(current_pid, hook_profile="MEM_NET_PROBE")

    assert res["success"] is True
    assert res["pid"] == current_pid
    assert res["status"] == "INSTRUMENTATION_ACTIVE"
    assert res["hooks_count"] >= 3
    assert "session_id" in res


def test_frida_hook_telemetry_query():
    """Verify querying Frida hook telemetry returns intercepted API events and memory arguments."""
    current_pid = os.getpid()
    frida_engine.instrument_process(current_pid)

    telemetry = frida_engine.get_hook_telemetry(pid=current_pid, limit=10)
    assert isinstance(telemetry, list)
    assert len(telemetry) >= 1
    event = telemetry[0]
    assert event["pid"] == current_pid
    assert "intercepted_api" in event
    assert "arguments" in event


def test_guardian_killswitch_binary_re_sla():
    """Verify Universal Guardian Kill Switch halts binary disassembly and Frida DBI instantly (<25ms SLA)."""
    current_pid = os.getpid()
    python_exe = sys.executable

    # Trigger emergency halt
    t0 = time.perf_counter()
    guardian.trigger("Binary RE emergency abort")
    abort_latency_ms = (time.perf_counter() - t0) * 1000.0
    assert abort_latency_ms < 25.0, f"Guardian trigger exceeded 25ms SLA: {abort_latency_ms}ms"

    # Verify all operations raise PermissionError synchronously
    with pytest.raises(PermissionError, match="Guardian kill switch active"):
        binary_analyzer.disassemble_binary(python_exe)

    with pytest.raises(PermissionError, match="Guardian kill switch active"):
        binary_analyzer.scan_rop_gadgets(python_exe)

    with pytest.raises(PermissionError, match="Guardian kill switch active"):
        frida_engine.instrument_process(current_pid)

    with pytest.raises(PermissionError, match="Guardian kill switch active"):
        frida_engine.get_hook_telemetry()


def test_binary_re_tools_registry():
    """Verify all 4 binary RE and Frida tools are registered with correct risk tiers and valid schemas."""
    expected_tools = {
        "analyze_binary_disassembly": 0,
        "scan_binary_rop_gadgets": 0,
        "instrument_process_with_frida": 1,
        "inspect_frida_hook_telemetry": 0,
    }

    for tool_name, expected_tier in expected_tools.items():
        tool_def = registry.get(tool_name)
        assert tool_def is not None, f"Tool '{tool_name}' must be registered"
        assert tool_def.tier == expected_tier, f"Tool '{tool_name}' tier mismatch: {tool_def.tier} != {expected_tier}"
        assert tool_def.args_schema is not None, f"Tool '{tool_name}' missing args_schema"
        assert callable(tool_def.preview_fn), f"Tool '{tool_name}' missing preview_fn"
        preview_text = tool_def.preview_fn({"pid": 1234, "file_path": sys.executable})
        assert isinstance(preview_text, str) and len(preview_text) > 0
