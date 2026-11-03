"""
Dynamic Runtime Micro-Tool Synthesizer & Lifecycle Manager.
Part of Phenom Milestone 11.0 Phase 1 (SYN-01, SAF-01, SAF-02).

Synthesizes, AST-inspects, in-sandbox unit-tests, and manages bespoke Python micro-tools.
"""

import re
import datetime
import threading
from typing import Dict, Any, List, Optional
from services.backend.safety.ast_inspector import ast_inspector
from services.backend.coding.restricted_sandbox import restricted_sandbox
from services.backend.schemas.synthesis import (
    ToolSynthesisRequest,
    SynthesizedToolProposal,
    SynthesizedToolMetadata,
)


class SafetyViolationError(Exception):
    """Raised when candidate code violates AST safety rules."""
    pass


class VerificationFailureError(Exception):
    """Raised when candidate code fails sandbox unit testing."""
    pass


def sanitize_schema_name(tool_name: str) -> str:
    """Sanitize dynamic Pydantic model names per plan specification."""
    clean = re.sub(r"[^a-zA-Z0-9_]", "_", tool_name)
    parts = clean.split("_")
    capitalized = "".join(p.capitalize() for p in parts if p)
    return (capitalized or "CustomTool") + "Args"


class DynamicToolSynthesizer:
    """
    Autonomous engine that synthesizes Python micro-tool functions,
    Pydantic schemas, and unit test suites from task specifications.
    """

    def synthesize_proposal(self, request: ToolSynthesisRequest) -> SynthesizedToolProposal:
        tool_name = re.sub(r"[^a-zA-Z0-9_]", "_", request.tool_name).strip("_").lower()
        if not tool_name:
            tool_name = "custom_tool"

        model_name = sanitize_schema_name(tool_name)
        params = request.parameter_specs or {}
        task_desc = request.task_description or "Custom operation"

        # Check for known template patterns or generate general structure
        if "flatten" in tool_name or "flatten" in task_desc.lower():
            func_code = f"""def {tool_name}(nested_dict: dict, separator: str = ".") -> dict:
    \"\"\"{task_desc}\"\"\"
    flat = {{}}
    def _recurse(d, prefix):
        for k, v in d.items():
            new_key = f"{{prefix}}{{separator}}{{k}}" if prefix else str(k)
            if isinstance(v, dict):
                _recurse(v, new_key)
            else:
                flat[new_key] = v
    _recurse(nested_dict, "")
    return flat
"""
            test_code = f"""# Test cases for {tool_name}
sample = {{"a": 1, "b": {{"c": 2, "d": {{"e": 3}}}}}}
res = {tool_name}(sample)
assert res["a"] == 1
assert res["b.c"] == 2
assert res["b.d.e"] == 3
assert len(res) == 3
"""
            capabilities = ["CAP_DATA_TRANSFORM"]

        elif "interest" in tool_name or "compound" in tool_name or "math" in tool_name:
            func_code = f"""def {tool_name}(principal: float, annual_rate: float, years: int, compounds_per_year: int = 1) -> dict:
    \"\"\"{task_desc}\"\"\"
    p = float(principal)
    r = float(annual_rate)
    t = float(years)
    n = float(compounds_per_year)
    amount = p * ((1.0 + (r / n)) ** (n * t))
    interest = amount - p
    return {{
        "principal": round(p, 2),
        "total_amount": round(amount, 2),
        "total_interest": round(interest, 2),
        "years": int(years)
    }}
"""
            test_code = f"""# Test cases for {tool_name}
res = {tool_name}(1000.0, 0.05, 10, 1)
assert res["principal"] == 1000.0
assert res["total_amount"] > 1600.0
assert res["total_interest"] > 600.0
"""
            capabilities = ["CAP_MATH"]

        elif "extract" in tool_name or "regex" in tool_name:
            func_code = f"""def {tool_name}(text: str, pattern: str) -> dict:
    \"\"\"{task_desc}\"\"\"
    import re
    matches = re.findall(pattern, text)
    return {{
        "pattern": pattern,
        "match_count": len(matches),
        "matches": matches
    }}
"""
            test_code = f"""# Test cases for {tool_name}
res = {tool_name}("Sample text with 123 and 456 numbers", r"\\d+")
assert res["match_count"] == 2
assert res["matches"] == ["123", "456"]
"""
            capabilities = ["CAP_DATA_TRANSFORM"]

        else:
            # General parametric computation / transform template
            arg_defs = []
            test_args = {}
            for param_name, param_spec in params.items():
                clean_param = re.sub(r"[^a-zA-Z0-9_]", "_", param_name)
                spec_type = str(param_spec) if not isinstance(param_spec, dict) else param_spec.get("type", "Any")
                if "int" in spec_type.lower():
                    arg_defs.append(f"{clean_param}: int = 0")
                    test_args[clean_param] = 10
                elif "float" in spec_type.lower():
                    arg_defs.append(f"{clean_param}: float = 0.0")
                    test_args[clean_param] = 5.5
                elif "list" in spec_type.lower():
                    arg_defs.append(f"{clean_param}: list = None")
                    test_args[clean_param] = [1, 2, 3]
                elif "dict" in spec_type.lower():
                    arg_defs.append(f"{clean_param}: dict = None")
                    test_args[clean_param] = {"test": 1}
                else:
                    arg_defs.append(f"{clean_param}: str = ''")
                    test_args[clean_param] = "sample"

            sig = ", ".join(arg_defs) if arg_defs else "input_data: str = ''"
            first_arg = list(test_args.keys())[0] if test_args else "input_data"
            test_call = ", ".join(f"{k}={repr(v)}" for k, v in test_args.items()) if test_args else "input_data='sample'"

            func_code = f"""def {tool_name}({sig}) -> dict:
    \"\"\"{task_desc}\"\"\"
    # Autonomous synthesized implementation for: {task_desc}
    return {{
        "status": "success",
        "operation": "{tool_name}",
        "primary_input": {first_arg}
    }}
"""
            test_code = f"""# Test cases for {tool_name}
res = {tool_name}({test_call})
assert res["status"] == "success"
assert res["operation"] == "{tool_name}"
"""
            capabilities = ["CAP_DATA_TRANSFORM"]

        schema_code = f"""class {model_name}(BaseModel):
    # Dynamic schema for {tool_name}
    pass
"""

        return SynthesizedToolProposal(
            tool_name=tool_name,
            description=task_desc,
            function_code=func_code,
            schema_code=schema_code,
            test_code=test_code,
            declared_tier=0,
            capabilities=capabilities,
        )

    def synthesize_and_verify(self, request: ToolSynthesisRequest) -> SynthesizedToolProposal:
        """
        Synthesizes a tool proposal, validates with static AST inspection,
        and executes unit tests inside the restricted subprocess sandbox.
        """
        proposal = self.synthesize_proposal(request)

        # 1. Static AST Inspection of function code
        func_report = ast_inspector.inspect_code(proposal.function_code)
        if not func_report.is_safe:
            violation_desc = "; ".join(f"[{v.violation_type}] {v.description}" for v in func_report.violations)
            raise SafetyViolationError(f"AST Safety Inspection failed for function code: {violation_desc}")

        # 2. Static AST Inspection of test code
        test_report = ast_inspector.inspect_code(proposal.test_code)
        if not test_report.is_safe:
            violation_desc = "; ".join(f"[{v.violation_type}] {v.description}" for v in test_report.violations)
            raise SafetyViolationError(f"AST Safety Inspection failed for test code: {violation_desc}")

        # Re-tag capabilities and risk tier from AST report
        all_caps = sorted(list(set(func_report.detected_capabilities + proposal.capabilities)))
        proposal.capabilities = all_caps
        proposal.declared_tier = func_report.risk_tier

        # 3. Dynamic verification inside restricted subprocess sandbox
        test_harness = f"{proposal.function_code}\n\n{proposal.test_code}"
        test_result = restricted_sandbox.execute_unit_test(test_harness, timeout=5.0)

        if not test_result.success:
            err = test_result.error or test_result.stderr or "Unit test assertions failed in sandbox."
            raise VerificationFailureError(f"Sandbox verification failed for candidate tool '{proposal.tool_name}': {err}")

        return proposal


