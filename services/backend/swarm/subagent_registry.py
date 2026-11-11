"""Specialist Subagent Registry for Phenom Swarm Mesh (Milestone 27 Phase 1).

Defines specialist subagent profiles, capability vectors, and execution constraints (AGT-04.1).
"""

from __future__ import annotations

import logging
from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field

logger = logging.getLogger("phenom.swarm.registry")


class SpecialistCapabilityProfile(BaseModel):
    specialization: str
    description: str
    allowed_actions: List[str]
    skill_vector: Dict[str, float]  # e.g. {"code_synthesis": 0.95, "security_audit": 0.30}
    max_concurrency: int = 2
    default_priority: int = 1


SPECIALIST_PROFILES: Dict[str, SpecialistCapabilityProfile] = {
    "CodeArchitect": SpecialistCapabilityProfile(
        specialization="CodeArchitect",
        description="Synthesizes AST structures, scaffolds modular Python/TypeScript logic, and refactors components.",
        allowed_actions=["CODE_GEN", "AST_MUTATE", "REFACTOR", "QUERY_GRAPH"],
        skill_vector={"code_synthesis": 0.95, "ast_manipulation": 0.90, "security_audit": 0.40, "testing": 0.60},
        max_concurrency=2,
    ),
    "SecurityAuditor": SpecialistCapabilityProfile(
        specialization="SecurityAuditor",
        description="Audits AST visitors, validates Rule 1 & Rule 8 compliance, inspects permissions, and scans for leaks.",
        allowed_actions=["SECURITY_AUDIT", "RULE_8_CHECK", "PERM_INSPECT", "QUERY_POLICIES"],
        skill_vector={"code_synthesis": 0.30, "ast_manipulation": 0.70, "security_audit": 0.98, "testing": 0.80},
        max_concurrency=2,
    ),
    "TestOrchestrator": SpecialistCapabilityProfile(
        specialization="TestOrchestrator",
        description="Executes unit and chaos concurrency test batteries, validates Guardian SLA halts, and asserts verdicts.",
        allowed_actions=["RUN_TEST", "CHAOS_BATTERY", "BENCHMARK_SLA", "ASSERT_VERDICT"],
        skill_vector={"code_synthesis": 0.50, "ast_manipulation": 0.50, "security_audit": 0.75, "testing": 0.95},
        max_concurrency=3,
    ),
    "KnowledgeResearcher": SpecialistCapabilityProfile(
        specialization="KnowledgeResearcher",
        description="Queries hierarchical memory graphs, evaluates epistemic beliefs, and synthesizes long-horizon context.",
        allowed_actions=["QUERY_MEMORY", "RESOLVE_BELIEF", "SEARCH_TOPOLOGY", "SYNTHESIZE_DOC"],
        skill_vector={"code_synthesis": 0.40, "ast_manipulation": 0.30, "security_audit": 0.50, "testing": 0.50},
        max_concurrency=2,
    ),
}


def get_specialist_profile(specialization: str) -> Optional[SpecialistCapabilityProfile]:
    """Retrieve capability profile by specialization name."""
    return SPECIALIST_PROFILES.get(specialization)
