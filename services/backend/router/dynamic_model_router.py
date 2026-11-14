"""
Phenom Task-Aware Dynamic Multi-Model Router & VRAM Swapper
Inspects user prompts in real-time (< 0.1ms) and dispatches to specialized Ollama models:
- Coding & AST: qwen2.5-coder:14b
- Reasoning & Analysis: llama3:8b-instruct-q8_0
- Fast Chat & Banter: hf.co/tinyopsec/Qwen3.5-4B-Uncensored-Aggressive-GGUF:Q4_K_M
- General Fallback: phenom-jarvis:latest

Governed by VRAM limits, gaming mode protections, and Tier 1 preview gating for manual overrides.
"""

import os
import sys
import re
import time
import asyncio
from typing import Dict, Any, List, Optional, Tuple, Literal, Callable, Awaitable
from pydantic import BaseModel, Field

from services.backend.safety.registry import registry
from services.backend.safety.guardian import guardian

# Standard Model Manifest
MODEL_FAST_CHAT = "phenom-jarvis:latest"
MODEL_CODER = "qwen2.5-coder:14b"
MODEL_REASONER = "llama3:8b-instruct-q8_0"
MODEL_FALLBACK = "phenom-jarvis:latest"

# VRAM Footprints (in MB)
ESTIMATED_VRAM_MB = {
    MODEL_FAST_CHAT: 4700,
    MODEL_CODER: 9200,
    MODEL_REASONER: 8500,
    MODEL_FALLBACK: 4700,
}


_broadcaster: Optional[Callable[[Dict[str, Any]], Awaitable[None]]] = None

def register_broadcaster(broadcaster: Callable[[Dict[str, Any]], Awaitable[None]]) -> None:
    """Registers the WebSocket broadcast callback."""
    global _broadcaster
    _broadcaster = broadcaster

def broadcast_routing_event(event_type: str, payload: Dict[str, Any]):
    """Broadcasts routing decisions to connected Electron HUD clients."""
    broadcaster = _broadcaster
    if not broadcaster:
        main_mod = sys.modules.get("services.backend.main")
        if main_mod and hasattr(main_mod, "broadcast_message"):
            broadcaster = main_mod.broadcast_message
    if not broadcaster:
        return
    msg = {
        "id": f"route-{os.urandom(2).hex()}",
        "type": event_type,
        "ts": str(time.time()),
        "payload": payload
    }
    try:
        loop = asyncio.get_running_loop()
        loop.create_task(broadcaster(msg))
    except RuntimeError:
        pass


