"""
Unit Tests for Phenom Neural Speculative Decoding Suite.
Validates:
1. Dual-model speculative drafting & verification
2. Tokens/sec throughput acceleration & acceptance rate metrics
3. Comparative throughput benchmarking vs baseline
4. Guardian kill-switch SLA
5. Safety Registry metadata and risk tiers
"""

import pytest

from services.backend.safety.guardian import guardian
from services.backend.safety.registry import registry
from services.backend.orchestrator.speculative_decoder import NeuralSpeculativeDecoder
import services.backend.tools.speculative_tools as spec_tools


def test_speculative_decoding_generation():
    decoder = NeuralSpeculativeDecoder()
    guardian.resume()

    res = decoder.generate_speculative(prompt="Audit system security", max_tokens=15)
    assert "text" in res
    assert len(res["text"]) > 0

    metrics = res["metrics"]
    assert metrics["tokens_drafted"] > 0
    assert metrics["tokens_accepted"] > 0
    assert metrics["acceptance_rate_pct"] >= 50.0
    assert "speedup_ratio" in metrics
    assert "effective_tokens_per_second" in metrics


def test_speculative_throughput_benchmark():
    decoder = NeuralSpeculativeDecoder()
    guardian.resume()

    bench = decoder.benchmark_throughput(sample_prompt="Evaluate defensive perimeter")
    assert bench["benchmark_status"] == "COMPLETED"
    assert bench["baseline_throughput_tps"] > 0
    assert bench["speculative_throughput_tps"] >= bench["baseline_throughput_tps"]
    assert "x" in bench["speedup_multiplier"]
    assert "%" in bench["draft_acceptance_rate"]


def test_guardian_killswitch_speculative():
    decoder = NeuralSpeculativeDecoder()
    guardian.trigger("Emergency speculative halt")

    with pytest.raises(PermissionError):
        decoder.generate_speculative(prompt="Test")

    with pytest.raises(PermissionError):
        decoder.benchmark_throughput()

    guardian.resume()


def test_speculative_tools_registry():
    expected = [
        ("generate_speculative_response", 0),
        ("benchmark_speculative_decoding", 0),
        ("get_speculative_metrics", 0),
    ]
    for tool_name, exp_tier in expected:
        meta = registry.get(tool_name)
        assert meta is not None, f"Tool {tool_name} must be registered"
        assert meta.tier == exp_tier
