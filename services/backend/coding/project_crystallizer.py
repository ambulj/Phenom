"""
Deep Project Knowledge Crystallizer for Phenom (Phase 4 RES-01)

Extracts architectural decisions, code changes, build fixes, and technical findings
into structured Obsidian project documentation: `vault/Projects/{ProjectName}.md`.

Features:
1. Bidirectional wikilinks connecting repositories with [[Daily Notes/YYYY-MM-DD]] and topics.
2. Non-destructive section parsing preserving handwritten user content in ## Notes & Journal.
3. Reversible in-memory rollback snapshots with unique rollback tokens.
4. Synchronous Guardian kill switch integration blocking mutations when halted.
"""

from __future__ import annotations

import os
import re
import uuid
from datetime import datetime
import logging
from typing import Dict, Any, List, Optional

from services.backend.safety.guardian import guardian

logger = logging.getLogger(__name__)


PROJECT_TEMPLATE = """# Project: {project_name}

- **Repository Root:** `{root_path}`
- **Primary Stack:** `{stack_summary}`
- **Last Crystallized:** `{last_updated}`
- **Related Daily Notes:** [[Daily Notes/{today_str}]]

## Technical Architecture & Decisions
{decisions_block}

## Build Diagnostics & Fix Log
{fixes_block}

## Project Directives & Active Goals
{tasks_block}

## Notes & Journal
{notes_block}
"""


