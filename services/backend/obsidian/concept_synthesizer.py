"""
Structured Architectural Decision Record (ADR) & Concept Synthesis Engine.
Generates formalized Markdown notes with YAML frontmatter, taxonomy tags,
and bidirectional wikilinks across Developer and Research Obsidian vaults.

Part of Phenom 20.0 Sovereign Autonomous Developer (KNG-02.2).
"""

import datetime
import logging
import re
import time
from pathlib import Path
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field

from services.backend.obsidian.cross_vault_sync import CrossVaultManager, VaultNote, cross_vault_manager
from services.backend.safety.guardian import guardian

logger = logging.getLogger("phenom.obsidian.concept_synthesizer")


class ADRDraftRequest(BaseModel):
    title: str = Field(..., description="Short descriptive title of the architectural decision")
    context: str = Field(..., description="Problem description, technical constraints, and motivation")
    decision: str = Field(..., description="Chosen technical solution and implementation rationale")
    consequences: List[str] = Field(default_factory=list, description="List of positive, negative, and neutral trade-offs")
    status: str = Field(default="Accepted", description="Lifecycle status: Proposed, Accepted, Superseded, Deprecated")
    tags: List[str] = Field(default_factory=list, description="Topic and domain tags")
    related_notes: List[str] = Field(default_factory=list, description="Cross-vault wikilinks [[Target]]")


class ConceptDraftRequest(BaseModel):
    title: str = Field(..., description="Name of the technical concept or pattern")
    summary: str = Field(..., description="Executive summary and definition")
    mechanisms: str = Field(..., description="Detailed explanation of algorithms, structures, or rules")
    domain: str = Field(default="architecture", description="Domain: architecture, memory, safety, etc.")
    tags: List[str] = Field(default_factory=list, description="Categorization tags")
    related_notes: List[str] = Field(default_factory=list, description="Cross-vault wikilinks [[Target]]")


class ConceptSynthesizer:
    """
    Synthesizes and writes structured ADR and concept notes into Obsidian vaults.
    """

    def __init__(self, manager: Optional[CrossVaultManager] = None):
        self.manager = manager or cross_vault_manager

    def create_adr(self, req: ADRDraftRequest) -> VaultNote:
        """
        Creates an ADR note in the Developer Vault with full frontmatter and wikilinks.
        """
        if guardian.is_halted:
            raise PermissionError("Guardian kill switch is active. ADR creation halted.")

        dev_vault = self.manager.vaults.get("dev")
        if not dev_vault:
            raise ValueError("Developer vault is not registered.")

        dev_vault.mkdir(parents=True, exist_ok=True)

        # Calculate next ADR number
        existing_adrs = list(dev_vault.glob("ADR-*.md"))
        highest_num = 0
        for adr_path in existing_adrs:
            m = re.match(r"ADR-(\d+)", adr_path.name)
            if m:
                highest_num = max(highest_num, int(m.group(1)))
        next_num = highest_num + 1

        clean_slug = re.sub(r"[^a-zA-Z0-9_\-]+", "_", req.title.lower()).strip("_")
        file_name = f"ADR-{next_num:03d}_{clean_slug}.md"
        target_path = dev_vault / file_name

        today_str = datetime.date.today().isoformat()
        all_tags = sorted(list(set(["adr", "architecture"] + [t.lstrip("#") for t in req.tags])))

        # Format frontmatter
        fm_lines = [
            "---",
            f"title: 'ADR-{next_num:03d}: {req.title}'",
            f"status: '{req.status}'",
            f"date: '{today_str}'",
            "tags:",
        ]
        for t in all_tags:
            fm_lines.append(f"  - {t}")
        if req.related_notes:
            fm_lines.append("related_notes:")
            for rn in req.related_notes:
                clean_link = rn.strip("[]")
                fm_lines.append(f"  - '[[{clean_link}]]'")
        fm_lines.append("---")

        # Format markdown body
        consequences_formatted = "\n".join(f"- {c}" for c in req.consequences) if req.consequences else "- No negative consequences identified."
        related_formatted = "\n".join(f"- [[{rn.strip('[]')}]]" for rn in req.related_notes) if req.related_notes else "- No linked notes."

        body_lines = [
            "\n".join(fm_lines),
            "",
            f"# ADR-{next_num:03d}: {req.title}",
            "",
            "## Status",
            req.status,
            "",
            "## Context",
            req.context.strip(),
            "",
            "## Decision",
            req.decision.strip(),
            "",
            "## Consequences & Trade-Offs",
            consequences_formatted,
            "",
            "## References & Cross-Vault Links",
            related_formatted,
            "",
        ]

        full_content = "\n".join(body_lines)
        target_path.write_text(full_content, encoding="utf-8")

        # Refresh index
        note = self.manager.parse_note("dev", target_path)
        if note:
            self.manager.sync_all_vaults()
            return note
        raise RuntimeError("Failed to parse newly created ADR note.")

    def create_concept_note(self, req: ConceptDraftRequest) -> VaultNote:
        """
        Creates a technical concept synthesis note in the Research Vault.
        """
        if guardian.is_halted:
            raise PermissionError("Guardian kill switch is active. Concept creation halted.")

        research_vault = self.manager.vaults.get("research")
        if not research_vault:
            raise ValueError("Research vault is not registered.")

        research_vault.mkdir(parents=True, exist_ok=True)

        clean_slug = re.sub(r"[^a-zA-Z0-9_\-]+", "_", req.title.lower()).strip("_")
        file_name = f"{clean_slug}.md"
        target_path = research_vault / file_name

        today_str = datetime.date.today().isoformat()
        all_tags = sorted(list(set(["concept", req.domain] + [t.lstrip("#") for t in req.tags])))

        fm_lines = [
            "---",
            f"title: '{req.title}'",
            f"domain: '{req.domain}'",
            f"date: '{today_str}'",
            "tags:",
        ]
        for t in all_tags:
            fm_lines.append(f"  - {t}")
        if req.related_notes:
            fm_lines.append("related_notes:")
            for rn in req.related_notes:
                clean_link = rn.strip("[]")
                fm_lines.append(f"  - '[[{clean_link}]]'")
        fm_lines.append("---")

        related_formatted = "\n".join(f"- [[{rn.strip('[]')}]]" for rn in req.related_notes) if req.related_notes else "- No linked notes."

        body_lines = [
            "\n".join(fm_lines),
            "",
            f"# {req.title}",
            "",
            "## Overview & Definition",
            req.summary.strip(),
            "",
            "## Core Mechanisms & Architecture",
            req.mechanisms.strip(),
            "",
            "## Cross-Vault Linkage",
            related_formatted,
            "",
        ]

        full_content = "\n".join(body_lines)
        target_path.write_text(full_content, encoding="utf-8")

        note = self.manager.parse_note("research", target_path)
        if note:
            self.manager.sync_all_vaults()
            return note
        raise RuntimeError("Failed to parse newly created concept note.")


# Global singleton
concept_synthesizer = ConceptSynthesizer()
