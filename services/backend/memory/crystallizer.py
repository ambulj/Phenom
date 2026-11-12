"""
Phenom Obsidian Second Brain & Session Crystallization Engine
Automatically extracts decisions, tasks, and research insights from assistant conversations
and autonomous execution sessions into structured Obsidian Markdown notes with strict
directory sandboxing, action logging, and 1-click reversible rollbacks.
"""

import os
import re
import time
import uuid
from enum import Enum
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field

from services.backend.memory.vault import (
    vault_manager,
    resolve_and_sandbox_vault_path,
    VaultSandboxViolation
)
from services.backend.safety.action_log import action_log


class NoteType(str, Enum):
    DECISION = "decision"
    TASK = "task"
    RESEARCH = "research"
    DAILY_LOG = "daily_log"


class CrystallizedItem(BaseModel):
    note_type: NoteType
    title: str
    summary: str
    content: str
    tags: List[str] = Field(default_factory=list)
    metadata: Dict[str, Any] = Field(default_factory=dict)
    wikilinks: List[str] = Field(default_factory=list)


class CrystallizationResult(BaseModel):
    session_id: str
    items_extracted: int
    notes_written: List[str]
    daily_log_updated: bool
    undo_tokens: List[str]
    timestamp: float


def sanitize_filename(title: str, max_length: int = 80) -> str:
    """Sanitizes note titles for Windows filesystem compliance."""
    # Remove Windows reserved characters: \ / : * ? " < > |
    cleaned = re.sub(r'[\\/*?:"<>|]', "", title)
    cleaned = re.sub(r'\s+', " ", cleaned).strip()
    if not cleaned:
        cleaned = f"note-{uuid.uuid4().hex[:6]}"
    if len(cleaned) > max_length:
        cleaned = cleaned[:max_length].rstrip()
    return cleaned


