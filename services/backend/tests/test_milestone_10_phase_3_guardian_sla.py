"""
Guardian Kill Switch Sub-25ms SLA Benchmark for Cognitive Mirror (SAF-02)
Verifies synchronous halt latency < 25.0ms (typical < 1.0ms),
instant operation rejection with PermissionError, and clean state recovery upon resume.
"""

import time
import pytest
from services.backend.safety.guardian import guardian
from services.backend.personality.cognitive_mirror import cognitive_mirror
from services.backend.schemas.cognitive_mirror import MirrorDimension, SynthesisTaskType


def test_guardian_halt_latency_sla():
    """
    Benchmarks synchronous halt latency of the cognitive mirror engine.
    Asserts strict SLA < 25.0ms and typical latency < 1.0ms.
    """
    # Ensure clean starting state
    cognitive_mirror.reset()
    assert not cognitive_mirror.is_halted

    # Benchmark halt latency over 100 trials
    latencies_ms = []
    for _ in range(100):
        cognitive_mirror.reset()
        t0 = time.perf_counter()
        cognitive_mirror.halt()
        t1 = time.perf_counter()
        latencies_ms.append((t1 - t0) * 1000.0)

    max_latency = max(latencies_ms)
    avg_latency = sum(latencies_ms) / len(latencies_ms)

    print(f"\n[Guardian SLA] Cognitive Mirror Halt - Max: {max_latency:.4f}ms, Avg: {avg_latency:.4f}ms")

    # Hard SLA: must be strictly under 25ms
    assert max_latency < 25.0, f"Halt SLA breach: {max_latency:.4f}ms >= 25.0ms"
    # Typical SLA: average should be well under 1ms
    assert avg_latency < 1.0, f"Typical halt performance degraded: {avg_latency:.4f}ms >= 1.0ms"


def test_immediate_rejection_when_halted():
    """Verifies that all cognitive mirror operations are immediately rejected when halted."""
    cognitive_mirror.halt()
    assert cognitive_mirror.is_halted

    # 1. get_profile must raise PermissionError
    with pytest.raises(PermissionError, match="Guardian kill switch is active"):
        cognitive_mirror.get_profile()

    # 2. get_stats must raise PermissionError
    with pytest.raises(PermissionError, match="Guardian kill switch is active"):
        cognitive_mirror.get_stats()

    # 3. learning methods must raise PermissionError
    with pytest.raises(PermissionError, match="Guardian kill switch is active"):
        cognitive_mirror.learn_from_git(commits_override=["feat: test"])

    with pytest.raises(PermissionError, match="Guardian kill switch is active"):
        cognitive_mirror.learn_from_obsidian(notes_override=["# Note"])

    with pytest.raises(PermissionError, match="Guardian kill switch is active"):
        cognitive_mirror.learn_from_email_drafts(drafts=["Hi"])

    with pytest.raises(PermissionError, match="Guardian kill switch is active"):
        cognitive_mirror.learn_from_work_habits(timestamps=[123456789.0])

    with pytest.raises(PermissionError, match="Guardian kill switch is active"):
        cognitive_mirror.learn_from_sources(sources=["git"])

    # 4. synthesize_text must raise PermissionError
    with pytest.raises(PermissionError, match="Guardian kill switch is active"):
        cognitive_mirror.synthesize_text(
            task=SynthesisTaskType.COMMIT_MESSAGE,
            context_prompt="update something",
        )

    # 5. reset_profile must raise PermissionError
    with pytest.raises(PermissionError, match="Guardian kill switch is active"):
        cognitive_mirror.reset_profile()

    # Clean up
    cognitive_mirror.reset()
    assert not cognitive_mirror.is_halted


def test_clean_resumption_after_reset():
    """Verifies that engine operations cleanly resume once Guardian resets to idle."""
    cognitive_mirror.halt()
    assert cognitive_mirror.is_halted

    cognitive_mirror.reset()
    assert not cognitive_mirror.is_halted

    # Operations should succeed without exception
    stats = cognitive_mirror.get_stats()
    assert "confidence_scores" in stats

    synth = cognitive_mirror.synthesize_text(
        task=SynthesisTaskType.COMMIT_MESSAGE,
        context_prompt="add integration test for resume state",
    )
    assert synth.synthesized_text


def test_main_guardian_callback_integration():
    """Verifies that main.py on_guardian_state_change correctly cascades halt and reset."""
    from services.backend.main import on_guardian_state_change

    # Trigger halt cascade
    on_guardian_state_change("halted")
    assert cognitive_mirror.is_halted

    with pytest.raises(PermissionError):
        cognitive_mirror.get_stats()

    # Trigger resume cascade
    on_guardian_state_change("idle")
    assert not cognitive_mirror.is_halted
    assert "confidence_scores" in cognitive_mirror.get_stats()
