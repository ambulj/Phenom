"""AST Static Security Visitor for Phenom (Milestone 24 Phase 2).

Audits Python abstract syntax trees for disallowed modules, sandbox jail escape vectors,
dangerous builtin invocations, and Rule 8 payment tokens (SEC-04.1).
"""

from __future__ import annotations

import ast
import logging
import re
from typing import Any, Dict, List, Optional, Set
from pydantic import BaseModel, Field

from services.backend.safety.guardian import guardian

logger = logging.getLogger("phenom.sandbox.security_visitor")


class Rule8ViolationError(Exception):
    """Raised when code involves payment, checkout, or automated financial transactions."""
    pass


class SecurityAuditVerdict(BaseModel):
    is_safe: bool
    risk_level: str  # SAFE, LOW, HIGH, CRITICAL
    disallowed_imports: List[str] = Field(default_factory=list)
    dangerous_calls: List[str] = Field(default_factory=list)
    jail_escape_vectors: List[str] = Field(default_factory=list)
    rule_8_flags: List[str] = Field(default_factory=list)
    details: str
    metadata: Dict[str, Any] = Field(default_factory=dict)


class ASTSecurityVisitor(ast.NodeVisitor):
    """AST visitor detecting hazardous imports, calls, and attributes."""

    DISALLOWED_MODULES: Set[str] = {
        "os",
        "subprocess",
        "socket",
        "ctypes",
        "requests",
        "urllib",
        "shutil",
        "importlib",
        "sys",
        "builtins",
        "posix",
        "nt",
        "pty",
        "multiprocessing",
    }

    DANGEROUS_CALLS: Set[str] = {
        "exec",
        "eval",
        "compile",
        "open",
        "__import__",
        "globals",
        "locals",
        "vars",
    }

    JAIL_ESCAPE_ATTRS: Set[str] = {
        "__subclasses__",
        "__bases__",
        "__globals__",
        "__code__",
        "__class__",
        "__mro__",
    }

    _RULE_8_PATTERN = re.compile(
        r"\b(checkout|pay|payment|purchase|buy|order|credit.?card|cvv|billing|stripe|paypal)\b",
        re.IGNORECASE,
    )

    def __init__(self) -> None:
        self.disallowed_imports: List[str] = []
        self.dangerous_calls: List[str] = []
        self.jail_escape_vectors: List[str] = []
        self.rule_8_flags: List[str] = []

    def _check_rule_8_text(self, text: str) -> None:
        cleaned = re.sub(r"[_]+", " ", text).lower()
        if self._RULE_8_PATTERN.search(cleaned):
            self.rule_8_flags.append(text)

    def visit_Import(self, node: ast.Import) -> None:
        for alias in node.names:
            base_mod = alias.name.split(".")[0]
            if base_mod in self.DISALLOWED_MODULES:
                self.disallowed_imports.append(alias.name)
            self._check_rule_8_text(alias.name)
        self.generic_visit(node)

    def visit_ImportFrom(self, node: ast.ImportFrom) -> None:
        if node.module:
            base_mod = node.module.split(".")[0]
            if base_mod in self.DISALLOWED_MODULES:
                self.disallowed_imports.append(node.module)
            self._check_rule_8_text(node.module)
        for alias in node.names:
            self._check_rule_8_text(alias.name)
        self.generic_visit(node)

    def visit_Call(self, node: ast.Call) -> None:
        # Check direct calls (e.g. eval("..."))
        if isinstance(node.func, ast.Name):
            if node.func.id in self.DANGEROUS_CALLS:
                self.dangerous_calls.append(node.func.id)
            self._check_rule_8_text(node.func.id)
        # Check attribute calls (e.g. os.system("..."))
        elif isinstance(node.func, ast.Attribute):
            if node.func.attr in self.DANGEROUS_CALLS or node.func.attr == "system":
                self.dangerous_calls.append(node.func.attr)
            self._check_rule_8_text(node.func.attr)
        self.generic_visit(node)

    def visit_Attribute(self, node: ast.Attribute) -> None:
        if node.attr in self.JAIL_ESCAPE_ATTRS:
            self.jail_escape_vectors.append(node.attr)
        self._check_rule_8_text(node.attr)
        self.generic_visit(node)

    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
        self._check_rule_8_text(node.name)
        self.generic_visit(node)

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> None:
        self._check_rule_8_text(node.name)
        self.generic_visit(node)

    def visit_ClassDef(self, node: ast.ClassDef) -> None:
        self._check_rule_8_text(node.name)
        self.generic_visit(node)

    def visit_arg(self, node: ast.arg) -> None:
        self._check_rule_8_text(node.arg)
        self.generic_visit(node)

    def visit_Name(self, node: ast.Name) -> None:
        self._check_rule_8_text(node.id)
        self.generic_visit(node)

    def visit_Constant(self, node: ast.Constant) -> None:
        if isinstance(node.value, str):
            self._check_rule_8_text(node.value)
        self.generic_visit(node)


class CodeSecurityAuditor:
    """Orchestrates static AST security inspections."""

    _RULE_8_PATTERN = re.compile(
        r"\b(checkout|pay|payment|purchase|buy|order|credit.?card|cvv|billing|stripe|paypal)\b",
        re.IGNORECASE,
    )

    def _check_guardian(self) -> None:
        if guardian.is_halted:
            raise PermissionError("Guardian kill switch is TRIPPED. Security audit halted immediately.")

    def _validate_rule_8(self, text: str) -> None:
        cleaned = re.sub(r"[_]+", " ", text).lower()
        if self._RULE_8_PATTERN.search(cleaned):
            raise Rule8ViolationError(
                f"Rule 8 violation: code involves payment or checkout operations: {text}"
            )

    def audit_code(self, source_code: str) -> SecurityAuditVerdict:
        """Inspect source code tree for security violations."""
        self._check_guardian()
        self._validate_rule_8(source_code)

        try:
            tree = ast.parse(source_code)
        except SyntaxError as e:
            return SecurityAuditVerdict(
                is_safe=False,
                risk_level="CRITICAL",
                details=f"AST SyntaxError: {e.msg} at line {e.lineno}",
            )

        visitor = ASTSecurityVisitor()
        visitor.visit(tree)

        # Rule 8 check raises immediately
        if visitor.rule_8_flags:
            raise Rule8ViolationError(
                f"Rule 8 violation: code involves payment or checkout operations: {visitor.rule_8_flags}"
            )

        is_safe = (
            len(visitor.disallowed_imports) == 0
            and len(visitor.dangerous_calls) == 0
            and len(visitor.jail_escape_vectors) == 0
        )

        risk_level = "SAFE"
        if visitor.jail_escape_vectors or any(c in ("exec", "eval") for c in visitor.dangerous_calls):
            risk_level = "CRITICAL"
        elif visitor.disallowed_imports or visitor.dangerous_calls:
            risk_level = "HIGH"

        details = "Code tree passed AST security inspection with zero violations."
        if not is_safe:
            details = (
                f"Security violations detected: imports={visitor.disallowed_imports}, "
                f"calls={visitor.dangerous_calls}, escapes={visitor.jail_escape_vectors}"
            )

        return SecurityAuditVerdict(
            is_safe=is_safe,
            risk_level=risk_level,
            disallowed_imports=visitor.disallowed_imports,
            dangerous_calls=visitor.dangerous_calls,
            jail_escape_vectors=visitor.jail_escape_vectors,
            rule_8_flags=visitor.rule_8_flags,
            details=details,
        )


# Singleton instance
code_security_auditor = CodeSecurityAuditor()
