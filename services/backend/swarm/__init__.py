"""
Phenom Autonomous Multi-Agent Collaborative Swarm & Synthetic Debate Engine
"""

from services.backend.schemas.swarm_debate import (
    SpecialistRole,
    CritiqueVerdict,
    ConsensusVerdict,
    SpecialistCritique,
    DebateTurn,
    ConsensusReport,
    SwarmProposal,
    SwarmDispatchSpecialistsArgs,
    SwarmGetDebateStatusArgs,
    SwarmSubmitUserDecisionArgs,
)
from services.backend.swarm.synthetic_debate import SyntheticDebateEngine, calculate_consensus
from services.backend.swarm.specialist_orchestrator import (
    SpecialistSwarmOrchestrator,
    specialist_swarm_orchestrator,
)

__all__ = [
    "SpecialistRole",
    "CritiqueVerdict",
    "ConsensusVerdict",
    "SpecialistCritique",
    "DebateTurn",
    "ConsensusReport",
    "SwarmProposal",
    "SwarmDispatchSpecialistsArgs",
    "SwarmGetDebateStatusArgs",
    "SwarmSubmitUserDecisionArgs",
    "SyntheticDebateEngine",
    "calculate_consensus",
    "SpecialistSwarmOrchestrator",
    "specialist_swarm_orchestrator",
]
