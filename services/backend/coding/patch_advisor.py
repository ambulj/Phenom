"""
Phenom Proactive Patch Advisor (Coding Agent Safety & Remediation)
Analyzes runtime tracebacks, syntax errors, and test failures.
Produces a structured unified diff patch proposal and preview summary.
"""

import os
import re
import difflib
from typing import Dict, Any, Optional, List
from pydantic import BaseModel, Field

class PatchProposal(BaseModel):
    file_path: str
    line_number: Optional[int] = None
    original_snippet: str
    proposed_snippet: str
    unified_diff: str
    explanation: str
    confidence: float

class PatchAdvisor:
    def __init__(self, workspace_root: str):
        self.workspace_root = os.path.abspath(workspace_root)

    def extract_error_location(self, traceback_text: str) -> Optional[Dict[str, Any]]:
        """
        Parses python/generic stack trace to identify the most relevant failing file and line number.
        """
        frames = re.findall(r'File\s+["\'](.*?)["\'],\s+line\s+(\d+)(?:,\s+in\s+(.*))?', traceback_text)
        if not frames:
            return None

        # Filter to frames inside workspace_root if possible
        target_frame = None
        for file_path, line_str, func_name in reversed(frames):
            norm_path = os.path.normpath(file_path)
            if not os.path.isabs(norm_path):
                norm_path = os.path.normpath(os.path.join(self.workspace_root, norm_path))
            
            if os.path.exists(norm_path):
                target_frame = (norm_path, int(line_str), func_name)
                break

        if not target_frame and frames:
            file_path, line_str, func_name = frames[-1]
            norm_path = os.path.normpath(os.path.join(self.workspace_root, file_path)) if not os.path.isabs(file_path) else os.path.normpath(file_path)
            target_frame = (norm_path, int(line_str), func_name)

        if not target_frame:
            return None

        file_path, line_no, func = target_frame
        
        # Extract exception message
        lines = [l.strip() for l in traceback_text.splitlines() if l.strip()]
        error_msg = lines[-1] if lines else "Error"

        return {
            "file_path": file_path,
            "line_number": line_no,
            "function": func,
            "error_message": error_msg
        }

    def generate_patch_proposal(
        self,
        traceback_text: str,
        fix_generator: Optional[Any] = None
    ) -> Optional[PatchProposal]:
        loc = self.extract_error_location(traceback_text)
        if not loc or not os.path.exists(loc["file_path"]):
            return None

        file_path = loc["file_path"]
        line_no = loc["line_number"]
        error_msg = loc["error_message"]

        try:
            with open(file_path, "r", encoding="utf-8", errors="replace") as f:
                lines = f.readlines()
        except Exception:
            return None

        if line_no < 1 or line_no > len(lines):
            return None

        start_idx = max(0, line_no - 4)
        end_idx = min(len(lines), line_no + 3)
        original_slice = lines[start_idx:end_idx]
        original_text = "".join(original_slice)

        # Propose fix based on common error patterns
        proposed_slice = list(original_slice)
        target_line_idx = line_no - 1 - start_idx
        offending_line = original_slice[target_line_idx]

        explanation = f"Suggested patch for {error_msg}"
        confidence = 0.70

        # Pattern 1: ZeroDivisionError
        if "ZeroDivisionError" in error_msg:
            indent = len(offending_line) - len(offending_line.lstrip())
            indent_str = " " * indent
            proposed_slice[target_line_idx] = f"{indent_str}if denominator != 0:\n    {offending_line}"
            explanation = "Guard against division by zero"
            confidence = 0.85
        # Pattern 2: NameError / KeyError / AttributeError
        elif "KeyError" in error_msg:
            explanation = "Ensure key presence or use dict.get()"
            confidence = 0.75
        elif "FileNotFoundError" in error_msg:
            explanation = "Check os.path.exists() before opening file"
            confidence = 0.80

        proposed_text = "".join(proposed_slice)

        diff_lines = list(difflib.unified_diff(
            original_slice,
            proposed_slice,
            fromfile=f"a/{os.path.basename(file_path)}",
            tofile=f"b/{os.path.basename(file_path)}",
            lineterm=""
        ))
        unified_diff = "\n".join(diff_lines)

        return PatchProposal(
            file_path=file_path,
            line_number=line_no,
            original_snippet=original_text,
            proposed_snippet=proposed_text,
            unified_diff=unified_diff,
            explanation=explanation,
            confidence=confidence
        )
