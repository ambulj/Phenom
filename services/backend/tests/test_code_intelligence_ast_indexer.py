"""
Phase 20-01 Verification Suite: AST Code Intelligence & Semantic Workspace Indexer
(DEV-01.1, DEV-01.2, DEV-01.3, SAF-01, SAF-02)

Validates:
1. Python AST parsing for classes, methods, functions, type hints, docstrings, and calls.
2. TypeScript/JavaScript token parsing for interfaces, types, classes, and exported functions.
3. Incremental workspace symbol table indexing with file-hash caching and sub-10ms lookup.
4. Call graph dependency tracing and symbol reference discovery.
5. Multi-file atomic code refactoring with unified diff preview and error rollback.
6. Safety Engine tool registry audit for all 5 code intelligence tools (Tiers 0 & 1).
7. Guardian Kill Switch synchronous halt latency benchmark (< 25.0ms SLA, target < 1.0ms).
"""

import os
import sys
import time
import pytest
from typing import Dict, Any, List
from pydantic import BaseModel

# Ensure root import
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../..")))

from services.backend.safety.guardian import guardian
from services.backend.safety.registry import registry
from services.backend.coding.ast_parser import ast_parser, AstCodeParser, SymbolKind
from services.backend.coding.workspace_indexer import WorkspaceIndexer, workspace_indexer
from services.backend.coding.refactor_engine import RefactorEngine, refactor_engine
import services.backend.tools.code_intelligence_tools as code_tools


# ==============================================================================
# 1. Python AST Parsing (DEV-01.1)
# ==============================================================================

def test_python_ast_parsing():
    """Verify Python AST parser extracts symbols, signatures, docstrings, and call dependencies."""
    code = '''"""Module docstring."""
import os

@decorator_a
class ArchitectureEngine:
    """Core engine class."""
    def __init__(self, mode: str = "fast"):
        self.mode = mode

    async def execute_plan(self, plan_id: str) -> bool:
        """Executes a plan."""
        helper_call()
        return True

def standalone_helper(x: int) -> int:
    return x * 2
'''
    symbols = ast_parser.parse_python(code, file_path="engine.py")
    assert len(symbols) >= 4

    names = {s.name: s for s in symbols}
    assert "ArchitectureEngine" in names
    cls_sym = names["ArchitectureEngine"]
    assert cls_sym.kind == SymbolKind.CLASS.value
    assert cls_sym.docstring == "Core engine class."
    assert "decorator_a" in cls_sym.decorators
    assert "helper_call" in cls_sym.calls

    assert "execute_plan" in names
    fn_sym = names["execute_plan"]
    assert fn_sym.kind == SymbolKind.METHOD.value
    assert fn_sym.parent == "ArchitectureEngine"
    assert "async def execute_plan(self, plan_id: str) -> bool" in fn_sym.signature
    assert fn_sym.docstring == "Executes a plan."
    assert "helper_call" in fn_sym.calls

    assert "standalone_helper" in names
    helper_sym = names["standalone_helper"]
    assert helper_sym.kind == SymbolKind.FUNCTION.value
    assert helper_sym.parent is None
    assert "def standalone_helper(x: int) -> int" in helper_sym.signature


# ==============================================================================
# 2. TypeScript / JavaScript Symbol Parsing (DEV-01.1)
# ==============================================================================

def test_typescript_symbol_parsing():
    """Verify TypeScript parser extracts interfaces, types, classes, and exported functions."""
    ts_code = '''
export interface UserSession {
  id: string;
  token: string;
}

export type RiskLevel = 'low' | 'medium' | 'high';

export class GuardianController {
  constructor(private name: string) {}
}

export async function checkSession(user: UserSession): Promise<boolean> {
  return true;
}

export const formatUserName = (first: string, last: string): string => {
  return `${first} ${last}`;
};
'''
    symbols = ast_parser.parse_typescript(ts_code, file_path="session.ts")
    assert len(symbols) >= 5

    names = {s.name: s for s in symbols}
    assert "UserSession" in names
    assert names["UserSession"].kind == SymbolKind.INTERFACE.value
    assert names["UserSession"].exported is True

    assert "RiskLevel" in names
    assert names["RiskLevel"].kind == SymbolKind.TYPE_ALIAS.value

    assert "GuardianController" in names
    assert names["GuardianController"].kind == SymbolKind.CLASS.value

    assert "checkSession" in names
    assert names["checkSession"].kind == SymbolKind.ASYNC_FUNCTION.value

    assert "formatUserName" in names
    assert names["formatUserName"].kind == SymbolKind.FUNCTION.value


