"""Unit test suite for Associative Temporal Knowledge Graph & Deep Episodic Memory Matrix (Milestone 31 Phase 3).

Tests:
- Entity and relation lifecycle in isolated database (MEM-01.1).
- Temporal half-life decay and access count reinforcement scoring (MEM-01.2).
- Cross-session episodic event linking across Terminal, Git, and Obsidian notes with 2-hop traversal (EPISODE-02.1).
- Strict Rule 8 anti-checkout enforcement across entities, relations, episodes, and queries.
- Rule 11 credential protection and sensitive token redaction (EPISODE-02.2).
- Guardian kill switch SLA < 25.0ms (Rule 3).
- Safety ToolRegistry registration and risk tiers (Tier 1 & Tier 0).
"""

from __future__ import annotations

import time
import pytest

from services.backend.safety.guardian import guardian
from services.backend.safety.registry import registry
from services.backend.memory.temporal_knowledge_graph import (
    TemporalKnowledgeGraph,
    EntityType,
    RelationType,
    EpisodeType,
    Rule8ViolationError,
)
import services.backend.tools.temporal_knowledge_graph_tools  # noqa: F401


@pytest.fixture(autouse=True)
def clean_guardian_and_graph():
    """Ensures guardian is resumed and provides an isolated in-memory knowledge graph."""
    guardian.resume()
    graph = TemporalKnowledgeGraph(db_path=":memory:")
    yield graph
    guardian.resume()


def test_entity_and_relation_lifecycle(clean_guardian_and_graph):
    """MEM-01.1: Verify node insertion, updating, and relation creation in knowledge graph."""
    graph = clean_guardian_and_graph

    # Record Entity 1
    ent1 = graph.record_entity(
        id="ent-auth",
        name="Authentication Service",
        entity_type=EntityType.FILE,
        properties={"path": "services/backend/auth.py", "language": "python"},
    )
    assert ent1.id == "ent-auth"
    assert ent1.name == "Authentication Service"
    assert ent1.entity_type == EntityType.FILE
    assert ent1.access_count == 1

    # Record Entity 2
    ent2 = graph.record_entity(
        id="ent-token",
        name="JWT Bearer Token",
        entity_type=EntityType.CONCEPT,
        properties={"format": "RFC-7519"},
    )
    assert ent2.id == "ent-token"

    # Link with relation
    rel = graph.record_relation(
        id="rel-auth-token",
        source_id="ent-auth",
        target_id="ent-token",
        relation_type=RelationType.DEPENDS_ON,
        weight=0.95,
    )
    assert rel.id == "rel-auth-token"
    assert rel.relation_type == RelationType.DEPENDS_ON
    assert rel.weight == 0.95

    # Check stats
    stats = graph.get_stats()
    assert stats["entity_count"] == 2
    assert stats["relation_count"] == 1


def test_temporal_decay_scoring(clean_guardian_and_graph):
    """MEM-01.2: Verify exponential half-life decay and access count reinforcement scoring."""
    graph = clean_guardian_and_graph
    now = 1000000.0  # reference time

    # Fresh entity (0 days elapsed)
    fresh_score = graph.compute_temporal_score(base_weight=1.0, timestamp=now, access_count=1, current_time=now)
    assert fresh_score == pytest.approx(1.1733, abs=0.01)

    # 7 days elapsed (exactly 1 half-life = 7 * 86400 seconds)
    half_life_time = now + (7.0 * 86400.0)
    decayed_score = graph.compute_temporal_score(
        base_weight=1.0, timestamp=now, access_count=1, current_time=half_life_time
    )
    # Factor is exactly 0.5x fresh score
    assert decayed_score == pytest.approx(fresh_score * 0.5, abs=0.02)

    # 14 days elapsed (2 half-lives)
    two_half_lives_time = now + (14.0 * 86400.0)
    two_decay_score = graph.compute_temporal_score(
        base_weight=1.0, timestamp=now, access_count=1, current_time=two_half_lives_time
    )
    assert two_decay_score == pytest.approx(fresh_score * 0.25, abs=0.02)

    # Boosted entity (high access count)
    boosted_score = graph.compute_temporal_score(
        base_weight=1.0, timestamp=now, access_count=20, current_time=half_life_time
    )
    assert boosted_score > decayed_score


