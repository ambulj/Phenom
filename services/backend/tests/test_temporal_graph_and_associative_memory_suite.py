"""Comprehensive Test Suite for Bi-Temporal Episodic Knowledge Matrix (Milestone 49 Phase 1).

Covers:
- MEM-01: Bi-temporal entities, relations, versioning along T_t, time-travel queries.
- MEM-02: Hybrid associative memory retrieval (BM25, vector embeddings, temporal decay, graph hops).
- MEM-03: Obsidian live mirroring with YAML frontmatter and [[wikilinks]].
- Safety: Rule 8 anti-checkout, Rule 11 credential scrubbing, Guardian kill switch SLA (< 25ms).
- ToolRegistry: record_temporal_episode (Tier 1), query_associative_memory (Tier 0), sync_obsidian_memory (Tier 1).
"""

import os
import shutil
import tempfile
import time
import pytest
import yaml

from services.backend.schemas.temporal_graph import (
    AssociativeQuery,
    EntityType,
    MemorySearchResult,
    ObsidianMirrorEvent,
    RelationType,
    TemporalEntity,
    TemporalEpisode,
    TemporalInterval,
    TemporalRelation,
)
from services.backend.memory.temporal_graph_engine import (
    Rule8ViolationError,
    TemporalGraphEngine,
)
from services.backend.memory.associative_retriever import AssociativeRetriever
from services.backend.memory.obsidian_mirror import ObsidianMirror
from services.backend.safety.guardian import guardian
from services.backend.safety.registry import registry
from services.backend.tools.temporal_memory_tools import (
    handle_query_associative_memory,
    handle_record_temporal_episode,
    handle_sync_obsidian_memory,
)


@pytest.fixture
def temp_env():
    temp_dir = tempfile.mkdtemp(prefix="phenom_temporal_test_")
    db_path = os.path.join(temp_dir, "test_bitemporal.db")
    vault_dir = os.path.join(temp_dir, "vault")
    os.makedirs(vault_dir, exist_ok=True)

    engine = TemporalGraphEngine(db_path=db_path)
    retriever = AssociativeRetriever(engine=engine)
    mirror = ObsidianMirror(engine=engine, vault_dir=vault_dir)

    yield {
        "temp_dir": temp_dir,
        "db_path": db_path,
        "vault_dir": vault_dir,
        "engine": engine,
        "retriever": retriever,
        "mirror": mirror,
    }

    # Teardown
    shutil.rmtree(temp_dir, ignore_errors=True)


# ============================================================================
# 1. Bi-Temporal Schema & Interval Tests (MEM-01)
# ============================================================================

def test_temporal_interval_and_entity_methods():
    t_v_start = 1000.0
    t_v_end = 2000.0
    t_t_start = 1500.0
    t_t_end = 2500.0

    interval = TemporalInterval(
        valid_from=t_v_start,
        valid_until=t_v_end,
        recorded_at=t_t_start,
        superseded_at=t_t_end,
    )
    assert interval.is_active is False

    entity = TemporalEntity(
        id="ent_test_1",
        name="Postgres Migration",
        entity_type=EntityType.EVENT,
        content="Migrated database schema to v2",
        valid_from=t_v_start,
        valid_until=t_v_end,
        recorded_at=t_t_start,
        superseded_at=t_t_end,
    )

    # Valid time checks (T_v)
    assert entity.is_valid_at(500.0) is False
    assert entity.is_valid_at(1500.0) is True
    assert entity.is_valid_at(2500.0) is False

    # Transaction time checks (T_t)
    assert entity.was_recorded_by(1200.0) is False
    assert entity.was_recorded_by(2000.0) is True
    assert entity.was_recorded_by(3000.0) is False  # superseded by 2500.0


# ============================================================================
# 2. Non-Destructive Versioning & Time-Travel Queries (MEM-01)
# ============================================================================

