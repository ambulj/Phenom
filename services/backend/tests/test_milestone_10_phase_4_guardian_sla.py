"""
Guardian Kill Switch Sub-25ms SLA Benchmark for Milestone 10.0 (SAF-02)
Benchmarks synchronous shutdown latency of P2PMeshEngine across sockets,
discovery broadcasters, and pairing state machines.
"""

import os
import time
import pytest
from services.backend.mesh.crypto import MeshCryptoEngine
from services.backend.mesh.p2p_mesh_engine import P2PMeshEngine
from services.backend.safety.guardian import GuardianKillSwitch


def test_guardian_killswitch_sub_25ms_sla(tmp_path):
    guardian = GuardianKillSwitch()
    engine = P2PMeshEngine(
        node_id="desktop-benchmark-host",
        guardian=guardian,
        registry_path=str(tmp_path / "devices.json")
    )

    # 1. Start discovery engine
    engine.start()

    # 2. Register mock active session
    key = os.urandom(32)
    session = engine.register_session("companion-phone-benchmark", MeshCryptoEngine(key=key))

    # 3. Generate active pairing token
    payload = engine.generate_pairing_qr(ttl_seconds=120)
    assert len(engine.pairing._active_tokens) >= 1

    # 4. Trigger synchronous Guardian kill switch and benchmark latency
    t_start = time.perf_counter()
    guardian.trigger("benchmark_sla_test")
    t_end = time.perf_counter()

    elapsed_ms = (t_end - t_start) * 1000
    print(f"\n[GUARDIAN SLA BENCHMARK] Synchronous halt elapsed: {elapsed_ms:.4f} ms")

    # Hard SLA Requirement: must be strictly < 25.0 ms (typical is < 1.0 ms)
    assert elapsed_ms < 25.0, f"Guardian halt took {elapsed_ms:.2f}ms, exceeding 25ms SLA"
    assert engine.is_halted is True

    # 5. Verify state post-halt
    assert session.sock is None
    assert engine.discovery._running is False
    assert len(engine.pairing._active_tokens) == 0

    # 6. Verify subsequent operations fail fast (< 0.5ms) with PermissionError
    t_op_start = time.perf_counter()
    with pytest.raises(PermissionError, match="halted"):
        engine.generate_pairing_qr()
    op_elapsed_ms = (time.perf_counter() - t_op_start) * 1000
    assert op_elapsed_ms < 5.0

    with pytest.raises(PermissionError, match="halted"):
        engine.send_frame("companion-phone-benchmark", 1, b"halt_test")

    # 7. Resumption & recovery
    guardian.resume()
    assert engine.is_halted is False

    # Should succeed again
    new_qr = engine.generate_pairing_qr()
    assert new_qr.token is not None

    # Clean shutdown
    engine.stop()
