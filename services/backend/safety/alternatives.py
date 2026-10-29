"""
Phenom Safe Alternative Fallback Engine (Task 7l)
Finds and validates safe alternative actions when a tool is declined or times out.

Strict Invariants:
1. Tier Restriction: Alternative must be equal or lower risk tier than declined action (never higher).
2. Re-use Block: Alternative must NEVER re-invoke a tool the owner just declined in that chain.
3. Taint Quarantine: Alternative must NEVER be suggested by untrusted/tainted content.
4. If no safe alternative satisfies all three criteria, halts and asks owner for direction.
"""

from typing import Dict, Any, List, Optional, Set
from services.backend.safety.taint import taint_tracker
from services.backend.safety.registry import registry

class SafeAlternativeEngine:
    # Map of fallback alternatives: {declined_tool: [candidate_safe_alternatives]}
    ALTERNATIVE_MAP: Dict[str, List[Dict[str, Any]]] = {
        "recycle_file": [
            {"tool": "read_file", "tier": 0, "action": "inspect_file_contents_first"},
            {"tool": "list_files", "tier": 0, "action": "review_directory_listing"}
        ],
        "execute_command": [
            {"tool": "read_file", "tier": 0, "action": "inspect_script_contents"},
            {"tool": "list_files", "tier": 0, "action": "list_working_directory"}
        ],
        "write_file": [
            {"tool": "read_file", "tier": 0, "action": "read_existing_file_contents"}
        ],
        "coding_apply_changes": [
            {"tool": "coding_get_diff", "tier": 0, "action": "generate_and_review_diff_preview"}
        ]
    }

    def find_safe_alternative(
        self,
        declined_tool: str,
        declined_tier: int,
        declined_chain: Optional[Set[str]] = None,
        is_tainted: bool = False
    ) -> Dict[str, Any]:
        """
        Evaluates potential fallback actions under strict invariants.
        Returns alternative action dict, or raises ValueError if none is safe.
        """
        # Invariant 3: Taint Quarantine
        # If the context is tainted by untrusted external sources (web/email/PDF/OCR),
        # automated fallback alternatives are strictly forbidden to prevent injection chains.
        if is_tainted or taint_tracker.is_tainted:
            return {
                "safe_alternative_found": False,
                "reason": "taint_quarantine_active",
                "message": f"Declined '{declined_tool}'. Context contains untrusted input; automated fallbacks are blocked for safety. Awaiting your instructions."
            }

        candidates = self.ALTERNATIVE_MAP.get(declined_tool, [])
        used_chain = set(declined_chain or set())
        used_chain.add(declined_tool)

        for cand in candidates:
            cand_tool = cand["tool"]
            cand_tier = cand["tier"]

            # Invariant 1: Tier Restriction (must be <= declined_tier)
            if cand_tier > declined_tier:
                continue

            # Invariant 2: Re-use Block (must never invoke a tool already declined)
            if cand_tool in used_chain:
                continue

            # Verified clean candidate
            return {
                "safe_alternative_found": True,
                "tool": cand_tool,
                "tier": cand_tier,
                "action": cand["action"],
                "conversational_text": f"Declined {declined_tool}. Trying safe alternative: {cand['action']} via {cand_tool}."
            }

        # No candidate satisfied all invariants
        return {
            "safe_alternative_found": False,
            "reason": "no_valid_alternative",
            "message": f"Declined '{declined_tool}'. No safe lower-tier alternative available. What would you like me to do next?"
        }

# Global safe alternative engine instance
safe_alternative_engine = SafeAlternativeEngine()
