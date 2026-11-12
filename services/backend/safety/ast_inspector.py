"""
AST Safety Inspector for Dynamic Runtime Micro-Tool Synthesis.
Part of Phenom Milestone 11.0 Phase 1 (SYN-01, SAF-01, SAF-02).
Enforces strict static safety invariants before execution or disk persistence.
"""

import ast
import re
from typing import List, Set, Optional, Tuple
from services.backend.schemas.synthesis import (
    ASTInspectionReport,
    ASTViolation,
)

# Prohibited Built-in Functions & Reflection Primitives
BANNED_BUILTINS: Set[str] = {
    "eval",
    "exec",
    "compile",
    "globals",
    "locals",
    "__import__",
    "breakpoint",
    "input",
    "getattr",
    "setattr",
    "delattr",
    "open_code",
}

# Prohibited Standard & External Modules (Permanent Rule 4: No Network Exfiltration, No Subprocesses)
BANNED_MODULES: Set[str] = {
    "socket",
    "subprocess",
    "ctypes",
    "winreg",
    "urllib",
    "requests",
    "http",
    "ftplib",
    "telnetlib",
    "aiohttp",
    "httpx",
    "multiprocessing",
    "pty",
    "commands",
    "importlib",
    "shutil",
    "pickle",
    "shelve",
    "marshal",
    "smtplib",
    "imaplib",
    "poplib",
    "nntplib",
    "asyncio.subprocess",
}

# Prohibited Call / Method Attributes (Permanent Rule 7: Delete Means Recycle Bin, No Unlink/Remove)
BANNED_CALL_ATTRIBUTES: Set[str] = {
    "system",
    "popen",
    "spawn",
    "spawnl",
    "spawnle",
    "spawnlp",
    "spawnlpe",
    "spawnv",
    "spawnve",
    "spawnvp",
    "spawnvpe",
    "unlink",
    "remove",
    "rmdir",
    "rmtree",
}

# Prohibited Reflection Dunder Attributes (Sandboxing Invariant)
BANNED_DUNDERS: Set[str] = {
    "__subclasses__",
    "__bases__",
    "__mro__",
    "__globals__",
    "__code__",
    "__closure__",
    "__builtins__",
    "__dict__",
    "__class__",
    "__qualname__",
    "__module__",
}

# Prohibited Payment & Financial Transaction Primitives (Permanent Rule 8)
PAYMENT_KEYWORDS: Set[str] = {
    "pay",
    "payment",
    "payments",
    "checkout",
    "credit_card",
    "creditcard",
    "purchase",
    "purchases",
    "stripe",
    "paypal",
    "razorpay",
    "bank_transfer",
    "cvv",
    "otp",
}


def _matches_payment_primitive(symbol: str) -> bool:
    """Check if symbol references payment/checkout primitives prohibited by Rule 8."""
    sym_lower = symbol.lower()
    # Check compound substrings
    for kw in ("credit_card", "creditcard", "bank_transfer", "paypal", "stripe", "razorpay", "checkout", "purchase"):
        if kw in sym_lower:
            return True
    tokens = re.split(r"[_\W]+", sym_lower)
    for token in tokens:
        if token in PAYMENT_KEYWORDS:
            return True
        if token.startswith("pay") and token not in ("payload", "payloads"):
            return True
    return False


