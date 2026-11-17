"""Contextual Semantic Anchor for Desktop Application Context (Milestone 51 Phase 4).

Maps active foreground windows, process executables, and window titles to semantic
workspaces, active project files, and application categories (REFLEX-04.1).
"""

from __future__ import annotations

import re
import time
from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field

from services.backend.schemas.semantic_focus import WindowContext
from services.backend.desktop.window_focus_tracker import WindowFocusTracker


class ApplicationCategory(str, Enum):
    """Categorical classification of foreground applications."""
    IDE = "IDE"
    TERMINAL = "TERMINAL"
    BROWSER = "BROWSER"
    OFFICE_DOCUMENT = "OFFICE_DOCUMENT"
    COMMUNICATION = "COMMUNICATION"
    OTHER = "OTHER"


class ActiveContextAnchor(BaseModel):
    """Semantic anchor representing the operator's current active workspace."""
    hwnd: int = Field(default=0, description="Foreground window handle")
    window_title: str = Field(default="", description="Window title text")
    process_name: str = Field(default="", description="Executable name")
    app_category: ApplicationCategory = Field(default=ApplicationCategory.OTHER)
    project_name: Optional[str] = Field(default=None, description="Identified project or workspace")
    active_file: Optional[str] = Field(default=None, description="Active editing file if in IDE")
    timestamp: float = Field(default_factory=time.time)
    metadata: Dict[str, Any] = Field(default_factory=dict)


class ContextualAnchorManager:
    """Resolves and correlates active desktop context with project workspaces."""

    # Process name to category mappings
    CATEGORY_MAPPINGS: Dict[ApplicationCategory, List[str]] = {
        ApplicationCategory.IDE: ["code.exe", "cursor.exe", "devenv.exe", "pycharm64.exe", "idea64.exe", "sublime_text.exe"],
        ApplicationCategory.TERMINAL: ["windowsterminal.exe", "powershell.exe", "pwsh.exe", "cmd.exe", "bash.exe", "alacritty.exe"],
        ApplicationCategory.BROWSER: ["chrome.exe", "msedge.exe", "firefox.exe", "brave.exe", "opera.exe"],
        ApplicationCategory.OFFICE_DOCUMENT: ["winword.exe", "excel.exe", "powerpnt.exe", "acrobat.exe"],
        ApplicationCategory.COMMUNICATION: ["telegram.exe", "slack.exe", "discord.exe", "teams.exe", "outlook.exe"],
    }

    def __init__(self, tracker: Optional[WindowFocusTracker] = None) -> None:
        self.tracker = tracker or WindowFocusTracker()

    def categorize_process(self, process_name: str) -> ApplicationCategory:
        """Classifies process executable into an ApplicationCategory."""
        proc_lower = process_name.lower()
        for cat, procs in self.CATEGORY_MAPPINGS.items():
            if any(p in proc_lower for p in procs):
                return cat
        return ApplicationCategory.OTHER

    def parse_ide_title(self, title: str) -> Tuple[Optional[str], Optional[str]]:
        """Extracts active file name and project name from IDE window titles.
        
        Examples:
        - "main.py - Phenom - Visual Studio Code" -> ("main.py", "Phenom")
        - "App.tsx • Phenom - Visual Studio Code" -> ("App.tsx", "Phenom")
        """
        parts = [p.strip() for p in re.split(r"[\-•|]", title) if p.strip()]

        active_file: Optional[str] = None
        project_name: Optional[str] = None

        if len(parts) >= 2:
            first = parts[0]
            if re.search(r"\.[a-zA-Z0-9]{1,5}$", first):
                active_file = first
            if len(parts) >= 3:
                project_name = parts[1]
            elif not active_file:
                project_name = parts[0]

        return active_file, project_name

    def resolve_anchor(self, window_context: Optional[WindowContext] = None) -> ActiveContextAnchor:
        """Resolves the current ActiveContextAnchor from live or provided WindowContext."""
        ctx = window_context or self.tracker.get_active_window()
        category = self.categorize_process(ctx.process_name)

        active_file: Optional[str] = None
        project_name: Optional[str] = None

        if category == ApplicationCategory.IDE:
            active_file, project_name = self.parse_ide_title(ctx.title)
        elif category == ApplicationCategory.TERMINAL:
            # Check if directory path is in title
            dir_match = re.search(r"([A-Za-z]:\\[^:\*\?\"<>\|]+)", ctx.title)
            if dir_match:
                project_name = dir_match.group(1).split("\\")[-1]

        return ActiveContextAnchor(
            hwnd=ctx.hwnd,
            window_title=ctx.title,
            process_name=ctx.process_name,
            app_category=category,
            project_name=project_name,
            active_file=active_file,
            timestamp=time.time(),
            metadata={"pid": ctx.pid},
        )
