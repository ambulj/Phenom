"""Phenom Epistemic Belief Subsystem (Milestone 26 Phase 2).

Autonomous Epistemic Belief Updating & Contradiction Resolution (EPI-01, RES-03).
"""

from services.backend.epistemic.belief_network import (
    EpistemicBelief,
    BeliefRevisionRecord,
    EpistemicBeliefNetwork,
    epistemic_belief_network,
)
from services.backend.epistemic.contradiction_resolver import (
    ContradictionDetectionResult,
    ContradictionResolver,
    contradiction_resolver,
)

__all__ = [
    "EpistemicBelief",
    "BeliefRevisionRecord",
    "EpistemicBeliefNetwork",
    "epistemic_belief_network",
    "ContradictionDetectionResult",
    "ContradictionResolver",
    "contradiction_resolver",
]
