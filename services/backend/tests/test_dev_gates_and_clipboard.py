"""
Tests for Developer Quality Gates, Smart Clipboard Assistance,
Proactive Patch Advisor, and Triple-Escape Kill Switch.
"""

import os
import time
import pytest
from services.backend.tools.git_tools import handle_git_pre_push_gate, git_pre_push_preview
from services.backend.tools.clipboard_tools import handle_smart_clipboard_inspect, analyze_clipboard_snippet
from services.backend.coding.patch_advisor import PatchAdvisor
from services.backend.safety.guardian import GuardianKillSwitch
from services.backend.safety.registry import registry
from services.backend.voice.hotkeys import HotkeyManager

def test_git_pre_push_gate_registered_tier2():
    tool = registry.get("git_pre_push_gate")
    assert tool is not None
    assert tool.tier == 2
    preview = tool.preview_fn({"repo_path": ".", "target_branch": "main"})
    assert "pre-push quality gate" in preview.lower()

def test_git_pre_push_gate_executes_on_current_repo():
    result = handle_git_pre_push_gate(repo_path=".", target_branch="main")
    assert "verdict" in result
    assert result["verdict"] in ["PASS", "BLOCKED"]
    assert "pr_markdown" in result
    assert "## Pull Request:" in result["pr_markdown"]
    assert "Quality Checklist" in result["pr_markdown"]

def test_smart_clipboard_stack_trace_detection():
    sample_trace = """Traceback (most recent call last):
  File "services/backend/main.py", line 42, in handle_request
    result = calculate_metrics(items)
  File "services/backend/tools/calc.py", line 15, in calculate_metrics
    val = total / count
ZeroDivisionError: division by zero"""

    res = analyze_clipboard_snippet(sample_trace)
    assert res["type"] == "stack_trace"
    assert "ZeroDivisionError" in res["summary"]
    assert res["failing_file"] == "services/backend/tools/calc.py"
    assert res["failing_line"] == 15
    assert res["failing_function"] == "calculate_metrics"
    assert res["suggested_action"] == "propose_patch"

def test_smart_clipboard_git_url_detection():
    res = analyze_clipboard_snippet("https://github.com/ambulj/phenom.git")
    assert res["type"] == "git_url"
    assert res["repo_name"] == "phenom"
    assert "git clone" in res["suggested_action"]

    res_ssh = analyze_clipboard_snippet("git@github.com:facebook/react.git")
    assert res_ssh["type"] == "git_url"
    assert res_ssh["repo_name"] == "react"

def test_smart_clipboard_json_detection():
    json_str = '{"name": "Phenom", "status": "active", "version": "1.0.0"}'
    res = analyze_clipboard_snippet(json_str)
    assert res["type"] == "json_object"
    assert "name" in res["keys"]
    assert res["total_keys"] == 3

    json_arr = '[1, 2, 3, 4, 5]'
    res_arr = analyze_clipboard_snippet(json_arr)
    assert res_arr["type"] == "json_array"
    assert res_arr["item_count"] == 5

def test_smart_clipboard_regex_detection():
    res = analyze_clipboard_snippet(r"/^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$/")
    assert res["type"] == "regex"
    assert "pattern" in res

def test_patch_advisor_traceback_analysis_and_diff(tmp_path):
    # Create sample faulty file
    code_file = tmp_path / "faulty_module.py"
    code_file.write_text("""def compute(val, count):
    # Perform math
    baseline = val * 10
    average = baseline / count
    return average
""", encoding="utf-8")

    traceback_str = f"""Traceback (most recent call last):
  File "{str(code_file)}", line 4, in compute
    average = baseline / count
ZeroDivisionError: division by zero"""

    advisor = PatchAdvisor(workspace_root=str(tmp_path))
    proposal = advisor.generate_patch_proposal(traceback_str)

    assert proposal is not None
    assert proposal.line_number == 4
    assert "ZeroDivisionError" in proposal.explanation or "division by zero" in proposal.explanation
    assert proposal.unified_diff != ""
    assert "--- a/faulty_module.py" in proposal.unified_diff
    assert "+++ b/faulty_module.py" in proposal.unified_diff

def test_guardian_triple_escape_trigger():
    guardian_inst = GuardianKillSwitch()
    assert not guardian_inst.is_halted

    # Simulate triple-escape timestamp detection
    timestamps = [100.0, 100.2, 100.4]
    # Check that 3 presses within 1.0s trigger halt
    now = 100.5
    valid_presses = [t for t in timestamps if now - t <= 1.0]
    assert len(valid_presses) == 3

    guardian_inst.trigger("global_hotkey_triple_escape")
    assert guardian_inst.is_halted

    guardian_inst.resume()
    assert not guardian_inst.is_halted

def test_hotkey_manager_loads_config_defaults():
    hm = HotkeyManager()
    keys = hm.get_hotkeys()
    assert "push_to_talk" in keys
    assert "toggle_phenom" in keys
    assert "kill_switch" in keys
    assert keys["push_to_talk"] == "ctrl+space"
    assert keys["toggle_phenom"] == "alt+space"
    assert keys["kill_switch"] == "triple_escape"
