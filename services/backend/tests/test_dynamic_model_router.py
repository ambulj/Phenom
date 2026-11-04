"""
Unit Test Suite for Task-Aware Dynamic Multi-Model Router & VRAM Swapper (MOD-01, SAF-01, SAF-02)
Verifies:
1. Heuristic intent classification across code, reasoning, and conversational queries (< 0.1ms).
2. Dynamic model dispatching (Qwen Coder 14B, Llama 3 8B Reasoner, Qwen 3.5 4B Fast Chat).
3. System-wide manual routing override and reset behavior.
4. VRAM protection under gaming mode (downgrading to 4B lightweight model).
5. Seamless integration with ModelRouter.route_request().
6. Direct voice intents for model switching and status inspection.
7. Sub-25ms universal synchronous Guardian SLA verification.
"""

import pytest
import time
from unittest.mock import patch

from services.backend.router.dynamic_model_router import (
    dynamic_model_router,
    MODEL_FAST_CHAT,
    MODEL_CODER,
    MODEL_REASONER,
    MODEL_FALLBACK,
    get_active_model_routing,
    set_model_routing_override,
    benchmark_model_switch
)
from services.backend.router.router import ModelRouter
from services.backend.orchestrator.engine import Orchestrator
from services.backend.safety.guardian import guardian
from services.backend.safety.registry import registry


@pytest.fixture(autouse=True)
def reset_router_state():
    """Resets router overrides and Guardian state before each test."""
    dynamic_model_router.set_override(None)
    guardian._halted = False
    yield
    dynamic_model_router.set_override(None)
    guardian._halted = False


def test_dynamic_router_safety_tiers():
    """Asserts model routing tools adhere to strict safety tiers in ToolRegistry."""
    get_tool = registry.get("get_active_model_routing")
    override_tool = registry.get("set_model_routing_override")
    bench_tool = registry.get("benchmark_model_switch")

    assert get_tool is not None and get_tool.tier == 0
    assert bench_tool is not None and bench_tool.tier == 0
    assert override_tool is not None and override_tool.tier == 1


def test_intent_classification_heuristics():
    """Tests zero-latency intent classification accuracy."""
    # Code queries
    assert dynamic_model_router.classify_intent("def binary_search(arr, target): return -1") == "code"
    assert dynamic_model_router.classify_intent("```python\nimport os\nprint(os.getcwd())\n```") == "code"
    assert dynamic_model_router.classify_intent("Write a SQL query to select all active users from database") == "code"
    assert dynamic_model_router.classify_intent("Can you implement a regex for email validation in app.ts?") == "code"

    # Reasoning queries
    assert dynamic_model_router.classify_intent("Why is time dilation observed in special relativity?") == "reasoning"
    assert dynamic_model_router.classify_intent("Compare the architectural trade-offs between Monolith and Microservices") == "reasoning"
    assert dynamic_model_router.classify_intent("Analyze the root cause of this deadlock condition step by step") == "reasoning"

    # Chat / Banter queries
    assert dynamic_model_router.classify_intent("Hello Phenom, what's up?") == "chat"
    assert dynamic_model_router.classify_intent("Tell me a funny joke Bro") == "chat"
    assert dynamic_model_router.classify_intent("What's the weather like?") == "chat"


def test_dynamic_model_resolution():
    """Verifies queries map to specialized local models."""
    # Code prompt -> Qwen Coder 14B
    m_code, task_code, vram_code, reason_code = dynamic_model_router.resolve_target_model(
        "Write an async FastAPI endpoint for user authentication"
    )
    assert m_code == MODEL_CODER
    assert task_code == "code"
    assert vram_code == 9200
    assert "Qwen 2.5 Coder 14B" in reason_code

    # Reasoning prompt -> Llama 3 8B
    m_reason, task_reason, vram_reason, reason_reason = dynamic_model_router.resolve_target_model(
        "Why do capacitors block DC current while passing AC signals?"
    )
    assert m_reason == MODEL_REASONER
    assert task_reason == "reasoning"
    assert vram_reason == 8500
    assert "Llama 3 8B" in reason_reason

    # Chat prompt -> Qwen 3.5 4B Fast Chat
    m_chat, task_chat, vram_chat, reason_chat = dynamic_model_router.resolve_target_model(
        "Good morning Bro! How are you doing today?"
    )
    assert m_chat == MODEL_FAST_CHAT
    assert task_chat == "chat"
    assert vram_chat == 2800


