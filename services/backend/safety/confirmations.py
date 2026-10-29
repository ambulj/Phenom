"""
Phenom Unified Confirmation & Preconditions Re-Validation Engine (Task 7l)
Enforces:
1. Pydantic ConfirmationRequest schema with strict One-Line Summary Invariant:
   "[Tier {tier}] {action_verb} {item_count} item(s) in {target_summary}"
2. Channel-aware timeouts: Desktop (900s / 15 min), Telegram (None / indefinite).
3. Late-approval preconditions re-validation (file mtime/SHA-256 integrity, mode drift, kill switch).
"""

import os
import time
import hashlib
from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field

from services.backend.schemas.protocol import RiskTier
from services.backend.safety.guardian import guardian

class PreconditionFailedError(RuntimeError):
    """Raised when preconditions for a late approval have been violated."""
    pass

class ConfirmationRequest(BaseModel):
    id: str
    tier: int # 1, 2, or 3
    tool_name: str
    action_verb: str
    item_count: int
    target_summary: str
    one_line_summary: str
    details: Dict[str, Any] = Field(default_factory=dict)
    preconditions: Dict[str, Any] = Field(default_factory=dict)
    created_at: float = Field(default_factory=time.time)
    channel: str = "desktop" # "desktop" or "telegram"
    timeout_seconds: Optional[int] = 900 # 900s for desktop, None for telegram

class ConfirmationEngine:
    DESKTOP_TIMEOUT_SECONDS = 900 # 15 minutes

    @staticmethod
    def format_one_line_summary(tier: int, action_verb: str, item_count: int, target_summary: str) -> str:
        """
        Enforces strict formatting invariant:
        [Tier {tier}] {action_verb} {item_count} item(s) in {target_summary}
        """
        verb = action_verb.strip().title()
        return f"[Tier {tier}] {verb} {item_count} item(s) in {target_summary}"

    @staticmethod
    def calculate_file_hash(path: str) -> str:
        """Calculates SHA-256 hash of a file."""
        if not os.path.exists(path) or os.path.isdir(path):
            return ""
        hasher = hashlib.sha256()
        with open(path, "rb") as f:
            while chunk := f.read(65536):
                hasher.update(chunk)
        return hasher.hexdigest()

    def build_confirmation(
        self,
        request_id: str,
        tier: int,
        tool_name: str,
        action_verb: str,
        item_count: int,
        target_summary: str,
        target_paths: Optional[List[str]] = None,
        details: Optional[Dict[str, Any]] = None,
        channel: str = "desktop",
        current_mode: str = "work"
    ) -> ConfirmationRequest:
        """
        Creates a structured ConfirmationRequest with recorded preconditions.
        """
        one_line = self.format_one_line_summary(tier, action_verb, item_count, target_summary)
        timeout = self.DESKTOP_TIMEOUT_SECONDS if channel == "desktop" else None

        # Record preconditions
        preconditions: Dict[str, Any] = {
            "mode": current_mode,
            "created_at": time.time(),
            "guardian_halted": guardian.is_halted,
            "file_hashes": {}
        }

        if target_paths:
            for p in target_paths:
                if os.path.exists(p):
                    preconditions["file_hashes"][p] = {
                        "mtime": os.path.getmtime(p),
                        "sha256": self.calculate_file_hash(p)
                    }

        return ConfirmationRequest(
            id=request_id,
            tier=tier,
            tool_name=tool_name,
            action_verb=action_verb,
            item_count=item_count,
            target_summary=target_summary,
            one_line_summary=one_line,
            details=details or {},
            preconditions=preconditions,
            created_at=time.time(),
            channel=channel,
            timeout_seconds=timeout
        )

    def validate_approval(
        self,
        confirmation: ConfirmationRequest,
        current_mode: str = "work"
    ) -> bool:
        """
        Re-validates preconditions before executing a delayed or late approval.
        Raises PreconditionFailedError if conditions drifted.
        """
        # 1. Check timeout on desktop channel
        if confirmation.timeout_seconds is not None:
            elapsed = time.time() - confirmation.created_at
            if elapsed > confirmation.timeout_seconds:
                raise PreconditionFailedError(
                    f"Confirmation request '{confirmation.id}' expired ({elapsed:.1f}s elapsed, limit {confirmation.timeout_seconds}s)."
                )

        # 2. Check Guardian Kill Switch
        if guardian.is_halted:
            raise PreconditionFailedError("Execution rejected: Guardian Kill Switch is engaged.")

        # 3. Check Mode Drift (e.g. user entered Meeting Mode or Gaming Mode)
        recorded_mode = confirmation.preconditions.get("mode")
        if recorded_mode and recorded_mode != current_mode:
            raise PreconditionFailedError(
                f"Mode drift detected: confirmation was created in '{recorded_mode}' mode, but current mode is '{current_mode}'."
            )

        # 4. Check File Integrity (Target files modified or deleted since confirmation)
        file_hashes = confirmation.preconditions.get("file_hashes", {})
        for path, meta in file_hashes.items():
            if not os.path.exists(path):
                raise PreconditionFailedError(
                    f"Target file integrity failure: '{path}' was deleted since confirmation was issued."
                )
            current_mtime = os.path.getmtime(path)
            if abs(current_mtime - meta["mtime"]) > 0.001:
                # Timestamps differ; check if content actually changed
                current_sha = self.calculate_file_hash(path)
                if current_sha != meta["sha256"]:
                    raise PreconditionFailedError(
                        f"Target file integrity failure: '{path}' was modified on disk after confirmation was issued."
                    )

        return True

# Global confirmation engine instance
confirmation_engine = ConfirmationEngine()
