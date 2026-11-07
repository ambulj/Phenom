"""
AST Code Intelligence & Symbol Parser (DEV-01.1).
Extracts structured symbol definitions, type signatures, docstrings, and call dependencies
for Python, TypeScript, and JavaScript source files.
"""

import ast
import os
import re
from enum import Enum
from dataclasses import dataclass, field, asdict
from typing import List, Dict, Optional, Any, Set


class SymbolKind(str, Enum):
    FUNCTION = "function"
    ASYNC_FUNCTION = "async_function"
    CLASS = "class"
    METHOD = "method"
    INTERFACE = "interface"
    TYPE_ALIAS = "type"
    VARIABLE = "variable"


@dataclass
class SymbolDefinition:
    name: str
    kind: str
    file_path: str
    line_number: int
    end_line_number: int
    column: int
    signature: str
    docstring: Optional[str] = None
    parent: Optional[str] = None
    decorators: List[str] = field(default_factory=list)
    calls: List[str] = field(default_factory=list)
    exported: bool = True

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class PythonSymbolVisitor(ast.NodeVisitor):
    """AST visitor traversing Python code to extract top-level and class-scoped symbols."""

    def __init__(self, file_path: str, code_lines: List[str]):
        self.file_path = file_path
        self.code_lines = code_lines
        self.symbols: List[SymbolDefinition] = []
        self._current_class: Optional[str] = None

    def visit_ClassDef(self, node: ast.ClassDef):
        docstring = ast.get_docstring(node)
        bases = [ast.unparse(b) for b in node.bases]
        sig = f"class {node.name}({', '.join(bases)})" if bases else f"class {node.name}"
        decs = [ast.unparse(d) for d in node.decorator_list]

        # Extract calls inside class body
        calls: Set[str] = set()
        for child in ast.walk(node):
            if isinstance(child, ast.Call):
                if isinstance(child.func, ast.Name):
                    calls.add(child.func.id)
                elif isinstance(child.func, ast.Attribute):
                    calls.add(child.func.attr)

        symbol = SymbolDefinition(
            name=node.name,
            kind=SymbolKind.CLASS.value,
            file_path=self.file_path,
            line_number=node.lineno,
            end_line_number=getattr(node, 'end_lineno', node.lineno),
            column=node.col_offset,
            signature=sig,
            docstring=docstring,
            parent=None,
            decorators=decs,
            calls=sorted(list(calls)),
            exported=not node.name.startswith("_")
        )
        self.symbols.append(symbol)

        prev_class = self._current_class
        self._current_class = node.name
        self.generic_visit(node)
        self._current_class = prev_class

    def visit_FunctionDef(self, node: ast.FunctionDef):
        self._handle_function(node, is_async=False)

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef):
        self._handle_function(node, is_async=True)

    def _handle_function(self, node: ast.AST, is_async: bool):
        name = getattr(node, 'name', '')
        docstring = ast.get_docstring(node)
        decs = [ast.unparse(d) for d in getattr(node, 'decorator_list', [])]

        # Format signature from arguments and returns
        args_str = ast.unparse(getattr(node, 'args')) if hasattr(node, 'args') else ""
        returns_str = f" -> {ast.unparse(node.returns)}" if getattr(node, 'returns', None) else ""
        prefix = "async def " if is_async else "def "
        sig = f"{prefix}{name}({args_str}){returns_str}"

        # Extract call targets inside this function
        calls: Set[str] = set()
        for child in ast.walk(node):
            if isinstance(child, ast.Call):
                if isinstance(child.func, ast.Name):
                    calls.add(child.func.id)
                elif isinstance(child.func, ast.Attribute):
                    calls.add(child.func.attr)

        kind = SymbolKind.METHOD.value if self._current_class else (
            SymbolKind.ASYNC_FUNCTION.value if is_async else SymbolKind.FUNCTION.value
        )

        symbol = SymbolDefinition(
            name=name,
            kind=kind,
            file_path=self.file_path,
            line_number=getattr(node, 'lineno', 1),
            end_line_number=getattr(node, 'end_lineno', getattr(node, 'lineno', 1)),
            column=getattr(node, 'col_offset', 0),
            signature=sig,
            docstring=docstring,
            parent=self._current_class,
            decorators=decs,
            calls=sorted(list(calls)),
            exported=not name.startswith("_")
        )
        self.symbols.append(symbol)
        # We do not recurse into nested functions to keep clean symbol hierarchy
        # but if needed generic_visit can be called


