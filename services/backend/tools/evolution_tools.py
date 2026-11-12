"""
Autonomous Neuro-Evolution & Adapter Governance Tools (EVO-01, SAF-01, SAF-02).
Registers Tier 0 and Tier 1 tools for synthetic instruction distillation,
local parameter-efficient adapter fine-tuning, benchmark evaluation, and atomic rollback.
"""

from typing import Dict, Any, Optional

from services.backend.safety.guardian import guardian
from services.backend.safety.registry import registry
from services.backend.schemas.evolution import (
    EvolutionGetStatusArgs,
    EvolutionDistillInstructionsArgs,
    EvolutionTrainAdapterArgs,
    EvolutionActivateAdapterArgs,
    EvolutionRollbackAdapterArgs,
)
from services.backend.evolution.instruction_distiller import instruction_distiller
from services.backend.evolution.adapter_manager import local_adapter_manager


# ==========================================
# Tier 0 Tools (Read-Only)
# ==========================================

@registry.register(
    name="evolution_get_status",
    tier=0,
    description="Queries Neuro-Evolution engine status, active LoRA adapter, and benchmark telemetry (Read-Only)",
    args_schema=EvolutionGetStatusArgs,
    preview_fn=lambda a: "Inspect Neuro-Evolution status and active LoRA adapters (Read-Only)",
)
def evolution_get_status(**kwargs) -> Dict[str, Any]:
    """Inspect neuro-evolution status."""
    status = local_adapter_manager.get_status()
    return {
        "status": "success",
        "evolution_status": status.model_dump(),
    }


# ==========================================
# Tier 1 Tools (Reversible Changes with Preview)
# ==========================================

@registry.register(
    name="evolution_distill_instructions",
    tier=1,
    description="Distills synthetic instruction-response pairs from validated dream schemas (Reversible change with preview)",
    args_schema=EvolutionDistillInstructionsArgs,
    preview_fn=lambda a: (
        f"Distill synthetic instruction training pairs "
        f"(domain={a.get('domain') if isinstance(a, dict) else getattr(a, 'domain', None)}, "
        f"max_pairs={a.get('max_pairs', 20) if isinstance(a, dict) else getattr(a, 'max_pairs', 20)})"
    ),
)
def evolution_distill_instructions(
    domain: Optional[str] = None,
    max_pairs: int = 20,
    **kwargs,
) -> Dict[str, Any]:
    """Distill synthetic instructions."""
    if guardian.is_halted or local_adapter_manager.is_halted():
        raise PermissionError("Evolution operations halted by Guardian kill switch.")

    pairs = instruction_distiller.distill_from_schemas(domain_filter=domain, max_pairs=max_pairs)
    return {
        "status": "success",
        "pairs_count": len(pairs),
        "pairs": [p.model_dump() for p in pairs],
    }


@registry.register(
    name="evolution_train_adapter",
    tier=1,
    description="Executes parameter-efficient local LoRA fine-tuning and benchmark validation (Reversible change with preview)",
    args_schema=EvolutionTrainAdapterArgs,
    preview_fn=lambda a: (
        f"Train local LoRA adapter '{a.get('adapter_id') if isinstance(a, dict) else getattr(a, 'adapter_id', '')}' "
        f"for domain '{a.get('domain') if isinstance(a, dict) else getattr(a, 'domain', '')}' "
        f"(rank={a.get('lora_rank', 8) if isinstance(a, dict) else getattr(a, 'lora_rank', 8)}, "
        f"epochs={a.get('epochs', 3) if isinstance(a, dict) else getattr(a, 'epochs', 3)})"
    ),
)
def evolution_train_adapter(
    adapter_id: str,
    domain: str,
    lora_rank: int = 8,
    lora_alpha: int = 16,
    epochs: int = 3,
    **kwargs,
) -> Dict[str, Any]:
    """Train local adapter."""
    if guardian.is_halted or local_adapter_manager.is_halted():
        raise PermissionError("Evolution operations halted by Guardian kill switch.")

    adapter = local_adapter_manager.train_adapter(
        adapter_id=adapter_id,
        domain=domain,
        lora_rank=lora_rank,
        lora_alpha=lora_alpha,
        epochs=epochs,
    )
    return {
        "status": "success",
        "adapter": adapter.model_dump(),
    }


@registry.register(
    name="evolution_activate_adapter",
    tier=1,
    description="Mounts a trained and benchmark-validated LoRA adapter (Reversible change with preview)",
    args_schema=EvolutionActivateAdapterArgs,
    preview_fn=lambda a: (
        f"Mount and activate validated LoRA adapter '{a.get('adapter_id') if isinstance(a, dict) else getattr(a, 'adapter_id', '')}'"
    ),
)
def evolution_activate_adapter(
    adapter_id: str,
    **kwargs,
) -> Dict[str, Any]:
    """Activate adapter."""
    if guardian.is_halted or local_adapter_manager.is_halted():
        raise PermissionError("Evolution operations halted by Guardian kill switch.")

    adapter = local_adapter_manager.activate_adapter(adapter_id=adapter_id)
    return {
        "status": "success",
        "active_adapter": adapter.model_dump(),
    }


@registry.register(
    name="evolution_rollback_adapter",
    tier=1,
    description="Rolls back active adapter to previous checkpoint or base weights (Reversible change with preview)",
    args_schema=EvolutionRollbackAdapterArgs,
    preview_fn=lambda a: (
        f"Rollback active adapter to "
        f"'{a.get('target_adapter_id') if (isinstance(a, dict) and a.get('target_adapter_id')) else 'previous stable checkpoint / base weights'}'"
    ),
)
def evolution_rollback_adapter(
    target_adapter_id: Optional[str] = None,
    reset_to_base: bool = False,
    **kwargs,
) -> Dict[str, Any]:
    """Rollback adapter."""
    if guardian.is_halted or local_adapter_manager.is_halted():
        raise PermissionError("Evolution operations halted by Guardian kill switch.")

    restored = local_adapter_manager.rollback_adapter(
        target_adapter_id=target_adapter_id,
        reset_to_base=reset_to_base or (target_adapter_id == "base"),
    )
    return {
        "status": "success",
        "restored_adapter": restored.model_dump() if restored else None,
        "is_base_model": restored is None,
    }
