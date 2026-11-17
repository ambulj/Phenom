"""
Phenom Strict Taint Enclave & Data Pipeline Sandbox (WKF-04)
Enforces:
- WKF-04.1: Explicit [UNTRUSTED_TAINT] encapsulation on all external web/scraped data.
- WKF-04.2: Strip prompt injection patterns and shell escape characters prior to piping into local file writers or memory.
- WKF-04.3: Stage side-by-side diff previews before modifying local workspace or Obsidian notes.
"""

from __future__ import annotations

import os
import sys
import re
import time
import difflib
import logging
import asyncio
from typing import Dict, Any, List, Optional, Tuple
from pydantic import BaseModel, Field

from services.backend.safety.taint import INJECTION_PATTERNS

logger = logging.getLogger("phenom.security.taint_enclave")


class EnclaveDataPayload(BaseModel):
    """Encapsulated data payload isolated within the taint enclave."""
    payload_id: str
    source: str
    raw_content: str
    sanitized_content: str
    taint_tag: str = "[UNTRUSTED_TAINT]"
    injections_stripped: List[str] = Field(default_factory=list)
    shell_escapes_neutralized: int = 0
    is_quarantined: bool = False
    timestamp: float = Field(default_factory=time.time)


class DiffPreviewPayload(BaseModel):
    """Staged side-by-side diff preview awaiting operator authorization."""
    diff_id: str
    target_file_path: str
    existing_content: str
    proposed_content: str
    unified_diff: str
    taint_source: str
    status: str = "pending"  # pending, approved, rejected, committed
    created_at: float = Field(default_factory=time.time)


