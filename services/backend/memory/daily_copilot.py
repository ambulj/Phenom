"""Phenom Obsidian Daily Note Auto-Co-Pilot.

Automatically scaffolds and continuously synchronizes the user's second-brain daily note
(vault/Daily Notes/YYYY-MM-DD.md) with calendar timeblocks, action items, and autonomous
background triage logs with non-destructive section merging and local git commits (WRK-02).
"""

from __future__ import annotations

from datetime import datetime, timezone
import logging
import os
import re
import uuid
from typing import Any, Dict, List, Optional, Tuple

from services.backend.memory.vault import vault_manager, resolve_and_sandbox_vault_path
from services.backend.safety.action_log import action_log

logger = logging.getLogger("phenom.daily_copilot")


DEFAULT_DAILY_NOTE_TEMPLATE = """# Daily Note: {date_str}

## Scheduled Timeblocks
{timeblocks}

## Action Items & Directives
{action_items}

## Background Swarm & Triage Log
{triage_log}

## Notes & Journal
- Personal reflections, meeting notes, and spontaneous ideas.
"""


class ObsidianDailyCoPilot:
    """Manages idempotent, non-destructive synchronization of Obsidian Daily Notes."""

    def __init__(self) -> None:
        self._undo_snapshots: Dict[str, Tuple[str, str]] = {}  # token -> (file_path, old_content)

    def _get_target_path(self, date_str: Optional[str] = None) -> str:
        """Resolves sandboxed absolute path to Daily Notes/YYYY-MM-DD.md."""
        target_date = date_str or datetime.now().strftime("%Y-%m-%d")
        daily_folder = os.path.join(vault_manager.vault_path, "Daily Notes")
        os.makedirs(daily_folder, exist_ok=True)
        rel_path = os.path.join("Daily Notes", f"{target_date}.md")
        return resolve_and_sandbox_vault_path(rel_path, vault_manager.vault_path)

    def read_daily_note(self, date_str: Optional[str] = None) -> str:
        """Reads the contents of the specified daily note if it exists."""
        target_path = self._get_target_path(date_str)
        if not os.path.exists(target_path):
            raise FileNotFoundError(f"Daily note for {date_str or 'today'} does not exist.")
        with open(target_path, "r", encoding="utf-8") as f:
            return f.read()

    def ensure_daily_note(
        self,
        date_str: Optional[str] = None,
        initial_timeblocks: str = "- No events scheduled for today.",
        initial_action_items: str = "- [ ] Review today's executive briefing.",
        initial_triage_log: str = "- Initialized daily workspace co-pilot.",
    ) -> str:
        """Ensures the daily note exists, scaffolding it with default structure if missing."""
        target_date = date_str or datetime.now().strftime("%Y-%m-%d")
        target_path = self._get_target_path(target_date)

        if not os.path.exists(target_path):
            content = DEFAULT_DAILY_NOTE_TEMPLATE.format(
                date_str=target_date,
                timeblocks=initial_timeblocks.strip(),
                action_items=initial_action_items.strip(),
                triage_log=initial_triage_log.strip(),
            )
            with open(target_path, "w", encoding="utf-8") as f:
                f.write(content)
            try:
                vault_manager.commit_changes(f"copilot: scaffold daily note {target_date}")
            except Exception as exc:
                logger.debug("Failed to commit scaffolded daily note: %s", exc)

        return target_path

    def _merge_section(self, full_text: str, section_title: str, new_body: str) -> str:
        """Replaces or injects a specific Markdown section while strictly preserving all other content.

        Matches '## Section Title' up to the next '## ' or end of string.
        """
        pattern = re.compile(
            rf"(^##\s+{re.escape(section_title)}\s*\n)(.*?)(?=\n##\s+|\Z)",
            re.MULTILINE | re.DOTALL,
        )

        formatted_body = new_body.strip() + "\n"

        if pattern.search(full_text):
            return pattern.sub(rf"\g<1>{formatted_body}", full_text)
        else:
            # Append section before '## Notes & Journal' if present, else at the end
            notes_match = re.search(r"^##\s+Notes & Journal", full_text, re.MULTILINE)
            section_block = f"\n## {section_title}\n{formatted_body}\n"
            if notes_match:
                idx = notes_match.start()
                return full_text[:idx] + section_block + full_text[idx:]
            else:
                return full_text.rstrip() + "\n" + section_block

    def _write_with_undo(self, target_path: str, new_content: str, commit_msg: str) -> str:
        """Writes content safely, recording an undo snapshot and committing to git."""
        old_content = ""
        if os.path.exists(target_path):
            with open(target_path, "r", encoding="utf-8") as f:
                old_content = f.read()

        undo_token = f"undo-copilot-{uuid.uuid4().hex[:12]}"
        self._undo_snapshots[undo_token] = (target_path, old_content)

        with open(target_path, "w", encoding="utf-8") as f:
            f.write(new_content)

        try:
            vault_manager.commit_changes(commit_msg)
        except Exception as exc:
            logger.debug("Vault commit failed: %s", exc)

        return undo_token

    def rollback_mutation(self, undo_token: str) -> bool:
        """Reverts a previous daily note mutation using an undo token."""
        if undo_token not in self._undo_snapshots:
            return False

        target_path, old_content = self._undo_snapshots.pop(undo_token)
        try:
            with open(target_path, "w", encoding="utf-8") as f:
                f.write(old_content)
            vault_manager.commit_changes(f"rollback: reverted {undo_token}")
            return True
        except Exception as exc:
            logger.error("Failed to rollback mutation %s: %s", undo_token, exc)
            return False

    def sync_calendar_timeblocks(
        self,
        events: List[Dict[str, Any]],
        date_str: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Updates ## Scheduled Timeblocks with the latest calendar schedule."""
        target_date = date_str or datetime.now().strftime("%Y-%m-%d")
        target_path = self.ensure_daily_note(target_date)

        current_content = self.read_daily_note(target_date)

        if not events:
            timeblocks_text = "- No events scheduled for today."
        else:
            lines = []
            for ev in events:
                summary = ev.get("summary") or ev.get("title") or "Meeting"
                start = ev.get("start", "")
                end = ev.get("end", "")
                # Format start/end if ISO
                start_fmt = start.split("T")[-1][:5] if "T" in start else start
                end_fmt = end.split("T")[-1][:5] if "T" in end else end
                time_range = f"{start_fmt} - {end_fmt}" if start_fmt and end_fmt else "Scheduled"
                meet_link = ev.get("meet_link")
                link_suffix = f" ([Link]({meet_link}))" if meet_link else ""
                lines.append(f"- [ ] {time_range}: **{summary}**{link_suffix}")
            timeblocks_text = "\n".join(lines)

        new_content = self._merge_section(current_content, "Scheduled Timeblocks", timeblocks_text)
        undo_token = self._write_with_undo(
            target_path,
            new_content,
            f"copilot: sync calendar timeblocks ({len(events)} events) for {target_date}",
        )

        action_log.log_action(
            tool="daily_copilot_sync_timeblocks",
            tier=1,
            args={"events_count": len(events), "date": target_date},
            decision="approved",
            result_status="SUCCESS",
        )

        return {
            "status": "ok",
            "date": target_date,
            "events_synced": len(events),
            "undo_token": undo_token,
            "file_path": target_path,
        }

    def add_action_item(
        self,
        task: str,
        date_str: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Appends a new checklist item to ## Action Items & Directives."""
        if not task.strip():
            raise ValueError("Task description must not be empty.")

        target_date = date_str or datetime.now().strftime("%Y-%m-%d")
        target_path = self.ensure_daily_note(target_date)

        current_content = self.read_daily_note(target_date)

        # Extract existing action items
        match = re.search(
            r"^##\s+Action Items & Directives\s*\n(.*?)(?=\n##\s+|\Z)",
            current_content,
            re.MULTILINE | re.DOTALL,
        )
        existing_body = match.group(1).strip() if match else ""
        new_item = f"- [ ] {task.strip()}"

        if existing_body and existing_body != "- No action items defined.":
            updated_body = f"{existing_body}\n{new_item}"
        else:
            updated_body = new_item

        new_content = self._merge_section(current_content, "Action Items & Directives", updated_body)
        undo_token = self._write_with_undo(
            target_path,
            new_content,
            f"copilot: add action item for {target_date}",
        )

        return {
            "status": "ok",
            "date": target_date,
            "task": task.strip(),
            "undo_token": undo_token,
        }

    def log_background_operation(
        self,
        operation: str,
        date_str: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Appends a timestamped record to ## Background Swarm & Triage Log."""
        if not operation.strip():
            return {"status": "skipped"}

        target_date = date_str or datetime.now().strftime("%Y-%m-%d")
        target_path = self.ensure_daily_note(target_date)

        current_content = self.read_daily_note(target_date)
        time_str = datetime.now().strftime("%H:%M:%S")
        log_line = f"- [{time_str}] {operation.strip()}"

        match = re.search(
            r"^##\s+Background Swarm & Triage Log\s*\n(.*?)(?=\n##\s+|\Z)",
            current_content,
            re.MULTILINE | re.DOTALL,
        )
        existing_body = match.group(1).strip() if match else ""

        if existing_body and not existing_body.startswith("- Initialized"):
            updated_body = f"{existing_body}\n{log_line}"
        else:
            updated_body = log_line

        new_content = self._merge_section(current_content, "Background Swarm & Triage Log", updated_body)
        undo_token = self._write_with_undo(
            target_path,
            new_content,
            f"copilot: log background operation for {target_date}",
        )

        return {
            "status": "ok",
            "date": target_date,
            "operation": operation,
            "undo_token": undo_token,
        }


# Global singleton
daily_copilot = ObsidianDailyCoPilot()
