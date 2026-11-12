"""
Unit & Integration Test Suite for Phenom 6.0 Phase 3:
Deep Obsidian Second-Brain Knowledge Graph Co-Pilot

Verifies:
1. Bidirectional Graph Indexer: Parses [[wikilinks]], #tags, YAML frontmatter, backlinks.
2. Graph Analytics: Detects orphan notes and hub notes.
3. Subgraph Traversal: Neighborhood expansion across directed graph edges.
4. Unlinked Mention Suggestions: Discovers plain text mentions of vault notes.
5. 1-Click Reversible Link Insertion: Inserts [[wikilinks]], commits to git, rolls back with undo_token.
6. Grounded Topic Synthesis: Multihop note context with citations.
7. Safety Registry Integration: Tier 0 and Tier 1 tool definitions and schemas.
"""

import os
import shutil
import tempfile
import pytest
from typing import Dict, Any, List

from services.backend.memory.graph_index import ObsidianGraphIndex
from services.backend.memory.graph_copilot import ObsidianGraphCoPilot
from services.backend.memory.vault import ObsidianVaultManager
from services.backend.memory.crystallizer import SessionCrystallizer
from services.backend.safety.registry import registry
from services.backend.tools.obsidian_graph_tools import (
    query_obsidian_graph, find_orphan_notes, synthesize_vault_topic, link_vault_notes
)


@pytest.fixture
def test_vault():
    """Sets up a temporary git-initialized Obsidian vault with interconnected notes."""
    tmp_dir = tempfile.mkdtemp(prefix="phenom_test_vault_")
    vault = ObsidianVaultManager(vault_path=tmp_dir)

    # Note 1: Architecture
    vault.write_note(
        title="Architecture",
        content="""---
tags: [system, architecture]
aliases: [System Design]
---

Phenom 6.0 core architecture incorporates [[Visual Memory]] and [[Autonomous Swarm]].
""",
        subfolder="Notes"
    )

    # Note 2: Visual Memory
    vault.write_note(
        title="Visual Memory",
        content="""---
tags: [vision, cuda]
---

Continuous screen capture in RAM linked to [[Local Embeddings]].
""",
        subfolder="Notes"
    )

    # Note 3: Autonomous Swarm
    vault.write_note(
        title="Autonomous Swarm",
        content="""---
tags: [workers, automation]
---

Parallel headless browser workers and subprocess runners. Mentions Visual Memory frequently.
""",
        subfolder="Notes"
    )

    # Note 4: Orphan Note (Disconnected)
    vault.write_note(
        title="Secret Ideas",
        content="""---
tags: [ideas]
---

An unlinked standalone brainstorming note.
""",
        subfolder="Notes"
    )

    vault.commit_changes("init test vault notes")

    yield tmp_dir, vault

    # Teardown
    shutil.rmtree(tmp_dir, ignore_errors=True)


# ==============================================================================
# TEST 1: Bidirectional Graph Indexer & Frontmatter Parsing
# ==============================================================================

def test_obsidian_graph_indexer(test_vault):
    tmp_dir, vault = test_vault
    index = ObsidianGraphIndex(vault_path=tmp_dir)
    stats = index.build_index()

    assert stats["total_notes"] == 4
    assert stats["total_links"] >= 2
    assert stats["orphans_count"] >= 1

    # Check Architecture node
    node_arch = index.get_node("Architecture")
    assert node_arch is not None
    assert "Visual Memory" in node_arch.links_out
    assert "Autonomous Swarm" in node_arch.links_out
    assert "system" in node_arch.tags
    assert "architecture" in node_arch.tags
    assert "System Design" in node_arch.aliases

    # Check Backlinks: Visual Memory should have Architecture as backlink
    node_vis = index.get_node("Visual Memory")
    assert node_vis is not None
    assert "Architecture" in node_vis.links_in

    # Check Orphan detection: Secret Ideas is an orphan
    orphans = index.get_orphans()
    orphan_titles = [o["title"] for o in orphans]
    assert "Secret Ideas" in orphan_titles


# ==============================================================================
# TEST 2: Subgraph Traversal & Hub Ranking
# ==============================================================================