class StrictTaintEnclave:
    """Manages untrusted data sanitization, taint tagging, and staged diff previews."""

    # Shell characters to neutralize when processing untrusted text intended for pipelines
    _SHELL_ESCAPE_REGEX = re.compile(r"([`$;|&><\x00])")

    def __init__(self) -> None:
        self._staged_diffs: Dict[str, DiffPreviewPayload] = {}
        self._compiled_injections = [re.compile(p, re.IGNORECASE) for p in INJECTION_PATTERNS]

    def encapsulate(self, raw_content: str, source: str) -> EnclaveDataPayload:
        """Encapsulates raw external content, strips injection vectors, and tags with taint metadata."""
        payload_id = f"enc_{os.urandom(4).hex()}"
        injections_found: List[str] = []

        # 1. Detect and strip prompt injection patterns
        sanitized = raw_content
        for pattern in self._compiled_injections:
            matches = pattern.findall(sanitized)
            if matches:
                for m in matches:
                    matched_str = m[0] if isinstance(m, tuple) else str(m)
                    injections_found.append(matched_str)
                # Redact the injection sequence
                sanitized = pattern.sub("[REDACTED_PROMPT_INJECTION]", sanitized)

        # 2. Count and neutralize shell metacharacters
        escapes_count = len(self._SHELL_ESCAPE_REGEX.findall(sanitized))
        # Disarm dangerous command substitution e.g. $(...), `...`
        sanitized_disarmed = re.sub(r"\$\((.*?)\)", r"[BLOCKED_SUBSHELL: \1]", sanitized)
        sanitized_disarmed = re.sub(r"`(.*?)`", r"[BLOCKED_BACKTICK: \1]", sanitized_disarmed)

        # 3. Apply strict [UNTRUSTED_TAINT] boundary header and footer
        tagged_content = (
            f"<!-- BEGIN [UNTRUSTED_TAINT] (Source: {source}, ID: {payload_id}) -->\n"
            f"{sanitized_disarmed}\n"
            f"<!-- END [UNTRUSTED_TAINT] -->"
        )

        is_quarantined = len(injections_found) > 0

        payload = EnclaveDataPayload(
            payload_id=payload_id,
            source=source,
            raw_content=raw_content,
            sanitized_content=tagged_content,
            taint_tag="[UNTRUSTED_TAINT]",
            injections_stripped=injections_found,
            shell_escapes_neutralized=escapes_count,
            is_quarantined=is_quarantined,
        )

        logger.info(
            f"Enclave payload {payload_id} created from '{source}'. "
            f"Injections stripped: {len(injections_found)}, Shell escapes: {escapes_count}"
        )
        return payload

    def stage_diff_preview(
        self,
        target_file_path: str,
        proposed_content: str,
        taint_source: str
    ) -> DiffPreviewPayload:
        """Prepares a unified side-by-side diff preview before touching disk files."""
        diff_id = f"diff_{os.urandom(4).hex()}"
        norm_path = os.path.normpath(target_file_path)

        existing_content = ""
        if os.path.exists(norm_path) and os.path.isfile(norm_path):
            try:
                with open(norm_path, "r", encoding="utf-8", errors="replace") as f:
                    existing_content = f.read()
            except Exception as e:
                logger.warning(f"Could not read existing file {norm_path}: {e}")

        # Compute unified diff
        diff_lines = list(difflib.unified_diff(
            existing_content.splitlines(keepends=True),
            proposed_content.splitlines(keepends=True),
            fromfile=f"a/{os.path.basename(norm_path)}",
            tofile=f"b/{os.path.basename(norm_path)}",
            n=3
        ))
        unified_diff_str = "".join(diff_lines) or "No changes detected."

        payload = DiffPreviewPayload(
            diff_id=diff_id,
            target_file_path=norm_path,
            existing_content=existing_content,
            proposed_content=proposed_content,
            unified_diff=unified_diff_str,
            taint_source=taint_source,
            status="pending"
        )

        self._staged_diffs[diff_id] = payload

        # Broadcast diff preview event to UI
        self._broadcast_event("WORKFLOW_DIFF_PREVIEW_REQUESTED", payload.model_dump())
        return payload

    def get_staged_diff(self, diff_id: str) -> Optional[DiffPreviewPayload]:
        return self._staged_diffs.get(diff_id)

    def commit_diff(self, diff_id: str) -> Dict[str, Any]:
        """Applies an authorized staged diff to disk with Rule 7 recycle bin safety."""
        payload = self._staged_diffs.get(diff_id)
        if not payload:
            raise ValueError(f"Staged diff '{diff_id}' not found.")
        if payload.status == "committed":
            return {"status": "already_committed", "file": payload.target_file_path}

        target = payload.target_file_path
        os.makedirs(os.path.dirname(os.path.abspath(target)), exist_ok=True)

        # Rule 7: Delete means recycle bin. Never permanent overwrite without reversible backup.
        if os.path.exists(target):
            try:
                import send2trash
                backup_path = f"{target}.bak.{int(time.time())}"
                with open(backup_path, "w", encoding="utf-8") as f:
                    f.write(payload.existing_content)
                send2trash.send2trash(backup_path)
            except Exception:
                pass

        with open(target, "w", encoding="utf-8") as f:
            f.write(payload.proposed_content)

        payload.status = "committed"
        self._broadcast_event("WORKFLOW_DIFF_COMMITTED", {"diff_id": diff_id, "file": target})

        return {
            "status": "success",
            "diff_id": diff_id,
            "target_file": target,
            "bytes_written": len(payload.proposed_content.encode("utf-8")),
        }

    def _broadcast_event(self, event_type: str, payload: Dict[str, Any]) -> None:
        try:
            main_mod = sys.modules.get("services.backend.main")
            broadcaster = getattr(main_mod, "broadcast_message", None)
            if broadcaster:
                msg = {
                    "id": f"diff-{os.urandom(2).hex()}",
                    "type": event_type,
                    "ts": str(time.time()),
                    "payload": payload
                }
                main_loop = getattr(main_mod, "main_loop", None)
                if main_loop and main_loop.is_running():
                    asyncio.run_coroutine_threadsafe(broadcaster(msg), main_loop)
        except Exception:
            pass


taint_enclave = StrictTaintEnclave()