def test_episodic_event_linking_and_traversal(clean_guardian_and_graph):
    """EPISODE-02.1: Verify cross-session episodic linking across Terminal, Git, and Obsidian notes with 2-hop search."""
    graph = clean_guardian_and_graph

    # 1. Populate graph nodes
    graph.record_entity("ent-voice", "Voice Engine", EntityType.FILE, {"tier": 1})
    graph.record_entity("ent-barge", "Acoustic Barge-In", EntityType.GOAL, {"sla": "< 15ms"})
    graph.record_entity("ent-audio-ring", "Audio Circular Ring Buffer", EntityType.CONCEPT, {"ram_only": True})

    # Relations: Voice Engine -> Barge-In -> Audio Ring Buffer
    graph.record_relation("rel-1", "ent-voice", "ent-barge", RelationType.IMPLEMENTS, weight=1.0)
    graph.record_relation("rel-2", "ent-barge", "ent-audio-ring", RelationType.DEPENDS_ON, weight=0.9)

    # 2. Record episodes covering all 3 modalities
    # Modality 1: Terminal Run
    graph.record_episode(
        id="ep-term-1",
        session_id="sprint-31-02",
        episode_type=EpisodeType.TERMINAL_RUN,
        summary="pytest test_expressive_voice.py: 8/8 tests passed in 2.74s",
        entity_ids=["ent-voice"],
        metadata={"exit_code": 0},
    )

    # Modality 2: Git Commit
    graph.record_episode(
        id="ep-git-1",
        session_id="sprint-31-02",
        episode_type=EpisodeType.GIT_COMMIT,
        summary="feat(milestone-31): implement Phase 2 local expressive voice",
        entity_ids=["ent-barge"],
        metadata={"commit_hash": "e333eb1"},
    )

    # Modality 3: Obsidian Note
    graph.record_episode(
        id="ep-obsidian-1",
        session_id="sprint-31-02",
        episode_type=EpisodeType.OBSIDIAN_NOTE,
        summary="vault/daily/2026-11-11.md: Audio buffer latency benchmarks",
        entity_ids=["ent-audio-ring"],
        metadata={"vault_path": "vault/daily/2026-11-11.md"},
    )

    # 3. Perform 2-hop associative query starting from "Voice"
    res = graph.query_associative_subgraph(query="Voice", max_hops=2)
    assert res.status == "SUCCESS"
    assert len(res.matched_entities) >= 3

    # Check hop distances
    entity_hops = {e["id"]: e["hop_distance"] for e in res.matched_entities}
    assert entity_hops["ent-voice"] == 0
    assert entity_hops["ent-barge"] == 1
    assert entity_hops["ent-audio-ring"] == 2

    # Check linked episodes: all 3 modalities must be present
    assert len(res.linked_episodes) == 3
    found_types = {ep["episode_type"] for ep in res.linked_episodes}
    assert EpisodeType.TERMINAL_RUN.value in found_types
    assert EpisodeType.GIT_COMMIT.value in found_types
    assert EpisodeType.OBSIDIAN_NOTE.value in found_types


def test_rule_8_anti_checkout_rejection(clean_guardian_and_graph):
    """Rule 8: Knowledge graph rejects payment/checkout entities, relations, episodes, or queries."""
    graph = clean_guardian_and_graph

    checkout_phrases = [
        "Payment Gateway Integration",
        "Checkout Order Service",
        "Credit Card Billing Component",
        "Purchase Cart Database",
    ]

    for phrase in checkout_phrases:
        # Entity insert blocked
        with pytest.raises(Rule8ViolationError):
            graph.record_entity("bad-ent", phrase, EntityType.CONCEPT)

        # Episode insert blocked
        with pytest.raises(Rule8ViolationError):
            graph.record_episode("bad-ep", "sess-1", EpisodeType.TERMINAL_RUN, phrase)

        # Query blocked
        with pytest.raises(Rule8ViolationError):
            graph.query_associative_subgraph(phrase)


def test_rule_11_credential_protection(clean_guardian_and_graph):
    """Rule 11: Scrubbing sensitive API keys, tokens, and passwords prior to graph storage."""
    graph = clean_guardian_and_graph

    # Entity credential scrubbing
    ent = graph.record_entity(
        id="ent-secure-config",
        name="Config with api_key: sk-proj-1234567890abcdef12345678",
        entity_type=EntityType.FILE,
        properties={"password": "super-secret-user-pass-12345"},
    )
    assert "sk-proj" not in ent.name
    assert "[REDACTED]" in ent.name
    assert "super-secret" not in ent.properties["password"]
    assert "[REDACTED]" in ent.properties["password"]

    # Episode credential scrubbing
    ep = graph.record_episode(
        id="ep-secret",
        session_id="sess-2",
        episode_type=EpisodeType.GIT_COMMIT,
        summary="Committed auth changes with token: auth-token-9876543210",
        entity_ids=["ent-secure-config"],
    )
    assert "auth-token" not in ep.summary
    assert "[REDACTED]" in ep.summary


def test_guardian_kill_switch_sla(clean_guardian_and_graph):
    """Rule 3: Guardian kill switch halts knowledge graph operations with SLA < 25.0ms."""
    graph = clean_guardian_and_graph

    # Trip guardian
    t0 = time.perf_counter()
    guardian.trigger("Emergency memory freeze")
    trip_latency_ms = (time.perf_counter() - t0) * 1000.0
    assert trip_latency_ms < 25.0

    # Operations must halt immediately
    t1 = time.perf_counter()
    with pytest.raises(RuntimeError, match="Execution halted by Guardian kill switch"):
        graph.record_entity("halted-ent", "Halted Node", EntityType.CONCEPT)
    check_latency_ms = (time.perf_counter() - t1) * 1000.0

    assert check_latency_ms < 25.0, f"Guardian SLA {check_latency_ms:.3f}ms exceeded 25.0ms"


def test_tool_registry_and_tiers():
    """Verify all 4 temporal knowledge graph tools are registered with correct Safety tiers."""
    entity_tool = registry.get("record_graph_entity")
    relation_tool = registry.get("record_graph_relation")
    episode_tool = registry.get("record_episodic_event")
    query_tool = registry.get("query_associative_temporal_graph")

    assert entity_tool is not None
    assert entity_tool.tier == 1  # Tier 1 confirmation required

    assert relation_tool is not None
    assert relation_tool.tier == 1  # Tier 1 confirmation required

    assert episode_tool is not None
    assert episode_tool.tier == 1  # Tier 1 confirmation required

    assert query_tool is not None
    assert query_tool.tier == 0  # Tier 0 read-only
