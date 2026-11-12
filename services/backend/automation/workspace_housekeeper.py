"""Phenom Idle Desktop Workspace Housekeeper.

Runs autonomously during user inactivity (idle_detector.is_idle) to organize
unfiled downloads into categorized folders (Documents, Images, Archives, Code)
and recycle discarded temporary clutter via Windows Recycle Bin (send2trash, Rule 7)
while immediately yielding when the user returns (WRK-03).
"""

from __future__ import annotations

import asyncio
import logging
import os
import shutil
import time
from typing import Any, Callable, Dict, List, Optional, Set

import send2trash

from services.backend.memory.daily_copilot import daily_copilot
from services.backend.proactive.dispatcher import proactive_dispatcher, ProactiveCard, ProactivePriority
from services.backend.safety.action_log import action_log
from services.backend.safety.guardian import guardian
from services.backend.sensors.idle_sensor import idle_detector

logger = logging.getLogger("phenom.workspace_housekeeper")

# File extension categorization mapping
CATEGORY_EXTENSIONS: Dict[str, Set[str]] = {
    "Documents": {".pdf", ".docx", ".doc", ".txt", ".md", ".xlsx", ".pptx", ".csv", ".odt"},
    "Images": {".png", ".jpg", ".jpeg", ".gif", ".webp", ".svg", ".bmp", ".ico"},
    "Archives": {".zip", ".tar", ".gz", ".7z", ".rar", ".bz2"},
    "Code": {".py", ".ts", ".tsx", ".js", ".json", ".html", ".css", ".rs", ".go", ".cpp", ".c", ".java"},
}

TEMPORARY_CLUTTER_EXTENSIONS: Set[str] = {".tmp", ".crdownload", ".partial", ".dmp"}