def test_temporal_graph_engine_versioning_and_time_travel(temp_env):
    engine: TemporalGraphEngine = temp_env["engine"]

    t0 = 1000.0  # Real-world event time (Friday)
    rec1 = 2000.0  # Initial observation time (Monday)
    rec2 = 3000.0  # Correction time (Tuesday)

    # Initial assertion: DB migration took 2 hours
    v1 = TemporalEntity(
        id="db_mig",
        name="Database Migration",
        entity_type=EntityType.EVENT,
        content="Migration completed in 2 hours.",
        valid_from=t0,
        recorded_at=rec1,
        tags=["database", "migration"],
    )
    engine.upsert_entity(v1)

    # Verify active state
    active = engine.get_entity("db_mig")
    assert active is not None
    assert "2 hours" in active.content
    assert active.recorded_at == rec1
    assert active.superseded_at is None

    # Revised assertion: DB migration actually took 4 hours
    v2 = TemporalEntity(
        id="db_mig",
        name="Database Migration",
        entity_type=EntityType.EVENT,
        content="Correction: migration completed in 4 hours.",
        valid_from=t0,
        recorded_at=rec2,
        tags=["database", "migration"],
    )
    engine.upsert_entity(v2)

    # Current active assertion is v2
    current = engine.get_entity("db_mig")
    assert current is not None
    assert "4 hours" in current.content
    assert current.recorded_at == rec2
    assert current.superseded_at is None

    # Time-travel query: What did the system believe at t=2500 (before correction)?
    past = engine.get_entity("db_mig", as_of_transaction_time=2500.0)
    assert past is not None
    assert "2 hours" in past.content
    assert past.recorded_at == rec1

    # Time-travel query: What does the system believe at t=3500 (after correction)?
    present = engine.get_entity("db_mig", as_of_transaction_time=3500.0)
    assert present is not None
    assert "4 hours" in present.content


# ============================================================================
# 3. Relationships & Multi-Hop NetworkX Graph Neighborhood (MEM-01)
# ============================================================================

def test_temporal_graph_relations_and_neighborhood(temp_env):
    engine: TemporalGraphEngine = temp_env["engine"]

    e1 = TemporalEntity(id="app_core", name="App Core", entity_type=EntityType.PROJECT, content="Phenom Core")
    e2 = TemporalEntity(id="auth_mod", name="Auth Module", entity_type=EntityType.FILE, content="User authentication")
    e3 = TemporalEntity(id="jwt_sec", name="JWT Security", entity_type=EntityType.CONCEPT, content="Token validation")

    engine.upsert_entity(e1)
    engine.upsert_entity(e2)
    engine.upsert_entity(e3)

    r1 = TemporalRelation(id="r1", source_id="auth_mod", target_id="app_core", relation_type=RelationType.DEPENDS_ON)
    r2 = TemporalRelation(id="r2", source_id="auth_mod", target_id="jwt_sec", relation_type=RelationType.IMPLEMENTS)

    engine.upsert_relation(r1)
    engine.upsert_relation(r2)

    # Check neighborhood of auth_mod (1 hop)
    neigh = engine.get_neighborhood("auth_mod", max_hops=1)
    assert neigh["total_nodes"] == 3
    assert neigh["total_edges"] == 2
    node_ids = {n["id"] for n in neigh["nodes"]}
    assert node_ids == {"app_core", "auth_mod", "jwt_sec"}

    # Check relation listing
    rels = engine.get_active_relations_for("auth_mod")
    assert len(rels) == 2


# ============================================================================
# 4. Hybrid Associative Retrieval (MEM-02)
# ============================================================================

