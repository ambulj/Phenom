"""
Safety-Wrapped LoRA Adapter Evolution & Dataset Synthesis Tools.
Registers tools with ToolRegistry for PEFT/LoRA adapter routing, VRAM telemetry,
and privacy-preserving dataset synthesis (Phase 23-02 ADA-01 / MOD-02).
"""

from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field

from services.backend.safety.registry import registry
from services.backend.evolution.dataset_generator import dataset_generator
from services.backend.evolution.adapter_router import adapter_router


# ==========================================
# 1. Synthesize Tuning Dataset (Tier 1)
# ==========================================

class SynthesizeTuningDatasetArgs(BaseModel):
    category: Optional[str] = Field(default=None, description="Filter category e.g. coding, reasoning, persona")

def synthesize_tuning_dataset_preview(args: Dict[str, Any]) -> str:
    c = args.get("category", "all")
    return f"Export privacy-sanitized instruction tuning dataset for '{c}' to .phenom/datasets/."

@registry.register(
    name="synthesize_tuning_dataset",
    tier=1,
    description="Compiles collected and sanitized user interactions into a local JSONL fine-tuning dataset.",
    args_schema=SynthesizeTuningDatasetArgs,
    preview_fn=synthesize_tuning_dataset_preview,
    can_remember_per_folder=False
)
def handle_synthesize_tuning_dataset(
    category: Optional[str] = None
) -> Dict[str, Any]:
    filepath = dataset_generator.export_dataset_jsonl(category=category)
    stats = dataset_generator.get_dataset_stats()
    return {
        "status": "exported",
        "filepath": filepath,
        "category": category or "all",
        "total_samples": stats["total_samples"],
    }


# ==========================================
# 2. Route Model Adapter (Tier 0)
# ==========================================

class RouteModelAdapterArgs(BaseModel):
    query: str = Field(..., description="User query or task prompt to classify and route")

def route_model_adapter_preview(args: Dict[str, Any]) -> str:
    q = args.get("query", "query")
    return f"Evaluate task intent and route to specialized LoRA adapter for '{q[:45]}...'."

@registry.register(
    name="route_model_adapter",
    tier=0,
    description="Selects the optimal specialized LoRA adapter (coding, reasoning, persona, base) based on task intent.",
    args_schema=RouteModelAdapterArgs,
    preview_fn=route_model_adapter_preview,
    can_remember_per_folder=False
)
def handle_route_model_adapter(query: str) -> Dict[str, Any]:
    decision = adapter_router.route_query(query)
    return decision.model_dump()


# ==========================================
# 3. Get Adapter Telemetry (Tier 0)
# ==========================================

class GetAdapterTelemetryArgs(BaseModel):
    pass

def get_adapter_telemetry_preview(args: Dict[str, Any]) -> str:
    return "Inspect active LoRA adapter weights, GPU VRAM allocation, and fine-tuning dataset statistics."

@registry.register(
    name="get_adapter_telemetry",
    tier=0,
    description="Returns GPU VRAM consumption, active LoRA adapter status, and dataset sample counts.",
    args_schema=GetAdapterTelemetryArgs,
    preview_fn=get_adapter_telemetry_preview,
    can_remember_per_folder=False
)
def handle_get_adapter_telemetry() -> Dict[str, Any]:
    vram = adapter_router.get_vram_telemetry()
    dataset = dataset_generator.get_dataset_stats()
    return {
        "vram_telemetry": vram,
        "dataset_stats": dataset,
        "available_adapters": [a.model_dump() for a in adapter_router.list_adapters()],
    }


# Programmatic aliases
synthesize_tuning_dataset = handle_synthesize_tuning_dataset
route_model_adapter = handle_route_model_adapter
get_adapter_telemetry = handle_get_adapter_telemetry
