"""
Sub-10ms Synchronous Guardian Kill Switch SLA Benchmark for Telepresence (SAF-02).
Benchmarks 100 consecutive synchronous Guardian halts of StreamingAVPipeline.
Asserts average latency < 10.0ms and maximum latency < 25.0ms (hard SLA).
"""

import time
from services.backend.schemas.telepresence import MediaStreamType, SensorState
from services.backend.telepresence.av_pipeline import StreamingAVPipeline


def test_telepresence_guardian_halt_sla_benchmark():
    pipeline = StreamingAVPipeline()
    halt_latencies_ms = []

    for i in range(100):
        # Start session and populate ring buffer
        pipeline.start_session(MediaStreamType.AUDIO_VIDEO)
        for j in range(10):
            pipeline.ingest_telemetry(
                audio_rms=0.5,
                speech_probability=0.8,
                landmarks=[(0.1, 0.2), (0.3, 0.4)],
                timestamp=time.time(),
            )

        # Benchmark synchronous halt latency
        t0 = time.perf_counter()
        pipeline.halt()
        dt_ms = (time.perf_counter() - t0) * 1000.0
        halt_latencies_ms.append(dt_ms)

        # Verify fail-closed states
        state = pipeline.get_state()
        assert state.is_active is False
        assert state.microphone_state == SensorState.DISABLED
        assert state.camera_state == SensorState.DISABLED
        assert len(pipeline._telemetry_buffer) == 0

        # Resume for next cycle
        pipeline.resume()

    avg_ms = sum(halt_latencies_ms) / len(halt_latencies_ms)
    max_ms = max(halt_latencies_ms)
    min_ms = min(halt_latencies_ms)

    print(f"\n[Guardian Telepresence SLA Benchmark] 100 Cycles:")
    print(f"  Avg Latency: {avg_ms:.4f} ms")
    print(f"  Max Latency: {max_ms:.4f} ms")
    print(f"  Min Latency: {min_ms:.4f} ms")

    # Hard SLA verification
    assert avg_ms < 10.0, f"Average halt latency {avg_ms:.4f}ms exceeded 10.0ms target"
    assert max_ms < 25.0, f"Maximum halt latency {max_ms:.4f}ms exceeded 25.0ms hard SLA"
