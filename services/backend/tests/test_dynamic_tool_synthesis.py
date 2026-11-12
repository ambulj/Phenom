"""
Unit tests for Dynamic Tool Synthesizer (SYN-01, SAF-01).
Tests automated tool proposal generation, AST verification,
sandbox test execution, and lifecycle management.
"""

import pytest
from services.backend.schemas.synthesis import (
    ToolSynthesisRequest,
    SynthesizedToolProposal,
)
from services.backend.coding.dynamic_synthesizer import (
    dynamic_synthesizer,
    dynamic_synthesizer_manager,
    SafetyViolationError,
    VerificationFailureError,
    sanitize_schema_name,
)


def test_sanitize_schema_name():
    assert sanitize_schema_name("calc_interest") == "CalcInterestArgs"
    assert sanitize_schema_name("flatten-dict") == "FlattenDictArgs"
    assert sanitize_schema_name("extract_regex_123") == "ExtractRegex123Args"
    assert sanitize_schema_name("") == "CustomToolArgs"


def test_synthesize_math_tool():
    req = ToolSynthesisRequest(
        tool_name="calculate_compound_interest",
        task_description="Calculate compound interest",
        parameter_specs={
            "principal": {"type": "float"},
            "annual_rate": {"type": "float"},
            "years": {"type": "int"},
        },
    )
    proposal = dynamic_synthesizer.synthesize_and_verify(req)
    assert proposal.tool_name == "calculate_compound_interest"
    assert proposal.declared_tier == 0
    assert "CAP_MATH" in proposal.capabilities

    meta = dynamic_synthesizer_manager.register_synthesized_tool(proposal)
    assert meta.tool_name == "calculate_compound_interest"
    assert meta.tier == 0
    assert meta.invocation_count == 0

    # Test list tools
    tools = dynamic_synthesizer_manager.list_tools(capability_filter="CAP_MATH")
    assert any(t.tool_name == "calculate_compound_interest" for t in tools)

    # Clean up
    dynamic_synthesizer_manager.unregister_tool("calculate_compound_interest")


def test_synthesize_data_transform_tool():
    req = ToolSynthesisRequest(
        tool_name="flatten_dictionary",
        task_description="Flatten nested dictionaries into dot-separated keys",
        parameter_specs={"nested_dict": {"type": "dict"}},
    )
    proposal = dynamic_synthesizer.synthesize_and_verify(req)
    assert proposal.tool_name == "flatten_dictionary"
    assert proposal.declared_tier == 0
    assert "CAP_DATA_TRANSFORM" in proposal.capabilities


def test_rejection_of_ast_violations():
    # Proposal containing dangerous AST elements
    req = ToolSynthesisRequest(
        tool_name="dangerous_downloader",
        task_description="Attempt network download",
        parameter_specs={},
    )
    proposal = dynamic_synthesizer.synthesize_proposal(req)
    # Inject socket import into function code
    proposal.function_code = "import socket\ndef dangerous_downloader(): pass"

    with pytest.raises(SafetyViolationError, match="BANNED_MODULE"):
        # Direct verification of tainted proposal
        from services.backend.safety.ast_inspector import ast_inspector
        rep = ast_inspector.inspect_code(proposal.function_code)
        if not rep.is_safe:
            raise SafetyViolationError(f"AST Safety Inspection failed: [{rep.violations[0].violation_type}]")


def test_rejection_of_failing_unit_tests():
    req = ToolSynthesisRequest(
        tool_name="broken_adder",
        task_description="Failing unit test assertion",
        parameter_specs={},
    )
    proposal = dynamic_synthesizer.synthesize_proposal(req)
    proposal.test_code = "assert 1 + 1 == 3"  # Broken assertion

    from services.backend.coding.restricted_sandbox import restricted_sandbox
    harness = f"{proposal.function_code}\n\n{proposal.test_code}"
    res = restricted_sandbox.execute_unit_test(harness)
    assert res.success is False


def test_manager_lifecycle_and_metrics():
    proposal = SynthesizedToolProposal(
        tool_name="demo_tool",
        description="Demo tool for metrics",
        function_code="def demo_tool(): return 42",
        schema_code="class DemoToolArgs(BaseModel): pass",
        test_code="assert demo_tool() == 42",
        declared_tier=0,
        capabilities=["CAP_MATH"],
    )
    meta = dynamic_synthesizer_manager.register_synthesized_tool(proposal)
    assert meta.tool_name == "demo_tool"

    dynamic_synthesizer_manager.record_execution("demo_tool", duration_ms=12.5, success=True)
    updated = dynamic_synthesizer_manager.get_tool("demo_tool")
    assert updated is not None
    assert updated.invocation_count == 1
    assert updated.avg_duration_ms == 12.5
    assert updated.last_status == "active"

    # Unregister
    assert dynamic_synthesizer_manager.unregister_tool("demo_tool") is True
    assert dynamic_synthesizer_manager.get_tool("demo_tool") is None