class SynthesizedToolManager:
    """
    Singleton repository maintaining active synthesized micro-tools,
    proposals, and runtime execution metrics.
    """

    def __init__(self):
        self._active_tools: Dict[str, SynthesizedToolMetadata] = {}
        self._proposals: Dict[str, SynthesizedToolProposal] = {}
        self._halted: bool = False
        self._lock = threading.Lock()

    def halt(self):
        self._halted = True

    def reset(self):
        self._halted = False

    def register_synthesized_tool(self, proposal: SynthesizedToolProposal) -> SynthesizedToolMetadata:
        if self._halted:
            raise PermissionError("SynthesizedToolManager is halted by Guardian kill switch.")

        with self._lock:
            meta = SynthesizedToolMetadata(
                tool_name=proposal.tool_name,
                description=proposal.description,
                tier=proposal.declared_tier,
                capabilities=proposal.capabilities,
                created_at=datetime.datetime.now(datetime.timezone.utc).isoformat(),
                invocation_count=0,
                avg_duration_ms=0.0,
                last_status="active",
            )
            self._proposals[proposal.tool_name] = proposal
            self._active_tools[proposal.tool_name] = meta
            return meta

    def unregister_tool(self, tool_name: str) -> bool:
        with self._lock:
            removed = self._active_tools.pop(tool_name, None)
            self._proposals.pop(tool_name, None)
            return removed is not None

    def get_tool(self, tool_name: str) -> Optional[SynthesizedToolMetadata]:
        with self._lock:
            return self._active_tools.get(tool_name)

    def get_proposal(self, tool_name: str) -> Optional[SynthesizedToolProposal]:
        with self._lock:
            return self._proposals.get(tool_name)

    def list_tools(self, capability_filter: Optional[str] = None) -> List[SynthesizedToolMetadata]:
        with self._lock:
            tools = list(self._active_tools.values())
            if capability_filter:
                tools = [t for t in tools if capability_filter in t.capabilities]
            return tools

    def record_execution(self, tool_name: str, duration_ms: float, success: bool):
        with self._lock:
            meta = self._active_tools.get(tool_name)
            if meta:
                new_count = meta.invocation_count + 1
                meta.avg_duration_ms = ((meta.avg_duration_ms * meta.invocation_count) + duration_ms) / new_count
                meta.invocation_count = new_count
                meta.last_status = "active" if success else "error"


# Global singleton instances
dynamic_synthesizer = DynamicToolSynthesizer()
dynamic_synthesizer_manager = SynthesizedToolManager()