# ==============================================================================
# 3. Workspace Symbol Indexing & Sub-10ms Lookup (DEV-01.2)
# ==============================================================================

def test_workspace_symbol_indexing_and_lookup(tmp_path):
    """Verify in-memory workspace symbol table indexing with call graph and sub-10ms query latency."""
    f1 = tmp_path / "module_a.py"
    f1.write_text("""
def alpha_service():
    '''Alpha service doc.'''
    beta_worker()
    return "alpha"
""", encoding="utf-8")

    f2 = tmp_path / "module_b.py"
    f2.write_text("""
def beta_worker():
    return "beta"
""", encoding="utf-8")

    indexer = WorkspaceIndexer(root_dir=str(tmp_path))
    stats = indexer.index_workspace()

    assert stats["status"] == "indexed"
    assert stats["files_scanned"] >= 2
    assert stats["total_symbols"] >= 2

    # Verify sub-10ms lookup
    t0 = time.perf_counter()
    definitions = indexer.lookup_symbol("alpha_service")
    t1 = time.perf_counter()
    lookup_ms = (t1 - t0) * 1000.0

    print(f"\n[Symbol Lookup Latency] {lookup_ms:.4f} ms")
    assert lookup_ms < 10.0, f"Symbol lookup took {lookup_ms:.2f} ms (> 10.0ms limit)"
    assert len(definitions) == 1
    assert definitions[0]["name"] == "alpha_service"
    assert definitions[0]["kind"] == "function"
    assert "Alpha service doc" in definitions[0]["docstring"]

    # Verify call graph reverse reference discovery
    refs = indexer.find_references("beta_worker")
    assert refs["symbol"] == "beta_worker"
    assert refs["reference_count"] >= 1
    assert any("alpha_service" in r for r in refs["references"])


# ==============================================================================
# 4. Incremental SHA256 Hash Invalidation (DEV-01.2)
# ==============================================================================

def test_incremental_hash_invalidation(tmp_path):
    """Verify unchanged files are cached and only modified files are reparsed on re-index."""
    f1 = tmp_path / "service.py"
    f1.write_text("def run_job(): pass", encoding="utf-8")

    indexer = WorkspaceIndexer(root_dir=str(tmp_path))
    initial_stats = indexer.index_workspace()
    assert initial_stats["files_reparsed"] == 1

    # Second index with no changes
    cached_stats = indexer.index_workspace()
    assert cached_stats["files_reparsed"] == 0, "Unchanged files must be skipped without reparsing."

    # Modify file
    f1.write_text("def run_job_modified(): pass", encoding="utf-8")
    reparsed_stats = indexer.index_workspace()
    assert reparsed_stats["files_reparsed"] == 1, "Modified file must be incrementally reparsed."
    assert len(indexer.lookup_symbol("run_job_modified")) == 1
    assert len(indexer.lookup_symbol("run_job")) == 0, "Old symbol should be invalidated."


# ==============================================================================
# 5. Multi-File Atomic Code Refactoring & Rollback (DEV-01.3)
# ==============================================================================

