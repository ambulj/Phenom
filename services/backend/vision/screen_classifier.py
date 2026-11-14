"""
Phenom NEURAL-NEOCORTEX Screen Classifier & Local OCR Pipeline
Milestone 44.0: Project NEURAL-NEOCORTEX (Phase 2)

Key Capabilities:
1. Active Window Context Classification:
   Identifies window domain: RED_TEAM_TERMINAL, REVERSE_ENGINEERING, CODE_EDITOR, BROWSER, SENSITIVE_VAULT.
2. Structured OCR Bounding Box Extraction:
   Parses terminal text output into bounding boxes with confidence, screen coordinates,
   and integrated PII redaction via PrivacyMasker.
"""

from __future__ import annotations

import re
import time
from enum import Enum
from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field

from services.backend.vision.privacy_masker import privacy_masker


class WindowCategory(str, Enum):
    RED_TEAM_TERMINAL = "RED_TEAM_TERMINAL"
    REVERSE_ENGINEERING = "REVERSE_ENGINEERING"
    CODE_EDITOR = "CODE_EDITOR"
    BROWSER = "BROWSER"
    SENSITIVE_VAULT = "SENSITIVE_VAULT"
    GENERAL = "GENERAL"


class OCRBoundingBox(BaseModel):
    text: str
    confidence: float
    x: int
    y: int
    width: int
    height: int
    is_redacted: bool = False


class WindowClassificationResult(BaseModel):
    window_title: str
    process_name: str
    category: WindowCategory
    is_sensitive: bool
    is_terminal: bool
    detected_security_context: Optional[str] = None


class ScreenClassifier:
    """
    Classifies foreground windows and extracts privacy-redacted OCR blocks.
    """

    def classify_window(self, title: str, process_name: str) -> WindowClassificationResult:
        """Classifies foreground window process and title into semantic category."""
        proc = process_name.lower().strip()
        tit = title.lower().strip()

        # Check sensitive vault first
        is_sensitive = privacy_masker.is_sensitive_window(title, process_name)
        if is_sensitive:
            return WindowClassificationResult(
                window_title=title,
                process_name=process_name,
                category=WindowCategory.SENSITIVE_VAULT,
                is_sensitive=True,
                is_terminal=False,
                detected_security_context="Sensitive Vault / Password Manager",
            )

        # Check Red-Team Terminal
        is_term = any(t in proc for t in ["wsl", "powershell", "pwsh", "cmd", "bash", "terminal", "alacritty", "kitty"])
        if is_term or any(k in tit for k in ["kali", "root@", "nmap", "msfconsole", "powershell"]):
            sec_ctx = "Kali Linux WSL2 Environment" if "wsl" in proc or "kali" in tit else "Command Terminal"
            return WindowClassificationResult(
                window_title=title,
                process_name=process_name,
                category=WindowCategory.RED_TEAM_TERMINAL,
                is_sensitive=False,
                is_terminal=True,
                detected_security_context=sec_ctx,
            )

        # Check Reverse Engineering
        if any(r in proc for r in ["ghidra", "ida", "cutter", "rizin", "x64dbg", "wireshark"]):
            return WindowClassificationResult(
                window_title=title,
                process_name=process_name,
                category=WindowCategory.REVERSE_ENGINEERING,
                is_sensitive=False,
                is_terminal=False,
                detected_security_context="Binary Disassembly & Reverse Engineering",
            )

        # Check Code Editor
        if any(c in proc for c in ["code", "cursor", "pycharm", "sublime", "notepad++", "devenv"]):
            return WindowClassificationResult(
                window_title=title,
                process_name=process_name,
                category=WindowCategory.CODE_EDITOR,
                is_sensitive=False,
                is_terminal=False,
                detected_security_context="Source Code Development",
            )

        # Check Browser
        if any(b in proc for b in ["chrome", "firefox", "msedge", "brave", "opera"]):
            return WindowClassificationResult(
                window_title=title,
                process_name=process_name,
                category=WindowCategory.BROWSER,
                is_sensitive=False,
                is_terminal=False,
                detected_security_context="Web Browser Navigation",
            )

        return WindowClassificationResult(
            window_title=title,
            process_name=process_name,
            category=WindowCategory.GENERAL,
            is_sensitive=False,
            is_terminal=False,
            detected_security_context=None,
        )

    def extract_ocr_blocks(
        self,
        raw_text_lines: List[str],
        base_x: int = 50,
        base_y: int = 50,
        line_height: int = 24,
    ) -> List[OCRBoundingBox]:
        """
        Transforms raw terminal text lines into structured OCR bounding boxes with automatic PII masking.
        """
        boxes: List[OCRBoundingBox] = []

        for idx, line in enumerate(raw_text_lines):
            clean_line = line.strip()
            if not clean_line:
                continue

            # Run automated PII redactor (Rule 11)
            masked_text, red_count = privacy_masker.mask_pii_text(clean_line)

            y_pos = base_y + (idx * line_height)
            box_width = min(1200, len(masked_text) * 9 + 20)

            boxes.append(
                OCRBoundingBox(
                    text=masked_text,
                    confidence=0.98 if red_count == 0 else 0.99,
                    x=base_x,
                    y=y_pos,
                    width=box_width,
                    height=line_height,
                    is_redacted=red_count > 0,
                )
            )

        return boxes


# Singleton instance
screen_classifier = ScreenClassifier()