class AstCodeParser:
    """Multi-language AST and semantic symbol parser."""

    TS_INTERFACE_REGEX = re.compile(r'(?:export\s+)?interface\s+([A-Za-z0-9_$]+)(?:\s+extends\s+[^{]+)?\s*\{')
    TS_TYPE_REGEX = re.compile(r'(?:export\s+)?type\s+([A-Za-z0-9_$]+)(?:<[^>]+>)?\s*=\s*')
    TS_CLASS_REGEX = re.compile(r'(?:export\s+)?class\s+([A-Za-z0-9_$]+)(?:\s+extends\s+[^{]+)?(?:\s+implements\s+[^{]+)?\s*\{')
    TS_FUNC_REGEX = re.compile(r'(?:export\s+)?(?:async\s+)?function\s+([A-Za-z0-9_$]+)\s*\(([^)]*)\)(?:\s*:\s*([^;{]+))?\s*\{')
    TS_ARROW_REGEX = re.compile(r'(?:export\s+)?const\s+([A-Za-z0-9_$]+)\s*=\s*(?:async\s*)?\(([^)]*)\)(?:\s*:\s*([^=>]+))?\s*=>')

    def parse_python(self, code: str, file_path: str = "") -> List[SymbolDefinition]:
        """Parses Python source code and extracts symbol definitions."""
        try:
            tree = ast.parse(code, filename=file_path or "<string>")
            code_lines = code.splitlines()
            visitor = PythonSymbolVisitor(file_path=file_path, code_lines=code_lines)
            visitor.visit(tree)
            return visitor.symbols
        except SyntaxError:
            # Fallback to regex if syntax error (e.g. partial edits)
            return self._regex_fallback_python(code, file_path)

    def _regex_fallback_python(self, code: str, file_path: str) -> List[SymbolDefinition]:
        symbols: List[SymbolDefinition] = []
        lines = code.splitlines()
        for idx, line in enumerate(lines, start=1):
            sline = line.strip()
            if sline.startswith("def ") or sline.startswith("async def "):
                is_async = sline.startswith("async def ")
                name_match = re.search(r'def\s+([A-Za-z0-9_]+)\s*\(', sline)
                if name_match:
                    name = name_match.group(1)
                    symbols.append(SymbolDefinition(
                        name=name,
                        kind=SymbolKind.ASYNC_FUNCTION.value if is_async else SymbolKind.FUNCTION.value,
                        file_path=file_path,
                        line_number=idx,
                        end_line_number=idx,
                        column=len(line) - len(line.lstrip()),
                        signature=sline.split(":")[0].strip(),
                        docstring=None,
                        exported=not name.startswith("_")
                    ))
            elif sline.startswith("class "):
                name_match = re.search(r'class\s+([A-Za-z0-9_]+)', sline)
                if name_match:
                    name = name_match.group(1)
                    symbols.append(SymbolDefinition(
                        name=name,
                        kind=SymbolKind.CLASS.value,
                        file_path=file_path,
                        line_number=idx,
                        end_line_number=idx,
                        column=len(line) - len(line.lstrip()),
                        signature=sline.split(":")[0].strip(),
                        docstring=None,
                        exported=not name.startswith("_")
                    ))
        return symbols

    def parse_typescript(self, code: str, file_path: str = "") -> List[SymbolDefinition]:
        """Parses TypeScript/JavaScript source code and extracts exported and top-level symbols."""
        symbols: List[SymbolDefinition] = []
        lines = code.splitlines()

        for idx, line in enumerate(lines, start=1):
            raw = line.strip()
            if not raw or raw.startswith("//") or raw.startswith("/*") or raw.startswith("*"):
                continue

            exported = "export " in raw

            # 1. Interface
            if m := self.TS_INTERFACE_REGEX.search(raw):
                name = m.group(1)
                symbols.append(SymbolDefinition(
                    name=name,
                    kind=SymbolKind.INTERFACE.value,
                    file_path=file_path,
                    line_number=idx,
                    end_line_number=idx,
                    column=len(line) - len(line.lstrip()),
                    signature=f"interface {name}",
                    docstring=None,
                    exported=exported
                ))
                continue

            # 2. Type Alias
            if m := self.TS_TYPE_REGEX.search(raw):
                name = m.group(1)
                symbols.append(SymbolDefinition(
                    name=name,
                    kind=SymbolKind.TYPE_ALIAS.value,
                    file_path=file_path,
                    line_number=idx,
                    end_line_number=idx,
                    column=len(line) - len(line.lstrip()),
                    signature=raw.split("=")[0].strip(),
                    docstring=None,
                    exported=exported
                ))
                continue

            # 3. Class
            if m := self.TS_CLASS_REGEX.search(raw):
                name = m.group(1)
                symbols.append(SymbolDefinition(
                    name=name,
                    kind=SymbolKind.CLASS.value,
                    file_path=file_path,
                    line_number=idx,
                    end_line_number=idx,
                    column=len(line) - len(line.lstrip()),
                    signature=raw.split("{")[0].strip(),
                    docstring=None,
                    exported=exported
                ))
                continue

            # 4. Standard Function
            if m := self.TS_FUNC_REGEX.search(raw):
                name = m.group(1)
                args = m.group(2)
                ret = f": {m.group(3).strip()}" if m.group(3) else ""
                is_async = "async " in raw
                symbols.append(SymbolDefinition(
                    name=name,
                    kind=SymbolKind.ASYNC_FUNCTION.value if is_async else SymbolKind.FUNCTION.value,
                    file_path=file_path,
                    line_number=idx,
                    end_line_number=idx,
                    column=len(line) - len(line.lstrip()),
                    signature=f"{'async ' if is_async else ''}function {name}({args}){ret}",
                    docstring=None,
                    exported=exported
                ))
                continue

            # 5. Arrow Function / Const Function
            if m := self.TS_ARROW_REGEX.search(raw):
                name = m.group(1)
                args = m.group(2)
                ret = f": {m.group(3).strip()}" if m.group(3) else ""
                symbols.append(SymbolDefinition(
                    name=name,
                    kind=SymbolKind.FUNCTION.value,
                    file_path=file_path,
                    line_number=idx,
                    end_line_number=idx,
                    column=len(line) - len(line.lstrip()),
                    signature=f"const {name} = ({args}){ret} =>",
                    docstring=None,
                    exported=exported
                ))
                continue

        return symbols

    def parse_file(self, file_path: str) -> List[SymbolDefinition]:
        """Reads and parses code file by extension."""
        if not os.path.exists(file_path):
            return []

        ext = os.path.splitext(file_path)[1].lower()
        try:
            with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                code = f.read()
        except Exception:
            return []

        if ext == ".py":
            return self.parse_python(code, file_path)
        elif ext in (".ts", ".tsx", ".js", ".jsx"):
            return self.parse_typescript(code, file_path)
        return []


ast_parser = AstCodeParser()