class _ASTVisitor(ast.NodeVisitor):
    def __init__(self):
        self.violations: List[ASTViolation] = []
        self.capabilities: Set[str] = set()
        self.imported_modules: List[str] = []
        self.analyzed_functions: List[str] = []

    def _record_violation(
        self,
        violation_type: str,
        node_type: str,
        line_number: int,
        description: str,
        offending_symbol: str,
    ):
        self.violations.append(
            ASTViolation(
                violation_type=violation_type,
                node_type=node_type,
                line_number=line_number,
                description=description,
                offending_symbol=offending_symbol,
            )
        )

    def visit_FunctionDef(self, node: ast.FunctionDef):
        self.analyzed_functions.append(node.name)
        if _matches_payment_primitive(node.name):
            self._record_violation(
                violation_type="RULE_8_PAYMENT_PRIMITIVE",
                node_type="FunctionDef",
                line_number=node.lineno,
                description=f"Function name '{node.name}' violates Permanent Rule 8 (payments prohibited by construction).",
                offending_symbol=node.name,
            )
        self.generic_visit(node)

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef):
        self.analyzed_functions.append(node.name)
        if _matches_payment_primitive(node.name):
            self._record_violation(
                violation_type="RULE_8_PAYMENT_PRIMITIVE",
                node_type="AsyncFunctionDef",
                line_number=node.lineno,
                description=f"Function name '{node.name}' violates Permanent Rule 8 (payments prohibited by construction).",
                offending_symbol=node.name,
            )
        self.generic_visit(node)

    def visit_ClassDef(self, node: ast.ClassDef):
        if _matches_payment_primitive(node.name):
            self._record_violation(
                violation_type="RULE_8_PAYMENT_PRIMITIVE",
                node_type="ClassDef",
                line_number=node.lineno,
                description=f"Class name '{node.name}' violates Permanent Rule 8 (payments prohibited by construction).",
                offending_symbol=node.name,
            )
        self.generic_visit(node)

    def visit_arg(self, node: ast.arg):
        if _matches_payment_primitive(node.arg):
            self._record_violation(
                violation_type="RULE_8_PAYMENT_PRIMITIVE",
                node_type="arg",
                line_number=node.lineno,
                description=f"Argument name '{node.arg}' violates Permanent Rule 8 (payments prohibited by construction).",
                offending_symbol=node.arg,
            )
        self.generic_visit(node)

    def visit_Import(self, node: ast.Import):
        for alias in node.names:
            name = alias.name
            self.imported_modules.append(name)
            base_module = name.split(".")[0]
            if name in BANNED_MODULES or base_module in BANNED_MODULES:
                self._record_violation(
                    violation_type="BANNED_MODULE",
                    node_type="Import",
                    line_number=node.lineno,
                    description=f"Import of module '{name}' is forbidden for sandboxed micro-tools.",
                    offending_symbol=name,
                )
            elif name in {"math", "statistics", "decimal", "fractions"}:
                self.capabilities.add("CAP_MATH")
            elif name in {"re", "json", "csv", "collections", "itertools", "datetime", "string"}:
                self.capabilities.add("CAP_DATA_TRANSFORM")
            elif name in {"pathlib", "os.path"}:
                # Module alone does not imply write, inspect calls
                pass
        self.generic_visit(node)

    def visit_ImportFrom(self, node: ast.ImportFrom):
        mod = node.module or ""
        self.imported_modules.append(mod)
        base_mod = mod.split(".")[0]
        if mod in BANNED_MODULES or base_mod in BANNED_MODULES:
            self._record_violation(
                violation_type="BANNED_MODULE",
                node_type="ImportFrom",
                line_number=node.lineno,
                description=f"Import from module '{mod}' is forbidden for sandboxed micro-tools.",
                offending_symbol=mod,
            )
        for alias in node.names:
            if alias.name in BANNED_BUILTINS or alias.name in BANNED_CALL_ATTRIBUTES:
                self._record_violation(
                    violation_type="BANNED_SYMBOL_IMPORT",
                    node_type="ImportFrom",
                    line_number=node.lineno,
                    description=f"Import of symbol '{alias.name}' from '{mod}' is prohibited.",
                    offending_symbol=alias.name,
                )
        if mod in {"math", "statistics", "decimal", "fractions"}:
            self.capabilities.add("CAP_MATH")
        elif mod in {"re", "json", "csv", "collections", "itertools", "datetime", "string"}:
            self.capabilities.add("CAP_DATA_TRANSFORM")
        self.generic_visit(node)

    def visit_Name(self, node: ast.Name):
        if node.id in BANNED_BUILTINS:
            self._record_violation(
                violation_type="BANNED_BUILTIN",
                node_type="Name",
                line_number=node.lineno,
                description=f"Reference to dangerous built-in or reflection primitive '{node.id}' is prohibited.",
                offending_symbol=node.id,
            )
        elif node.id in BANNED_DUNDERS:
            self._record_violation(
                violation_type="REFLECTION_ESCAPE",
                node_type="Name",
                line_number=node.lineno,
                description=f"Dunder reflection symbol '{node.id}' is prohibited.",
                offending_symbol=node.id,
            )
        elif _matches_payment_primitive(node.id):
            self._record_violation(
                violation_type="RULE_8_PAYMENT_PRIMITIVE",
                node_type="Name",
                line_number=node.lineno,
                description=f"Identifier '{node.id}' matches payment keyword prohibited by Permanent Rule 8.",
                offending_symbol=node.id,
            )
        self.generic_visit(node)

    def visit_Attribute(self, node: ast.Attribute):
        attr = node.attr
        if attr in BANNED_DUNDERS:
            self._record_violation(
                violation_type="REFLECTION_ESCAPE",
                node_type="Attribute",
                line_number=node.lineno,
                description=f"Dunder attribute access '{attr}' is prohibited (reflection escape guard).",
                offending_symbol=attr,
            )
        elif attr in BANNED_CALL_ATTRIBUTES:
            self._record_violation(
                violation_type="RULE_7_PERMANENT_DELETE_OR_EXEC",
                node_type="Attribute",
                line_number=node.lineno,
                description=f"Attribute '{attr}' violates Permanent Rule 7 (delete means recycle bin) or process execution rules.",
                offending_symbol=attr,
            )
        elif attr in BANNED_BUILTINS:
            self._record_violation(
                violation_type="BANNED_BUILTIN",
                node_type="Attribute",
                line_number=node.lineno,
                description=f"Attribute '{attr}' references banned reflection or evaluation primitive.",
                offending_symbol=attr,
            )
        elif _matches_payment_primitive(attr):
            self._record_violation(
                violation_type="RULE_8_PAYMENT_PRIMITIVE",
                node_type="Attribute",
                line_number=node.lineno,
                description=f"Attribute '{attr}' matches payment keyword prohibited by Permanent Rule 8.",
                offending_symbol=attr,
            )
        elif attr in {"read_text", "read_bytes"}:
            self.capabilities.add("CAP_FILE_READ")
        elif attr in {"write_text", "write_bytes"}:
            self.capabilities.add("CAP_FILE_WRITE")
        self.generic_visit(node)

    def visit_Call(self, node: ast.Call):
        # Check direct call to open()
        if isinstance(node.func, ast.Name):
            func_name = node.func.id
            if func_name in BANNED_BUILTINS:
                self._record_violation(
                    violation_type="BANNED_BUILTIN",
                    node_type="Call",
                    line_number=node.lineno,
                    description=f"Direct invocation of '{func_name}' is forbidden.",
                    offending_symbol=func_name,
                )
            elif func_name == "open":
                # Inspect open mode if provided
                mode = "r"
                if len(node.args) >= 2 and isinstance(node.args[1], ast.Constant) and isinstance(node.args[1].value, str):
                    mode = node.args[1].value
                for kw in node.keywords:
                    if kw.arg == "mode" and isinstance(kw.value, ast.Constant) and isinstance(kw.value.value, str):
                        mode = kw.value.value
                if any(m in mode for m in ("w", "a", "x", "+")):
                    self.capabilities.add("CAP_FILE_WRITE")
                else:
                    self.capabilities.add("CAP_FILE_READ")

        elif isinstance(node.func, ast.Attribute):
            attr_name = node.func.attr
            if attr_name in BANNED_CALL_ATTRIBUTES:
                self._record_violation(
                    violation_type="RULE_7_PERMANENT_DELETE_OR_EXEC",
                    node_type="Call",
                    line_number=node.lineno,
                    description=f"Invocation of method '{attr_name}' is prohibited.",
                    offending_symbol=attr_name,
                )
            elif attr_name in {"read_text", "read_bytes"}:
                self.capabilities.add("CAP_FILE_READ")
            elif attr_name in {"write_text", "write_bytes"}:
                self.capabilities.add("CAP_FILE_WRITE")

        self.generic_visit(node)

    def visit_BinOp(self, node: ast.BinOp):
        if isinstance(node.op, (ast.Add, ast.Sub, ast.Mult, ast.Div, ast.FloorDiv, ast.Mod, ast.Pow, ast.MatMult)):
            self.capabilities.add("CAP_MATH")
        self.generic_visit(node)

    def visit_ListComp(self, node: ast.ListComp):
        self.capabilities.add("CAP_DATA_TRANSFORM")
        self.generic_visit(node)

    def visit_DictComp(self, node: ast.DictComp):
        self.capabilities.add("CAP_DATA_TRANSFORM")
        self.generic_visit(node)

    def visit_SetComp(self, node: ast.SetComp):
        self.capabilities.add("CAP_DATA_TRANSFORM")
        self.generic_visit(node)


