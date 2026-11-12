"""
Phenom Obsidian Knowledge Tools (Milestone 18 - Phase 1)
Wraps ObsidianSyncEngine into formal Safety Engine ToolDefinitions:
- sync_obsidian_vault (Tier 0): Scans vault, updates in-RAM graph, returns index summary
- create_daily_debrief_note (Tier 1): Formulates and writes daily debrief note with diff preview
- query_vault_knowledge (Tier 0): Semantic and tag-based search over notes and wikilinks
"""

import os
from typing import List, Dict, Any, Optional
from datetime import datetime
from pydantic import BaseModel, Field

from services.backend.safety.registry import registry
from services.backend.safety.guardian import guardian
from services.backend.memory.obsidian_sync import obsidian_sync


class SyncObsidianVaultArgs(BaseModel):
    pass


@registry.register(
    name="sync_obsidian_vault",
    tier=0,
    description="Synchronize Obsidian markdown vault, parsing frontmatter YAML, wikilinks, and backlink knowledge graph",
    args_schema=SyncObsidianVaultArgs,
    preview_fn=lambda a: "Synchronize local Obsidian vault and update in-memory knowledge graph"
)
def sync_obsidian_vault() -> Dict[str, Any]:
    """Tier 0 tool to scan and index vault."""
    if guardian.is_halted:
        raise RuntimeError("Operation halted by Guardian Kill Switch")
    return obsidian_sync.sync_vault()


class CreateDailyDebriefNoteArgs(BaseModel):
    date: Optional[str] = Field(default=None, description="Date in YYYY-MM-DD format (defaults to today)")
    accomplishments: Optional[List[str]] = Field(default=None, description="List of completed tasks, goals, or milestones")
    metrics: Optional[Dict[str, Any]] = Field(default=None, description="System metrics, uptime, or memory stats")
    custom_notes: Optional[str] = Field(default=None, description="Additional executive markdown reflections or notes")
    cross_links: Optional[List[str]] = Field(default=None, description="Related note names to link using [[wikilinks]]")


def preview_daily_debrief_note(args: Dict[str, Any]) -> str:
    """Tier 1 preview generator for writing daily debrief note."""
    target_date = args.get("date") or datetime.now().strftime("%Y-%m-%d")
    target_path = os.path.join(obsidian_sync.daily_dir, f"{target_date}.md")
    exists = os.path.exists(target_path)
    file_state = "OVERWRITE_PREVIEW" if exists else "CREATE_NEW"

    acc_count = len(args.get("accomplishments") or [])
    links_count = len(args.get("cross_links") or [])
    return (
        f"[Tier 1] Write Daily Debrief Note: '{target_date}.md' [{file_state}] "
        f"(+{acc_count} accomplishments, {links_count} cross-links). Target: {target_path}"
    )


@registry.register(
    name="create_daily_debrief_note",
    tier=1,
    description="Formulate and save an executive daily debrief note in Obsidian vault with YAML frontmatter and wikilinks",
    args_schema=CreateDailyDebriefNoteArgs,
    preview_fn=preview_daily_debrief_note
)
def create_daily_debrief_note(
    date: Optional[str] = None,
    accomplishments: Optional[List[str]] = None,
    metrics: Optional[Dict[str, Any]] = None,
    custom_notes: Optional[str] = None,
    cross_links: Optional[List[str]] = None
) -> Dict[str, Any]:
    """
    Tier 1 tool writing daily debrief note with Rule 7 recycle bin protection.
    """
    if guardian.is_halted:
        raise RuntimeError("Operation halted by Guardian Kill Switch")

    res = obsidian_sync.create_daily_debrief(
        date_str=date,
        accomplishments=accomplishments,
        metrics=metrics,
        custom_notes=custom_notes,
        cross_links=cross_links
    )
    return {
        "status": "success",
        "action": "create_daily_debrief_note",
        "details": res
    }


class QueryVaultKnowledgeArgs(BaseModel):
    query: str = Field(default="", description="Search keywords for titles, headings, or content")
    tag: Optional[str] = Field(default=None, description="Optional tag filter, e.g. 'milestone18' or '#daily'")
    link_target: Optional[str] = Field(default=None, description="Optional wikilink target to find backlinks for")


@registry.register(
    name="query_vault_knowledge",
    tier=0,
    description="Query notes, tags, and wikilink graph from the Obsidian knowledge vault",
    args_schema=QueryVaultKnowledgeArgs,
    preview_fn=lambda a: f"Query Obsidian vault knowledge graph: '{a.get('query', '')}'" + (f" [tag: {a.get('tag')}]" if a.get('tag') else "")
)
def query_vault_knowledge(
    query: str = "",
    tag: Optional[str] = None,
    link_target: Optional[str] = None
) -> Dict[str, Any]:
    """Tier 0 search across in-RAM Obsidian vault knowledge index."""
    if guardian.is_halted:
        raise RuntimeError("Operation halted by Guardian Kill Switch")

    matches = obsidian_sync.query_vault(
        query=query,
        tag=tag,
        link_target=link_target
    )
    return {
        "status": "success",
        "query": query,
        "tag": tag,
        "link_target": link_target,
        "count": len(matches),
        "results": matches
    }
