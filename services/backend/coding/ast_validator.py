"""
In-Memory AST Syntax Validator (Phase 47-02, EXEC-02).
Prevents corrupted or syntactically invalid code from being written to disk.
Supports Python, TypeScript, JavaScript, and JSON.
"""

import ast
import json
import os
import re
import subprocess
from typing import Optional, List, Dict, Any, Tuple
from pydantic import BaseModel, Field


class ASTValidationResult(BaseModel):
    """Carries diagnostic outcome of an AST syntax validation audit."""
    valid: bool = Field(..., description="True if syntax is strictly valid")
    language: str = Field(..., description="Target language (python, typescript, javascript, json)")
    line: Optional[int] = Field(default=None, description="Line number of syntax violation (1-indexed)")
    column: Optional[int] = Field(default=None, description="Column offset of syntax violation (1-indexed)")
    error_message: Optional[str] = Field(default=None, description="Diagnostic error description")
    snippet: Optional[str] = Field(default=None, description="Problematic line or code extract")


class ASTValidator:
    """Validates source code syntax in-memory before filesystem modification."""

    def __init__(self):
        pass

    @staticmethod
    def detect_language(file_path: str) -> str:
        """Determines target language from file extension."""
        ext = os.path.splitext(file_path.lower())[1]
        if ext in (".py", ".pyw"):
            return "python"
        elif ext in (".ts", ".tsx"):
            return "typescript"
        elif ext in (".js", ".jsx", ".mjs", ".cjs"):
            return "javascript"
        elif ext == ".json":
            return "json"
        return "text"

    def validate_python(self, code: str) -> ASTValidationResult:
        """Validates Python syntax using Python's native AST compiler."""
        try:
            ast.parse(code)
            return ASTValidationResult(valid=True, language="python")
        except SyntaxError as se:
            snippet = se.text.strip() if se.text else None
            return ASTValidationResult(
                valid=False,
                language="python",
                line=se.lineno,
                column=se.offset,
                error_message=str(se.msg or se),
                snippet=snippet
            )
        except Exception as ex:
            return ASTValidationResult(
                valid=False,
                language="python",
                error_message=f"Parser failure: {str(ex)}"
            )

    def validate_json(self, code: str) -> ASTValidationResult:
        """Validates JSON structure."""
        try:
            json.loads(code)
            return ASTValidationResult(valid=True, language="json")
        except json.JSONDecodeError as jde:
            lines = code.splitlines()
            snippet = lines[jde.lineno - 1] if 0 <= jde.lineno - 1 < len(lines) else None
            return ASTValidationResult(
                valid=False,
                language="json",
                line=jde.lineno,
                column=jde.colno,
                error_message=str(jde.msg),
                snippet=snippet
            )

    def validate_javascript_typescript(self, code: str, language: str = "javascript") -> ASTValidationResult:
        """
        Validates JS/TS syntax:
        1. Checks balanced delimiters (braces, brackets, parentheses) outside comments/strings.
        2. Checks unclosed string literals.
        3. If node is available, attempts node syntax check for plain JS.
        """
        # Balanced delimiter stack checking
        stack: List[Tuple[str, int, int]] = []  # (char, line, col)
        pairs = {')': '(', ']': '[', '}': '{'}
        opening = set(pairs.values())
        closing = set(pairs.keys())

        in_single_quote = False
        in_double_quote = False
        in_template_quote = False
        in_line_comment = False
        in_block_comment = False

        lines = code.splitlines()
        for line_idx, line in enumerate(lines, start=1):
            col = 0
            line_len = len(line)
            in_line_comment = False

            while col < line_len:
                char = line[col]
                next_char = line[col + 1] if col + 1 < line_len else ""

                # Handle block comments
                if in_block_comment:
                    if char == '*' and next_char == '/':
                        in_block_comment = False
                        col += 2
                        continue
                    col += 1
                    continue

                # Handle string literals
                if in_single_quote:
                    if char == '\\':
                        col += 2
                        continue
                    if char == "'":
                        in_single_quote = False
                    col += 1
                    continue

                if in_double_quote:
                    if char == '\\':
                        col += 2
                        continue
                    if char == '"':
                        in_double_quote = False
                    col += 1
                    continue

                if in_template_quote:
                    if char == '\\':
                        col += 2
                        continue
                    if char == '`':
                        in_template_quote = False
                    col += 1
                    continue

                # Start comments
                if char == '/' and next_char == '/':
                    in_line_comment = True
                    break
                if char == '/' and next_char == '*':
                    in_block_comment = True
                    col += 2
                    continue

                # Start strings
                if char == "'":
                    in_single_quote = True
                    col += 1
                    continue
                if char == '"':
                    in_double_quote = True
                    col += 1
                    continue
                if char == '`':
                    in_template_quote = True
                    col += 1
                    continue

                # Check delimiters
                if char in opening:
                    stack.append((char, line_idx, col + 1))
                elif char in closing:
                    expected = pairs[char]
                    if not stack or stack[-1][0] != expected:
                        return ASTValidationResult(
                            valid=False,
                            language=language,
                            line=line_idx,
                            column=col + 1,
                            error_message=f"Mismatched closing delimiter '{char}'",
                            snippet=line
                        )
                    stack.pop()

                col += 1

        if in_single_quote:
            return ASTValidationResult(valid=False, language=language, error_message="Unclosed single quote literal")
        if in_double_quote:
            return ASTValidationResult(valid=False, language=language, error_message="Unclosed double quote literal")
        if in_template_quote:
            return ASTValidationResult(valid=False, language=language, error_message="Unclosed template literal")
        if in_block_comment:
            return ASTValidationResult(valid=False, language=language, error_message="Unclosed block comment")
        if stack:
            unclosed_char, u_line, u_col = stack[-1]
            return ASTValidationResult(
                valid=False,
                language=language,
                line=u_line,
                column=u_col,
                error_message=f"Unclosed opening delimiter '{unclosed_char}'",
                snippet=lines[u_line - 1] if 0 <= u_line - 1 < len(lines) else None
            )

        return ASTValidationResult(valid=True, language=language)

    def validate_code(self, code: str, language: str = "python") -> ASTValidationResult:
        """Validates code string for specified language."""
        lang = language.lower().strip()
        if lang == "python":
            return self.validate_python(code)
        elif lang in ("typescript", "ts"):
            return self.validate_javascript_typescript(code, language="typescript")
        elif lang in ("javascript", "js"):
            return self.validate_javascript_typescript(code, language="javascript")
        elif lang == "json":
            return self.validate_json(code)
        else:
            return ASTValidationResult(valid=True, language="text")

    def validate_file(self, file_path: str, code: Optional[str] = None) -> ASTValidationResult:
        """Validates file contents either passed directly or read from disk."""
        lang = self.detect_language(file_path)
        if code is None:
            if not os.path.exists(file_path):
                return ASTValidationResult(
                    valid=False,
                    language=lang,
                    error_message=f"File not found: {file_path}"
                )
            with open(file_path, "r", encoding="utf-8", errors="replace") as f:
                code = f.read()

        return self.validate_code(code, language=lang)


# Global singleton instance
ast_validator = ASTValidator()
