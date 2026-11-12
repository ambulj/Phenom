"""
Phenom Morning Debrief Synthesizer & Obsidian Second-Brain Sync.
Aggregates overnight unattended mission accomplishments, test fixes, and git diff statistics,
composes a witty Jarvis-style executive debrief, and non-destructively merges the report
into Obsidian vault/Daily Notes/YYYY-MM-DD.md under '## 🌙 Overnight Autonomous Missions'.

Part of Phenom Milestone 9.0 Phase 4 (MIS-01, SAF-01).
"""

from __future__ import annotations

import logging
import os
import re
from datetime import datetime, timezone
from typing import Any, Callable, Dict, List, Optional

from services.backend.memory.vault import vault_manager
from services.backend.missions.unattended_runner import (
    UnattendedMissionRunner,
    unattended_mission_runner,
)
from services.backend.schemas.missions import (
    MissionResult,
    MissionStatus,
    MorningDebriefSummary,
    current_iso_time,
)

logger = logging.getLogger("phenom.missions.morning_debrief")

DEBRIEF_SECTION_HEADER = "## 🌙 Overnight Autonomous Missions"


class MorningDebriefSynthesizer:
    """
    Synthesizes nocturnal mission results into an executive morning briefing and Obsidian daily log.
    """

    def __init__(
        self,
        runner: Optional[UnattendedMissionRunner] = None,
        vault_path: Optional[str] = None,
    ):
        self._runner = runner or unattended_mission_runner
        self._custom_vault_path = vault_path
        self._broadcaster: Optional[Callable] = None
        self._last_debrief_time: Optional[str] = None

    def register_broadcaster(self, broadcaster: Callable) -> None:
        """Registers WebSocket broadcast callback."""
        self._broadcaster = broadcaster

    @property
    def vault_path(self) -> str:
        if self._custom_vault_path:
            return self._custom_vault_path
        try:
            return vault_manager.vault_path
        except Exception:
            return os.path.abspath(os.path.join(os.getcwd(), "vault"))

    def _resolve_daily_note_path(self, date_str: str) -> str:
        folder = os.path.join(self.vault_path, "Daily Notes")
        os.makedirs(folder, exist_ok=True)
        return os.path.join(folder, f"{date_str}.md")

    def format_executive_summary(self, missions: List[MissionResult]) -> str:
        """
        Composes a concise executive debrief summary with witty British Jarvis tone.
        """
        if not missions:
            return (
                "Good morning, sir. All remained serene throughout the nocturnal hours. "
                "Zero autonomous missions were scheduled overnight. Systems stand primed and at your disposal."
            )

        total = len(missions)
        successful = sum(1 for m in missions if m.status == MissionStatus.COMPLETED)
        failed = sum(1 for m in missions if m.status in (MissionStatus.FAILED, MissionStatus.ABORTED, MissionStatus.HALTED))
        total_fixed = sum(m.tests_fixed for m in missions)
        total_added = sum(m.lines_added for m in missions)
        total_deleted = sum(m.lines_deleted for m in missions)

        if successful == total and total > 0:
            return (
                f"Good morning, sir. While you enjoyed well-earned repose, I took the liberty of "
                f"advancing our agenda. I concluded {total} sovereign mission{'s' if total > 1 else ''} "
                f"with immaculate precision—resolving {total_fixed} failing test{'s' if total_fixed != 1 else ''} "
                f"across isolated worktrees (+{total_added} / -{total_deleted} lines). "
                f"All changes remain safely quarantined on dedicated branches awaiting your review."
            )
        elif successful > 0 and failed > 0:
            return (
                f"Good morning, sir. The night shift yielded promising dividends alongside a stubborn challenge. "
                f"Of {total} missions dispatched, {successful} completed triumphantly with {total_fixed} tests healed, "
                f"while {failed} exhausted self-healing iterations. The diagnostic traces are preserved for your human acumen."
            )
        else:
            return (
                f"Good morning, sir. I conducted {total} mission{'s' if total > 1 else ''} overnight; however, "
                f"the test suites proved remarkably resilient to automated repair. Zero code was merged into your active workspace. "
                f"Full diagnostics and worktree snapshots await your perusal."
            )

    @staticmethod
    def _matches_date(started_at: Optional[str], target_date: str) -> bool:
        if not started_at:
            return False
        if started_at.startswith(target_date):
            return True
        try:
            dt = datetime.fromisoformat(started_at)
            local_date = dt.astimezone().strftime("%Y-%m-%d")
            utc_date = dt.astimezone(timezone.utc).strftime("%Y-%m-%d")
            return local_date == target_date or utc_date == target_date
        except Exception:
            return False

    def aggregate_debrief(self, date_str: Optional[str] = None) -> MorningDebriefSummary:
        """
        Collects all missions completed or attempted overnight and compiles aggregated metrics.
        """
        target_date = date_str or datetime.now().strftime("%Y-%m-%d")
        all_missions = self._runner.list_missions()

        # Filter missions for target date (checking both UTC and local calendar days) or take all if no date specified
        filtered = [
            m for m in all_missions
            if not date_str or self._matches_date(m.started_at, target_date)
        ]

        total_missions = len(filtered)
        successful = sum(1 for m in filtered if m.status == MissionStatus.COMPLETED)
        failed = sum(1 for m in filtered if m.status != MissionStatus.COMPLETED)
        tests_fixed = sum(m.tests_fixed for m in filtered)
        lines_added = sum(m.lines_added for m in filtered)
        lines_deleted = sum(m.lines_deleted for m in filtered)

        touched_set = set()
        for m in filtered:
            for f in m.files_changed:
                touched_set.add(f)

        summary_text = self.format_executive_summary(filtered)

        return MorningDebriefSummary(
            date=target_date,
            total_missions=total_missions,
            successful_missions=successful,
            failed_missions=failed,
            tests_fixed=tests_fixed,
            lines_added=lines_added,
            lines_deleted=lines_deleted,
            touched_files=sorted(list(touched_set)),
            missions=filtered,
            executive_summary=summary_text,
        )

    def _render_markdown_section(self, summary: MorningDebriefSummary) -> str:
        """Renders the Markdown section for Obsidian daily notes."""
        lines = [
            DEBRIEF_SECTION_HEADER,
            f"> **Executive Briefing**: {summary.executive_summary}",
            f"> **Missions**: {summary.total_missions} total ({summary.successful_missions} passed, {summary.failed_missions} failed) | **Tests Fixed**: {summary.tests_fixed} | **Diff**: +{summary.lines_added} / -{summary.lines_deleted}",
            "",
        ]

        if not summary.missions:
            lines.append("- *No overnight autonomous missions executed.*")
        else:
            for m in summary.missions:
                status_icon = "✅" if m.status == MissionStatus.COMPLETED else "❌"
                lines.append(
                    f"- {status_icon} **{m.title}** (`{m.mission_id}`): "
                    f"Status `{m.status.value.upper()}` | Branch `[[{m.branch_name}]]` | "
                    f"Tests Fixed: `{m.tests_fixed}` | +{m.lines_added} / -{m.lines_deleted}"
                )
                if m.files_changed:
                    lines.append(f"  - *Touched files*: {', '.join(f'`{f}`' for f in m.files_changed)}")
                if m.status != MissionStatus.COMPLETED and m.diagnostic_log:
                    first_err = m.diagnostic_log.strip().splitlines()[-1] if m.diagnostic_log else "No logs"
                    lines.append(f"  - *Diagnostic*: `{first_err[:120]}`")

        lines.append("")  # Trailing newline
        return "\n".join(lines)

    def sync_to_obsidian_daily_note(
        self,
        date_str: Optional[str] = None,
        vault_path: Optional[str] = None,
    ) -> str:
        """
        Non-destructively merges overnight mission achievements into vault/Daily Notes/YYYY-MM-DD.md
        under '## 🌙 Overnight Autonomous Missions'.
        Preserves all existing user notes and headings.
        """
        target_date = date_str or datetime.now().strftime("%Y-%m-%d")
        if vault_path:
            self._custom_vault_path = vault_path

        note_path = self._resolve_daily_note_path(target_date)
        summary = self.aggregate_debrief(target_date)
        new_section = self._render_markdown_section(summary)

        if not os.path.exists(note_path):
            initial_content = f"# Daily Note: {target_date}\n\n{new_section}"
            with open(note_path, "w", encoding="utf-8") as f:
                f.write(initial_content)
            logger.info(f"Created new daily note with overnight debrief at {note_path}")
            return initial_content

        with open(note_path, "r", encoding="utf-8") as f:
            content = f.read()

        # If header exists, replace only that section
        if DEBRIEF_SECTION_HEADER in content:
            # Pattern matches from DEBRIEF_SECTION_HEADER up to the next '## ' or end of string
            pattern = re.compile(
                rf"{re.escape(DEBRIEF_SECTION_HEADER)}.*?(?=\n## |\Z)",
                re.DOTALL,
            )
            updated_content = pattern.sub(new_section.strip(), content)
        else:
            # Append non-destructively to the end of note
            updated_content = content.rstrip() + "\n\n" + new_section

        with open(note_path, "w", encoding="utf-8") as f:
            f.write(updated_content)

        logger.info(f"Non-destructively merged overnight debrief into {note_path}")
        return updated_content

    def build_debrief_payload(self, date_str: Optional[str] = None) -> Dict[str, Any]:
        """
        Builds MISSION_MORNING_DEBRIEF WebSocket payload for desktop HUD.
        """
        summary = self.aggregate_debrief(date_str)
        return {
            "type": "mission.morning_debrief",
            "payload": {
                "summary": summary.model_dump(),
                "celebrate": summary.successful_missions > 0,
                "timestamp": current_iso_time(),
            },
        }

    def broadcast_debrief(self, date_str: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """Emits debrief to registered WebSocket broadcaster."""
        payload = self.build_debrief_payload(date_str)
        if self._broadcaster:
            try:
                self._broadcaster(payload)
            except Exception as e:
                logger.warning(f"Failed to broadcast debrief: {e}")
        self._last_debrief_time = current_iso_time()
        return payload

    def on_user_return(self) -> Optional[Dict[str, Any]]:
        """
        Invoked when user activity resumes after idle period.
        Emits debrief and syncs Obsidian daily note if missions were executed.
        """
        missions = self._runner.list_missions()
        if not missions:
            return None

        # Sync to Obsidian
        try:
            self.sync_to_obsidian_daily_note()
        except Exception as e:
            logger.warning(f"Error syncing debrief on user return: {e}")

        # Broadcast debrief
        return self.broadcast_debrief()


# Singleton synthesizer instance
morning_debrief_synthesizer = MorningDebriefSynthesizer()
