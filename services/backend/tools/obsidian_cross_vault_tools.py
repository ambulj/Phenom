"""
Safety-Wrapped Cross-Vault Obsidian Knowledge Tools.
Registers tools with ToolRegistry for multi-vault synchronization, ADR generation,
and concept synthesis with bidirectional wikilinks (Phase 20-04 KNG-02.1 / KNG-02.2).
"""

from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field

from services.backend.safety.registry import registry
from services.backend.obsidian.cross_vault_sync import cross_vault_manager
from services.backend.obsidian.concept_synthesizer import concept_synthesizer, ADRDraftRequest, ConceptDraftRequest


# ==========================================
# 1. Sync Cross Vaults (Tier 0)
# ==========================================

class SyncCrossVaultsArgs(BaseModel):
    pass

def sync_cross_vaults_preview(args: Dict[str, Any]) -> str:
    return "Synchronize and index all configured Obsidian vaults (Developer, Research, Daily) into the unified cross-vault link graph."

@registry.register(
    name="sync_cross_vaults",
    tier=0,
    description="Indexes all Obsidian vaults and builds a unified bidirectional wikilink graph.",
    args_schema=SyncCrossVaultsArgs,
    preview_fn=sync_cross_vaults_preview,
    can_remember_per_folder=False
)
def handle_sync_cross_vaults() -> Dict[str, Any]:
    graph = cross_vault_manager.sync_all_vaults()
    return {
        "total_notes": graph.total_notes,
        "total_links": graph.total_links,
        "taxonomy_tags_count": len(graph.tag_taxonomy),
    }


# ==========================================
# 2. Generate Architectural Decision Record (Tier 1)
# ==========================================

class GenerateADRArgs(BaseModel):
    title: str = Field(..., description="Title of the architectural decision record.")
    context: str = Field(..., description="Context, motivation, and problem statement.")
    decision: str = Field(..., description="Technical decision and justification.")
    consequences: Optional[List[str]] = Field(default_factory=list, description="Trade-offs and outcomes.")
    related_notes: Optional[List[str]] = Field(default_factory=list, description="Wikilinks to related notes [[Target]].")
    tags: Optional[List[str]] = Field(default_factory=list, description="Tags for categorization.")
    status: Optional[str] = Field(default="Accepted", description="ADR status: Proposed, Accepted, Superseded.")

def generate_adr_preview(args: Dict[str, Any]) -> str:
    title = args.get("title", "")
    return f"Generate Architectural Decision Record (ADR) '{title}' in Developer Obsidian Vault."

@registry.register(
    name="generate_architectural_decision_record",
    tier=1,
    description="Generates a structured Architectural Decision Record note in the Developer Obsidian Vault.",
    args_schema=GenerateADRArgs,
    preview_fn=generate_adr_preview,
    can_remember_per_folder=False
)
def handle_generate_adr(
    title: str,
    context: str,
    decision: str,
    consequences: Optional[List[str]] = None,
    related_notes: Optional[List[str]] = None,
    tags: Optional[List[str]] = None,
    status: str = "Accepted"
) -> Dict[str, Any]:
    req = ADRDraftRequest(
        title=title,
        context=context,
        decision=decision,
        consequences=consequences or [],
        related_notes=related_notes or [],
        tags=tags or [],
        status=status,
    )
    note = concept_synthesizer.create_adr(req)
    return note.model_dump()


# ==========================================
# 3. Synthesize Concept Note (Tier 1)
# ==========================================

class SynthesizeConceptNoteArgs(BaseModel):
    title: str = Field(..., description="Title of the concept or pattern.")
    summary: str = Field(..., description="Executive definition and summary.")
    mechanisms: str = Field(..., description="Mechanisms, algorithms, and components.")
    domain: Optional[str] = Field(default="architecture", description="Domain classification.")
    related_notes: Optional[List[str]] = Field(default_factory=list, description="Wikilinks to related notes [[Target]].")
    tags: Optional[List[str]] = Field(default_factory=list, description="Categorization tags.")

def synthesize_concept_note_preview(args: Dict[str, Any]) -> str:
    title = args.get("title", "")
    return f"Synthesize concept note '{title}' in Research Obsidian Vault with bidirectional wikilinks."

@registry.register(
    name="synthesize_concept_note",
    tier=1,
    description="Synthesizes and writes a structured concept note into the Research Obsidian Vault.",
    args_schema=SynthesizeConceptNoteArgs,
    preview_fn=synthesize_concept_note_preview,
    can_remember_per_folder=False
)
def handle_synthesize_concept_note(
    title: str,
    summary: str,
    mechanisms: str,
    domain: str = "architecture",
    related_notes: Optional[List[str]] = None,
    tags: Optional[List[str]] = None
) -> Dict[str, Any]:
    req = ConceptDraftRequest(
        title=title,
        summary=summary,
        mechanisms=mechanisms,
        domain=domain,
        related_notes=related_notes or [],
        tags=tags or [],
    )
    note = concept_synthesizer.create_concept_note(req)
    return note.model_dump()


# ==========================================
# 4. Query Cross Vault Graph (Tier 0)
# ==========================================

class QueryCrossVaultGraphArgs(BaseModel):
    query: Optional[str] = Field(default="", description="Search query string.")
    vault: Optional[str] = Field(default=None, description="Filter by vault name: dev, research, daily.")
    tag: Optional[str] = Field(default=None, description="Filter by tag.")
    limit: Optional[int] = Field(default=60, description="Max nodes to return for visual payload.")

def query_cross_vault_graph_preview(args: Dict[str, Any]) -> str:
    q = args.get("query", "")
    v = args.get("vault", "all vaults")
    return f"Query cross-vault knowledge graph for '{q}' in {v}."

@registry.register(
    name="query_cross_vault_graph",
    tier=0,
    description="Queries notes, tags, and returns formatted node-link data for graph visualization.",
    args_schema=QueryCrossVaultGraphArgs,
    preview_fn=query_cross_vault_graph_preview,
    can_remember_per_folder=False
)
def handle_query_cross_vault_graph(
    query: str = "",
    vault: Optional[str] = None,
    tag: Optional[str] = None,
    limit: int = 60
) -> Dict[str, Any]:
    notes = cross_vault_manager.search_graph(query=query, vault=vault, tag=tag)
    viz_data = cross_vault_manager.get_visualization_data(limit=limit)
    return {
        "matched_notes_count": len(notes),
        "notes": [n.model_dump() for n in notes[:20]],
        "visualization": viz_data,
    }
