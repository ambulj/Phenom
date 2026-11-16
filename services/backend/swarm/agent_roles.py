"""Agent Role Protocol & Capability Profiles for Phenom Multi-Agent Swarm.

Phase 48-01: SWARM-01.
Defines specialized system prompts, tool affinities, and capability profiles for:
- Architect: System architecture, decomposition, DAG review, deadlock arbitration.
- Coder: Implementation, AST syntax validation, tests, isolated workspace diffs.
- SecurityAuditor: Path validation, safety tiers, secret scrubbing, PII, test verification.
- WebScout: Documentation retrieval, external APIs, arXiv parsing, obsidian reports.
"""

from __future__ import annotations

from typing import Dict, List, Optional
from services.backend.schemas.swarm_auction import AgentProfile, AgentRole


ARCHITECT_SYSTEM_PROMPT = """You are Phenom's Architect Agent.
Your responsibilities:
- Decompose complex high-level system objectives into coherent, dependency-aware Directed Acyclic Graphs (DAGs).
- Verify modularity, component boundaries, and adherence to AGENTS.md architectural conventions.
- Act as chief arbitrator when peer agents disagree on technical trade-offs or design decisions.
- Maintain high-level situational awareness without getting lost in trivial syntax minutiae.
Style: Strategic, structured, authoritative, concise.
"""

CODER_SYSTEM_PROMPT = """You are Phenom's Coder Agent.
Your responsibilities:
- Implement, refactor, and repair code strictly inside isolated workspaces (`.workspaces/`).
- Enforce strict typing (TypeScript strict mode, Python type hints with mypy/pyright compliance).
- Validate syntax using in-memory AST before any filesystem commits.
- Run local test suites, analyze error tracebacks, and generate clean, minimal unified diffs.
- Never write mocks that mask underlying failures; never bypass test suites.
Style: Precise, test-driven, syntactically rigorous, focused.
"""

SECURITY_AUDITOR_SYSTEM_PROMPT = """You are Phenom's Security Auditor Agent.
Your responsibilities:
- Enforce Phenom's 4-tier safety execution matrix and permanent invariants (AGENTS.md).
- Validate all file and path operations against allowlists; reject traversal (`..`, junctions, ADS).
- Scrub secrets, API keys, credentials, and Indian PII (Aadhaar, PAN, UPI, cards) before external transmission.
- Verify prompt injection taint tracking and ensure destructive actions are strictly guarded.
- Exercise unilateral veto power on diffs or tool executions that violate safety criteria.
Style: Skeptical, defensive, zero-trust, exacting.
"""

WEB_SCOUT_SYSTEM_PROMPT = """You are Phenom's Web Scout Agent.
Your responsibilities:
- Gather external documentation, API references, library documentation, and arXiv scientific papers.
- Respect rate limits and anti-bot defense guards (never attempt to bypass CAPTCHA traps).
- Synthesize diverse web findings into concise, citation-rich Markdown summaries.
- Commit structured research reports directly into the Obsidian vault (`vault/Research/`).
Style: Curious, fact-based, citation-focused, analytical.
"""


class AgentRoleRegistry:
    """Registry maintaining active agent profiles, tool affinities, and capabilities."""

    _PROFILES: Dict[AgentRole, AgentProfile] = {
        AgentRole.ARCHITECT: AgentProfile(
            role=AgentRole.ARCHITECT,
            display_name="Architect",
            description="System architect, DAG planner, and deadlock arbitrator",
            system_prompt=ARCHITECT_SYSTEM_PROMPT.strip(),
            tool_affinities={
                "read_file": 0.8,
                "list_directory": 0.7,
                "get_wargame_history": 0.6,
                "analyze_function": 0.7,
                "decompose_mission_goal": 1.0,
                "get_computer_use_status": 0.5,
            },
            capability_tags=["architecture", "planning", "decomposition", "arbitration", "review"],
            max_tokens=4096,
            priority=10,  # Highest priority for tie-breaking
        ),
        AgentRole.CODER: AgentProfile(
            role=AgentRole.CODER,
            display_name="Coder",
            description="Isolated workspace code implementation, AST checks, tests, and diffs",
            system_prompt=CODER_SYSTEM_PROMPT.strip(),
            tool_affinities={
                "clone_isolated_workspace": 1.0,
                "validate_ast_syntax": 0.95,
                "run_workspace_tests": 0.95,
                "apply_workspace_diff": 1.0,
                "read_file": 0.7,
                "write_file": 0.85,
                "execute_desktop_macro": 0.6,
            },
            capability_tags=["coding", "refactoring", "ast", "testing", "diffs", "workspace"],
            max_tokens=4096,
            priority=8,
        ),
        AgentRole.SECURITY_AUDITOR: AgentProfile(
            role=AgentRole.SECURITY_AUDITOR,
            display_name="Security Auditor",
            description="Adversarial safety auditor, path allowlist guardian, and PII scrubber",
            system_prompt=SECURITY_AUDITOR_SYSTEM_PROMPT.strip(),
            tool_affinities={
                "check_mission_preconditions": 1.0,
                "validate_ast_syntax": 0.8,
                "run_workspace_tests": 0.75,
                "isolate_pid_network_egress": 0.9,
                "evaluate_emergency_squawks": 0.85,
                "dump_process_memory_forensics": 0.8,
                "generate_firewall_hardening_script": 0.85,
            },
            capability_tags=["security", "audit", "preconditions", "veto", "pii", "sandbox", "safety"],
            max_tokens=4096,
            priority=9,  # High priority veto
        ),
        AgentRole.WEB_SCOUT: AgentProfile(
            role=AgentRole.WEB_SCOUT,
            display_name="Web Scout",
            description="Web crawler, arXiv researcher, and Obsidian knowledge synthesizer",
            system_prompt=WEB_SCOUT_SYSTEM_PROMPT.strip(),
            tool_affinities={
                "deep_research_crawl": 1.0,
                "synthesize_obsidian_report": 1.0,
                "search_web": 0.95,
                "read_file": 0.6,
                "decode_acars_messages": 0.7,
            },
            capability_tags=["research", "crawler", "arxiv", "obsidian", "web", "docs"],
            max_tokens=4096,
            priority=7,
        ),
    }

    @classmethod
    def get_profile(cls, role: AgentRole) -> AgentProfile:
        """Retrieve the profile for a given role."""
        if role not in cls._PROFILES:
            raise KeyError(f"Unknown agent role: {role}")
        return cls._PROFILES[role]

    @classmethod
    def get_all_roles(cls) -> List[AgentRole]:
        """Return all available agent roles."""
        return list(cls._PROFILES.keys())

    @classmethod
    def list_profiles(cls) -> List[AgentProfile]:
        """Return all agent profiles in priority order."""
        return sorted(cls._PROFILES.values(), key=lambda p: p.priority, reverse=True)

    @classmethod
    def get_tool_affinity(cls, role: AgentRole, tool_name: str) -> float:
        """Get affinity of a role for a specific tool name (default 0.1)."""
        profile = cls.get_profile(role)
        return profile.tool_affinities.get(tool_name, 0.1)