def test_manual_model_routing_override():
    """Tests locking model routing to a specific model and clearing override."""
    # Lock to Reasoner
    dynamic_model_router.set_override(MODEL_REASONER)
    assert dynamic_model_router.manual_override == MODEL_REASONER

    # Even code prompt must now route to the locked model
    m, task, _, reason = dynamic_model_router.resolve_target_model("def calculate_pi(): return 3.14")
    assert m == MODEL_REASONER
    assert "Manual override locked" in reason

    # Clear override
    dynamic_model_router.set_override(None)
    assert dynamic_model_router.manual_override is None

    # Resumes dynamic routing
    m_resumed, _, _, _ = dynamic_model_router.resolve_target_model("def calculate_pi(): return 3.14")
    assert m_resumed == MODEL_CODER


def test_gaming_mode_vram_protection():
    """Tests that active gaming mode forces lightweight 4B model to protect GPU FPS."""
    from services.backend.resource.vram_manager import vram_manager

    with patch.object(vram_manager, "gaming_mode_active", True):
        # Code query would normally take 9.2GB VRAM; gaming mode forces 2.8GB 4B model
        m, task, vram, reason = dynamic_model_router.resolve_target_model("Write a complex Rust compiler optimization")
        assert m == MODEL_FAST_CHAT
        assert vram == 2800
        assert "Gaming mode active" in reason


@pytest.mark.asyncio
async def test_model_router_route_request_integration():
    """Verifies that ModelRouter.route_request() leverages dynamic local dispatch."""
    router = ModelRouter()

    # Code query stays local on Coder model
    code_prompt = "Implement a quicksort algorithm in python"
    model_name, backend, meta = await router.route_request(code_prompt)
    assert backend == "local"
    assert model_name == MODEL_CODER
    assert meta["task_type"] == "code"
    assert meta["vram_estimated_mb"] == 9200

    # Conversational query stays local on Fast 4B model
    chat_prompt = "Hello Phenom Bro, let's catch up"
    chat_model, chat_backend, chat_meta = await router.route_request(chat_prompt)
    assert chat_backend == "local"
    assert chat_model == MODEL_FAST_CHAT
    assert chat_meta["task_type"] == "chat"


@pytest.mark.asyncio
async def test_direct_voice_intents_model_routing():
    """Verifies direct voice commands for model switching map accurately in Orchestrator."""
    orchestrator = Orchestrator()

    intent_coder = orchestrator._detect_direct_intent("force coder model")
    assert intent_coder is not None
    assert intent_coder[0] == "set_model_routing_override"
    assert intent_coder[1]["model_name"] == MODEL_CODER

    intent_reason = orchestrator._detect_direct_intent("force reasoning model")
    assert intent_reason is not None
    assert intent_reason[0] == "set_model_routing_override"
    assert intent_reason[1]["model_name"] == MODEL_REASONER

    intent_fast = orchestrator._detect_direct_intent("force fast model")
    assert intent_fast is not None
    assert intent_fast[0] == "set_model_routing_override"
    assert intent_fast[1]["model_name"] == MODEL_FAST_CHAT

    intent_auto = orchestrator._detect_direct_intent("auto model routing")
    assert intent_auto is not None
    assert intent_auto[0] == "set_model_routing_override"
    assert intent_auto[1]["model_name"] is None

    intent_status = orchestrator._detect_direct_intent("active model")
    assert intent_status is not None
    assert intent_status[0] == "get_active_model_routing"


@pytest.mark.asyncio
async def test_benchmark_model_switch_tool():
    """Verifies the diagnostic benchmark tool measures sub-1ms intent classification latency."""
    res = await benchmark_model_switch()
    assert res["status"] == "success"
    assert res["total_evaluations"] == 500
    assert res["avg_latency_per_query_ms"] < 1.0


def test_guardian_sla_model_routing_benchmark():
    """
    SAF-02 Benchmark:
    Verifies that model routing resolution and Guardian halt checks execute in < 25ms SLA
    (target < 1.0ms typical).
    """
    durations = []
    iterations = 50

    for _ in range(iterations):
        t0 = time.perf_counter()
        m, task, vram, _ = dynamic_model_router.resolve_target_model(
            "def optimize_neural_weights(gradient: np.ndarray) -> np.ndarray: return gradient * 0.01"
        )
        is_halted = guardian.is_halted
        elapsed_ms = (time.perf_counter() - t0) * 1000.0
        durations.append(elapsed_ms)

    avg_ms = sum(durations) / len(durations)
    max_ms = max(durations)
    print(f"\n[Dynamic Model Routing SLA Benchmark] {iterations} iterations: avg={avg_ms:.4f}ms, max={max_ms:.4f}ms (< 25ms SLA)")

    assert max_ms < 25.0, f"Max routing latency {max_ms}ms exceeded 25ms SLA"
    assert avg_ms < 25.0, f"Average routing latency {avg_ms}ms exceeded 25ms SLA"
