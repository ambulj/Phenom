"""
Unit & Integration Test Suite for Milestone 40 Phase 1: Universal Cross-Platform OS Abstraction & Dual-Boot Parity Engine
Validates:
- Platform auto-detection (Windows vs Kali Linux).
- Linux /proc/{pid}/maps parser identifying RWX (0x40 equivalent) and unbacked executable regions.
- Cross-platform process memory scanning abstraction.
- Non-destructive network egress containment (Netsh / iptables).
- Sub-25ms Universal Guardian Kill Switch enforcement.
- ToolRegistry registration audit for all 4 cross-platform tools.
"""

import os
import time
import pytest
from unittest.mock import patch

from services.backend.safety.guardian import guardian
from services.backend.safety.registry import registry
from services.backend.platform.os_bridge import OSBridge, Platform, os_bridge
import services.backend.tools.cross_platform_tools


@pytest.fixture(autouse=True)
def reset_os_bridge_state():
    guardian.resume()
    yield
    guardian.resume()


def test_platform_detection_and_environment():
    """Verify platform detection correctly identifies the active operating system environment."""
    bridge = OSBridge()
    assert bridge.current_platform in [Platform.WINDOWS, Platform.LINUX_KALI, Platform.LINUX_GENERIC, Platform.DARWIN]

    env = bridge.get_system_environment()
    assert "platform" in env
    assert "os_name" in env
    assert "kernel_release" in env
    assert "architecture" in env
    assert "dual_boot_supported" in env
    assert env["dual_boot_supported"] is True
    assert "memory_audit_mode" in env
    assert "containment_mode" in env
    assert env["cpu_cores"] >= 1
    assert env["total_ram_gb"] > 0


def test_linux_proc_maps_parser_synthetic():
    """Verify Linux /proc/maps parser accurately flags RWX pages and unbacked anonymous executable code."""
    synthetic_maps = """
00400000-00452000 r-xp 00000000 08:02 173521 /usr/bin/python3.11
00651000-00652000 r--p 00051000 08:02 173521 /usr/bin/python3.11
00652000-0065b000 rw-p 00052000 08:02 173521 /usr/bin/python3.11
01b2c000-01c3e000 rw-p 00000000 00:00 0 [heap]
7f8e3c000000-7f8e3c020000 rwxp 00000000 00:00 0 [anon]
7f8e3c020000-7f8e3c030000 r-xp 00000000 00:00 0 [anon]
7ffd8a120000-7ffd8a141000 rw-p 00000000 00:00 0 [stack]
7ffd8a1fe000-7ffd8a200000 r-xp 00000000 00:00 0 [vdso]
"""
    bridge = OSBridge()
    parsed = bridge.parse_linux_proc_maps(synthetic_maps, pid=1337)

    assert parsed["pid"] == 1337
    assert parsed["total_mappings_scanned"] == 8
    assert parsed["rwx_pages_count"] == 1
    assert parsed["unbacked_exec_pages_count"] == 1
    assert parsed["threat_verdict"] == "CRITICAL"
    assert parsed["containment_action"] == "IPTABLES_EGRESS_DROP_RECOMMENDED"

    rwx = parsed["rwx_regions"][0]
    assert rwx["base_address"] == "0x7F8E3C000000"
    assert rwx["permissions"] == "rwxp"
    assert rwx["risk_level"] == "CRITICAL"

    unbacked = parsed["unbacked_regions"][0]
    assert unbacked["base_address"] == "0x7F8E3C020000"
    assert unbacked["permissions"] == "r-xp"
    assert unbacked["pathname"] == "[anon]"
    assert unbacked["risk_level"] == "HIGH"


def test_cross_platform_memory_scan_current_pid():
    """Verify cross-platform memory auditing executes seamlessly on current process."""
    current_pid = os.getpid()
    res = os_bridge.scan_process_memory(current_pid)

    assert res["pid"] == current_pid
    assert "rwx_pages_count" in res
    assert res["threat_verdict"] in ["CLEAN", "SUSPICIOUS", "CRITICAL"]


def test_cross_platform_contain_process():
    """Verify non-destructive process containment operates with process RAM preserved."""
    current_pid = os.getpid()
    res = os_bridge.contain_process_network_egress(current_pid)

    assert res["success"] is True
    assert res["pid"] == current_pid
    assert res["process_state"] == "PRESERVED_IN_RAM"
    assert res["forensics_intact"] is True
    assert current_pid in os_bridge.get_isolated_pids()


def test_guardian_killswitch_cross_platform_sla():
    """Verify Universal Guardian Kill Switch aborts cross-platform operations in <25ms SLA."""
    current_pid = os.getpid()

    # Trigger emergency halt
    t0 = time.perf_counter()
    guardian.trigger("Cross-platform test abort")
    abort_latency_ms = (time.perf_counter() - t0) * 1000.0
    assert abort_latency_ms < 25.0, f"Guardian trigger exceeded 25ms SLA: {abort_latency_ms}ms"

    # Verify all operations raise PermissionError synchronously
    with pytest.raises(PermissionError, match="Guardian kill switch active"):
        os_bridge.get_system_environment()

    with pytest.raises(PermissionError, match="Guardian kill switch active"):
        os_bridge.scan_process_memory(current_pid)

    with pytest.raises(PermissionError, match="Guardian kill switch active"):
        os_bridge.contain_process_network_egress(current_pid)


def test_cross_platform_tool_registry():
    """Verify all 4 cross-platform tools are registered with correct risk tiers and valid schemas."""
    expected_tools = {
        "get_platform_environment": 0,
        "cross_platform_memory_audit": 0,
        "cross_platform_contain_process": 1,
        "verify_dual_boot_posture": 0,
    }

    for tool_name, expected_tier in expected_tools.items():
        tool_def = registry.get(tool_name)
        assert tool_def is not None, f"Tool '{tool_name}' must be registered"
        assert tool_def.tier == expected_tier, f"Tool '{tool_name}' tier mismatch: {tool_def.tier} != {expected_tier}"
        assert tool_def.args_schema is not None, f"Tool '{tool_name}' missing args_schema"
        assert callable(tool_def.preview_fn), f"Tool '{tool_name}' missing preview_fn"
        preview_text = tool_def.preview_fn({"pid": 1234})
        assert isinstance(preview_text, str) and len(preview_text) > 0
