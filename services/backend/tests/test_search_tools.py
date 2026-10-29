import os
import pytest
from services.backend.tools.search_tools import ripgrep_search, _python_fallback_search
from services.backend.safety.registry import registry

def test_ripgrep_tool_registered():
    tool = registry.get("ripgrep_search")
    assert tool is not None
    assert tool.tier == 0
    assert "ripgrep_search" in registry.list_all()

def test_ripgrep_fallback_search(tmp_path):
    f1 = tmp_path / "hello.py"
    f1.write_text("def special_function_alpha():\n    return 42\n", encoding="utf-8")
    f2 = tmp_path / "world.txt"
    f2.write_text("This is another file without match.\n", encoding="utf-8")

    matches = _python_fallback_search(
        query="special_function_alpha",
        root_dir=str(tmp_path)
    )
    assert len(matches) == 1
    assert matches[0]["file"] == "hello.py"
    assert matches[0]["line"] == 1
    assert "special_function_alpha" in matches[0]["content"]

def test_ripgrep_search_end_to_end(tmp_path):
    sub = tmp_path / "src"
    sub.mkdir()
    target = sub / "app.ts"
    target.write_text("export const PHENOM_SECRET_KEY_PROBE = 'probe';\n", encoding="utf-8")

    res = ripgrep_search(
        query="PHENOM_SECRET_KEY_PROBE",
        path=str(tmp_path)
    )
    assert "matches" in res
    assert res["total_matches"] >= 1
    assert any("PHENOM_SECRET_KEY_PROBE" in m["content"] for m in res["matches"])

def test_ripgrep_glob_filtering(tmp_path):
    py_file = tmp_path / "test.py"
    py_file.write_text("target_token = 123", encoding="utf-8")
    md_file = tmp_path / "test.md"
    md_file.write_text("target_token in markdown", encoding="utf-8")

    res = ripgrep_search(
        query="target_token",
        path=str(tmp_path),
        file_glob="*.py"
    )
    assert res["total_matches"] == 1
    assert res["matches"][0]["file"] == "test.py"