def test_multi_file_atomic_refactor_and_rollback(tmp_path):
    """Verify unified diff generation, atomic multi-file application, and error rollback."""
    f1 = tmp_path / "caller.py"
    f1.write_text("import callee\ncallee.process_data()\n", encoding="utf-8")

    f2 = tmp_path / "callee.py"
    f2.write_text("def process_data():\n    return 42\n", encoding="utf-8")

    engine = RefactorEngine()

    # 1. Preview Rename
    preview = engine.preview_symbol_rename(
        old_symbol="process_data",
        new_symbol="transform_payload",
        target_files=[str(f1), str(f2)]
    )

    assert preview["status"] == "preview"
    assert preview["total_occurrences"] == 2
    assert len(preview["affected_files"]) == 2
    assert str(f1) in preview["diffs"]
    assert str(f2) in preview["diffs"]

    # Assert unified diff format
    diff_f2 = preview["diffs"][str(f2)]
    assert "-def process_data():" in diff_f2
    assert "+def transform_payload():" in diff_f2

    # 2. Apply Refactor Atomically
    updates = {
        str(f1): "import callee\ncallee.transform_payload()\n",
        str(f2): "def transform_payload():\n    return 42\n"
    }
    apply_res = engine.apply_refactor(updates)
    assert apply_res["status"] == "applied"
    assert len(apply_res["modified_files"]) == 2

    assert "transform_payload" in f1.read_text(encoding="utf-8")
    assert "transform_payload" in f2.read_text(encoding="utf-8")

    # 3. Test Atomic Rollback on Failure
    original_f1 = f1.read_text(encoding="utf-8")
    original_f2 = f2.read_text(encoding="utf-8")

    # Pass an invalid file path that cannot be written to force an OS exception mid-operation
    invalid_updates = {
        str(f1): "CORRUPTED CONTENT",
        "Z:/invalid_drive_that_does_not_exist/file.py": "FAIL"
    }

    with pytest.raises(RuntimeError):
        engine.apply_refactor(invalid_updates)

    # Confirm f1 was rolled back to original content
    assert f1.read_text(encoding="utf-8") == original_f1, "Failed atomic refactor must restore original file content."


# ==============================================================================
# 6. Safety Engine Tool Registry Audit (SAF-01.1)
# ==============================================================================

def test_code_intelligence_tool_registry_audit():
    """Asserts all 5 code intelligence tools are registered in ToolRegistry with proper risk tiers and previews."""
    expected_tools = {
        "index_workspace_symbols": 0,
        "lookup_symbol_definition": 0,
        "find_symbol_references": 0,
        "preview_code_refactor": 0,
        "apply_code_refactor": 1
    }

    for tool_name, expected_tier in expected_tools.items():
        assert tool_name in registry._tools, f"Tool '{tool_name}' must be registered in ToolRegistry."
        tool_def = registry._tools[tool_name]
        assert tool_def.tier == expected_tier, f"Tool '{tool_name}' tier mismatch."
        assert issubclass(tool_def.args_schema, BaseModel), f"Tool '{tool_name}' missing Pydantic schema."

    # Test preview generators
    preview_index = registry._tools["index_workspace_symbols"].preview_fn({"max_files": 500})
    assert "500" in preview_index

    preview_lookup = registry._tools["lookup_symbol_definition"].preview_fn({"symbol_name": "AstCodeParser"})
    assert "AstCodeParser" in preview_lookup

    preview_refactor = registry._tools["preview_code_refactor"].preview_fn({"old_symbol": "old_name", "new_symbol": "new_name"})
    assert "old_name" in preview_refactor and "new_name" in preview_refactor

    preview_apply = registry._tools["apply_code_refactor"].preview_fn({"file_updates": {"a.py": "new"}})
    assert "a.py" in preview_apply


# ==============================================================================
# 7. Guardian Kill Switch SLA Benchmark (< 25.0ms SLA)
# ==============================================================================

def test_guardian_kill_switch_code_intelligence_sla():
    """Asserts Guardian kill switch halts code indexing and refactoring with SLA < 25.0ms."""
    latencies = []

    for i in range(50):
        guardian.resume()
        assert not guardian.is_halted

        t0 = time.perf_counter()
        guardian.trigger("Benchmark Code Intelligence Kill Switch")
        t1 = time.perf_counter()

        elapsed_ms = (t1 - t0) * 1000.0
        latencies.append(elapsed_ms)
        assert guardian.is_halted

        # Verify operations raise PermissionError
        with pytest.raises(PermissionError):
            workspace_indexer.lookup_symbol("AstCodeParser")

        with pytest.raises(PermissionError):
            refactor_engine.preview_symbol_rename("old", "new")

    guardian.resume()

    max_latency = max(latencies)
    avg_latency = sum(latencies) / len(latencies)

    print(f"\n[Guardian Code Intelligence SLA] Max: {max_latency:.4f} ms | Avg: {avg_latency:.4f} ms")
    assert max_latency < 25.0, f"Guardian SLA violation: {max_latency:.2f} ms exceeded 25.0ms SLA."
    assert avg_latency < 25.0, f"Guardian avg SLA violation: {avg_latency:.2f} ms exceeded 25.0ms SLA."
