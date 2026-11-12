"""
Tests for Autonomous Local Fine-Tuning & Adaptive LoRA Adapter Synthesis.
Part of Phenom 23.0 Sovereign Neural Evolution (ADA-01, MOD-02, SAF-01, SAF-02).
"""

import time
import os
import json
import pytest
from typing import Dict, Any

from services.backend.evolution.dataset_generator import (
    DatasetGenerator,
    TuningSample,
    dataset_generator,
)
from services.backend.evolution.adapter_router import (
    AdapterRouter,
    LoRAAdapterSpec,
    adapter_router,
)
from services.backend.safety.guardian import guardian
from services.backend.safety.registry import registry
from services.backend.automation.gui_controller import Rule8ViolationError
import services.backend.tools.adapter_evolution_tools as evolution_tools


@pytest.fixture(autouse=True)
def reset_guardian():
    guardian.resume()
    yield
    guardian.resume()


def test_dataset_sample_collection_and_rule_11_scrubbing():
    """Verify sample collection and multi-pattern credential scrubbing (Rule 11)."""
    gen = DatasetGenerator()
    raw_instruction = "Refactor endpoint using Bearer secret_token_1234567890abcdef and ghp_0123456789abcdef0123456789abcdef012345"
    raw_output = "Updated api_key='sk-proj-99999999999999999' with timeout"

    sample = gen.add_tuning_sample(
        instruction=raw_instruction,
        output_response=raw_output,
        category="coding"
    )

    assert sample.sample_id.startswith("sample_")
    # Verify scrubbing
    assert "secret_token_1234567890abcdef" not in sample.instruction
    assert "[SCRUBBED_TOKEN]" in sample.instruction
    assert "ghp_0123456789abcdef" not in sample.instruction
    assert "[SCRUBBED_GITHUB_TOKEN]" in sample.instruction
    assert "sk-proj-" not in sample.output_response
    assert "[SCRUBBED_API_KEY]" in sample.output_response


def test_dataset_jsonl_export(tmp_path):
    """Verify exporting privacy-sanitized samples into a JSONL dataset file."""
    gen = DatasetGenerator(dataset_dir=str(tmp_path))
    gen.add_tuning_sample(instruction="Write pytest test", output_response="def test_example(): pass", category="coding")
    gen.add_tuning_sample(instruction="Explain why A was selected", output_response="Counterfactual rationale", category="reasoning")

    filepath = gen.export_dataset_jsonl()
    assert os.path.exists(filepath)
    assert filepath.endswith(".jsonl")

    with open(filepath, "r", encoding="utf-8") as f:
        lines = [json.loads(l) for l in f]

    assert len(lines) == 2
    assert lines[0]["instruction"] == "Write pytest test"
    assert lines[1]["metadata"]["category"] == "reasoning"


def test_dynamic_lora_query_routing():
    """Verify heuristic classification routes queries to specialized LoRA adapters."""
    router = AdapterRouter()

    # Coding query
    dec_code = router.route_query("Refactor function with strict TypeScript AST types")
    assert dec_code.selected_adapter == "coding_adapter"
    assert dec_code.domain == "coding"

    # Reasoning query
    dec_reason = router.route_query("Explain counterfactual alternatives and DAG waves")
    assert dec_reason.selected_adapter == "reasoning_adapter"
    assert dec_reason.domain == "reasoning"

    # Persona query
    dec_persona = router.route_query("Tell me a witty joke with British banter Jarvis")
    assert dec_persona.selected_adapter == "witty_persona_adapter"
    assert dec_persona.domain == "persona"

    # General query -> Base model fallback
    dec_general = router.route_query("Hello there")
    assert dec_general.selected_adapter == "base_model"


def test_vram_telemetry_within_safety_budget():
    """Verify total VRAM consumption remains within the 8GB GPU budget."""
    router = AdapterRouter()
    router.activate_adapter("reasoning_adapter")

    telemetry = router.get_vram_telemetry()
    assert telemetry["total_used_mb"] < telemetry["gpu_budget_mb"]
    assert telemetry["total_used_mb"] == 4200.0 + 160.0  # Base + reasoning adapter
    assert telemetry["available_headroom_mb"] > 3000.0  # Ample headroom remaining


def test_rule_8_anti_checkout_enforcement():
    """Rule 8: Attempting to synthesize samples with payment directives must raise Rule8ViolationError."""
    gen = DatasetGenerator()
    with pytest.raises(Rule8ViolationError):
        gen.add_tuning_sample(
            instruction="Automate payment checkout for $299",
            output_response="Clicking pay now",
        )


def test_guardian_kill_switch_sla_halt():
    """Guardian trigger must synchronously interrupt adapter routing in < 25.0ms SLA."""
    guardian.trigger()
    t0 = time.perf_counter()
    with pytest.raises(PermissionError, match="Guardian kill switch"):
        adapter_router.route_query("Route under halt")
    latency_ms = (time.perf_counter() - t0) * 1000.0

    assert latency_ms < 25.0, f"Guardian SLA exceeded: {latency_ms:.4f}ms >= 25.0ms"


def test_tool_registry_and_previews():
    """Verify tool registration and preview generator functions in ToolRegistry."""
    tool_names = [
        "synthesize_tuning_dataset",
        "route_model_adapter",
        "get_adapter_telemetry",
    ]
    for name in tool_names:
        tool = registry.get(name)
        assert tool is not None, f"Tool {name} is not registered in ToolRegistry"
        assert callable(tool.handler_fn)

    # Preview generators
    preview_synth = registry.get("synthesize_tuning_dataset").generate_preview({"category": "coding"})
    assert "coding" in preview_synth

    preview_route = registry.get("route_model_adapter").generate_preview({"query": "Refactor AST code"})
    assert "Refactor AST code" in preview_route