def test_subgraph_traversal_and_hubs(test_vault):
    tmp_dir, vault = test_vault
    index = ObsidianGraphIndex(vault_path=tmp_dir)
    index.build_index()

    # 1-hop subgraph around Architecture
    subgraph = index.get_connected_subgraph("Architecture", hops=1)
    node_titles = [n["title"] for n in subgraph["nodes"]]
    assert "Architecture" in node_titles
    assert "Visual Memory" in node_titles
    assert "Autonomous Swarm" in node_titles
    assert "Secret Ideas" not in node_titles  # Orphan not in 1-hop neighborhood

    # Concept Hubs
    hubs = index.get_concept_hubs(top_k=2)
    assert len(hubs) >= 1
    assert hubs[0]["title"] in ("Architecture", "Visual Memory")


# ==============================================================================
# TEST 3: Unlinked Mention Discovery
# ==============================================================================

def test_suggest_unlinked_mentions(test_vault):
    tmp_dir, vault = test_vault
    index = ObsidianGraphIndex(vault_path=tmp_dir)
    copilot = ObsidianGraphCoPilot(vault=vault, graph_idx=index)

    # Autonomous Swarm text mentions "Visual Memory" without [[...]]
    suggestions = copilot.suggest_unlinked_mentions("Autonomous Swarm")
    assert len(suggestions) >= 1
    assert any(s["target_note"] == "Visual Memory" for s in suggestions)


# ==============================================================================
# TEST 4: Reversible Link Insertion & Git Commit Rollback
# ==============================================================================

def test_reversible_link_notes_and_rollback(test_vault):
    tmp_dir, vault = test_vault
    index = ObsidianGraphIndex(vault_path=tmp_dir)
    crystallizer = SessionCrystallizer(vault_inst=vault)
    copilot = ObsidianGraphCoPilot(vault=vault, graph_idx=index, crystallizer=crystallizer)

    # 1. Connect Autonomous Swarm -> Secret Ideas
    res_link = copilot.link_notes(
        source_note="Autonomous Swarm",
        target_note="Secret Ideas"
    )
    assert res_link["status"] == "linked"
    undo_token = res_link["undo_token"]
    assert undo_token is not None

    # Verify link is now present in the file
    content_after = vault.read_note("Autonomous Swarm")
    assert "[[Secret Ideas]]" in content_after

    # Verify graph index now recognizes the new link
    index.build_index()
    assert "Secret Ideas" in index.get_forward_links("Autonomous Swarm")
    assert "Autonomous Swarm" in index.get_backlinks("Secret Ideas")

    # 2. Reversible Rollback using undo_token
    rollback_res = crystallizer.rollback_vault_mutation(undo_token)
    assert rollback_res["status"] == "restored"

    # Verify file reverted to original state without link
    content_reverted = vault.read_note("Autonomous Swarm")
    assert "[[Secret Ideas]]" not in content_reverted


# ==============================================================================
# TEST 5: Vault-Grounded Conversational Topic Synthesis
# ==============================================================================

def test_topic_synthesis(test_vault):
    tmp_dir, vault = test_vault
    index = ObsidianGraphIndex(vault_path=tmp_dir)
    copilot = ObsidianGraphCoPilot(vault=vault, graph_idx=index)

    res = copilot.synthesize_topic("architecture of visual memory")
    assert res["status"] == "success"
    assert "synthesis" in res
    assert len(res["citations"]) >= 1
    assert "[[Architecture]]" in res["synthesis"] or "[[Visual Memory]]" in res["synthesis"]


# ==============================================================================
# TEST 6: Safety Registry Integration
# ==============================================================================

def test_obsidian_graph_tools_registration():
    # Verify Tier 0 tools
    q_entry = registry.get("query_obsidian_graph")
    assert q_entry is not None
    assert q_entry.tier == 0

    orphans_entry = registry.get("find_orphan_notes")
    assert orphans_entry is not None
    assert orphans_entry.tier == 0

    synth_entry = registry.get("synthesize_vault_topic")
    assert synth_entry is not None
    assert synth_entry.tier == 0

    # Verify Tier 1 tool
    link_entry = registry.get("link_vault_notes")
    assert link_entry is not None
    assert link_entry.tier == 1
    assert link_entry.preview_fn is not None