class SessionCrystallizer:
    """
    Distills session interactions into structured Obsidian notes with strict sandboxing
    and reversible rollback state.
    """

    def __init__(self, vault_inst=None):
        self.vault = vault_inst or vault_manager
        self._undo_registry: Dict[str, Dict[str, Any]] = {}

    def extract_from_text(self, text: str, session_id: Optional[str] = None) -> List[CrystallizedItem]:
        """
        Heuristically extracts decisions, tasks, and research insights from dialogue text.
        """
        if not text or not text.strip():
            return []

        extracted: List[CrystallizedItem] = []
        lines = text.strip().splitlines()

        # 1. Decisions extraction
        decision_patterns = [
            r"(?i)^(?:decision|decided|we decided|architectural decision):\s*(.+)",
            r"(?i)^###\s*Decision:\s*(.+)",
            r"(?i)\*\*Decision:\*\*\s*(.+)"
        ]
        # 2. Tasks extraction
        task_patterns = [
            r"^\s*-\s*\[ \]\s*(.+)",
            r"^\s*\*\s*\[ \]\s*(.+)",
            r"(?i)^(?:todo|task|action item):\s*(.+)",
            r"(?i)\*\*Task:\*\*\s*(.+)"
        ]
        # 3. Research extraction
        research_patterns = [
            r"(?i)^(?:research|finding|tech note|insight):\s*(.+)",
            r"(?i)^###\s*Research:\s*(.+)",
            r"(?i)\*\*Research:\*\*\s*(.+)"
        ]

        current_block: Optional[Dict[str, Any]] = None

        for line in lines:
            trimmed = line.strip()
            if not trimmed:
                continue

            matched = False

            # Check Decisions
            for pat in decision_patterns:
                m = re.match(pat, trimmed)
                if m:
                    d_title = m.group(1).strip()
                    extracted.append(CrystallizedItem(
                        note_type=NoteType.DECISION,
                        title=f"Decision - {d_title[:60]}",
                        summary=d_title,
                        content=f"**Decision**: {d_title}\n\n**Status**: Approved\n**Source Session**: {session_id or 'ambient'}",
                        tags=["decision", "architecture", "phenom"],
                        wikilinks=["[[Decisions Index]]"]
                    ))
                    matched = True
                    break
            if matched:
                continue

            # Check Tasks
            for pat in task_patterns:
                m = re.match(pat, trimmed)
                if m:
                    t_title = m.group(1).strip()
                    # Check priority flag
                    priority = "normal"
                    if re.search(r"(?i)\[high|urgent|p0|critical\]", t_title):
                        priority = "high"
                    elif re.search(r"(?i)\[low|p2\]", t_title):
                        priority = "low"

                    extracted.append(CrystallizedItem(
                        note_type=NoteType.TASK,
                        title=f"Task - {t_title[:60]}",
                        summary=t_title,
                        content=f"- [ ] {t_title}\n\n**Priority**: {priority}\n**Created**: {datetime.now(timezone.utc).strftime('%Y-%m-%d')}",
                        tags=["task", f"priority-{priority}"],
                        metadata={"priority": priority},
                        wikilinks=["[[Tasks Index]]"]
                    ))
                    matched = True
                    break
            if matched:
                continue

            # Check Research
            for pat in research_patterns:
                m = re.match(pat, trimmed)
                if m:
                    r_title = m.group(1).strip()
                    extracted.append(CrystallizedItem(
                        note_type=NoteType.RESEARCH,
                        title=f"Research - {r_title[:60]}",
                        summary=r_title,
                        content=f"**Finding**: {r_title}\n\n**Verified**: Yes\n**Context**: Captured during Phenom execution session.",
                        tags=["research", "reference", "knowledge"],
                        wikilinks=["[[Knowledge Index]]"]
                    ))
                    matched = True
                    break

        # If text contains extensive multi-line code block or analysis without explicit tags,
        # extract as a general research note if substantive
        if not extracted and "```" in text and len(text.strip()) > 100:
            snippet_title = "Technical Code Reference"
            for line in lines:
                if line.strip().startswith("#"):
                    snippet_title = line.strip().lstrip("#").strip()[:60]
                    break
            extracted.append(CrystallizedItem(
                note_type=NoteType.RESEARCH,
                title=f"Research - {snippet_title}",
                summary=f"Technical code snippet from session {session_id or ''}",
                content=text.strip(),
                tags=["research", "code-snippet"],
                wikilinks=["[[Code Snippets]]"]
            ))

        return extracted

    def format_obsidian_note(self, item: CrystallizedItem) -> str:
        """
        Formats a CrystallizedItem into standard Obsidian Markdown with YAML frontmatter.
        """
        now_iso = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        tags_yaml = "\n".join(f"  - {tag}" for tag in item.tags) if item.tags else "  - second-brain"
        wikilinks_md = "\n".join(f"- {link}" for link in item.wikilinks) if item.wikilinks else "- [[Vault Home]]"

        return f"""---
title: "{item.title}"
date: {now_iso}
updated: {now_iso}
type: {item.note_type.value}
tags:
{tags_yaml}
status: active
---

# {item.title}

> [!NOTE] Summary
> {item.summary}

## Details
{item.content}

## Related Notes
{wikilinks_md}
"""

    def crystallize_session(
        self,
        items: List[CrystallizedItem],
        session_id: Optional[str] = None,
        update_daily_log: bool = True
    ) -> CrystallizationResult:
        """
        Writes extracted items into Obsidian vault notes with strict sandboxing and action logging.
        """
        sid = session_id or f"session-{uuid.uuid4().hex[:8]}"
        notes_written: List[str] = []
        undo_tokens: List[str] = []

        subfolder_map = {
            NoteType.DECISION: os.path.join("Notes", "Decisions"),
            NoteType.TASK: os.path.join("Notes", "Tasks"),
            NoteType.RESEARCH: os.path.join("Notes", "Research"),
            NoteType.DAILY_LOG: "Daily Logs"
        }

        for item in items:
            subfolder = subfolder_map.get(item.note_type, "Notes")
            clean_name = sanitize_filename(item.title) + ".md"
            rel_path = os.path.join(subfolder, clean_name)

            # Strict sandboxing validation
            target_path = resolve_and_sandbox_vault_path(rel_path, self.vault.vault_path)
            os.makedirs(os.path.dirname(target_path), exist_ok=True)

            # Capture pre-mutation state for reversible rollback
            existed = os.path.exists(target_path)
            prev_content = None
            if existed:
                try:
                    with open(target_path, "r", encoding="utf-8") as f:
                        prev_content = f.read()
                except Exception:
                    prev_content = None

            formatted_md = self.format_obsidian_note(item)

            with open(target_path, "w", encoding="utf-8") as f:
                f.write(formatted_md)

            notes_written.append(target_path)

            # Generate undo token and register in memory ledger
            u_token = f"undo-vault-{uuid.uuid4().hex}"
            self._undo_registry[u_token] = {
                "filepath": target_path,
                "existed": existed,
                "prev_content": prev_content,
                "mutation_type": "update" if existed else "create",
                "timestamp": time.time()
            }
            undo_tokens.append(u_token)

            # Log to Action Log with undo token
            action_log.log_action(
                tool="vault_crystallize",
                tier=1,
                args={"title": item.title, "path": target_path, "type": item.note_type.value},
                decision="auto",
                result_status="SUCCESS",
                undo_token=u_token,
                source="crystallizer"
            )

        daily_log_updated = False
        if update_daily_log and items:
            daily_token = self._append_session_to_daily_log(items, sid)
            if daily_token:
                undo_tokens.append(daily_token)
                daily_log_updated = True

        # Commit to vault git repository
        if notes_written:
            self.vault.commit_changes(f"crystallize: {len(notes_written)} notes from {sid}")

        return CrystallizationResult(
            session_id=sid,
            items_extracted=len(items),
            notes_written=notes_written,
            daily_log_updated=daily_log_updated,
            undo_tokens=undo_tokens,
            timestamp=time.time()
        )

    def _append_session_to_daily_log(self, items: List[CrystallizedItem], session_id: str) -> Optional[str]:
        """Appends a structured session crystallization briefing to today's Daily Log."""
        now = datetime.now()
        date_str = now.strftime("%Y-%m-%d")
        time_str = now.strftime("%H:%M:%S")

        daily_rel = os.path.join("Daily Logs", f"{date_str}.md")
        daily_path = resolve_and_sandbox_vault_path(daily_rel, self.vault.vault_path)
        os.makedirs(os.path.dirname(daily_path), exist_ok=True)

        existed = os.path.exists(daily_path)
        prev_content = None
        if existed:
            try:
                with open(daily_path, "r", encoding="utf-8") as f:
                    prev_content = f.read()
            except Exception:
                prev_content = None

        decisions = [it for it in items if it.note_type == NoteType.DECISION]
        tasks = [it for it in items if it.note_type == NoteType.TASK]
        research = [it for it in items if it.note_type == NoteType.RESEARCH]

        bullets = []
        for it in items:
            clean_t = sanitize_filename(it.title)
            bullets.append(f"  - [[{clean_t}]] ({it.note_type.value})")

        briefing = f"""

### [{time_str}] Session Crystallization ({session_id})
- **Summary**: Distilled {len(items)} items ({len(decisions)} decisions, {len(tasks)} tasks, {len(research)} research).
- **Notes Crystallized**:
{chr(10).join(bullets)}
"""

        if not existed:
            header = f"# Daily Log: {date_str}\n"
            content_to_write = header + briefing
        else:
            content_to_write = (prev_content or "") + briefing

        with open(daily_path, "w", encoding="utf-8") as f:
            f.write(content_to_write)

        # Register undo token for daily log modification
        daily_undo = f"undo-daily-{uuid.uuid4().hex}"
        self._undo_registry[daily_undo] = {
            "filepath": daily_path,
            "existed": existed,
            "prev_content": prev_content,
            "mutation_type": "update" if existed else "create",
            "timestamp": time.time()
        }

        action_log.log_action(
            tool="vault_daily_log_crystallize",
            tier=1,
            args={"session_id": session_id, "path": daily_path},
            decision="auto",
            result_status="SUCCESS",
            undo_token=daily_undo,
            source="crystallizer"
        )
        return daily_undo

    def rollback_vault_mutation(self, undo_token: str) -> Dict[str, Any]:
        """
        1-Click Reversible Rollback: Reverses a note creation, update, or daily log append
        using the stored undo token.
        """
        entry = self._undo_registry.get(undo_token)
        if not entry:
            raise ValueError(f"Undo token '{undo_token}' not found or already reverted.")

        filepath = entry["filepath"]
        existed = entry["existed"]
        prev_content = entry["prev_content"]

        # Sandbox check on target
        resolve_and_sandbox_vault_path(filepath, self.vault.vault_path)

        if not existed:
            # File was created from scratch -> delete it cleanly
            if os.path.exists(filepath):
                os.remove(filepath)
            status = "deleted"
        else:
            # File was modified -> restore previous content
            if prev_content is not None:
                with open(filepath, "w", encoding="utf-8") as f:
                    f.write(prev_content)
                status = "restored"
            else:
                status = "unmodified"

        # Remove from registry so it cannot be undone twice
        self._undo_registry.pop(undo_token, None)

        # Commit rollback to vault git repo
        self.vault.commit_changes(f"rollback: reverted mutation {undo_token}")

        action_log.log_action(
            tool="vault_rollback",
            tier=1,
            args={"undo_token": undo_token, "path": filepath, "status": status},
            decision="auto",
            result_status="SUCCESS",
            source="crystallizer"
        )

        return {
            "status": status,
            "filepath": filepath,
            "undo_token": undo_token
        }


# Global crystallizer instance
session_crystallizer = SessionCrystallizer()
