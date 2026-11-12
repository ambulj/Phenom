"""
Phenom Obsidian Knowledge Graph Tools
Provides tool endpoints for querying vault graph topology, finding orphan notes,
synthesizing multi-note topics, and linking notes with 1-click reversible rollbacks.
Strictly respects SAFETY.md:
- query_obsidian_graph (Tier 0): Read-only graph query.
- find_orphan_notes (Tier 0): Read-only orphan note discovery.
- synthesize_vault_topic (Tier 0): Read-only knowledge synthesis.
- link_vault_notes (Tier 1): Requires interactive preview confirmation.
"""

from typing import Dict, Any, Optional, List
from pydantic import BaseModel, Field

from services.backend.safety.registry import registry
from services.backend.memory.graph_index import graph_index
from services.backend.memory.graph_copilot import graph_copilot


class QueryObsidianGraphArgs(BaseModel):
    note_title: str = Field(
        description="Title or filename of the note to query in the Obsidian graph"
    )
    hops: int = Field(
        default=1,
        description="Graph traversal depth (1 = direct neighbors, 2 = 2-hop neighborhood)"
    )


class FindOrphanNotesArgs(BaseModel):
    limit: int = Field(
        default=10,
        description="Maximum number of orphan notes to return"
    )


class SynthesizeVaultTopicArgs(BaseModel):
    query: str = Field(
        description="Topic or research question to synthesize across the Obsidian second brain"
    )
    limit_notes: int = Field(
        default=4,
        description="Maximum number of core notes to aggregate into the synthesis"
    )


class LinkVaultNotesArgs(BaseModel):
    source_note: str = Field(
        description="Title of the note in which to insert the wikilink"
    )
    target_note: str = Field(
        description="Title of the target note being linked to"
    )
    anchor_text: Optional[str] = Field(
        default=None,
        description="Optional unlinked text within source note to replace with [[target_note]]"
    )


@registry.register(
    name="query_obsidian_graph",
    tier=0,
    description="Inspects the Obsidian knowledge graph around a note, returning forward links, backlinks, and connected nodes. Read-only.",
    args_schema=QueryObsidianGraphArgs,
    preview_fn=lambda a: f"Query knowledge graph around '[[{a.get('note_title')}]]' (Read-only)"
)
def query_obsidian_graph(note_title: str, hops: int = 1) -> Dict[str, Any]:
    """Returns local connected subgraph around note_title."""
    graph_index.build_index()
    subgraph = graph_index.get_connected_subgraph(note_title, hops=hops)
    backlinks = graph_index.get_backlinks(note_title)
    forward_links = graph_index.get_forward_links(note_title)

    return {
        "status": "success",
        "note_title": note_title,
        "backlinks": backlinks,
        "forward_links": forward_links,
        "subgraph": subgraph
    }


@registry.register(
    name="find_orphan_notes",
    tier=0,
    description="Discovers isolated 'orphan' notes in the Obsidian vault that have zero forward links and zero backlinks. Read-only.",
    args_schema=FindOrphanNotesArgs,
    preview_fn=lambda a: "Scan vault for orphan notes (Read-only)"
)
def find_orphan_notes(limit: int = 10) -> Dict[str, Any]:
    """Returns disconnected notes in the second-brain vault."""
    graph_index.build_index()
    orphans = graph_index.get_orphans()
    return {
        "status": "success",
        "total_orphans": len(orphans),
        "orphans": orphans[:limit],
        "message": f"Found {len(orphans)} orphan note(s) needing connection."
    }


@registry.register(
    name="synthesize_vault_topic",
    tier=0,
    description="Synthesizes personal insights, decisions, and research across multiple connected vault notes for a query. Read-only.",
    args_schema=SynthesizeVaultTopicArgs,
    preview_fn=lambda a: f"Synthesize second-brain knowledge for topic: '{a.get('query')}' (Read-only)"
)
def synthesize_vault_topic(query: str, limit_notes: int = 4) -> Dict[str, Any]:
    """Synthesizes insights across relevant notes with wikilink citations."""
    return graph_copilot.synthesize_topic(query, limit_notes=limit_notes)


@registry.register(
    name="link_vault_notes",
    tier=1,
    description="Connects two notes in the Obsidian vault with a [[wikilink]], creates a 1-click reversible undo token, and commits changes to git.",
    args_schema=LinkVaultNotesArgs,
    preview_fn=lambda a: f"Insert [[{a.get('target_note')}]] into note '{a.get('source_note')}' (Reversible Git commit)"
)
def link_vault_notes(
    source_note: str,
    target_note: str,
    anchor_text: Optional[str] = None
) -> Dict[str, Any]:
    """Inserts a wikilink connecting source and target notes."""
    return graph_copilot.link_notes(
        source_note=source_note,
        target_note=target_note,
        anchor_text=anchor_text
    )
