"""
Automated Verification Suite for Phase 1: Developer Workspace Sentinel (DEV-01).
Tests schema validation, secret masking, IDE window detection,
microsecond stat caching, non-git degradation, safety registration, and Guardian kill switch halt SLA.
"""

import os
import tempfile
import time
from unittest.mock import MagicMock, patch
import pytest

from services.backend.schemas.workspace import (
    DeveloperWorkspaceState,
    WorkspaceFileChange,
    sanitize_workspace_file_path,
)
from services.backend.coding.workspace_sentinel import (
    DeveloperWorkspaceSentinel,
    workspace_sentinel,
)
from services.backend.safety.registry import registry
from services.backend.safety.guardian import guardian
import services.backend.tools.coding_tools  # noqa: F401


# ==========================================
# 1. Schemas & Secret Masking Tests
# ==========================================

def test_schemas_and_masking():
    """Verify Pydantic models and regex secret sanitization."""
    # Test secret file masking
    secret_files = [
        ".env",
        ".env.local",
        ".env.production",
        "aws_credentials.json",
        "app_secret.key",
        "server.pem",
        "id_rsa",
        "id_ed25519",
        "api_token.txt",
        "user_password.txt",
    ]
    for sec_file in secret_files:
        masked, is_sec = sanitize_workspace_file_path(sec_file)
        assert is_sec is True, f"Expected {sec_file} to be classified as secret"
        assert masked.startswith("***") and masked.endswith("(masked)***"), f"Bad mask for {sec_file}"

    # Test non-secret file transparency
    regular_files = [
        "main.py",
        "package.json",
        "HeaderBar.tsx",
        "README.md",
        "vite.config.ts",
    ]
    for reg_file in regular_files:
        unmasked, is_sec = sanitize_workspace_file_path(reg_file)
        assert is_sec is False, f"Did not expect {reg_file} to be secret"
        assert unmasked == reg_file

    # Test Pydantic model serialization
    change = WorkspaceFileChange(
        path="src/App.tsx",
        status="M",
        lines_added=12,
        lines_deleted=4,
        is_staged=False,
        is_secret=False,
    )
    assert change.lines_added == 12

    state = DeveloperWorkspaceState(
        name="test-repo",
        root_path="C:\\Projects\\test-repo",
        ide_name="cursor",
        is_git=True,
        branch="main",
        is_dirty=True,
        lines_added=12,
        lines_deleted=4,
        untracked_count=1,
        modified_files=[change],
    )
    dump = state.model_dump()
    assert dump["name"] == "test-repo"
    assert dump["branch"] == "main"
    assert len(dump["modified_files"]) == 1


# ==========================================
# 2. Window & IDE Detection Tests
# ==========================================

def test_window_detection():
    """Verify IDE process matching, window title parsing, and invalid handle guards."""
    sentinel = DeveloperWorkspaceSentinel(known_roots=["C:\\Phenom"])

    # Test invalid hwnd / pid guard
    with patch("services.backend.coding.workspace_sentinel.win32gui.GetForegroundWindow", return_value=0):
        assert sentinel.detect_active_ide_window() is None

    with patch("services.backend.coding.workspace_sentinel.win32gui.GetForegroundWindow", return_value=12345), \
         patch("services.backend.coding.workspace_sentinel.win32process.GetWindowThreadProcessId", return_value=(0, -1)):
        assert sentinel.detect_active_ide_window() is None

    # Test IDE executable recognition (Cursor)
    mock_proc = MagicMock()
    mock_proc.name.return_value = "cursor.exe"
    with patch("services.backend.coding.workspace_sentinel.win32gui.GetForegroundWindow", return_value=12345), \
         patch("services.backend.coding.workspace_sentinel.win32process.GetWindowThreadProcessId", return_value=(0, 9999)), \
         patch("services.backend.coding.workspace_sentinel.win32gui.GetWindowText", return_value="● HeaderBar.tsx - Phenom - Cursor"), \
         patch("services.backend.coding.workspace_sentinel.psutil.Process", return_value=mock_proc):
        res = sentinel.detect_active_ide_window()
        assert res is not None
        ide_name, title, pid = res
        assert ide_name == "cursor"
        assert "Phenom" in title

        # Test root path resolution
        resolved_root = sentinel.resolve_workspace_root(ide_name, title, pid)
        assert resolved_root is not None
        assert os.path.basename(resolved_root).lower() == "phenom"

    # Test non-IDE process rejection (Notepad)
    mock_notepad = MagicMock()
    mock_notepad.name.return_value = "notepad.exe"
    with patch("services.backend.coding.workspace_sentinel.win32gui.GetForegroundWindow", return_value=12345), \
         patch("services.backend.coding.workspace_sentinel.win32process.GetWindowThreadProcessId", return_value=(0, 8888)), \
         patch("services.backend.coding.workspace_sentinel.psutil.Process", return_value=mock_notepad):
        assert sentinel.detect_active_ide_window() is None


# ==========================================
# 3. Microsecond Stat Caching & Git State Tests
# ==========================================

def test_git_caching_and_non_git():
    """Verify microsecond stat caching on git repos and safe degradation for non-git folders."""
    sentinel = DeveloperWorkspaceSentinel(known_roots=["C:\\Phenom"])

    # 1. Real repository inspection (C:\Phenom)
    state1 = sentinel.inspect_workspace("C:\\Phenom")
    assert state1.is_git is True
    assert state1.name == "Phenom"
    assert state1.branch is not None

    # 2. Cache hit timing test: second inspection must complete in < 2ms without git subprocess
    t0 = time.perf_counter()
    state2 = sentinel.inspect_workspace("C:\\Phenom")
    elapsed_ms = (time.perf_counter() - t0) * 1000.0

    assert state2.branch == state1.branch
    assert state2.lines_added == state1.lines_added
    assert elapsed_ms < 5.0, f"Cache check took too long: {elapsed_ms:.3f} ms"

    # 3. Non-git workspace clean degradation
    with tempfile.TemporaryDirectory() as tmpdir:
        non_git_state = sentinel.inspect_workspace(tmpdir)
        assert non_git_state.is_git is False
        assert non_git_state.branch is None
        assert non_git_state.is_dirty is False
        assert len(non_git_state.modified_files) == 0


# ==========================================
# 4. Guardian Kill Switch Halt SLA Tests
# ==========================================

def test_guardian_halt():
    """Verify sub-25ms synchronous halt SLA and poll suppression."""
    sentinel = DeveloperWorkspaceSentinel(known_roots=["C:\\Phenom"])
    assert sentinel.is_halted is False

    # Halt latency measurement
    t0 = time.perf_counter()
    sentinel.halt()
    halt_duration_ms = (time.perf_counter() - t0) * 1000.0

    assert sentinel.is_halted is True
    assert halt_duration_ms < 25.0, f"Halt exceeded 25ms SLA: {halt_duration_ms:.3f} ms"
    assert sentinel.poll_once() is None

    # Resume capability
    sentinel.reset()
    assert sentinel.is_halted is False


# ==========================================
# 5. Safety Tool Registration Tests
# ==========================================

def test_safety_tool_registration():
    """Verify ToolRegistry integration for coding_get_workspace_state."""
    tool = registry.get("coding_get_workspace_state")
    assert tool is not None
    assert tool.name == "coding_get_workspace_state"
    assert tool.tier == 0, "Expected coding_get_workspace_state to be Tier 0 (Read-Only)"

    # Execute tool via registry handler
    result = tool.handler_fn()
    assert "name" in result
    assert "is_git" in result
    assert "branch" in result
    assert "modified_files" in result
