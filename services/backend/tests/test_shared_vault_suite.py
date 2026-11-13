"""
Unit tests for Milestone 42 Phase 1: Encrypted Shared Partition Vault
Validates:
1. PBKDF2 master encryption key derivation.
2. Campaign run upsert and retrieval.
3. Threat actor profile storage and search queries.
4. Database integrity audit (PRAGMA integrity_check).
5. Universal Guardian kill switch (<25ms SLA) enforcement.
6. ToolRegistry registration for all 3 tools.
"""

import os
import tempfile
import time
import pytest
from services.backend.safety.guardian import guardian
from services.backend.safety.registry import registry
from services.backend.platform.shared_vault import SharedVaultEngine, shared_vault


@pytest.fixture
def temp_vault():
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        tmp_path = f.name
    engine = SharedVaultEngine(db_path=tmp_path)
    yield engine
    try:
        os.remove(tmp_path)
    except Exception:
        pass


@pytest.fixture(autouse=True)
def ensure_guardian_active():
    guardian.resume()
    yield
    guardian.resume()


def test_vault_key_derivation(temp_vault):
    key = temp_vault._derive_master_key()
    assert isinstance(key, str)
    assert len(key) == 64  # SHA-256 hex is 64 characters (32 bytes)


def test_store_and_get_campaign_run(temp_vault):
    res = temp_vault.store_campaign_run(
        run_id="CHRONO-RUN-001",
        campaign_name="Autonomous Lab Pentest",
        target_scope="127.0.0.1",
        current_stage=2,
        status="RUNNING",
        findings={"open_ports": [8000, 11434], "vulns": ["CWE-121"]}
    )
    assert res["status"] == "STORED"
    assert res["stage"] == 2

    retrieved = temp_vault.get_campaign_run("CHRONO-RUN-001")
    assert retrieved is not None
    assert retrieved["campaign_name"] == "Autonomous Lab Pentest"
    assert retrieved["target_scope"] == "127.0.0.1"
    assert retrieved["current_stage"] == 2
    assert "open_ports" in retrieved["findings"]


def test_threat_actor_storage_and_query(temp_vault):
    temp_vault.store_threat_actor(
        actor_id="APT-29",
        name="Cozy Bear",
        aliases=["Midnight Blizzard", "Nobelium"],
        origin="State-Sponsored",
        ttps=["T1059", "T1078", "T1114"],
        c2_infrastructure=["c2.adversary-lab.local", "192.168.1.250"],
        severity="CRITICAL"
    )

    actors = temp_vault.query_threat_actors("Cozy Bear")
    assert len(actors) >= 1
    actor = actors[0]
    assert actor["actor_id"] == "APT-29"
    assert "Midnight Blizzard" in actor["aliases"]
    assert "T1059" in actor["ttps"]


def test_vault_integrity_verification(temp_vault):
    report = temp_vault.verify_vault_integrity()
    assert report["is_valid"] is True
    assert report["integrity_result"].lower() == "ok"
    assert report["duration_ms"] < 25.0


def test_guardian_kill_switch_sla():
    guardian.trigger("Emergency drill")

    t0 = time.perf_counter()
    with pytest.raises(PermissionError):
        shared_vault.verify_vault_integrity()
    latency_ms = (time.perf_counter() - t0) * 1000.0

    assert latency_ms < 25.0, f"Guardian SLA violation: {latency_ms:.3f}ms >= 25.0ms"


def test_shared_vault_tools_registered():
    import services.backend.tools.shared_vault_tools

    expected = [
        ("sync_shared_vault_state", 1),
        ("query_shared_vault_records", 0),
        ("verify_vault_integrity", 0)
    ]
    for t_name, exp_tier in expected:
        tool = registry.get(t_name)
        assert tool is not None, f"Tool '{t_name}' must be registered"
        assert tool.tier == exp_tier
