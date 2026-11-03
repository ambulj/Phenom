"""
Proactive Dev Build Sentinel & Obsidian Debug Journal Engine.
Diagnoses terminal test and build errors, drafts minimal unified diffs,
dispatches Cyber HUD proactive action cards, and logs resolutions to Obsidian.

Part of Phenom 8.0 Proactive Dev Build Sentinel (DEV-02).
"""

import asyncio
import datetime
import os
import time
from typing import Dict, Optional, Tuple

from services.backend.coding.traceback_parser import BuildFailureDiagnostic, TracebackParser
from services.backend.coding.patch_drafter import PatchDrafter, patch_drafter
from services.backend.coding.workspace_sentinel import workspace_sentinel
from services.backend.proactive.dispatcher import proactive_dispatcher, ProactiveCard, ProactivePriority


class BuildSentinel:
    """
    Coordinates error diagnosis, patch synthesis, proactive Cyber HUD notification,
    and second-brain debug documentation.
    """

    def __init__(
        self,
        vault_root: Optional[str] = None,
        failure_cooldown_seconds: float = 30.0,
    ):
        self.vault_root = vault_root or os.path.join("C:\\Phenom", "vault")
        self.failure_cooldown_seconds = failure_cooldown_seconds
        self.parser = TracebackParser()
        self.drafter: PatchDrafter = patch_drafter

        self._halted: bool = False
        self._last_diagnosed_times: Dict[str, float] = {}

    def halt(self) -> None:
        """Synchronously halts the build sentinel (< 25ms SLA)."""
        self._halted = True

    def reset(self) -> None:
        """Resets the build sentinel."""
        self._halted = False

    @property
    def is_halted(self) -> bool:
        return self._halted

    def diagnose_output(
        self, output: str, workspace_path: Optional[str] = None
    ) -> Optional[BuildFailureDiagnostic]:
        """
        Parses build or test runner logs into a structured diagnostic.
        """
        if self._halted or not output:
            return None

        diag = self.parser.parse(output)
        if not diag:
            return None

        # Check cooldown to prevent duplicate alerts
        diag_key = f"{diag.runner}:{diag.failing_file}:{diag.test_name or ''}"
        now = time.time()
        last_time = self._last_diagnosed_times.get(diag_key, 0)
        if now - last_time < self.failure_cooldown_seconds:
            return diag

        self._last_diagnosed_times[diag_key] = now

        # Broadcast proactive card to Cyber HUD if dispatcher available
        self._broadcast_proactive_failure_card(diag, workspace_path)
        return diag

    def _broadcast_proactive_failure_card(
        self, diag: BuildFailureDiagnostic, workspace_path: Optional[str]
    ) -> None:
        try:
            test_title = diag.test_name or os.path.basename(diag.failing_file)
            card = ProactiveCard(
                event_type="DEV_BUILD_FAILURE",
                priority=ProactivePriority.NORMAL,
                title=f"Failed {diag.runner.upper()}: {test_title}",
                description=f"{diag.error_type}: {diag.error_message}",
                action_chip="Review Fix Diff",
                action_payload={"failing_file": diag.failing_file, "workspace_path": workspace_path},
            )
            try:
                loop = asyncio.get_running_loop()
                if loop and loop.is_running():
                    loop.create_task(proactive_dispatcher.dispatch(card))
            except RuntimeError:
                pass
        except Exception:
            pass

    def draft_patch(
        self,
        failing_file: str,
        replacement_code: str,
        workspace_path: Optional[str] = None,
    ) -> Optional[str]:
        """
        Generates a unified diff for a failing file in the active workspace.
        """
        ws = workspace_path or (
            workspace_sentinel.get_current_state().root_path
            if workspace_sentinel.get_current_state()
            else "C:\\Phenom"
        )
        full_path = failing_file if os.path.isabs(failing_file) else os.path.join(ws, failing_file)

        if not os.path.exists(full_path):
            return None

        try:
            with open(full_path, "r", encoding="utf-8") as f:
                original_code = f.read()

            rel_path = os.path.relpath(full_path, ws)
            diff = self.drafter.create_unified_diff(rel_path, original_code, replacement_code)
            return diff
        except Exception:
            return None

    def apply_patch_fix(
        self,
        patch_diff: str,
        workspace_path: Optional[str] = None,
        diagnostic: Optional[BuildFailureDiagnostic] = None,
        resolution_notes: Optional[str] = None,
    ) -> Tuple[bool, Optional[str], Optional[str]]:
        """
        Applies a verified patch with pre-patch snapshot, optionally logging to Obsidian.
        """
        if self._halted:
            return False, None, "Sentinel is halted"

        ws = workspace_path or (
            workspace_sentinel.get_current_state().root_path
            if workspace_sentinel.get_current_state()
            else "C:\\Phenom"
        )

        success, token, err = self.drafter.apply_patch(ws, patch_diff)
        if success and token and diagnostic:
            self.log_resolution_to_obsidian(
                workspace_path=ws,
                diagnostic=diagnostic,
                resolution=resolution_notes or "Automated 1-click patch applied",
                rollback_token=token,
            )

        return success, token, err

    def revert_patch_fix(
        self, rollback_token: str, workspace_path: Optional[str] = None
    ) -> bool:
        """
        Reverts the workspace to the pre-patch snapshot.
        """
        ws = workspace_path or (
            workspace_sentinel.get_current_state().root_path
            if workspace_sentinel.get_current_state()
            else "C:\\Phenom"
        )
        return self.drafter.revert_patch(ws, rollback_token)

    def log_resolution_to_obsidian(
        self,
        workspace_path: str,
        diagnostic: BuildFailureDiagnostic,
        resolution: str,
        rollback_token: str,
    ) -> bool:
        """
        Logs error diagnosis and applied patch resolution to vault/Projects/{ProjectName}.md.
        """
        project_name = os.path.basename(os.path.normpath(workspace_path)) or "DefaultProject"
        projects_dir = os.path.join(self.vault_root, "Projects")
        os.makedirs(projects_dir, exist_ok=True)

        note_path = os.path.join(projects_dir, f"{project_name}.md")
        now_str = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")

        entry = (
            f"\n### {now_str} - {diagnostic.runner.upper()}: {diagnostic.test_name or diagnostic.failing_file}\n"
            f"- **Error:** `{diagnostic.error_type}: {diagnostic.error_message}`\n"
            f"- **File:** `{diagnostic.failing_file}`"
            + (f":{diagnostic.line_number}" if diagnostic.line_number else "")
            + f"\n- **Resolution:** {resolution}\n"
            f"- **Rollback Token:** `{rollback_token}`\n"
        )

        try:
            if not os.path.exists(note_path):
                content = (
                    f"# Project: {project_name}\n\n"
                    f"**Path:** `{workspace_path}`\n\n"
                    f"## Build & Test Debug Journal\n"
                    + entry
                )
                with open(note_path, "w", encoding="utf-8") as f:
                    f.write(content)
            else:
                with open(note_path, "r", encoding="utf-8") as f:
                    existing = f.read()

                if "## Build & Test Debug Journal" not in existing:
                    existing += "\n\n## Build & Test Debug Journal\n"

                parts = existing.split("## Build & Test Debug Journal", 1)
                updated = parts[0] + "## Build & Test Debug Journal\n" + entry + parts[1]
                with open(note_path, "w", encoding="utf-8") as f:
                    f.write(updated)
            return True
        except Exception:
            return False


# Global singleton instance
build_sentinel = BuildSentinel()
