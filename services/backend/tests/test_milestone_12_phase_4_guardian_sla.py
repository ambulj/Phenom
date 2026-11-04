"""
Universal Guardian Kill Switch Sub-25ms SLA Benchmark for Milestone 12.0 (SAF-02).
Benchmarks 100 consecutive synchronous Guardian halts across all 6 Milestone 12 subsystems simultaneously:
- DreamConsolidationEngine
- SpatialCanvasManager
- FocusTrackingEngine
- ProactiveEventBus
- AmbientFeedbackSynthesizer
- LocalWebRTCMirror

Asserts:
- Universal average latency < 1.0 ms
- Hard SLA maximum latency < 25.0 ms
"""

import time
from services.backend.memory.dream_engine import DreamConsolidationEngine, EpisodicReplayBuffer, GraphCompactor
from services.backend.memory.multi_source_graph import MultiSourceKnowledgeGraph
from services.backend.spatial.canvas_manager import SpatialCanvasManager
from services.backend.spatial.focus_tracker import FocusTrackingEngine
from services.backend.proactive.event_bus import ProactiveEventBus
from services.backend.ambient.feedback_synthesizer import AmbientFeedbackSynthesizer
from services.backend.ambient.webrtc_mirror import LocalWebRTCMirror
from services.backend.schemas.proactive_bus import Win32EventType, AudioCueType


def test_milestone_12_universal_guardian_halt_sla_benchmark():
    """Benchmark 100 consecutive synchronous halts across all Milestone 12 subsystems."""
    latencies = []
    iterations = 100

    for i in range(iterations):
        # 1. Instantiate active subsystems
        kg = MultiSourceKnowledgeGraph()
        dream = DreamConsolidationEngine(graph=kg)

        tracker = FocusTrackingEngine()
        spatial = SpatialCanvasManager(focus_tracker=tracker)

        bus = ProactiveEventBus()
        synth = AmbientFeedbackSynthesizer()
        mirror = LocalWebRTCMirror()

        # 2. Populate active states
        spatial.show_overlay()
        spatial.add_annotation(title=f"Note {i}", content="Active test note")
        bus.ingest_event(Win32EventType.FOCUS_CHANGE, window_title="IDE")
        synth.trigger_cue(AudioCueType.SUBTLE_CHIME)
        mirror.init_session(device_id="companion_tablet")

        # 3. Synchronous halt sequence benchmark
        t0 = time.perf_counter()
        dream.halt()
        spatial.halt()
        bus.halt()
        synth.halt()
        mirror.halt()
        elapsed_ms = (time.perf_counter() - t0) * 1000.0

        latencies.append(elapsed_ms)

        # 4. Assert fail-closed state invariants
        assert dream.is_halted() is True
        assert spatial.is_halted() is True
        assert len(spatial.get_state().annotations) == 0
        assert tracker.is_halted() is True
        assert bus.is_halted() is True
        assert synth.is_halted() is True
        assert mirror.is_halted() is True
        assert len(mirror.get_active_sessions()) == 0

    avg_ms = sum(latencies) / len(latencies)
    max_ms = max(latencies)
    min_ms = min(latencies)

    print(f"\n=======================================================")
    print(f"[Milestone 12 Universal Guardian SLA Benchmark] 100 Cycles:")
    print(f"  Avg Latency: {avg_ms:.4f} ms (Target: < 1.0 ms)")
    print(f"  Max Latency: {max_ms:.4f} ms (Hard SLA: < 25.0 ms)")
    print(f"  Min Latency: {min_ms:.4f} ms")
    print(f"=======================================================\n")

    assert avg_ms < 1.0, f"Average halt latency must be < 1.0ms, got {avg_ms:.4f}ms"
    assert max_ms < 25.0, f"Maximum halt latency must be < 25.0ms SLA, got {max_ms:.4f}ms"