class ProjectKnowledgeCrystallizer:
    """Manages deep technical knowledge crystallization into Obsidian project notes."""

    def __init__(self, vault_path: str = "vault") -> None:
        self.vault_path = vault_path
        self._halted: bool = False
        self._snapshots: Dict[str, str] = {}

    @property
    def is_halted(self) -> bool:
        """Returns True if halted manually or by Guardian kill switch."""
        return self._halted or guardian.is_halted

    def halt(self) -> None:
        """Immediately halts crystallization mutations."""
        self._halted = True

    def reset(self) -> None:
        """Resets halted state."""
        self._halted = False

    def get_project_note_path(self, project_name: str) -> str:
        """Returns path to vault/Projects/{ProjectName}.md."""
        clean_name = re.sub(r'[\\/*?:"<>|]', "", project_name).strip() or "UntitledProject"
        projects_dir = os.path.join(self.vault_path, "Projects")
        os.makedirs(projects_dir, exist_ok=True)
        return os.path.join(projects_dir, f"{clean_name}.md")

    def read_project_knowledge(self, project_name: str) -> Optional[str]:
        """Reads project note content if it exists."""
        path = self.get_project_note_path(project_name)
        if not os.path.isfile(path):
            return None
        with open(path, "r", encoding="utf-8") as f:
            return f.read()

    def _extract_section(self, content: str, section_title: str) -> str:
        """Extracts content between section headers."""
        pattern = rf"^##\s+{re.escape(section_title)}\s*\n(.*?)(?=^##\s+|\Z)"
        match = re.search(pattern, content, flags=re.MULTILINE | re.DOTALL)
        if match:
            return match.group(1).strip()
        return ""

    def crystallize_decision(
        self,
        project_name: str,
        root_path: str,
        title: str,
        decision: str,
        rationale: Optional[str] = None,
        stack_summary: Optional[str] = None
    ) -> Dict[str, Any]:
        """Crystallizes a technical or architectural decision into vault/Projects/{ProjectName}.md."""
        if self.is_halted:
            raise PermissionError("Project crystallization blocked: Guardian kill switch is active.")

        today_str = datetime.now().strftime("%Y-%m-%d")
        ts_str = datetime.now().strftime("%H:%M")
        entry = f"- **{today_str} {ts_str}** — **{title}**: {decision}"
        if rationale:
            entry += f" *(Rationale: {rationale})*"

        return self._merge_or_create_project_note(
            project_name=project_name,
            root_path=root_path,
            stack_summary=stack_summary or "TypeScript / Python / Polyglot",
            new_decision=entry
        )

    def crystallize_build_fix(
        self,
        project_name: str,
        root_path: str,
        error_type: str,
        file_path: str,
        patch_summary: str,
        stack_summary: Optional[str] = None
    ) -> Dict[str, Any]:
        """Crystallizes a resolved build failure and patch fix into vault/Projects/{ProjectName}.md."""
        if self.is_halted:
            raise PermissionError("Project crystallization blocked: Guardian kill switch is active.")

        today_str = datetime.now().strftime("%Y-%m-%d")
        ts_str = datetime.now().strftime("%H:%M")
        entry = (
            f"- **{today_str} {ts_str}** — Resolved `{error_type}` in `{file_path}`: {patch_summary}"
        )

        return self._merge_or_create_project_note(
            project_name=project_name,
            root_path=root_path,
            stack_summary=stack_summary or "TypeScript / Python / Polyglot",
            new_fix=entry
        )

    def _merge_or_create_project_note(
        self,
        project_name: str,
        root_path: str,
        stack_summary: str,
        new_decision: Optional[str] = None,
        new_fix: Optional[str] = None,
        new_task: Optional[str] = None
    ) -> Dict[str, Any]:
        """Performs non-destructive section merge with snapshot rollback token."""
        note_path = self.get_project_note_path(project_name)
        today_str = datetime.now().strftime("%Y-%m-%d")
        iso_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        existing_content = ""
        rollback_token = str(uuid.uuid4())

        if os.path.isfile(note_path):
            with open(note_path, "r", encoding="utf-8") as f:
                existing_content = f.read()
            self._snapshots[rollback_token] = existing_content

        if not existing_content:
            decisions_block = new_decision or "- *(No architectural decisions recorded yet)*"
            fixes_block = new_fix or "- *(No build fixes recorded yet)*"
            tasks_block = f"- [ ] {new_task}" if new_task else "- [ ] Initial project setup and architecture review"
            notes_block = "*(User notes and reflections here - preserved across automated updates)*\n"

            content = PROJECT_TEMPLATE.format(
                project_name=project_name,
                root_path=root_path,
                stack_summary=stack_summary,
                last_updated=iso_str,
                today_str=today_str,
                decisions_block=decisions_block,
                fixes_block=fixes_block,
                tasks_block=tasks_block,
                notes_block=notes_block
            )
        else:
            # Non-destructively parse existing sections
            existing_decisions = self._extract_section(existing_content, "Technical Architecture & Decisions")
            existing_fixes = self._extract_section(existing_content, "Build Diagnostics & Fix Log")
            existing_tasks = self._extract_section(existing_content, "Project Directives & Active Goals")
            existing_notes = self._extract_section(existing_content, "Notes & Journal")

            # Clean placeholder text
            if existing_decisions.startswith("- *(No architectural decisions"):
                existing_decisions = ""
            if existing_fixes.startswith("- *(No build fixes"):
                existing_fixes = ""

            # Append new items
            decisions_parts = [existing_decisions] if existing_decisions else []
            if new_decision:
                decisions_parts.append(new_decision)
            decisions_block = "\n".join(decisions_parts) if decisions_parts else "- *(No architectural decisions recorded yet)*"

            fixes_parts = [existing_fixes] if existing_fixes else []
            if new_fix:
                fixes_parts.append(new_fix)
            fixes_block = "\n".join(fixes_parts) if fixes_parts else "- *(No build fixes recorded yet)*"

            tasks_parts = [existing_tasks] if existing_tasks else []
            if new_task:
                tasks_parts.append(f"- [ ] {new_task}")
            tasks_block = "\n".join(tasks_parts) if tasks_parts else "- [ ] Ongoing project deliverables"

            notes_block = existing_notes if existing_notes else "*(User notes and reflections here)*\n"

            # Check if today's daily note is already referenced in Related Daily Notes
            daily_ref = f"[[Daily Notes/{today_str}]]"
            meta_pattern = r"(- \*\*Related Daily Notes:\*\*.*)"
            meta_match = re.search(meta_pattern, existing_content)
            if meta_match and daily_ref not in meta_match.group(1):
                updated_meta = f"{meta_match.group(1)}, {daily_ref}"
            else:
                updated_meta = f"- **Related Daily Notes:** {daily_ref}"

            content = (
                f"# Project: {project_name}\n\n"
                f"- **Repository Root:** `{root_path}`\n"
                f"- **Primary Stack:** `{stack_summary}`\n"
                f"- **Last Crystallized:** `{iso_str}`\n"
                f"{updated_meta}\n\n"
                f"## Technical Architecture & Decisions\n{decisions_block}\n\n"
                f"## Build Diagnostics & Fix Log\n{fixes_block}\n\n"
                f"## Project Directives & Active Goals\n{tasks_block}\n\n"
                f"## Notes & Journal\n{notes_block}\n"
            )

        with open(note_path, "w", encoding="utf-8") as f:
            f.write(content)

        return {
            "status": "crystallized",
            "project_name": project_name,
            "note_path": note_path,
            "rollback_token": rollback_token,
            "bytes_written": len(content)
        }

    def rollback_note(self, project_name: str, rollback_token: str) -> bool:
        """Restores project note to prior snapshot using rollback_token."""
        if self.is_halted:
            raise PermissionError("Rollback blocked: Guardian kill switch is active.")

        prior_content = self._snapshots.pop(rollback_token, None)
        if prior_content is None:
            return False

        note_path = self.get_project_note_path(project_name)
        with open(note_path, "w", encoding="utf-8") as f:
            f.write(prior_content)
        return True


# Global crystallizer singleton
project_crystallizer = ProjectKnowledgeCrystallizer()
