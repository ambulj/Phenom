"""
Multi-File Atomic Code Refactoring Engine (DEV-01.3).
Generates unified diffs for human preview before applying multi-file symbol renames
or code replacements with atomic rollback guarantees.
"""

import os
import re
import difflib
from typing import Dict, List, Optional, Any
from services.backend.safety.guardian import guardian
from services.backend.safety.action_log import action_log
from services.backend.coding.workspace_indexer import workspace_indexer


class RefactorEngine:
    """Safe multi-file code transformation and atomic refactoring engine."""

    def generate_diff(self, file_path: str, old_text: str, new_text: str) -> str:
        """Generates a standard unified diff between old and new text."""
        old_lines = old_text.splitlines(keepends=True)
        new_lines = new_text.splitlines(keepends=True)
        diff = difflib.unified_diff(
            old_lines,
            new_lines,
            fromfile=f"a/{file_path}",
            tofile=f"b/{file_path}",
            lineterm=""
        )
        return "".join(diff)

    def preview_symbol_rename(
        self,
        old_symbol: str,
        new_symbol: str,
        target_files: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        Scans workspace or specified files to generate unified diff previews
        for renaming an identifier (function, class, variable).
        Strictly read-only; zero disk writes.
        """
        if guardian.is_halted:
            raise PermissionError("Guardian kill switch is active. Refactor preview aborted.")

        if not old_symbol or not new_symbol:
            raise ValueError("old_symbol and new_symbol must be non-empty strings.")

        pattern = re.compile(rf"\b{re.escape(old_symbol)}\b")
        diffs: Dict[str, str] = {}
        affected_files: List[str] = []
        total_occurrences = 0

        # Determine files to inspect
        if target_files:
            candidate_files = target_files
        else:
            # Query workspace indexer for files declaring or referencing old_symbol
            sym_defs = workspace_indexer.lookup_symbol(old_symbol)
            candidate_files = list(set([s["file_path"] for s in sym_defs]))
            # Also check files indexed by workspace indexer
            for fp in list(workspace_indexer._symbols_by_file.keys()):
                if fp not in candidate_files:
                    candidate_files.append(fp)

        for fp in candidate_files:
            if not os.path.exists(fp) or not os.path.isfile(fp):
                continue

            try:
                with open(fp, "r", encoding="utf-8", errors="ignore") as f:
                    content = f.read()
            except Exception:
                continue

            matches = list(pattern.finditer(content))
            if not matches:
                continue

            total_occurrences += len(matches)
            new_content = pattern.sub(new_symbol, content)
            diff_str = self.generate_diff(fp, content, new_content)

            diffs[fp] = diff_str
            affected_files.append(fp)

        summary = f"Rename '{old_symbol}' -> '{new_symbol}' across {len(affected_files)} files ({total_occurrences} occurrences)."

        return {
            "status": "preview",
            "old_symbol": old_symbol,
            "new_symbol": new_symbol,
            "affected_files": affected_files,
            "total_occurrences": total_occurrences,
            "diffs": diffs,
            "summary": summary
        }

    def apply_refactor(
        self,
        file_updates: Dict[str, str]
    ) -> Dict[str, Any]:
        """
        Applies changes to multiple files atomically with in-memory backups.
        If any write fails, automatically rolls back all previously modified files.
        """
        if guardian.is_halted:
            raise PermissionError("Guardian kill switch is active. Refactor application aborted.")

        if not file_updates:
            return {"status": "no_changes", "applied_files": []}

        backups: Dict[str, str] = {}
        written_files: List[str] = []

        try:
            # 1. Read existing content for rollback backups
            for fp in file_updates.keys():
                if os.path.exists(fp):
                    with open(fp, "r", encoding="utf-8", errors="ignore") as f:
                        backups[fp] = f.read()
                else:
                    backups[fp] = ""

            # 2. Apply writes
            for fp, new_content in file_updates.items():
                if guardian.is_halted:
                    raise PermissionError("Guardian kill switch triggered mid-refactor. Rolling back.")

                os.makedirs(os.path.dirname(os.path.abspath(fp)), exist_ok=True)
                with open(fp, "w", encoding="utf-8") as f:
                    f.write(new_content)
                written_files.append(fp)

            # 3. Log to action log
            action_log.log_action(
                tool="apply_code_refactor",
                tier=1,
                args={"files_modified": written_files},
                decision="approved",
                result_status="COMMITTED",
                source="desktop"
            )

            # 4. Trigger incremental re-index
            for fp in written_files:
                cur_hash = workspace_indexer._compute_hash(fp)
                workspace_indexer._file_hashes[fp] = cur_hash
                from services.backend.coding.ast_parser import ast_parser
                workspace_indexer._symbols_by_file[fp] = ast_parser.parse_file(fp)

            return {
                "status": "applied",
                "modified_files": written_files,
                "count": len(written_files)
            }

        except Exception as e:
            # Atomic Rollback
            for fp, original in backups.items():
                try:
                    if original:
                        with open(fp, "w", encoding="utf-8") as f:
                            f.write(original)
                    elif os.path.exists(fp) and fp in written_files:
                        os.remove(fp)
                except Exception:
                    pass

            action_log.log_action(
                tool="apply_code_refactor",
                tier=1,
                args={"files_attempted": list(file_updates.keys()), "error": str(e)},
                decision="auto",
                result_status="ROLLED_BACK",
                source="desktop"
            )
            raise RuntimeError(f"Atomic refactor failed and rolled back: {e}")


refactor_engine = RefactorEngine()
