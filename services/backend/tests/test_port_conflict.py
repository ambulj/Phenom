import socket
import pytest
from services.backend.tools.coding_tools import (
    handle_inspect_port,
    handle_resolve_port_conflict,
    resolve_port_tier,
    resolve_port_preview
)
from services.backend.safety.registry import registry

def test_port_tools_registered():
    inspect_tool = registry.get("coding_inspect_port")
    assert inspect_tool is not None
    assert inspect_tool.tier == 0

    resolve_tool = registry.get("coding_resolve_port_conflict")
    assert resolve_tool is not None
    # Dynamic tier check: 0 if terminate=False, 2 if terminate=True
    assert resolve_tool.get_tier({"terminate": False}) == 0
    assert resolve_tool.get_tier({"terminate": True}) == 2

def test_inspect_free_port():
    # Find an unused port
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(('127.0.0.1', 0))
        free_port = s.getsockname()[1]
    
    # Now s is closed, so free_port should be free
    res = handle_inspect_port(free_port)
    assert res["status"] == "free"
    assert res["port"] == free_port

def test_inspect_bound_port():
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(('127.0.0.1', 0))
        s.listen(1)
        bound_port = s.getsockname()[1]

        res = handle_inspect_port(bound_port)
        assert res["status"] == "in_use"
        assert res["port"] == bound_port
        assert "pid" in res
        assert res["pid"] > 0

def test_resolve_port_conflict_without_terminate():
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(('127.0.0.1', 0))
        s.listen(1)
        bound_port = s.getsockname()[1]

        res = handle_resolve_port_conflict(bound_port, terminate=False)
        assert res["status"] == "in_use"
        assert res["port"] == bound_port
