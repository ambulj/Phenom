"""
Tests for Phenom Kali Linux Integration Module (kali_tools.py)
Verifies:
1. Catalog contains all 9 core cybersecurity domains and 40+ major tools.
2. execute_kali_tool runs commands in WSL and captures output.
3. launch_kali_gui spawns GUI tools via WSLg and tracks launcher PIDs.
4. audit_kali_toolkit inspects tool availability and provides install recipes.
"""

import pytest
import subprocess
from unittest.mock import patch, MagicMock
from services.backend.tools.kali_tools import (
    KALI_TOOL_CATALOG,
    execute_kali_tool,
    launch_kali_gui,
    audit_kali_toolkit,
)


def test_kali_catalog_coverage():
    """Verifies that major Kali tools across all 9 domains are cataloged."""
    expected_tools = [
        "nmap", "masscan", "rustscan", "amass", "sqlmap", "gobuster",
        "hashcat", "john", "hydra", "aircrack-ng", "airgeddon",
        "msfconsole", "msfvenom", "searchsploit", "tcpdump", "tshark",
        "radare2", "binwalk", "burpsuite", "wireshark", "ghidra"
    ]
    for tool in expected_tools:
        assert tool in KALI_TOOL_CATALOG, f"Expected {tool} to be cataloged in KALI_TOOL_CATALOG"
        assert "category" in KALI_TOOL_CATALOG[tool]
        assert "desc" in KALI_TOOL_CATALOG[tool]


def test_execute_kali_tool_success():
    """Verifies successful CLI tool execution via mock."""
    with patch("subprocess.run") as mock_run:
        mock_proc = MagicMock()
        mock_proc.returncode = 0
        mock_proc.stdout = "Nmap scan report for 127.0.0.1\nPORT 80/tcp open http\n"
        mock_proc.stderr = ""
        mock_run.return_value = mock_proc

        res = execute_kali_tool("nmap", "-sV 127.0.0.1", distro="kali-linux")
        assert res["success"] is True
        assert res["tool"] == "nmap"
        assert res["category"] == "Recon"
        assert "PORT 80/tcp open" in res["stdout"]
        mock_run.assert_called_once()
        cmd_called = mock_run.call_args[0][0]
        assert cmd_called == ["wsl", "-d", "kali-linux", "bash", "-c", "nmap -sV 127.0.0.1"]


def test_execute_kali_tool_timeout():
    """Verifies timeout handling when a long-running scan exceeds limit."""
    with patch("subprocess.run", side_effect=subprocess.TimeoutExpired(cmd="masscan", timeout=5)):
        res = execute_kali_tool("masscan", "10.0.0.0/8 -p80", timeout_seconds=5)
        assert res["success"] is False
        assert res["returncode"] == -1
        assert "timed out after 5s" in res["stderr"]


def test_launch_kali_gui_windows_native():
    """Verifies that native Windows installed tools are preferred if present."""
    with patch("shutil.which", return_value="C:\\Program Files\\Wireshark\\Wireshark.exe"), \
         patch("services.backend.tools.kali_tools._launch_on_default_desktop", return_value=12345):
        res = launch_kali_gui("wireshark")
        assert res["launched"] is True
        assert res["mode"] == "windows_native"
        assert res["pid"] == 12345


def test_launch_kali_gui_wslg():
    """Verifies that WSLg is used when tool is not installed natively on Windows."""
    with patch("shutil.which", return_value=None), \
         patch("services.backend.tools.kali_tools._launch_on_default_desktop", return_value=54321) as mock_launch:
        res = launch_kali_gui("burpsuite", distro="kali-linux")
        assert res["launched"] is True
        assert res["mode"] == "wslg_gui"
        assert res["pid"] == 54321
        cmd_called = mock_launch.call_args[0][0]
        assert "wsl.exe -d kali-linux burpsuite" in cmd_called


def test_audit_kali_toolkit_mocked():
    """Verifies auditing of installed vs missing tools in the target WSL distro."""
    with patch("subprocess.run") as mock_run:
        mock_proc = MagicMock()
        mock_proc.returncode = 0
        mock_proc.stdout = "/usr/bin/nmap\n/usr/bin/tcpdump\nMISSING_airgeddon\nMISSING_burpsuite\n"
        mock_run.return_value = mock_proc

        audit = audit_kali_toolkit(distro="kali-linux")
        assert "nmap" in audit["installed_tools"]
        assert "tcpdump" in audit["installed_tools"]
        assert "airgeddon" in audit["missing_tools"]
        assert "burpsuite" in audit["missing_tools"]
        assert "quick_install_command" in audit
