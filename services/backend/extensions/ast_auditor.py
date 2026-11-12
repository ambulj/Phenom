"""
AST Safety Auditor for Synthesized Micro-Extensions (EXT-01, SAF-01).
Performs static Python AST analysis to guarantee compliance with Phenom
permanent safety rules before any in-process compilation or execution.
"""

import ast
from typing import List, Set, Tuple


class ASTSafetyAuditor(ast.NodeVisitor):
    """Inspects Python AST for dangerous builtins, modules, reflection, and Rule 7/8 violations."""

    FORBIDDEN_CALLS: Set[str] = {
        "eval",
        "exec",
        "globals",
        "locals",
        "__import__",
        "breakpoint",
        "compile",
        "open",  # Raw file I/O must use Phenom file tools
    }

    FORBIDDEN_MODULES: Set[str] = {
        "os",
        "subprocess",
        "socket",
        "ctypes",
        "winreg",
        "requests",
        "urllib",
        "urllib3",
        "httpx",
        "aiohttp",
        "websockets",
        "http",
        "ftplib",
        "pty",
        "commands",
        "sys",
        "importlib",
        "shutil",
        "pathlib",
    }

    FORBIDDEN_DELETIONS: Set[str] = {
        "remove",
        "unlink",
        "rmdir",
        "rmtree",
    }

    FORBIDDEN_PAYMENT_TERMS: Set[str] = {
        "pay_now",
        "buy_now",
        "place_order",
        "complete_purchase",
        "credit_card",
        "stripe",
        "paypal",
    }

    def __init__(self) -> None:
        self.violations: List[str] = []

    def audit_code(self, code: str) -> Tuple[bool, List[str]]:
        """
        Parse and audit Python source code.
        Returns: (is_safe: bool, list of violation descriptions).
        """
        self.violations = []
        try:
            tree = ast.parse(code)
        except SyntaxError as e:
            return False, [f"SyntaxError in synthesized code: {e}"]

        self.visit(tree)
        return len(self.violations) == 0, self.violations

    def visit_Import(self, node: ast.Import) -> None:
        for alias in node.names:
            base_module = alias.name.split(".")[0]
            if base_module in self.FORBIDDEN_MODULES:
                self.violations.append(f"Forbidden module import: '{alias.name}' (Rule 1/4)")
        self.generic_visit(node)

    def visit_ImportFrom(self, node: ast.ImportFrom) -> None:
        if node.module:
            base_module = node.module.split(".")[0]
            if base_module in self.FORBIDDEN_MODULES:
                self.violations.append(f"Forbidden from-module import: '{node.module}' (Rule 1/4)")
        self.generic_visit(node)

    def visit_Call(self, node: ast.Call) -> None:
        # Check direct function call
        if isinstance(node.func, ast.Name):
            func_name = node.func.id
            if func_name in self.FORBIDDEN_CALLS:
                self.violations.append(f"Forbidden builtin call: '{func_name}()' (Rule 1)")
            if any(term in func_name.lower() for term in self.FORBIDDEN_PAYMENT_TERMS):
                self.violations.append(f"Forbidden payment call: '{func_name}()' (Rule 8)")

        # Check attribute method call e.g. os.remove, shutil.rmtree
        elif isinstance(node.func, ast.Attribute):
            attr_name = node.func.attr
            if attr_name in self.FORBIDDEN_DELETIONS:
                self.violations.append(f"Forbidden permanent deletion method: '.{attr_name}()' (Rule 7)")
            if any(term in attr_name.lower() for term in self.FORBIDDEN_PAYMENT_TERMS):
                self.violations.append(f"Forbidden payment method: '.{attr_name}()' (Rule 8)")

        self.generic_visit(node)

    def visit_Attribute(self, node: ast.Attribute) -> None:
        # Check reflection attempts
        if node.attr in ("__subclasses__", "__bases__", "__mro__", "__globals__"):
            self.violations.append(f"Forbidden reflection attribute access: '.{node.attr}' (Rule 1)")
        self.generic_visit(node)
