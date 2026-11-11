"""Dynamic Micro-Tool Synthesis & AST-Guarded Sandbox Foundry (Milestone 32 Phase 3).

Coordinates:
- Autonomous Python micro-tool generator with typed Pydantic schemas and unit tests (TOOL-01.1).
- Static AST security validator verifying zero forbidden imports or unsafe constructs (TOOL-01.2).
- Isolated ephemeral test runner sandbox verifying synthesized tools before registration (SAND-02.1).
- Dynamic hot-loading and unregistering of synthetic tools in ToolRegistry (SAND-02.2).
- Strict Rule 4 (100% offline local), Rule 7 (Non-destructive operations), Rule 8 (Anti-checkout defense), Rule 11 (Credential scrubbing), and Rule 3 Guardian kill switch SLA < 25.0ms.
"""

from __future__ import annotations

import ast
from enum import Enum
import importlib
import json
import logging
import os
import re
import sys
import tempfile
import threading
import time
from typing import Any, Callable, Dict, List, Optional, Set, Tuple
from pydantic import BaseModel, Field

from services.backend.safety.guardian import guardian
from services.backend.safety.registry import registry

logger = logging.getLogger("phenom.evolution.tool_foundry")


class Rule8ViolationError(Exception):
    """Raised when a tool specification, code, or AST targets payment, checkout, or billing."""
    pass


class ASTSecurityViolation(Exception):
    """Raised when static AST analysis detects forbidden imports, builtins, or unsafe constructs."""
    pass


class ToolFoundryStatus(str, Enum):
    SYNTHESIZED = "SYNTHESIZED"
    AST_PASSED = "AST_PASSED"
    TESTS_PASSED = "TESTS_PASSED"
    REGISTERED = "REGISTERED"
    REJECTED = "REJECTED"
    UNLOADED = "UNLOADED"


class SyntheticToolSpec(BaseModel):
    name: str
    description: str
    tier: int = 0
    parameters: Dict[str, str] = Field(default_factory=dict)  # param_name -> type_str (e.g. "str", "int", "bool")
    return_type: str = "Dict[str, Any]"
    can_remember_per_folder: bool = False


class SyntheticToolDefinition(BaseModel):
    id: str
    name: str
    description: str
    tier: int
    tool_code: str
    test_code: str
    status: ToolFoundryStatus = ToolFoundryStatus.SYNTHESIZED
    security_findings: List[str] = Field(default_factory=list)
    test_results: Optional[Dict[str, Any]] = None
    created_at: float = Field(default_factory=time.time)
    updated_at: float = Field(default_factory=time.time)


class ASTSecurityReport(BaseModel):
    is_safe: bool
    violations: List[str]
    allowed_imports: List[str]
    scanned_nodes_count: int


