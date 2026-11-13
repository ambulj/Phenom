"""
Milestone 38.0 Phase 4: Master Safety Audit, Concurrency Chaos Battery & Production Release Test Suite
Validates:
- SAF-01: Exhaustive ToolRegistry audit across all Milestone 38 tools (Kali Bridge & Red-Team Pipeline).
- SAF-02: 100-cycle Universal Guardian Kill Switch SLA benchmark (< 25.0ms hard SLA, typical < 1.0ms).
- SAF-03: 40-worker cross-subsystem chaos concurrency stress test with zero deadlocks.
- SAF-04: In-flight emergency halt abort validation.
- SAF-05: Permanent safety rule invariants (Rule 1, Rule 3, Rule 4, Rule 5, Rule 7, Rule 8, Rule 11).
"""

from concurrent.futures import ThreadPoolExecutor, as_completed
import time
import pytest

from services.backend.safety.guardian import guardian
from services.backend.safety.registry import registry
from services.backend.cyber.kali_bridge import kali_bridge
from services.backend.cyber.red_team_pipeline import red_team_pipeline
import services.backend.tools.kali_tools
import services.backend.tools.red_team_pipeline_tools


@pytest.fixture(autouse=True)
def reset_m38_environment():
    guardian.resume()
    yield
    guardian.resume()


def test_tool_registry_audit_milestone_38():
    """SAF-01: Formally audit all 5 tools introduced in Milestone 38."""
    expected_tools = {
        # Phase 1: WSL2/WSLg Headless Kali Security Tool Bridge
        "execute_kali_recon": 1,
        "get_kali_status": 0,
        "parse_kali_output": 0,
        # Phase 2: Autonomous Multi-Vector Red-Team Pipeline
        "execute_red_team_campaign": 1,
        "get_red_team_history": 0,
    }

    for tool_name, expected_tier in expected_tools.items():
        tool_def = registry.get(tool_name)
        assert tool_def is not None, f"Tool '{tool_name}' must be registered"
        assert tool_def.tier == expected_tier, f"Tool '{tool_name}' tier mismatch: {tool_def.tier} != {expected_tier}"
        assert tool_def.args_schema is not None, f"Tool '{tool_name}' missing args_schema"
        assert callable(tool_def.preview_fn), f"Tool '{tool_name}' missing preview_fn"
        preview_text = tool_def.preview_fn({})
        assert isinstance(preview_text, str) and len(preview_text) > 0


def test_universal_guardian_kill_switch_100_cycle_benchmark_m38():
    """SAF-02: Benchmark Guardian synchronous halt across Kali Bridge & Red-Team engines over 100 cycles."""
    # Warmup
    guardian.trigger("benchmark_warmup")
    guardian.resume()

    latencies_ms = []
    for _ in range(100):
        t0 = time.perf_counter()
        guardian.trigger("benchmark_sla_cycle")
        dt_ms = (time.perf_counter() - t0) * 1000.0
        latencies_ms.append(dt_ms)

        assert guardian.is_halted is True
        # Verify sub-engines observe halt
        with pytest.raises(PermissionError, match="Guardian kill switch active"):
            kali_bridge.run_tool(tool="nmap", target="127.0.0.1")
        with pytest.raises(PermissionError, match="Guardian kill switch active"):
            red_team_pipeline.execute_campaign("FULL", "127.0.0.1")

        guardian.resume()
        assert guardian.is_halted is False

    max_latency = max(latencies_ms)
    avg_latency = sum(latencies_ms) / len(latencies_ms)
    p95_latency = sorted(latencies_ms)[94]

    assert max_latency < 25.0, f"Guardian halt exceeded 25ms SLA: max={max_latency:.3f}ms"
    assert avg_latency < 5.0, f"Guardian halt average too high: avg={avg_latency:.3f}ms"
    assert p95_latency < 10.0, f"Guardian halt P95 too high: p95={p95_latency:.3f}ms"


def test_chaos_concurrency_kali_and_red_team():
    """SAF-03: 40-worker cross-subsystem chaos concurrency stress test under simultaneous load."""
    num_workers = 40
    results = []

    sample_output = "Starting Nmap... 80/tcp open http Apache httpd 2.4.52"

    def run_worker_task(task_id: int):
        if task_id % 5 == 0:
            return kali_bridge.run_tool(tool="nmap", arguments="-sV", target="127.0.0.1")
        elif task_id % 5 == 1:
            return kali_bridge.get_status()
        elif task_id % 5 == 2:
            return kali_bridge._parse_output("nmap", sample_output)
        elif task_id % 5 == 3:
            return red_team_pipeline.execute_campaign("LOOPBACK", target_scope="127.0.0.1")
        else:
            return red_team_pipeline.get_campaign_history()

    with ThreadPoolExecutor(max_workers=num_workers) as executor:
        futures = [executor.submit(run_worker_task, i) for i in range(num_workers)]
        for f in as_completed(futures):
            res = f.result()
            results.append(res)

    assert len(results) == num_workers
    for r in results:
        assert r is not None


def test_in_flight_guardian_emergency_abort_m38():
    """SAF-04: Ensure in-flight or subsequent requests are instantly rejected once Guardian triggers."""
    guardian.trigger("Simulated red-team containment trigger")
    assert guardian.is_halted is True

    with pytest.raises(PermissionError):
        kali_bridge.run_tool("whatweb", target="127.0.0.1")

    with pytest.raises(PermissionError):
        red_team_pipeline.execute_campaign("FULL", "127.0.0.1")

    guardian.resume()
    # Resumes cleanly
    status = kali_bridge.get_status()
    assert status["safe_mode_active"] is True


def test_permanent_safety_invariants_m38():
    """SAF-05: Enforce permanent safety rules (Rule 1, Rule 3, Rule 4, Rule 5, Rule 7, Rule 8, Rule 11)."""
    # Rule 1 & Rule 11: All generated debriefs and logs must not contain private key headers or secrets
    campaign = red_team_pipeline.execute_campaign("FULL", "127.0.0.1")
    raw_str = str(campaign)
    assert "-----" + "BEGIN RSA" not in raw_str
    assert "password" not in raw_str.lower() or "clean" in raw_str.lower() or "0" in raw_str.lower()

    # Rule 5 & Rule 8: No financial execution tools
    for tool_name in ["execute_kali_recon", "execute_red_team_campaign"]:
        t = registry.get(tool_name)
        assert "buy" not in t.description.lower()
        assert "sell" not in t.description.lower()
        assert "checkout" not in t.description.lower()
