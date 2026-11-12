"""
Phenom Obsidian Knowledge Graph Co-Pilot
Provides grounded conversational topic synthesis, link recommendations for unlinked mentions,
and 1-click reversible link insertion into the Obsidian second brain.
Strictly respects vault sandboxing and generates git commits on every mutation.
"""

import os
import re
import uuid
import time
import logging
from typing import Dict, Any, List, Optional, Tuple, Set

from services.backend.memory.vault import vault_manager, resolve_and_sandbox_vault_path, ObsidianVaultManager
from services.backend.memory.graph_index import ObsidianGraphIndex, graph_index as default_graph_index
from services.backend.memory.embeddings import LocalEmbeddingPipeline, embedding_pipeline as default_embedding_pipeline
from services.backend.memory.crystallizer import session_crystallizer, SessionCrystallizer
from services.backend.safety.action_log import action_log

logger = logging.getLogger("phenom.graph_copilot")


class ObsidianGraphCoPilot:
    """
    Cognitive assistant operating on the Obsidian second brain knowledge graph.
    """

    def __init__(
        self,
        vault: Optional[ObsidianVaultManager] = None,
        graph_idx: Optional[ObsidianGraphIndex] = None,
        embed_pipe: Optional[LocalEmbeddingPipeline] = None,
        crystallizer: Optional[SessionCrystallizer] = None
    ):
        self.vault = vault or vault_manager
        self.graph_index = graph_idx or default_graph_index
        self.embedding_pipeline = embed_pipe or default_embedding_pipeline
        self.crystallizer = crystallizer or session_crystallizer

    def synthesize_topic(self, query: str, limit_notes: int = 4) -> Dict[str, Any]:
        """
        Synthesizes insights across relevant notes and connected neighbors in the knowledge graph.
        Returns grounded answer with [[wikilink]] citations.
        """
        self.graph_index.build_index()
        nodes = list(self.graph_index.nodes.values())
        if not nodes:
            return {
                "query": query,
                "status": "empty_vault",
                "message": "Obsidian vault is currently empty.",
                "citations": []
            }

        # 1. Score note relevance via local vector embeddings
        query_vec = self.embedding_pipeline.embed_query(query)
        scored_nodes: List[Tuple[float, Any]] = []

        for node in nodes:
            # Read first 1000 characters for embedding representation
            note_path = resolve_and_sandbox_vault_path(node.rel_path, self.vault.vault_path)
            try:
                with open(note_path, "r", encoding="utf-8", errors="replace") as f:
                    snippet = f.read(1200)
            except Exception:
                snippet = node.title

            text_to_embed = f"{node.title}\n{' '.join(node.tags)}\n{snippet}"
            node_vec = self.embedding_pipeline.embed_query(text_to_embed)
            score = float(np_dot_similarity(query_vec, node_vec))
            scored_nodes.append((score, node))

        scored_nodes.sort(key=lambda x: x[0], reverse=True)
        top_candidates = [n for s, n in scored_nodes[:limit_notes]]

        # 2. Expand subgraph context: collect forward links and backlinks
        connected_titles: Set[str] = set()
        citations: List[Dict[str, Any]] = []
        synthesized_snippets: List[str] = []

        for node in top_candidates:
            connected_titles.add(node.title)
            connected_titles.update(node.links_out)
            connected_titles.update(node.links_in)

            note_path = resolve_and_sandbox_vault_path(node.rel_path, self.vault.vault_path)
            try:
                with open(note_path, "r", encoding="utf-8", errors="replace") as f:
                    content = f.read()
            except Exception:
                content = ""

            # Extract first section/summary
            lines = [l.strip() for l in content.splitlines() if l.strip() and not l.startswith("---") and not l.startswith("title:")]
            summary_part = " ".join(lines[:6]) if lines else "No text content."

            citations.append({
                "title": node.title,
                "rel_path": node.rel_path,
                "tags": sorted(list(node.tags)),
                "links_count": len(node.links_out) + len(node.links_in)
            })

            synthesized_snippets.append(f"• **[[{node.title}]]**: {summary_part[:300]}")

        # 3. Assemble Grounded Synthesis
        synthesis_text = (
            f"### Knowledge Synthesis for: '{query}'\n\n"
            f"Based on your Obsidian second-brain knowledge graph, the primary related concepts are:\n\n"
            + "\n\n".join(synthesized_snippets)
            + f"\n\n**Connected Concept Network**: {', '.join([f'[[{t}]]' for t in sorted(list(connected_titles))[:8]])}"
        )

        return {
            "query": query,
            "status": "success",
            "synthesis": synthesis_text,
            "citations": citations,
            "connected_graph_nodes": sorted(list(connected_titles))
        }

    def suggest_unlinked_mentions(self, note_title: str) -> List[Dict[str, Any]]:
        """
        Scans a note for unlinked mentions of other notes in the vault.
        Returns candidates for [[wikilink]] connection.
        """
        self.graph_index.build_index()
        target_node = self.graph_index.get_node(note_title)
        if not target_node:
            return []

        note_path = resolve_and_sandbox_vault_path(target_node.rel_path, self.vault.vault_path)
        try:
            with open(note_path, "r", encoding="utf-8", errors="replace") as f:
                content = f.read()
        except Exception:
            return []

        # Find existing links so we don't re-suggest them
        existing_links = set(l.lower() for l in target_node.links_out)
        existing_links.add(target_node.title.lower())

        suggestions = []
        for other_title, other_node in self.graph_index.nodes.items():
            if other_title in existing_links:
                continue

            # Check if other note's title appears as a whole word in content
            name_pattern = re.compile(rf"\b{re.escape(other_node.title)}\b", re.IGNORECASE)
            match = name_pattern.search(content)

            # Ensure it is not already inside a [[wikilink]]
            if match:
                start_idx = match.start()
                end_idx = match.end()
                surrounding = content[max(0, start_idx - 2):min(len(content), end_idx + 2)]
                if "[[" in surrounding or "]]" in surrounding:
                    continue

                # Context excerpt around mention
                ctx_start = max(0, start_idx - 40)
                ctx_end = min(len(content), end_idx + 40)
                snippet = content[ctx_start:ctx_end].replace("\n", " ")

                suggestions.append({
                    "target_note": other_node.title,
                    "target_path": other_node.rel_path,
                    "matched_text": match.group(0),
                    "context_snippet": f"...{snippet}..."
                })

        return suggestions

    def link_notes(
        self,
        source_note: str,
        target_note: str,
        anchor_text: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Inserts [[TargetNote]] into source note, logs action, and creates a 1-click reversible git commit.
        """
        self.graph_index.build_index()
        src_node = self.graph_index.get_node(source_note)
        if not src_node:
            raise FileNotFoundError(f"Source note '{source_note}' not found in vault.")

        source_path = resolve_and_sandbox_vault_path(src_node.rel_path, self.vault.vault_path)

        with open(source_path, "r", encoding="utf-8") as f:
            prev_content = f.read()

        wikilink_str = f"[[{target_note}]]"

        # If anchor_text provided and exists, replace first unlinked occurrence
        if anchor_text and anchor_text in prev_content and f"[[{anchor_text}]]" not in prev_content:
            new_content = prev_content.replace(anchor_text, wikilink_str, 1)
        else:
            # Append as related reference at end of note
            if "\n## Related Notes\n" in prev_content:
                new_content = prev_content + f"- {wikilink_str}\n"
            else:
                new_content = prev_content + f"\n\n## Related Notes\n- {wikilink_str}\n"

        # Capture pre-mutation state in crystallizer undo registry for 1-click rollback
        undo_token = f"undo-link-{uuid.uuid4().hex[:10]}"
        self.crystallizer._undo_registry[undo_token] = {
            "filepath": source_path,
            "existed": True,
            "prev_content": prev_content,
            "timestamp": time.time()
        }

        # Write updated content
        with open(source_path, "w", encoding="utf-8") as f:
            f.write(new_content)

        # Commit to vault local git repository
        self.vault.commit_changes(f"co-pilot: link [[{target_note}]] in {source_note}")

        action_log.log_action(
            tool="link_vault_notes",
            tier=1,
            args={"source_note": source_note, "target_note": target_note, "undo_token": undo_token},
            decision="auto",
            result_status="SUCCESS",
            source="graph_copilot"
        )

        return {
            "status": "linked",
            "source_note": source_note,
            "target_note": target_note,
            "filepath": source_path,
            "undo_token": undo_token,
            "message": f"Linked [[{target_note}]] into '{source_note}'. Changes committed to git."
        }


def np_dot_similarity(v1, v2) -> float:
    """Helper computing dot product of normalized vectors."""
    try:
        import numpy as np
        return float(np.dot(v1, v2))
    except Exception:
        return 0.0


# Global co-pilot singleton
graph_copilot = ObsidianGraphCoPilot()