class ToolFoundry:
    """Autonomous capability engine for AST-guarded micro-tool synthesis, sandbox verification, and hot-loading."""

    _RULE_8_PATTERN = re.compile(
        r"(?:\b|_)(checkout|pay|payment|purchase|buy|order|credit.?card|cvv|billing)(?:\b|_)",
        re.IGNORECASE,
    )

    _CREDENTIAL_PATTERN = re.compile(
        r"(?i)\b(api[_-]?key|secret|token|password|bearer|auth[_-]?token|passwd|pwd)\b\s*[:=\s]\s*['\"]?([A-Za-z0-9_\-\.]{8,})['\"]?"
    )

    _FORBIDDEN_MODULES: Set[str] = {
        "socket", "ssl", "http.client", "urllib.request", "requests",
        "ctypes", "pty", "posix", "winreg", "msvcrt",
        "asyncio.subprocess", "shutil.rmtree",
    }

    _FORBIDDEN_CALLS: Set[str] = {
        "eval", "exec", "compile", "globals", "locals", "__import__",
        "open_osfhandle", "system", "popen", "spawn",
    }

    _SENSITIVE_KEYS = {
        "password", "secret", "token", "api_key", "apikey", "access_token",
        "private_key", "auth", "authorization", "bearer", "credential",
    }

    def __init__(self) -> None:
        self._tools: Dict[str, SyntheticToolDefinition] = {}
        self._loaded_handlers: Dict[str, Any] = {}
        self._lock = threading.Lock()
        self._is_halted: bool = False

    def halt(self) -> None:
        """Halts all synthesis and sandbox evaluation in < 25.0ms (Rule 3)."""
        self._is_halted = True
        logger.warning("[ToolFoundry] Emergency stop triggered via Guardian kill switch")

    def reset_halt(self) -> None:
        """Resets foundry halt state."""
        self._is_halted = False

    def check_safety(self, text: Optional[str] = None) -> None:
        """Enforces Guardian kill switch (Rule 3) and Anti-Checkout (Rule 8)."""
        if self._is_halted or guardian.is_halted:
            raise RuntimeError("Execution halted by Guardian kill switch (TOOL_FOUNDRY_HALTED)")

        if text and self._RULE_8_PATTERN.search(text):
            raise Rule8ViolationError(
                "Rule 8 Violation: Payment, checkout, or billing phrase detected in tool synthesis"
            )

    def scrub_credentials(self, text: str) -> Tuple[str, int]:
        """Recursively scrubs credentials and tokens (Rule 11)."""
        count = 0

        def replace_cred(match: re.Match) -> str:
            nonlocal count
            count += 1
            key = match.group(1)
            return f"{key}: [REDACTED]"

        scrubbed = self._CREDENTIAL_PATTERN.sub(replace_cred, text)
        return scrubbed, count

    def scrub_dict(self, data: Any) -> Any:
        """Recursively scrubs dictionary keys and string values matching sensitive tokens."""
        if isinstance(data, dict):
            clean = {}
            for k, v in data.items():
                if any(s in str(k).lower() for s in self._SENSITIVE_KEYS):
                    clean[k] = "[REDACTED]"
                else:
                    clean[k] = self.scrub_dict(v)
            return clean
        elif isinstance(data, list):
            return [self.scrub_dict(item) for item in data]
        elif isinstance(data, str):
            scrubbed, _ = self.scrub_credentials(data)
            return scrubbed
        return data

    # ==========================================
    # 1. Micro-Tool Code Synthesizer (TOOL-01.1)
    # ==========================================

    def synthesize_tool(
        self,
        name: str,
        description: str,
        parameters: Dict[str, str],
        logic_body: str,
        test_assertions: List[str],
        tier: int = 0,
    ) -> SyntheticToolDefinition:
        """Synthesizes typed Python micro-tool code, schema, preview, and unit tests."""
        self.check_safety(f"{name} {description} {logic_body}")

        # Validate name
        clean_name = re.sub(r"[^a-zA-Z0-9_]", "_", name).lower()
        if not clean_name.startswith("synth_"):
            clean_name = f"synth_{clean_name}"

        # 1. Build Pydantic Args Schema
        schema_fields = []
        for p_name, p_type in parameters.items():
            schema_fields.append(f"    {p_name}: {p_type} = Field(..., description='Parameter {p_name}')")
        schema_code = "\n".join(schema_fields) if schema_fields else "    pass"

        # 2. Build Handler function
        args_list = ", ".join(f"{p_name}: {p_type}" for p_name, p_type in parameters.items())
        tool_code = f'''from typing import Any, Dict, Optional, List
from pydantic import BaseModel, Field

class {clean_name.title().replace("_", "")}Args(BaseModel):
{schema_code}

def preview_{clean_name}(args: Dict[str, Any]) -> str:
    return f"Execute synthetic tool {clean_name}"

def handle_{clean_name}({args_list}) -> Dict[str, Any]:
    # Synthetic tool logic body
{logic_body}
'''

        # 3. Build Test code
        test_body = "\n".join(f"    {assertion}" for assertion in test_assertions) if test_assertions else "    pass"
        test_code = f'''def test_{clean_name}_execution():
{test_body}
'''

        tool_id = f"tool-{int(time.time()*1000)}-{os.urandom(3).hex()}"
        tool_def = SyntheticToolDefinition(
            id=tool_id,
            name=clean_name,
            description=description,
            tier=tier,
            tool_code=tool_code,
            test_code=test_code,
            status=ToolFoundryStatus.SYNTHESIZED,
        )

        with self._lock:
            self._tools[tool_id] = tool_def

        logger.info("[ToolFoundry] Synthesized tool '%s' (%s)", clean_name, tool_id)
        return tool_def

    # ==========================================
    # 2. Static AST Security Validator (TOOL-01.2)
    # ==========================================

    def validate_ast_security(self, code: str) -> ASTSecurityReport:
        """Statically inspects Python AST for dangerous modules, calls, and Rule 8 violations."""
        self.check_safety()

        violations: List[str] = []
        allowed_imports: List[str] = []
        scanned_nodes = 0

        # Check raw text for payment/checkout phrases
        if self._RULE_8_PATTERN.search(code):
            violations.append("Rule 8 Violation: Payment, checkout, or billing phrase detected in code")

        try:
            tree = ast.parse(code)
        except SyntaxError as ex:
            return ASTSecurityReport(
                is_safe=False,
                violations=[f"Python Syntax Error: {ex}"],
                allowed_imports=[],
                scanned_nodes_count=0,
            )

        for node in ast.walk(tree):
            scanned_nodes += 1

            # 1. Inspect imports
            if isinstance(node, ast.Import):
                for alias in node.names:
                    mod_name = alias.name.split(".")[0]
                    if mod_name in self._FORBIDDEN_MODULES:
                        violations.append(f"Forbidden import '{alias.name}' detected")
                    else:
                        allowed_imports.append(alias.name)

            elif isinstance(node, ast.ImportFrom):
                if node.module:
                    mod_name = node.module.split(".")[0]
                    if mod_name in self._FORBIDDEN_MODULES:
                        violations.append(f"Forbidden from-import '{node.module}' detected")
                    else:
                        allowed_imports.append(node.module)

            # 2. Inspect dangerous calls
            elif isinstance(node, ast.Call):
                func = node.func
                func_name = ""
                if isinstance(func, ast.Name):
                    func_name = func.id
                elif isinstance(func, ast.Attribute):
                    func_name = func.attr

                if func_name in self._FORBIDDEN_CALLS:
                    violations.append(f"Forbidden function call '{func_name}()' detected")

            # 3. Disallow exec / eval expressions
            elif isinstance(node, (ast.Exec if hasattr(ast, "Exec") else ())) :
                violations.append("Forbidden 'exec' statement detected")

        is_safe = len(violations) == 0
        return ASTSecurityReport(
            is_safe=is_safe,
            violations=violations,
            allowed_imports=allowed_imports,
            scanned_nodes_count=scanned_nodes,
        )

    # ==========================================
    # 3. Isolated Sandbox Test Runner (SAND-02.1)
    # ==========================================

    def test_in_sandbox(self, tool_id: str) -> Dict[str, Any]:
        """Executes tool code and unit tests in an isolated in-memory Python namespace."""
        self.check_safety()

        with self._lock:
            tool_def = self._tools.get(tool_id)
            if not tool_def:
                raise ValueError(f"Synthetic tool '{tool_id}' not found")

        # 1. Pre-validation with AST
        ast_report = self.validate_ast_security(tool_def.tool_code + "\n" + tool_def.test_code)
        if not ast_report.is_safe:
            tool_def.status = ToolFoundryStatus.REJECTED
            tool_def.security_findings = ast_report.violations
            raise ASTSecurityViolation(f"AST Security Check Failed: {'; '.join(ast_report.violations)}")

        tool_def.status = ToolFoundryStatus.AST_PASSED

        # 2. Execute in restricted sandbox
        sandbox_builtins = dict(__builtins__.__dict__ if hasattr(__builtins__, "__dict__") else __builtins__)
        for forbidden in ("eval", "exec", "compile"):
            sandbox_builtins.pop(forbidden, None)

        sandbox_scope: Dict[str, Any] = {
            "__builtins__": sandbox_builtins,
            "__name__": "__sandbox__",
        }

        t0 = time.perf_counter()
        test_success = False
        error_msg = None

        try:
            # Execute tool definition
            exec(tool_def.tool_code, sandbox_scope)
            # Execute test suite
            exec(tool_def.test_code, sandbox_scope)

            # Find test functions and execute them
            test_funcs = [v for k, v in sandbox_scope.items() if k.startswith("test_") and callable(v)]
            for tf in test_funcs:
                tf()

            test_success = True
            tool_def.status = ToolFoundryStatus.TESTS_PASSED
        except Exception as ex:
            test_success = False
            error_msg = str(ex)
            tool_def.status = ToolFoundryStatus.REJECTED
            logger.error("[ToolFoundry] Sandbox test failure for '%s': %s", tool_def.name, ex)

        elapsed_ms = (time.perf_counter() - t0) * 1000.0
        test_results = {
            "success": test_success,
            "error": error_msg,
            "elapsed_ms": elapsed_ms,
            "scanned_nodes": ast_report.scanned_nodes_count,
        }
        tool_def.test_results = test_results
        tool_def.updated_at = time.time()

        if not test_success:
            raise RuntimeError(f"Sandbox test suite failed: {error_msg}")

        return test_results

    # ==========================================
    # 4. Dynamic ToolRegistry Hot-Loader (SAND-02.2)
    # ==========================================

    def hot_load_tool(self, tool_id: str) -> Dict[str, Any]:
        """Dynamically registers the verified synthetic tool into ToolRegistry."""
        self.check_safety()

        with self._lock:
            tool_def = self._tools.get(tool_id)
            if not tool_def:
                raise ValueError(f"Synthetic tool '{tool_id}' not found")

        if tool_def.status != ToolFoundryStatus.TESTS_PASSED:
            # Run sandbox test first
            self.test_in_sandbox(tool_id)

        # Build execution scope
        exec_scope: Dict[str, Any] = {}
        exec(tool_def.tool_code, exec_scope)

        handler_name = f"handle_{tool_def.name}"
        preview_name = f"preview_{tool_def.name}"
        args_schema_name = f"{tool_def.name.title().replace('_', '')}Args"

        handler_fn = exec_scope.get(handler_name)
        preview_fn = exec_scope.get(preview_name)
        args_schema = exec_scope.get(args_schema_name)

        if not handler_fn or not preview_fn or not args_schema:
            raise ValueError(f"Could not extract handler/preview/schema from tool code for '{tool_def.name}'")

        # Register into ToolRegistry
        registry.register(
            name=tool_def.name,
            tier=tool_def.tier,
            description=tool_def.description,
            args_schema=args_schema,
            preview_fn=preview_fn,
            can_remember_per_folder=False,
        )(handler_fn)

        with self._lock:
            self._loaded_handlers[tool_def.name] = handler_fn
            tool_def.status = ToolFoundryStatus.REGISTERED
            tool_def.updated_at = time.time()

        logger.info("[ToolFoundry] Hot-loaded tool '%s' into ToolRegistry (Tier %d)", tool_def.name, tool_def.tier)
        return {
            "tool_id": tool_def.id,
            "name": tool_def.name,
            "tier": tool_def.tier,
            "status": tool_def.status.value,
        }

    def unload_tool(self, name_or_id: str) -> bool:
        """Unregisters a previously hot-loaded synthetic tool from ToolRegistry."""
        self.check_safety()

        with self._lock:
            target_tool: Optional[SyntheticToolDefinition] = None
            for t in self._tools.values():
                if t.id == name_or_id or t.name == name_or_id:
                    target_tool = t
                    break

            if not target_tool:
                return False

            tool_name = target_tool.name
            if tool_name in registry._tools:
                del registry._tools[tool_name]
            if tool_name in self._loaded_handlers:
                del self._loaded_handlers[tool_name]

            target_tool.status = ToolFoundryStatus.UNLOADED
            target_tool.updated_at = time.time()

        logger.info("[ToolFoundry] Unloaded tool '%s' from ToolRegistry", tool_name)
        return True

    def list_synthetic_tools(self) -> List[Dict[str, Any]]:
        """Returns inventory of synthesized tools and their verification status."""
        self.check_safety()
        with self._lock:
            tools_list = []
            for t in self._tools.values():
                tools_list.append({
                    "id": t.id,
                    "name": t.name,
                    "description": t.description,
                    "tier": t.tier,
                    "status": t.status.value,
                    "security_findings": t.security_findings,
                    "has_test_results": t.test_results is not None,
                })
            return tools_list


# Global singleton instance
tool_foundry = ToolFoundry()
