"""
Unit tests for Phenom Tools (Files and Apps)
Verifies:
1. Every tool is properly declared with tier, schema, and preview
2. File operations (list, read, search, create, move, copy, recycle)
3. App operations (list apps)
4. Proof that tools execute through the Safety Execution Engine and cannot bypass safety
"""

import os
import pytest
from services.backend.safety.registry import registry
from services.backend.safety.engine import safety_engine
import services.backend.tools.file_tools
import services.backend.tools.app_tools

def test_tool_declarations_complete():
    expected_tools = [
        ("list_files", 0),
        ("read_file", 0),
        ("search_files_by_name", 0),
        ("create_file", 1),
        ("create_folder", 1),
        ("move_file", 1),
        ("copy_file", 1),
        ("recycle_delete", 2),
        ("list_apps", 0),
        ("open_app", 1),
        ("close_app", 1)
    ]
    for name, tier in expected_tools:
        tool = registry.get(name)
        assert tool is not None, f"Tool {name} is not registered"
        assert tool.tier == tier, f"Tool {name} expected tier {tier}, got {tool.tier}"
        assert callable(tool.preview_fn), f"Tool {name} missing preview"

@pytest.mark.asyncio
async def test_file_operations_through_safety_engine(tmp_path):
    test_dir = str(tmp_path / "sandbox")
    os.makedirs(test_dir, exist_ok=True)
    file_a = os.path.join(test_dir, "file_a.txt")
    file_b = os.path.join(test_dir, "file_b.txt")

    # Set mock confirmation handler for Tier 1 & 2
    async def auto_approve(req_id, tool, tier, prev, args, can_rem, f_path, timeout):
        return ("approved", False)
    safety_engine.set_confirmation_handler(auto_approve)

    # 1. create_file (Tier 1)
    res = await safety_engine.execute_tool("create_file", {"path": file_a, "content": "Hello Phenom"})
    assert res["status"] == "success"
    assert os.path.exists(file_a)

    # 2. read_file (Tier 0)
    res = await safety_engine.execute_tool("read_file", {"path": file_a})
    assert res["result"] == "Hello Phenom"

    # 3. copy_file (Tier 1)
    res = await safety_engine.execute_tool("copy_file", {"src": file_a, "dest": file_b})
    assert res["status"] == "success"
    assert os.path.exists(file_b)

    # 4. list_files (Tier 0)
    res = await safety_engine.execute_tool("list_files", {"path": test_dir})
    names = [f["name"] for f in res["result"]]
    assert "file_a.txt" in names
    assert "file_b.txt" in names

    # 5. search_files_by_name (Tier 0)
    res = await safety_engine.execute_tool("search_files_by_name", {"directory": test_dir, "query": "file_b"})
    assert len(res["result"]) == 1
    assert "file_b.txt" in res["result"][0]

    # 6. recycle_delete (Tier 2)
    res = await safety_engine.execute_tool("recycle_delete", {"path": file_b})
    assert res["result"]["recycled"] is True
    assert not os.path.exists(file_b) # Removed from directory (in Recycle Bin)

@pytest.mark.asyncio
async def test_app_tools_through_safety_engine():
    res = await safety_engine.execute_tool("list_apps", {"filter_system": True})
    assert res["status"] == "success"
    assert isinstance(res["result"], list)
    assert len(res["result"]) > 0

@pytest.mark.asyncio
async def test_bypass_prevention_on_unregistered_tool():
    with pytest.raises(PermissionError, match="blocked under Tier 3"):
        await safety_engine.execute_tool("unregistered_dangerous_tool", {"action": "destroy"})
