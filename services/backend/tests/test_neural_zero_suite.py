"""
Unit tests for Milestone 41 Phase 3: NEURAL-CIPHER & ZERO-TRACE
Validates:
1. Input mutation generation (bit flips, boundaries, format strings, overflows).
2. Crash triage mapping (SIGSEGV, SIGABRT, SIGFPE, Access Violation).
3. Target fuzzing harness and reporting.
4. Zero-Trace RAM-only mode toggle and volatile logging.
5. Cryptographic memory zeroization (<25ms SLA).
6. Auto-zeroization on Guardian kill switch trigger.
7. ToolRegistry registration for all 5 tools.
"""

import time
import pytest
from services.backend.safety.guardian import guardian
from services.backend.safety.registry import registry
from services.backend.cyber.neural_cipher import neural_cipher
from services.backend.cyber.zero_trace import zero_trace


@pytest.fixture(autouse=True)
def ensure_guardian_active():
    guardian.resume()
    zero_trace.set_stealth_mode(False)
    zero_trace.purge_and_zeroize()
    yield
    guardian.resume()
    zero_trace.set_stealth_mode(False)
    zero_trace.purge_and_zeroize()


def test_mutation_generation():
    muts = neural_cipher.generate_mutations(b"TEST_SEED_123", count=8)
    assert len(muts) == 8
    # Should include length expansions (overflows or format strings)
    has_expanded = any(len(m) > len(b"TEST_SEED_123") for m in muts)
    assert has_expanded is True


def test_crash_triage_classification():
    # Stack buffer overflow test
    overflow_payload = b"A" * 1024
    triage1 = neural_cipher.triage_crash(exit_code=-11, input_sample=overflow_payload)
    assert triage1["is_crash"] is True
    assert triage1["vulnerability_type"] == "STACK_BUFFER_OVERFLOW"
    assert triage1["cwe_identifier"] == "CWE-121"
    assert triage1["severity"] == "CRITICAL"

    # Format string test
    fmt_payload = b"PREFIX_%s%s%s%s%n"
    triage2 = neural_cipher.triage_crash(exit_code=-11, input_sample=fmt_payload)
    assert triage2["is_crash"] is True
    assert triage2["vulnerability_type"] == "FORMAT_STRING_VULNERABILITY"
    assert triage2["cwe_identifier"] == "CWE-134"

    # Heap corruption test (SIGABRT)
    triage3 = neural_cipher.triage_crash(exit_code=-6, input_sample=b"HEAP_DATA")
    assert triage3["is_crash"] is True
    assert triage3["vulnerability_type"] == "HEAP_CORRUPTION_OR_DOUBLE_FREE"


def test_fuzz_target_simulation():
    res = neural_cipher.fuzz_target("C:/Simulated/vulnerable_app.exe", iterations=5)
    assert res["status"] == "COMPLETED"
    assert res["iterations_completed"] == 5
    assert res["crashes_discovered"] >= 1


def test_zero_trace_mode_and_volatile_logging():
    status = zero_trace.set_stealth_mode(True)
    assert status["stealth_mode_active"] is True
    assert status["storage_layer"] == "VOLATILE_RAM"

    # Record some volatile traces
    zero_trace.record_volatile_trace("PACKET_SNIFF", "SENSITIVE_SESSION_TOKEN_12345")
    zero_trace.record_volatile_trace("HEAP_CHUNK", "PASSWORD_PLAINTEXT_SECRET")

    cur_status = zero_trace.get_status()
    assert cur_status["volatile_entries_count"] == 2
    assert cur_status["volatile_bytes_allocated"] > 0


def test_cryptographic_zeroization_sla():
    zero_trace.set_stealth_mode(True)
    for i in range(20):
        zero_trace.record_volatile_trace("KERNEL_DUMP", f"RAW_MEMORY_BLOCK_{i}" * 50)

    t0 = time.perf_counter()
    res = zero_trace.purge_and_zeroize()
    latency_ms = (time.perf_counter() - t0) * 1000.0

    assert latency_ms < 25.0, f"Zeroization SLA exceeded: {latency_ms:.3f}ms"
    assert res["status"] == "ZEROIZED"
    assert res["buffers_cleared"] == 20
    assert res["bytes_scrubbed"] > 0

    # Ensure buffer is empty
    assert zero_trace.get_status()["volatile_entries_count"] == 0


def test_auto_zeroization_on_guardian_kill_switch():
    zero_trace.set_stealth_mode(True)
    zero_trace.record_volatile_trace("TELEMETRY", "SUPER_SECRET_PAYLOAD")
    assert zero_trace.get_status()["volatile_entries_count"] == 1

    # Trigger guardian
    guardian.trigger("Manual emergency abort")

    # Verify zero_trace auto-cleared its buffers via callback
    assert zero_trace.get_status()["volatile_entries_count"] == 0


def test_neural_zero_tools_registered():
    import services.backend.tools.neural_zero_tools

    expected = [
        "fuzz_binary_target",
        "triage_crash_dump",
        "activate_zero_trace_mode",
        "purge_volatile_traces",
        "inspect_zero_trace_status"
    ]
    for t_name in expected:
        tool = registry.get(t_name)
        assert tool is not None, f"Tool '{t_name}' must be registered"
        assert tool.tier in [0, 1]
