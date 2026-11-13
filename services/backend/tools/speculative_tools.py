"""
Phenom Neural Speculative Decoding Tool Suite
Registers:
1. generate_speculative_response (Tier 0) - Runs dual-model speculative token drafting & verification
2. benchmark_speculative_decoding (Tier 0) - Benchmarks speculative throughput vs standard baseline
3. get_speculative_metrics (Tier 0) - Retrieves last generation throughput and acceptance rate
"""

from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field

from services.backend.safety.registry import registry
from services.backend.orchestrator.speculative_decoder import speculative_decoder


# 1. Generate Speculative Response
class SpeculativeGenArgs(BaseModel):
    prompt: str = Field(description="Input prompt to generate response for")
    max_tokens: int = Field(default=50, description="Maximum tokens to draft")

@registry.register(
    name="generate_speculative_response",
    tier=0,
    description="Generates text using dual-model speculative drafting (Qwen 4B draft + Jarvis 8B verifier) for accelerated token throughput.",
    args_schema=SpeculativeGenArgs,
    preview_fn=lambda a: f"Execute speculative decoding for prompt: '{a.get('prompt', '')[:40]}...'",
    can_remember_per_folder=False
)
def generate_speculative_response(prompt: str, max_tokens: int = 50) -> Dict[str, Any]:
    return speculative_decoder.generate_speculative(prompt=prompt, max_tokens=max_tokens)


# 2. Benchmark Speculative Decoding
class BenchmarkSpeculativeArgs(BaseModel):
    sample_prompt: str = Field(default="Assess current tactical security posture", description="Sample prompt for throughput test")

@registry.register(
    name="benchmark_speculative_decoding",
    tier=0,
    description="Benchmarks dual-model speculative generation throughput (tokens/sec) against standard baseline on NVIDIA GPU.",
    args_schema=BenchmarkSpeculativeArgs,
    preview_fn=lambda a: f"Benchmark speculative GPU decoding throughput",
    can_remember_per_folder=False
)
def benchmark_speculative_decoding(sample_prompt: str = "Assess current tactical security posture") -> Dict[str, Any]:
    return speculative_decoder.benchmark_throughput(sample_prompt=sample_prompt)


# 3. Get Metrics
class GetMetricsArgs(BaseModel):
    pass

@registry.register(
    name="get_speculative_metrics",
    tier=0,
    description="Retrieves the most recent speculative decoding performance metrics (acceptance rate, tokens/sec, speedup ratio).",
    args_schema=GetMetricsArgs,
    preview_fn=lambda a: "Retrieve speculative decoding throughput metrics",
    can_remember_per_folder=False
)
def get_speculative_metrics() -> Dict[str, Any]:
    return speculative_decoder.get_last_metrics()