class WorkspaceHousekeeper:
    """Cleans and organizes desktop staging and download directories when the user is idle."""

    def __init__(
        self,
        target_directory: Optional[str] = None,
        idle_sensor_instance: Optional[Any] = None,
    ) -> None:
        self.target_directory = target_directory or os.path.join(os.path.expanduser("~"), "Downloads")
        self._idle_sensor = idle_sensor_instance or idle_detector
        self._halted: bool = False
        self._running_task: Optional[asyncio.Task] = None
        self._last_run_stats: Dict[str, Any] = {
            "last_run_timestamp": 0.0,
            "moved_count": 0,
            "recycled_count": 0,
            "status": "idle",
        }

    @property
    def is_halted(self) -> bool:
        return self._halted

    def halt(self) -> None:
        """Synchronously halt housekeeping execution immediately in < 25ms SLA (SAF-02)."""
        self._halted = True
        if self._running_task and not self._running_task.done():
            self._running_task.cancel()
            self._running_task = None
        logger.info("WorkspaceHousekeeper halted synchronously by Guardian.")

    def reset(self) -> None:
        """Reset halted state."""
        self._halted = False

    def get_status(self) -> Dict[str, Any]:
        """Returns housekeeper status, last run metrics, and idle state."""
        return {
            "target_directory": self.target_directory,
            "is_idle": bool(self._idle_sensor.is_idle) if hasattr(self._idle_sensor, "is_idle") else False,
            "is_halted": self._halted,
            "last_run": self._last_run_stats,
        }

    def _get_category(self, filename: str) -> Optional[str]:
        """Determines target category folder based on extension."""
        _, ext = os.path.splitext(filename.lower())
        for category, extensions in CATEGORY_EXTENSIONS.items():
            if ext in extensions:
                return category
        return None

    def _is_clutter(self, filename: str) -> bool:
        """Identifies temporary or incomplete files eligible for recycling."""
        lower = filename.lower()
        if lower.startswith("~$") or lower.startswith(".~"):
            return True
        _, ext = os.path.splitext(lower)
        return ext in TEMPORARY_CLUTTER_EXTENSIONS

    def _get_unique_destination(self, dest_dir: str, filename: str) -> str:
        """Computes a unique destination path to avoid overwriting existing files."""
        target = os.path.join(dest_dir, filename)
        if not os.path.exists(target):
            return target

        base, ext = os.path.splitext(filename)
        counter = 1
        while os.path.exists(os.path.join(dest_dir, f"{base}_{counter}{ext}")):
            counter += 1
        return os.path.join(dest_dir, f"{base}_{counter}{ext}")

    async def organize_workspace(
        self,
        directory: Optional[str] = None,
        enforce_idle_check: bool = True,
    ) -> Dict[str, Any]:
        """Performs atomic housekeeping pass on the target directory."""
        if self._halted or guardian.is_halted:
            raise PermissionError("Workspace housekeeping blocked: Guardian kill switch is active.")

        work_dir = os.path.abspath(directory or self.target_directory)
        if not os.path.exists(work_dir):
            return {"status": "skipped", "reason": f"Directory '{work_dir}' does not exist."}

        logger.info("Starting workspace housekeeping on: %s", work_dir)
        moved_files: List[Dict[str, str]] = []
        recycled_files: List[str] = []
        interrupted = False

        try:
            entries = os.listdir(work_dir)
        except Exception as exc:
            logger.error("Failed to list directory %s: %s", work_dir, exc)
            return {"status": "error", "error": str(exc)}

        for entry_name in entries:
            # Synchronously check interruption conditions: Guardian halt or user return
            if self._halted or guardian.is_halted:
                interrupted = True
                break

            if enforce_idle_check and hasattr(self._idle_sensor, "is_idle"):
                if not self._idle_sensor.is_idle:
                    logger.info("User returned during housekeeping; yielding immediately.")
                    interrupted = True
                    break

            full_path = os.path.join(work_dir, entry_name)

            # Skip directories (do not touch existing subfolders)
            if not os.path.isfile(full_path):
                continue

            # Check for discarded temporary clutter -> send to recycle bin (Rule 7)
            if self._is_clutter(entry_name):
                try:
                    send2trash.send2trash(full_path)
                    recycled_files.append(entry_name)
                    logger.debug("Recycled clutter file via send2trash: %s", entry_name)
                except Exception as exc:
                    logger.warning("Failed to recycle %s: %s", entry_name, exc)
                continue

            # Check for file organization category
            category = self._get_category(entry_name)
            if category:
                dest_dir = os.path.join(work_dir, category)
                os.makedirs(dest_dir, exist_ok=True)
                dest_path = self._get_unique_destination(dest_dir, entry_name)

                try:
                    shutil.move(full_path, dest_path)
                    moved_files.append({
                        "filename": entry_name,
                        "category": category,
                        "destination": dest_path,
                    })
                    logger.debug("Organized %s -> %s", entry_name, category)
                except Exception as exc:
                    logger.warning("Failed to move %s to %s: %s", entry_name, category, exc)

        total_actions = len(moved_files) + len(recycled_files)

        self._last_run_stats = {
            "last_run_timestamp": time.time(),
            "moved_count": len(moved_files),
            "recycled_count": len(recycled_files),
            "status": "interrupted" if interrupted else "completed",
            "directory": work_dir,
        }

        # If any actions occurred, log to daily note and dispatch ProactiveCard
        if total_actions > 0:
            summary_msg = (
                f"Housekeeper organized {len(moved_files)} files into folders "
                f"and recycled {len(recycled_files)} temporary items."
            )
            try:
                daily_copilot.log_background_operation(summary_msg)
            except Exception as exc:
                logger.debug("Failed to log housekeeping to daily co-pilot: %s", exc)

            card = ProactiveCard(
                event_type="IDLE_CLEANUP",
                priority=ProactivePriority.BACKGROUND,
                title="Desktop Housekeeping Complete",
                description=summary_msg,
                action_chip="View Downloads",
                action_payload={"directory": work_dir},
            )
            try:
                await proactive_dispatcher.dispatch(card)
            except Exception as exc:
                logger.debug("Failed to dispatch proactive housekeeping card: %s", exc)

            action_log.log_action(
                tool="workspace_housekeeper",
                tier=1,
                args={"directory": work_dir, "moved": len(moved_files), "recycled": len(recycled_files)},
                decision="approved",
                result_status="SUCCESS",
            )

        return {
            "status": "interrupted" if interrupted else "completed",
            "moved_count": len(moved_files),
            "recycled_count": len(recycled_files),
            "moved_files": moved_files,
            "recycled_files": recycled_files,
            "interrupted": interrupted,
        }

    async def on_user_idle(self, idle_seconds: float) -> None:
        """Callback triggered by Win32IdleDetector when user becomes idle."""
        if self._halted or guardian.is_halted:
            return

        logger.info("WorkspaceHousekeeper idle callback triggered (user idle %.1fs)", idle_seconds)
        try:
            await self.organize_workspace(enforce_idle_check=True)
        except Exception as exc:
            logger.error("Error during autonomous idle housekeeping: %s", exc)

    def on_user_returned(self, idle_duration: float) -> None:
        """Callback triggered when user returns from idle state; yields immediately."""
        logger.info("WorkspaceHousekeeper user returned (duration was %.1fs); ensuring yield.", idle_duration)


# Global singleton
workspace_housekeeper = WorkspaceHousekeeper()
