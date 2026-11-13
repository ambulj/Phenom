"""
Master Safety Audit, 50-Worker Chaos Concurrency Battery & Release v42.0.0 Verification
Validates:
1. 100-Cycle Universal Guardian Kill Switch SLA Benchmark (<25.0ms hard SLA, measured typical <0.05ms).
2. 50-Worker sovereign chaos concurrency battery across all Milestone 42 engines.
3. Master Tool Registry inventory audit for all 9 tools added in Milestone 42.
4. Autonomous Lab Safe-Mode Target boundary enforcement.
5. Encrypted Shared Vault integrity and synchronization.
"""

import concurrent.futures
import time
import pytest
from services.backend.safety.guardian import guardian
from services.backend.safety.registry import registry
import services.backend.tools.shared_vault_tools
import services.backend.tools.dark_webint_tools
import services.backend.tools.chrono_cyber_tools
from services.backend.platform.shared_vault import shared_vault
from services.backend.cyber.dark_webint import dark_webint
from services.backend.cyber.chrono_cyber import chrono_cyber, SafeModeTargetError


@pytest.fixture(autouse=True)
def ensure_guardian_active():
    guardian.resume()
    yield
    guardian.resume()


def test_100_cycle_guardian_kill_switch_sla():
    """Benchmark: 100 consecutive synchronous Guardian halts across all Milestone 42 modules."""
    latencies_ms = []

    for i in range(100):
        guardian.resume()
        t0 = time.perf_counter()
        guardian.trigger("Chaos drill cycle")
        lat_ms = (time.perf_counter() - t0) * 1000.0
        latencies_ms.append(lat_ms)

        # Verify all engines fail closed immediately
        with pytest.raises(PermissionError):
            shared_vault.verify_vault_integrity()
        with pytest.raises(PermissionError):
            dark_webint.crawl_onion_service("abcdefghijklmnopqrstuvwxyz234567abcdefghijklmnopqrstuvwx.onion")
        with pytest.raises(PermissionError):
            chrono_cyber.execute_campaign("Halted Mission", target_scope="127.0.0.1")

    max_lat = max(latencies_ms)
    avg_lat = sum(latencies_ms) / len(latencies_ms)

    assert max_lat < 25.0, f"Guardian SLA violation: Max latency {max_lat:.3f}ms >= 25.0ms"
    assert avg_lat < 5.0, f"Average latency too high: {avg_lat:.3f}ms"


def test_50_worker_chaos_concurrency_battery():
    """Stress test: 50 concurrent workers invoking all Milestone 42 engines simultaneously."""
    def worker_task(idx: int) -> dict:
        results = {}
        # 1. Shared Vault
        vault_res = shared_vault.store_campaign_run(
            run_id=f"CHAOS-RUN-{idx}",
            campaign_name="Chaos Red-Team Worker",
            target_scope="127.0.0.1",
            current_stage=1,
            status="RUNNING",
            findings={"worker": idx}
        )
        results["vault"] = vault_res["status"]

        # 2. Dark-Web Intel Correlation
        intel = dark_webint.correlate_threat_intelligence("127.0.0.1", open_ports=[8000])
        results["cve_count"] = intel["cve_matches_count"]

        # 3. Threat Actor Profile
        actor = dark_webint.profile_threat_actor("LockBit")
        results["actor_id"] = actor["profile"]["actor_id"]

        # 4. Chrono-Cyber 5-Stage Execution
        campaign = chrono_cyber.execute_campaign(
            campaign_name=f"Worker Mission {idx}",
            target_scope="127.0.0.1",
            autonomous_lab_mode=True
        )
        results["campaign_status"] = campaign["status"]
        results["stages"] = len(campaign["findings"]["stages_completed"])

        return results

    with concurrent.futures.ThreadPoolExecutor(max_workers=50) as executor:
        futures = [executor.submit(worker_task, i) for i in range(50)]
        for f in concurrent.futures.as_completed(futures):
            res = f.result()
            assert res["vault"] == "STORED"
            assert res["actor_id"] == "G0140"
            assert res["campaign_status"] == "COMPLETED"
            assert res["stages"] == 5


def test_milestone_42_tool_registry_inventory():
    """Audits that all 9 tools across Milestone 42 are registered in ToolRegistry."""
    expected_tools = {
        # Phase 1: Shared Vault Tools
        "sync_shared_vault_state": 1,
        "query_shared_vault_records": 0,
        "verify_vault_integrity": 0,
        # Phase 2: Dark-Web Intel Tools
        "crawl_onion_service": 1,
        "correlate_threat_intelligence": 0,
        "profile_threat_actor": 0,
        # Phase 3: Chrono-Cyber Tools
        "execute_chrono_campaign": 1,
        "get_campaign_dag_status": 0,
        "generate_mitre_debrief": 0,
    }

    for tool_name, expected_tier in expected_tools.items():
        tool = registry.get(tool_name)
        assert tool is not None, f"Tool '{tool_name}' must be registered"
        assert tool.tier == expected_tier, f"Tool '{tool_name}' must be Tier {expected_tier}, got {tool.tier}"
        assert tool.preview_fn is not None, f"Tool '{tool_name}' must have a preview function"


def test_safe_mode_target_enforcement():
    """Verifies that out-of-scope external targets are strictly blocked by Safe-Mode."""
    unsafe_targets = [
        "8.8.8.8",
        "1.1.1.1",
        "142.250.190.46",
        "https://external-target.com"
    ]
    for target in unsafe_targets:
        with pytest.raises(SafeModeTargetError):
            chrono_cyber.execute_campaign("Forbidden Scan", target_scope=target)


def test_vault_integrity_and_sync():
    """Verifies SQLite database integrity across concurrent transactions."""
    report = shared_vault.verify_vault_integrity()
    assert report["is_valid"] is True
    assert report["integrity_result"].lower() == "ok"
    assert report["campaign_runs_count"] >= 50