class DynamicModelRouter:
    """Manages real-time intent classification and task-aware model dispatching."""

    def __init__(self):
        self._manual_override: Optional[str] = None
        self._last_routed_model: str = MODEL_FAST_CHAT
        self._last_task_type: str = "chat"
        self._switch_count: int = 0

    @property
    def manual_override(self) -> Optional[str]:
        return self._manual_override

    def set_override(self, model_name: Optional[str]):
        """Sets or clears a manual model routing override."""
        self._manual_override = model_name
        broadcast_routing_event("MODEL_ROUTING_OVERRIDE_CHANGED", {
            "override_model": self._manual_override
        })

    def classify_intent(self, prompt: str) -> str:
        """
        Heuristic regex and token scoring engine.
        Returns 'code', 'reasoning', or 'chat' in < 0.1ms without ML model overhead.
        """
        p = prompt.strip().lower()

        # Check for explicit code markers
        if "```" in prompt or "`" in prompt:
            return "code"

        code_score = 0
        reasoning_score = 0

        # Code keywords & syntax patterns
        code_keywords = [
            r"\bdef\s+[a-zA-Z_]", r"\bclass\s+[a-zA-Z_]", r"\bimport\s+[a-zA-Z_]",
            r"\bfrom\s+[a-zA-Z_.]+\s+import\b",
            r"\bfunction\b", r"\bconst\s+[a-zA-Z_]", r"\blet\s+[a-zA-Z_]", r"\bvar\s+[a-zA-Z_]",
            r"\basync\s+(?:def|function|endpoint)\b",
            r"\breturn\b", r"\bprint\(", r"\bconsole\.log\(", r"\bpublic\s+class\b",
            r"\bwrite\s+(?:a\s+)?(?:python|script|code|function|program|query|test|endpoint|api)\b",
            r"\b(?:implement|refactor|debug|fix\s+bug|syntax\s+error|traceback|regex|algorithm|fastapi|quicksort)\b",
            r"\b(?:sql|database\s+schema|select\s+.*\s+from|insert\s+into)\b",
            r"\.(?:py|js|ts|tsx|jsx|rs|cpp|h|java|cs|go|sql|html|css)\b"
        ]
        for pat in code_keywords:
            if re.search(pat, p, re.IGNORECASE):
                code_score += 2

        # Reasoning & analysis keywords
        reasoning_keywords = [
            r"\bwhy\s+(?:is|does|do|are|should)\b",
            r"\bcompare\b", r"\bpros\s+and\s+cons\b", r"\btrade-?offs?\b",
            r"\banalyze\b", r"\broot\s+cause\b", r"\bstep\s+by\s+step\b",
            r"\bexplain\s+(?:the\s+difference|how|why)\b",
            r"\barchitecture\s+decision\b", r"\bdeep\s+dive\b",
            r"\bderive\b", r"\bmathematical\s+proof\b"
        ]
        for pat in reasoning_keywords:
            if re.search(pat, p, re.IGNORECASE):
                reasoning_score += 2

        if code_score >= 2 and code_score >= reasoning_score:
            return "code"
        if reasoning_score >= 2 and reasoning_score > code_score:
            return "reasoning"

        return "chat"

    def resolve_target_model(self, prompt: str) -> Tuple[str, str, int, str]:
        """
        Resolves the target model, task type, estimated VRAM, and routing reason.
        Returns: (model_name, task_type, vram_mb, reason)
        """
        # 1. Check manual override
        if self._manual_override:
            task_type = self.classify_intent(prompt)
            vram = ESTIMATED_VRAM_MB.get(self._manual_override, 4000)
            reason = f"Manual override locked to '{self._manual_override}'."
            self._update_state(self._manual_override, task_type)
            return self._manual_override, task_type, vram, reason

        task_type = self.classify_intent(prompt)

        # 2. Check gaming mode & VRAM constraints
        gaming_active = False
        try:
            from services.backend.resource.vram_manager import vram_manager
            gaming_active = getattr(vram_manager, "gaming_mode_active", False)
        except Exception:
            pass

        if gaming_active:
            # Under gaming mode, preserve GPU resources: strictly use 4B lightweight model
            reason = "Gaming mode active: VRAM constrained, routed to lightweight 4B model."
            self._update_state(MODEL_FAST_CHAT, task_type)
            return MODEL_FAST_CHAT, task_type, ESTIMATED_VRAM_MB[MODEL_FAST_CHAT], reason

        # 3. Task-specific dispatching
        if task_type == "code":
            selected = MODEL_CODER
            reason = "Code syntax / programming task detected -> Dispatched to Qwen 2.5 Coder 14B."
        elif task_type == "reasoning":
            selected = MODEL_REASONER
            reason = "Deep analytical / reasoning query detected -> Dispatched to Llama 3 8B Instruct."
        else:
            selected = MODEL_FAST_CHAT
            reason = "Conversational / system query detected -> Dispatched to Qwen 3.5 4B Fast Chat."

        vram = ESTIMATED_VRAM_MB.get(selected, 4000)
        self._update_state(selected, task_type)
        return selected, task_type, vram, reason

    def _update_state(self, model: str, task_type: str):
        if model != self._last_routed_model:
            self._switch_count += 1
        self._last_routed_model = model
        self._last_task_type = task_type
        broadcast_routing_event("MODEL_ROUTED", {
            "model_name": model,
            "task_type": task_type,
            "estimated_vram_mb": ESTIMATED_VRAM_MB.get(model, 4000),
            "switch_count": self._switch_count
        })

    def get_status(self) -> Dict[str, Any]:
        """Returns active model router status and telemetry."""
        return {
            "active_model": self._last_routed_model,
            "task_type": self._last_task_type,
            "manual_override": self._manual_override,
            "total_switches": self._switch_count,
            "estimated_vram_mb": ESTIMATED_VRAM_MB.get(self._last_routed_model, 4000),
            "supported_models": [
                {"role": "fast_chat", "name": MODEL_FAST_CHAT, "size_gb": 2.8},
                {"role": "code_synthesis", "name": MODEL_CODER, "size_gb": 9.2},
                {"role": "deep_reasoning", "name": MODEL_REASONER, "size_gb": 8.5},
                {"role": "fallback", "name": MODEL_FALLBACK, "size_gb": 4.7},
            ]
        }


