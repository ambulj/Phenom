"""Patch Synthesizer for Phenom (Milestone 24 Phase 1).

Deterministically synthesizes AST repair patches from diagnostic reports, generates
unified diff previews, and manages reversible patch transactions (HEAL-01.2, SYM-02.1).
"""

from __future__ import annotations

import difflib
import logging
import re
import uuid
from pathlib import Path
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field

from services.backend.safety.guardian import guardian
from services.backend.healing.diagnostic_engine import DiagnosticReport

logger = logging.getLogger("phenom.healing.patch_synthesizer")


class Rule8ViolationError(Exception):
    """Raised when an action involves payment, checkout, or automated financial transactions."""
    pass


class HealingPatchResult(BaseModel):
    patch_id: str
    file_path: Optional[str] = None
    fault_category: str
    original_line: Optional[str] = None
    patched_line: Optional[str] = None
    unified_diff: str
    applied: bool = False
    dry_run: bool = True
    metadata: Dict[str, Any] = Field(default_factory=dict)


class PatchSynthesizer:
    """Symbolic AST patch generator and reversible transaction manager."""

    _RULE_8_PATTERN = re.compile(
        r"\b(checkout|pay|payment|purchase|buy|order|credit.?card|cvv|billing)\b",
        re.IGNORECASE,
    )

    def __init__(self) -> None:
        # Transactions: patch_id -> {file_path, original_source, patched_source, applied}
        self._transactions: Dict[str, Dict[str, Any]] = {}

    def _check_guardian(self) -> None:
        if guardian.is_halted:
            raise PermissionError("Guardian kill switch is TRIPPED. Patch synthesis operations halted immediately.")

    def _validate_rule_8(self, text: str) -> None:
        cleaned = re.sub(r"[_]+", " ", text).lower()
        if self._RULE_8_PATTERN.search(cleaned):
            raise Rule8ViolationError(
                f"Rule 8 violation: patch synthesis for checkout or payment code is strictly prohibited. Found: {text}"
            )

    def synthesize_patch(
        self,
        report: DiagnosticReport,
        source_code: str,
        dry_run: bool = True,
    ) -> HealingPatchResult:
        """Synthesize a deterministic repair patch matching the diagnostic fault category."""
        self._check_guardian()
        self._validate_rule_8(source_code)
        if report.culprit_line:
            self._validate_rule_8(report.culprit_line)

        patch_id = f"patch_{uuid.uuid4().hex[:10]}"
        lines = source_code.splitlines(keepends=True)
        patched_lines = list(lines)

        target_idx = None
        orig_line = report.culprit_line or ""

        # Locate target line index
        if report.line_number and 1 <= report.line_number <= len(lines):
            target_idx = report.line_number - 1
            orig_line = lines[target_idx].rstrip("\r\n")
        elif report.culprit_line:
            for idx, line in enumerate(lines):
                if report.culprit_line.strip() in line:
                    target_idx = idx
                    orig_line = line.rstrip("\r\n")
                    break

        patched_line = orig_line

        # Apply deterministic repair transformation based on fault category
        if report.fault_category == "MISSING_DICTIONARY_KEY" and target_idx is not None:
            # Replace d['key'] with d.get('key', None)
            dict_access = re.search(r"([a-zA-Z_]\w*)\[(['\"][^'\"]+['\"])\]", orig_line)
            if dict_access:
                d_var = dict_access.group(1)
                k_val = dict_access.group(2)
                patched_line = orig_line.replace(f"{d_var}[{k_val}]", f"{d_var}.get({k_val}, None)")
                patched_lines[target_idx] = patched_line + ("\n" if lines[target_idx].endswith("\n") else "")

        elif report.fault_category == "NULL_OR_NONE_DEREFERENCE" and target_idx is not None:
            # Replace obj.attr with (obj.attr if obj is not None else None)
            member_match = re.search(r"([a-zA-Z_]\w*)\.([a-zA-Z_]\w*)", orig_line)
            if member_match:
                obj_var = member_match.group(1)
                attr_var = member_match.group(2)
                # Avoid self / cls replacements
                if obj_var not in ("self", "cls", "logger", "os", "sys"):
                    safe_replacement = f"({obj_var}.{attr_var} if {obj_var} is not None else None)"
                    patched_line = orig_line.replace(f"{obj_var}.{attr_var}", safe_replacement)
                    patched_lines[target_idx] = patched_line + ("\n" if lines[target_idx].endswith("\n") else "")

        elif report.fault_category == "DIVISION_BY_ZERO" and target_idx is not None:
            # Replace a / b with (a / b if b != 0 else 0)
            div_match = re.search(r"(\S+)\s*/\s*([a-zA-Z_]\w*)", orig_line)
            if div_match:
                numerator = div_match.group(1)
                denominator = div_match.group(2)
                safe_div = f"({numerator} / {denominator} if {denominator} != 0 else 0)"
                patched_line = orig_line.replace(f"{numerator} / {denominator}", safe_div)
                patched_lines[target_idx] = patched_line + ("\n" if lines[target_idx].endswith("\n") else "")

        elif report.fault_category == "MISSING_IMPORT":
            # Extract missing module from error message
            mod_match = re.search(r"No module named ['\"]([^'\"]+)['\"]", report.error_message)
            missing_mod = mod_match.group(1) if mod_match else "math"
            import_stmt = f"import {missing_mod}\n"
            patched_lines.insert(0, import_stmt)
            patched_line = import_stmt.strip()

        else:
            # Generic fallback: Wrap culprit line in try-except block
            if target_idx is not None:
                indent = re.match(r"^\s*", orig_line).group(0)
                wrapped = (
                    f"{indent}try:\n"
                    f"{indent}    {orig_line.strip()}\n"
                    f"{indent}except Exception as _heal_err:\n"
                    f"{indent}    pass  # Handled by Phenom Self-Healing Kernel\n"
                )
                patched_lines[target_idx] = wrapped
                patched_line = wrapped.strip()

        patched_source = "".join(patched_lines)

        # Generate standard unified diff
        diff_iter = difflib.unified_diff(
            lines,
            patched_lines,
            fromfile=report.file_path or "source_original.py",
            tofile=report.file_path or "source_patched.py",
            lineterm="",
        )
        diff_text = "\n".join(diff_iter)

        result = HealingPatchResult(
            patch_id=patch_id,
            file_path=report.file_path,
            fault_category=report.fault_category,
            original_line=orig_line,
            patched_line=patched_line,
            unified_diff=diff_text,
            applied=not dry_run,
            dry_run=dry_run,
        )

        # Record transaction snapshot for Rule 7 reversibility
        self._transactions[patch_id] = {
            "patch_id": patch_id,
            "file_path": report.file_path,
            "original_source": source_code,
            "patched_source": patched_source,
            "applied": not dry_run,
        }

        return result

    def apply_patch(self, patch_id: str) -> Dict[str, Any]:
        """Apply a synthesized patch to its target file or mark transaction applied."""
        self._check_guardian()
        if patch_id not in self._transactions:
            raise KeyError(f"Patch transaction '{patch_id}' not found.")

        tx = self._transactions[patch_id]
        file_path = tx.get("file_path")
        patched_source = tx.get("patched_source")

        if file_path and Path(file_path).exists():
            with open(file_path, "w", encoding="utf-8") as f:
                f.write(patched_source)

        tx["applied"] = True
        return {
            "patch_id": patch_id,
            "status": "applied",
            "file_path": file_path,
            "message": f"Patch '{patch_id}' successfully applied with transaction snapshot.",
        }

    def rollback_patch(self, patch_id: str) -> Dict[str, Any]:
        """Roll back an applied patch to its original pre-mutation state (Rule 7)."""
        self._check_guardian()
        if patch_id not in self._transactions:
            raise KeyError(f"Patch transaction '{patch_id}' not found.")

        tx = self._transactions[patch_id]
        file_path = tx.get("file_path")
        orig_source = tx.get("original_source")

        if file_path and Path(file_path).exists():
            with open(file_path, "w", encoding="utf-8") as f:
                f.write(orig_source)

        tx["applied"] = False
        return {
            "patch_id": patch_id,
            "status": "rolled_back",
            "file_path": file_path,
            "message": f"Patch '{patch_id}' successfully rolled back to pre-mutation snapshot.",
        }

    def get_transaction(self, patch_id: str) -> Optional[Dict[str, Any]]:
        return self._transactions.get(patch_id)


# Singleton instance
patch_synthesizer = PatchSynthesizer()
