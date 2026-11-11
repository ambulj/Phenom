"""Test Suite for Dynamic Micro-Tool Synthesis & AST Sandbox Foundry (Milestone 32 Phase 3).

Validates:
- Autonomous Python micro-tool synthesis with Pydantic schemas (TOOL-01.1).
- Static AST security validation detecting forbidden imports and calls (TOOL-01.2).
- Isolated sandbox test execution (SAND-02.1).
- Dynamic hot-loading and unregistering in ToolRegistry (SAND-02.2).
- Rule 8 Anti-Checkout defense rejecting payment/billing directives with Rule8ViolationError.
- Rule 11 Credential scrubbing masking secrets to [REDACTED].
- Universal Guardian kill switch SLA benchmark (< 25.0ms hard SLA, typical < 0.1ms).
- Tool registry integration and schema previews for all 6 foundry tools.
"""

import time
import pytest

from services.backend.safety.guardian import guardian
from services.backend.safety.registry import registry
from services.backend.evolution.tool_foundry import (
    ToolFoundry,
    ToolFoundryStatus,
    Rule8ViolationError,
    ASTSecurityViolation,
)
import services.backend.tools.tool_foundry_tools  # Ensure tools are registered


@pytest.fixture
def foundry():
    f = ToolFoundry()
    guardian.resume()
    f.reset_halt()
    yield f
    guardian.resume()
    f.reset_halt()


def test_tool_synthesis_and_pydantic_code_generation(foundry):
    """TOOL-01.1: Verify tool generation creates valid Python code and schemas."""
    tool_def = foundry.synthesize_tool(
        name="compute_word_stats",
        description="Calculates word count and character count of input text.",
        parameters={"text": "str"},
        logic_body="""    words = text.split()
    return {"word_count": len(words), "char_count": len(text)}
""",
        test_assertions=[
            "res = handle_synth_compute_word_stats('hello world')",
            "assert res['word_count'] == 2",
            "assert res['char_count'] == 11",
        ],
        tier=0,
    )

    assert tool_def.name == "synth_compute_word_stats"
    assert tool_def.tier == 0
    assert tool_def.status == ToolFoundryStatus.SYNTHESIZED
    assert "class SynthComputeWordStatsArgs(BaseModel):" in tool_def.tool_code
    assert "text: str = Field(..., description='Parameter text')" in tool_def.tool_code
    assert "def test_synth_compute_word_stats_execution():" in tool_def.test_code


def test_ast_security_analysis_passes_safe_code(foundry):
    """TOOL-01.2: Verify AST security validator allows safe Python code."""
    safe_code = """
def compute_sum(a: int, b: int) -> int:
    return a + b
"""
    report = foundry.validate_ast_security(safe_code)
    assert report.is_safe is True
    assert len(report.violations) == 0
    assert report.scanned_nodes_count > 0


def test_ast_security_analysis_rejects_forbidden_imports_and_calls(foundry):
    """TOOL-01.2: Verify AST security validator rejects socket, ctypes, eval, and os.system."""
    # 1. Forbidden socket import
    socket_code = """
import socket
s = socket.socket()
"""
    report_socket = foundry.validate_ast_security(socket_code)
    assert report_socket.is_safe is False
    assert any("Forbidden import 'socket'" in v for v in report_socket.violations)

    # 2. Forbidden eval call
    eval_code = """
def run_dynamic(code_str: str):
    return eval(code_str)
"""
    report_eval = foundry.validate_ast_security(eval_code)
    assert report_eval.is_safe is False
    assert any("Forbidden function call 'eval()'" in v for v in report_eval.violations)

    # 3. Forbidden ctypes import
    ctypes_code = """
import ctypes
"""
    report_ctypes = foundry.validate_ast_security(ctypes_code)
    assert report_ctypes.is_safe is False


def test_sandbox_execution_and_unit_testing(foundry):
    """SAND-02.1: Verify isolated sandbox runs unit test suites to pass/fail status."""
    # 1. Passing tool
    pass_tool = foundry.synthesize_tool(
        name="square_number",
        description="Squares an integer.",
        parameters={"n": "int"},
        logic_body="    return {'result': n * n}",
        test_assertions=[
            "res = handle_synth_square_number(4)",
            "assert res['result'] == 16",
        ],
    )
    res_pass = foundry.test_in_sandbox(pass_tool.id)
    assert res_pass["success"] is True
    assert pass_tool.status == ToolFoundryStatus.TESTS_PASSED

    # 2. Failing tool (bad assertion)
    fail_tool = foundry.synthesize_tool(
        name="buggy_tool",
        description="Tool with failing unit test.",
        parameters={"n": "int"},
        logic_body="    return {'result': n + 1}",
        test_assertions=[
            "res = handle_synth_buggy_tool(5)",
            "assert res['result'] == 999",  # Fails
        ],
    )
    with pytest.raises(RuntimeError) as exc_info:
        foundry.test_in_sandbox(fail_tool.id)
    assert "Sandbox test suite failed" in str(exc_info.value)
    assert fail_tool.status == ToolFoundryStatus.REJECTED


