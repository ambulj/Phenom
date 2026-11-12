import time
import pytest
from services.backend.voice_action import streaming_voice_action_kernel
from services.backend.schemas.voice_action import VoiceKernelState


def test_voice_action_kernel_guardian_halt_sla_benchmark():
    """
    Benchmark 100 consecutive synchronous Guardian halt cycles on the Voice-to-Action Kernel.
    Hard SLA: < 10.0ms. Target: < 1.0ms typical.
    """
    latencies = []

    for _ in range(100):
        streaming_voice_action_kernel.reset()
        streaming_voice_action_kernel.start_session("sla-benchmark")
        streaming_voice_action_kernel.ingest_chunk(rms_energy=0.4, speech_prob=0.85, transcript_text="query test")

        start = time.perf_counter()
        streaming_voice_action_kernel.halt()
        elapsed_ms = (time.perf_counter() - start) * 1000.0

        latencies.append(elapsed_ms)
        assert streaming_voice_action_kernel.state == VoiceKernelState.HALTED
        assert not streaming_voice_action_kernel.is_listening
        assert len(streaming_voice_action_kernel._chunk_buffer) == 0

    streaming_voice_action_kernel.reset()

    avg_latency = sum(latencies) / len(latencies)
    max_latency = max(latencies)
    min_latency = min(latencies)

    print(f"\n[Guardian Voice-to-Action Kernel SLA Benchmark] 100 Cycles:")
    print(f"  Avg Latency: {avg_latency:.4f} ms")
    print(f"  Max Latency: {max_latency:.4f} ms")
    print(f"  Min Latency: {min_latency:.4f} ms")

    assert avg_latency < 1.0, f"Average Guardian halt latency ({avg_latency:.4f}ms) exceeded 1.0ms target"
    assert max_latency < 10.0, f"Max Guardian halt latency ({max_latency:.4f}ms) exceeded 10.0ms hard SLA"
