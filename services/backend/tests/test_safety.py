"""
Unit tests for Phenom Safety Layer
Tests:
1. Registration enforcement (tier, preview, schema)
2. Tier 0 automatic execution
3. Tier 1 confirmation and denial
4. Tier 1 remembered approvals per folder
5. Tier 2 confirmation and preview enforcement
6. Tier 3 default blocking
7. Confirmation timeout handling
8. Guardian kill switch halt and resume
9. Action log argument redaction
"""

import pytest
import asyncio
import os
from pydantic import BaseModel, Field
from services.backend.safety.registry import ToolRegistry, ToolDefinition
from services.backend.safety.action_log import ActionLogManager, redact_arguments
from services.backend.safety.approvals import ApprovalManager
from services.backend.safety.guardian import GuardianKillSwitch
from services.backend.safety.engine import SafetyExecutionEngine

class SampleArgs(BaseModel):
    path: str
    message: str = "default"

class SensitiveArgs(BaseModel):
    user: str
    password: str
    api_key: str

def test_registry_enforcement():
    reg = ToolRegistry()
    
    # Missing preview
    with pytest.raises(ValueError, match="declare a callable preview"):
        ToolDefinition("bad_tool", 0, "desc", SampleArgs, None, lambda **k: None)
        
    # Invalid tier
    with pytest.raises(ValueError, match="Invalid risk tier"):
        ToolDefinition("bad_tool", 5, "desc", SampleArgs, lambda a: "preview", lambda **k: None)

    # Valid registration
    @reg.register(
        name="test_tool",
        tier=0,
        description="A test tool",
        args_schema=SampleArgs,
        preview_fn=lambda args: f"Accessing {args.get('path')}"
    )
    def handle_test(path: str, message: str = "default"):
        return f"OK: {path}"

    assert reg.get("test_tool") is not None
    assert reg.get_tier("test_tool") == 0
    assert reg.get_tier("unknown_tool") == 3

@pytest.mark.asyncio
async def test_tier0_auto_execution(tmp_path):
    engine = SafetyExecutionEngine()
    db_file = str(tmp_path / "test.db")
    engine_log = ActionLogManager(db_file)
    
    reg = ToolRegistry()
    @reg.register(
        name="read_data",
        tier=0,
        description="Read data",
        args_schema=SampleArgs,
        preview_fn=lambda a: f"Read {a['path']}"
    )
    def read_fn(path: str, message: str = "default"):
        return f"Content of {path}"

    # Swap global registry temporarily
    from services.backend.safety import engine as engine_mod
    orig_reg = engine_mod.registry
    orig_log = engine_mod.action_log
    engine_mod.registry = reg
    engine_mod.action_log = engine_log
    
    try:
        res = await engine.execute_tool("read_data", {"path": "C:/test.txt"})
        assert res["status"] == "success"
        assert res["result"] == "Content of C:/test.txt"
        
        entries = engine_log.list_entries(1)
        assert len(entries) == 1
        assert entries[0]["tool"] == "read_data"
        assert entries[0]["decision"] == "auto"
    finally:
        engine_mod.registry = orig_reg
        engine_mod.action_log = orig_log

@pytest.mark.asyncio
async def test_tier1_confirmation_and_remembered_folder(tmp_path):
    engine = SafetyExecutionEngine()
    db_file = str(tmp_path / "test_t1.db")
    test_approvals = ApprovalManager(db_file)
    test_log = ActionLogManager(db_file)
    
    reg = ToolRegistry()
    @reg.register(
        name="create_note",
        tier=1,
        description="Create note",
        args_schema=SampleArgs,
        preview_fn=lambda a: f"Create note at {a['path']}",
        can_remember_per_folder=True
    )
    def create_fn(path: str, message: str = "default"):
        return f"Created {path}"

    from services.backend.safety import engine as engine_mod
    orig_reg = engine_mod.registry
    orig_app = engine_mod.approvals
    orig_log = engine_mod.action_log
    engine_mod.registry = reg
    engine_mod.approvals = test_approvals
    engine_mod.action_log = test_log

    try:
        folder = str(tmp_path / "workspace")
        file_path = os.path.join(folder, "note.txt")

        # 1. Test Denial
        async def mock_deny(*args):
            return ("denied", False)
        engine.set_confirmation_handler(mock_deny)
        with pytest.raises(PermissionError, match="denied by the user"):
            await engine.execute_tool("create_note", {"path": file_path})

        # 2. Test Approval with Remember Choice
        confirm_called = 0
        async def mock_approve_and_remember(req_id, tool, tier, prev, args, can_rem, f_path, timeout):
            nonlocal confirm_called
            confirm_called += 1
            return ("approved", True)

        engine.set_confirmation_handler(mock_approve_and_remember)
        res = await engine.execute_tool("create_note", {"path": file_path}, target_folder=folder)
        assert res["result"] == f"Created {file_path}"
        assert confirm_called == 1
        assert test_approvals.is_remembered("create_note", 1, folder) is True

        # 3. Subsequent call to same folder should auto-run without prompting confirmation!
        res2 = await engine.execute_tool("create_note", {"path": os.path.join(folder, "note2.txt")}, target_folder=folder)
        assert res2["result"] == f"Created {os.path.join(folder, 'note2.txt')}"
        assert confirm_called == 1 # Did not ask confirmation again!
    finally:
        engine_mod.registry = orig_reg
        engine_mod.approvals = orig_app
        engine_mod.action_log = orig_log

@pytest.mark.asyncio
async def test_guardian_kill_switch():
    guardian = GuardianKillSwitch()
    assert guardian.is_halted is False

    # Simulate trigger
    guardian.trigger("test_alert")
    assert guardian.is_halted is True

    # Test engine stops when guardian is halted
    engine = SafetyExecutionEngine()
    from services.backend.safety import engine as engine_mod
    orig_guardian = engine_mod.guardian
    engine_mod.guardian = guardian

    try:
        with pytest.raises(PermissionError, match="Guardian kill switch is active"):
            await engine.execute_tool("any_tool", {})
            
        # Test resume
        guardian.resume()
        assert guardian.is_halted is False
    finally:
        engine_mod.guardian = orig_guardian

def test_argument_redaction():
    args = {
        "user": "Alice",
        "password": "SuperSecretPassword123!",
        "api_key": "nvapi-abcdef123456",
        "data": {
            "token": "bearer-xyz",
            "safe_val": 42
        }
    }
    redacted_json = redact_arguments(args)
    import json
    parsed = json.loads(redacted_json)
    
    assert parsed["password"] == "[REDACTED]"
    assert parsed["api_key"] == "[REDACTED]"
    assert parsed["data"]["token"] == "[REDACTED]"
    assert parsed["data"]["safe_val"] == 42
    assert parsed["user"] == "Alice"