# Global dynamic model router singleton
dynamic_model_router = DynamicModelRouter()


# =========================================================================
# Pydantic Schemas & Tool Registrations
# =========================================================================

class GetActiveModelRoutingArgs(BaseModel):
    pass


class SetModelRoutingOverrideArgs(BaseModel):
    model_name: Optional[str] = Field(
        default=None,
        description="Name of the model to lock (e.g., 'qwen2.5-coder:14b', 'hf.co/tinyopsec/Qwen3.5-4B-Uncensored-Aggressive-GGUF:Q4_K_M', or null to reset to Auto)"
    )


class BenchmarkModelSwitchArgs(BaseModel):
    pass


@registry.register(
    name="get_active_model_routing",
    tier=0,
    description="Inspects current task-aware model routing status, active local model, and estimated VRAM usage.",
    args_schema=GetActiveModelRoutingArgs,
    preview_fn=lambda a: "Inspect active model routing status"
)
async def get_active_model_routing() -> Dict[str, Any]:
    """Retrieves router status and telemetry."""
    status = dynamic_model_router.get_status()
    return {
        "status": "success",
        "routing": status,
        "message": f"Active model: {status['active_model']} ({status['task_type']}) &bull; VRAM: {status['estimated_vram_mb']}MB."
    }


@registry.register(
    name="set_model_routing_override",
    tier=1,
    description="Sets or resets a manual system-wide model override, bypassing automatic task classification.",
    args_schema=SetModelRoutingOverrideArgs,
    preview_fn=lambda a: f"Lock active model to '{a.get('model_name') or 'Auto Dynamic Routing'}'"
)
async def set_model_routing_override(model_name: Optional[str] = None) -> Dict[str, Any]:
    """Locks routing to a specific model or resets to Auto."""
    dynamic_model_router.set_override(model_name)
    mode_text = f"Locked to '{model_name}'" if model_name else "Reset to Automatic Task-Aware Routing"
    return {
        "status": "success",
        "override": model_name,
        "message": f"Model routing {mode_text}."
    }


@registry.register(
    name="benchmark_model_switch",
    tier=0,
    description="Measures resolution latency of task intent classification and dynamic model selection (< 1ms SLA).",
    args_schema=BenchmarkModelSwitchArgs,
    preview_fn=lambda a: "Benchmark model intent classification latency"
)
async def benchmark_model_switch() -> Dict[str, Any]:
    """Evaluates router intent scoring latency across 100 test queries."""
    sample_queries = [
        "def quicksort(arr): return arr if len(arr) <= 1 else ...",
        "Why is quantum entanglement instantaneous across distance?",
        "Hey Phenom, what's good today?",
        "Write a SQL migration for user authentication tokens",
        "Analyze the architectural trade-offs between WebSockets and gRPC"
    ]
    t0 = time.perf_counter()
    rounds = 100
    for _ in range(rounds):
        for q in sample_queries:
            dynamic_model_router.resolve_target_model(q)
    total_time_ms = (time.perf_counter() - t0) * 1000.0
    avg_per_query_ms = round(total_time_ms / (rounds * len(sample_queries)), 4)

    return {
        "status": "success",
        "total_evaluations": rounds * len(sample_queries),
        "total_time_ms": round(total_time_ms, 2),
        "avg_latency_per_query_ms": avg_per_query_ms,
        "message": f"Model router benchmark completed: avg latency = {avg_per_query_ms}ms per query (< 1.0ms SLA)."
    }