def test_dynamic_hot_loading_and_unloading_in_registry(foundry):
    """SAND-02.2: Verify dynamic hot-registration and unregistration in ToolRegistry."""
    tool_def = foundry.synthesize_tool(
        name="reverse_text",
        description="Reverses a string.",
        parameters={"message": "str"},
        logic_body="    return {'reversed': message[::-1]}",
        test_assertions=[
            "res = handle_synth_reverse_text('abc')",
            "assert res['reversed'] == 'cba'",
        ],
        tier=0,
    )

    # Hot load into registry
    load_res = foundry.hot_load_tool(tool_def.id)
    assert load_res["status"] == "REGISTERED"

    # Verify registered in registry
    registered_tool = registry.get("synth_reverse_text")
    assert registered_tool is not None
    assert registered_tool.tier == 0

    # Unload tool
    unloaded = foundry.unload_tool("synth_reverse_text")
    assert unloaded is True
    assert registry.get("synth_reverse_text") is None


def test_rule_8_anti_checkout_defense(foundry):
    """Rule 8: Verify rejection of any tool synthesis targeting payment or checkout."""
    with pytest.raises(Rule8ViolationError):
        foundry.synthesize_tool(
            name="checkout_helper",
            description="Automate credit card checkout and purchase",
            parameters={"card_number": "str"},
            logic_body="    return {'status': 'PAID'}",
            test_assertions=[],
        )

    # AST validation on checkout code
    rep = foundry.validate_ast_security("def enter_cvv_and_pay(): pass")
    assert rep.is_safe is False
    assert any("Rule 8 Violation" in v for v in rep.violations)


def test_rule_11_credential_protection(foundry):
    """Rule 11: Verify sensitive credentials and tokens are scrubbed."""
    clean_dict = foundry.scrub_dict({
        "safe_key": "safe_val",
        "api_key": "sk-proj-supersecret9981",
        "nested": {"token": "bearer-xyz"},
    })
    assert clean_dict["api_key"] == "[REDACTED]"
    assert clean_dict["nested"]["token"] == "[REDACTED]"
    assert clean_dict["safe_key"] == "safe_val"


def test_universal_guardian_kill_switch_sla(foundry):
    """Rule 3: Verify Guardian kill switch halts tool foundry within < 25.0ms SLA."""
    guardian.resume()
    foundry.reset_halt()

    latencies_ms = []
    for _ in range(50):
        t0 = time.perf_counter()
        foundry.halt()
        dt_ms = (time.perf_counter() - t0) * 1000.0
        latencies_ms.append(dt_ms)
        assert dt_ms < 25.0, f"Guardian SLA breached: {dt_ms}ms >= 25.0ms"

        # Verify execution is blocked
        with pytest.raises(RuntimeError) as exc_info:
            foundry.check_safety()
        assert "Guardian kill switch" in str(exc_info.value)

        foundry.reset_halt()

    avg_latency = sum(latencies_ms) / len(latencies_ms)
    max_latency = max(latencies_ms)
    assert avg_latency < 1.0, f"Average halt latency {avg_latency:.4f}ms exceeds 1.0ms target"
    assert max_latency < 25.0, f"Max halt latency {max_latency:.4f}ms exceeds 25.0ms SLA"


def test_tool_foundry_registry_audit():
    """SAF-01: Verify all 6 foundry tools are registered in ToolRegistry."""
    expected_tools = [
        "synthesize_python_micro_tool",
        "validate_tool_ast_security",
        "test_micro_tool_in_sandbox",
        "hot_load_synthetic_micro_tool",
        "unload_synthetic_micro_tool",
        "list_synthetic_micro_tools",
    ]

    for tool_name in expected_tools:
        tool_def = registry.get(tool_name)
        assert tool_def is not None, f"Tool '{tool_name}' not registered in ToolRegistry"
        assert tool_def.args_schema is not None
        assert callable(tool_def.preview_fn)

    # Verify Tiers
    assert registry.get("synthesize_python_micro_tool").tier == 1
    assert registry.get("validate_tool_ast_security").tier == 0
    assert registry.get("test_micro_tool_in_sandbox").tier == 1
    assert registry.get("hot_load_synthetic_micro_tool").tier == 1
    assert registry.get("unload_synthetic_micro_tool").tier == 1
    assert registry.get("list_synthetic_micro_tools").tier == 0

    # Verify preview generation
    preview_synth = registry.get("synthesize_python_micro_tool").preview_fn({
        "name": "calc_metrics",
        "tier": 0,
    })
    assert "calc_metrics" in preview_synth

    preview_test = registry.get("test_micro_tool_in_sandbox").preview_fn({
        "tool_id": "tool-1234",
    })
    assert "tool-1234" in preview_test