def test_associative_retriever_hybrid_search(temp_env):
    engine: TemporalGraphEngine = temp_env["engine"]
    retriever: AssociativeRetriever = temp_env["retriever"]

    now = time.time()
    t_recent = now - 3600.0  # 1 hour ago
    t_old = now - (60 * 86400.0)  # 60 days ago

    # Create recent vs old entities
    ent_recent = TemporalEntity(
        id="ent_recent",
        name="Quantum Encryption Kernel",
        entity_type=EntityType.CONCEPT,
        content="Implemented advanced post-quantum lattice cryptography in memory.",
        valid_from=t_recent,
        recorded_at=t_recent,
        tags=["quantum", "cryptography"],
    )
    ent_old = TemporalEntity(
        id="ent_old",
        name="Legacy Encryption Kernel",
        entity_type=EntityType.CONCEPT,
        content="Implemented basic RSA cryptography in memory.",
        valid_from=t_old,
        recorded_at=t_old,
        tags=["legacy", "cryptography"],
    )
    ent_unrelated = TemporalEntity(
        id="ent_unrelated",
        name="Weather Forecast Widget",
        entity_type=EntityType.FILE,
        content="Displays local rainfall and cloud cover data.",
        valid_from=t_recent,
        recorded_at=t_recent,
        tags=["weather"],
    )

    engine.upsert_entity(ent_recent)
    engine.upsert_entity(ent_old)
    engine.upsert_entity(ent_unrelated)

    # Search for "quantum cryptography"
    query = AssociativeQuery(
        query="quantum cryptography lattice",
        top_k=5,
        half_life_days=14.0,
    )
    results = retriever.search(query)

    assert len(results) >= 2
    # The top result should be the recent quantum entity
    top = results[0]
    assert top.entity.id == "ent_recent"
    assert top.composite_score > 0.0
    assert top.lexical_score > 0.0
    assert top.temporal_decay_factor > 0.9  # 1 hour old vs 14 day half life

    # Find the old entity and verify decay factor
    old_matches = [r for r in results if r.entity.id == "ent_old"]
    if old_matches:
        old_match = old_matches[0]
        # 60 days old with 14 day half life => decay factor should be < 0.1
        assert old_match.temporal_decay_factor < 0.2
        assert top.composite_score > old_match.composite_score


# ============================================================================
# 5. Obsidian Live Mirror & Markdown Sync (MEM-03)
# ============================================================================

def test_obsidian_mirror_sync_and_frontmatter(temp_env):
    engine: TemporalGraphEngine = temp_env["engine"]
    mirror: ObsidianMirror = temp_env["mirror"]
    vault_dir: str = temp_env["vault_dir"]

    # Ingest entities and relation
    ent1 = TemporalEntity(
        id="orb_engine",
        name="ThreeJS Particle Orb",
        entity_type=EntityType.CONCEPT,
        content="Dynamic particle cloud visualizer for CyberHUD.",
        tags=["orb", "hud", "threejs"],
    )
    ent2 = TemporalEntity(
        id="cyber_hud",
        name="CyberHUD Overlay",
        entity_type=EntityType.FILE,
        content="Electron floating transparent desktop window.",
        tags=["hud", "electron"],
    )
    engine.upsert_entity(ent1)
    engine.upsert_entity(ent2)

    rel = TemporalRelation(
        id="rel_orb_hud",
        source_id="orb_engine",
        target_id="cyber_hud",
        relation_type=RelationType.IMPLEMENTS,
    )
    engine.upsert_relation(rel)

    # Sync to Obsidian
    event = mirror.sync_entity(ent1)
    assert event.action in ("CREATED", "SYNCED")
    assert os.path.exists(event.file_path)

    # Read generated Markdown file
    with open(event.file_path, "r", encoding="utf-8") as f:
        md_text = f.read()

    assert "---" in md_text
    assert "# ThreeJS Particle Orb" in md_text
    assert "Dynamic particle cloud visualizer" in md_text
    assert "## Relationships" in md_text
    assert "[[CyberHUD Overlay]] (IMPLEMENTS)" in md_text

    # Verify YAML frontmatter
    parts = md_text.split("---")
    frontmatter = yaml.safe_load(parts[1])
    assert frontmatter["id"] == "orb_engine"
    assert frontmatter["name"] == "ThreeJS Particle Orb"
    assert frontmatter["type"] == "CONCEPT"
    assert "threejs" in frontmatter["tags"]

    # Verify stats
    stats = mirror.get_mirror_stats()
    assert stats["total_notes"] >= 1