class ASTSafetyInspector:
    """
    Deterministic AST Static Safety Inspector.
    Validates micro-tool code against Phenom Permanent Safety Rules
    and Sandboxing Invariants prior to execution or storage.
    """

    def inspect_code(self, source_code: str) -> ASTInspectionReport:
        if not source_code or not source_code.strip():
            return ASTInspectionReport(
                is_safe=False,
                violations=[
                    ASTViolation(
                        violation_type="EMPTY_SOURCE",
                        node_type="Module",
                        line_number=1,
                        description="Source code is empty.",
                        offending_symbol="",
                    )
                ],
                risk_tier=3,
                detected_capabilities=[],
                imported_modules=[],
                analyzed_functions=[],
            )

        try:
            tree = ast.parse(source_code)
        except SyntaxError as ex:
            return ASTInspectionReport(
                is_safe=False,
                violations=[
                    ASTViolation(
                        violation_type="SYNTAX_ERROR",
                        node_type="SyntaxError",
                        line_number=ex.lineno or 1,
                        description=f"Python syntax error: {ex.msg}",
                        offending_symbol=ex.text.strip() if ex.text else "syntax_error",
                    )
                ],
                risk_tier=3,
                detected_capabilities=[],
                imported_modules=[],
                analyzed_functions=[],
            )

        visitor = _ASTVisitor()
        visitor.visit(tree)

        # Default fallback capability if none detected
        capabilities = sorted(list(visitor.capabilities))
        if not capabilities:
            capabilities = ["CAP_DATA_TRANSFORM"]

        is_safe = len(visitor.violations) == 0

        # Risk tier determination
        if not is_safe:
            risk_tier = 3
        elif "CAP_FILE_WRITE" in capabilities or "CAP_FILE_READ" in capabilities:
            risk_tier = 1
        else:
            risk_tier = 0

        return ASTInspectionReport(
            is_safe=is_safe,
            violations=visitor.violations,
            risk_tier=risk_tier,
            detected_capabilities=capabilities,
            imported_modules=visitor.imported_modules,
            analyzed_functions=visitor.analyzed_functions,
        )


# Global singleton instance
ast_inspector = ASTSafetyInspector()
