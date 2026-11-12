"""
Guardian Kill Switch Sub-10ms SLA Benchmark for Proactive Event Bus & Feedback (PRX-01, FBK-01, SAF-02).
Benchmarks 100 consecutive synchronous Guardian halts across ProactiveEventBus,
AmbientFeedbackSynthesizer, and LocalWebRTCMirror.
Verifies:
- All active WebRTC streams are torn down
- Ingestion and audio synthesis are immediately halted
- Average halt latency is well within < 10ms (and max < 25ms SLA)
"""

import time
from services.backend.proactive.event_bus import ProactiveEventBus
from services.backend.ambient.feedback_synthesizer import AmbientFeedbackSynthesizer
from services.backend.ambient.webrtc_mirror import LocalWebRTCMirror
from services.backend.schemas.proactive_bus import Win32EventType, AudioCueType


def test_proactive_feedback_guardian_halt_sla_benchmark():
    """Benchmark 100 consecutive synchronous halts across Proactive & Feedback subsystems."""
    latencies = []
    iterations = 100

    for i in range(iterations):
        bus = ProactiveEventBus()
        synth = AmbientFeedbackSynthesizer()
        mirror = LocalWebRTCMirror()

        # Ingest events, trigger cues, establish active WebRTC session
        bus.ingest_event(Win32EventType.FOCUS_CHANGE, window_title="IDE")
        synth.trigger_cue(AudioCueType.SUBTLE_CHIME)
        mirror.init_session(device_id="companion_tablet")

        assert len(mirror.get_active_sessions()) == 1

        # Synchronous halt benchmark
        t0 = time.perf_counter()
        bus.halt()
        synth.halt()
        mirror.halt()
        elapsed_ms = (time.perf_counter() - t0) * 1000.0

        latencies.append(elapsed_ms)

        # Assert immediate post-conditions
        assert bus.is_halted() is True
        assert synth.is_halted() is True
        assert mirror.is_halted() is True
        assert len(mirror.get_active_sessions()) == 0

    avg_ms = sum(latencies) / len(latencies)
    max_ms = max(latencies)
    min_ms = min(latencies)

    print(f"\n[Guardian Proactive & Feedback SLA Benchmark] 100 Cycles:")
    print(f"  Avg Latency: {avg_ms:.4f} ms")
    print(f"  Max Latency: {max_ms:.4f} ms")
    print(f"  Min Latency: {min_ms:.4f} ms")

    # Phenom strict safety SLA asserts
    assert avg_ms < 10.0, f"Average halt latency must be < 10ms, got {avg_ms:.4f}ms"
    assert max_ms < 25.0, f"Maximum halt latency must be < 25ms SLA, got {max_ms:.4f}ms"