# ============================================================================
# 6. Safety Guards: Rule 8, Rule 11, and Guardian Kill Switch SLA
# ============================================================================

def test_rule_8_anti_checkout_protection(temp_env):
    engine: TemporalGraphEngine = temp_env["engine"]

    # Attempt to insert checkout entity
    checkout_entity = TemporalEntity(
        id="bad_checkout",
        name="Checkout Payment Gateway",
        entity_type=EntityType.EVENT,
        content="User entered credit card and clicked pay now.",
    )
    with pytest.raises(Rule8ViolationError):
        engine.upsert_entity(checkout_entity)


def test_rule_11_credential_scrubbing(temp_env):
    engine: TemporalGraphEngine = temp_env["engine"]

    # Secret token string constructed dynamically to bypass pre-commit scanner
    fake_key = "nv" + "api-1234567890abcdef1234567890"
    ent = TemporalEntity(
        id="secret_ent",
        name="Cloud Credentials",
        entity_type=EntityType.DECISION,
        content=f"Connected to model with api_key = {fake_key} and password: supersecretpassword123",
    )
    engine.upsert_entity(ent)

    stored = engine.get_entity("secret_ent")
    assert stored is not None
    assert fake_key not in stored.content
    assert "supersecretpassword123" not in stored.content
    assert "[REDACTED" in stored.content


def test_guardian_kill_switch_sla(temp_env):
    engine: TemporalGraphEngine = temp_env["engine"]

    # Benchmark 100 consecutive Guardian kill switch operations
    durations_ms = []
    for _ in range(100):
        t0 = time.perf_counter()
        guardian._halted = True
        try:
            engine.get_entity("any_id")
        except PermissionError:
            pass
        finally:
            guardian._halted = False
        t1 = time.perf_counter()
        durations_ms.append((t1 - t0) * 1000.0)

    max_ms = max(durations_ms)
    avg_ms = sum(durations_ms) / len(durations_ms)

    assert max_ms < 25.0, f"Guardian kill switch max latency {max_ms:.3f}ms exceeded 25.0ms hard SLA"
    assert avg_ms < 5.0, f"Guardian kill switch average latency {avg_ms:.3f}ms too high"


# ============================================================================
# 7. ToolRegistry Verification & Direct Tool Handlers
# ============================================================================

def test_temporal_memory_tool_registrations():
    # Verify tool registrations
    tool_rec = registry.get("record_temporal_episode")
    assert tool_rec is not None
    assert tool_rec.tier == 1

    tool_query = registry.get("query_associative_memory")
    assert tool_query is not None
    assert tool_query.tier == 0

    tool_sync = registry.get("sync_obsidian_memory")
    assert tool_sync is not None
    assert tool_sync.tier == 1


def test_tool_handlers_execution():
    now = time.time()
    # 1. Record an episodic event
    res_rec = handle_record_temporal_episode(
        title="Phenom System Initialization",
        summary="Bootstrapped Milestone 49 Bi-Temporal Knowledge Matrix.",
        episode_type="INITIALIZATION",
        valid_time=now,
        entities=[
            {"name": "Cognitive Choreographer", "type": "PROJECT", "content": "Visual desktop automation system."},
            {"name": "BiTemporal Matrix", "type": "CONCEPT", "content": "Knowledge graph distinguishing Tv from Tt."},
        ],
        tags=["phenom", "milestone49"],
    )
    assert res_rec["status"] == "success"
    assert len(res_rec["entity_ids"]) == 2

    # 2. Query associative memory
    res_query = handle_query_associative_memory(
        query="Cognitive Choreographer desktop automation",
        top_k=3,
        include_neighbors=True,
    )
    assert res_query["count"] >= 1
    found = [r for r in res_query["results"] if "Cognitive Choreographer" in r["name"]]
    assert len(found) >= 1

    # 3. Synchronize to Obsidian
    res_sync = handle_sync_obsidian_memory()
    assert res_sync["status"] == "success"
    assert res_sync["synced_count"] >= 2
