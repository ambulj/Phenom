"""
Unit Tests for Neuro-Evolution Engine & Local LoRA Adapter Lifecycle (EVO-01, SAF-02).
Verifies:
- Synthetic instruction distillation from dream schemas & quality scoring
- Local adapter training simulation with loss tracking
- Regression benchmark evaluation & quality promotion gating
- Hot-swapping and atomic rollback to previous checkpoint / base weights
- Synchronous Guardian halt and clean reset
"""

import pytest
from services.backend.evolution.instruction_distiller import InstructionDistiller
from services.backend.evolution.adapter_manager import LocalAdapterManager
from services.backend.schemas.dream import GeneralizedSchema
from services.backend.schemas.evolution import AdapterStatus


class DummyDreamEngine:
    def __init__(self, schemas):
        self._schemas = schemas

    def get_schemas(self):
        return self._schemas


def test_instruction_distiller_from_schemas():
    """Verify synthetic instruction pair distillation from high-confidence schemas."""
    schemas = [
        GeneralizedSchema(
            schema_id="sch_1",
            domain="coding",
            heuristic_rule="Always write automated tests before committing new tools",
            confidence=0.92,
        ),
        GeneralizedSchema(
            schema_id="sch_2",
            domain="system",
            heuristic_rule="Low confidence rule to ignore",
            confidence=0.45,
        ),
    ]
    dummy_dream = DummyDreamEngine(schemas)
    distiller = InstructionDistiller(dream_eng=dummy_dream)

    pairs = distiller.distill_from_schemas(max_pairs=10)
    assert len(pairs) == 1
    assert pairs[0].domain == "coding"
    assert pairs[0].quality_score == 0.92
    assert "Always write automated tests" in pairs[0].instruction


def test_instruction_distiller_baseline_fallback():
    """Verify fallback baseline instruction generation when no schemas exist."""
    dummy_dream = DummyDreamEngine([])
    distiller = InstructionDistiller(dream_eng=dummy_dream)

    pairs = distiller.distill_from_schemas(domain_filter="planning")
    assert len(pairs) == 1
    assert pairs[0].domain == "planning"
    assert pairs[0].quality_score == 0.95


def test_adapter_training_and_benchmark():
    """Verify adapter training produces valid metadata and regression report."""
    distiller = InstructionDistiller(dream_eng=DummyDreamEngine([]))
    mgr = LocalAdapterManager(distiller=distiller)

    # Train adapter
    adapter = mgr.train_adapter(
        adapter_id="lora_coding_v1",
        domain="coding",
        lora_rank=8,
        lora_alpha=16,
        epochs=3,
    )
    assert adapter.adapter_id == "lora_coding_v1"
    assert adapter.training_loss < 0.5
    assert adapter.benchmark_score >= 0.85
    assert adapter.status == AdapterStatus.STANDBY
    assert adapter.is_active is False

    status = mgr.get_status()
    assert len(status.registered_adapters) == 1
    assert status.last_benchmark_report is not None
    assert status.last_benchmark_report.passed_threshold is True


def test_adapter_activation_and_rollback():
    """Verify mounting, quality gate rejection, and atomic rollback."""
    distiller = InstructionDistiller(dream_eng=DummyDreamEngine([]))
    mgr = LocalAdapterManager(distiller=distiller)

    # 1. Train 2 adapters
    a1 = mgr.train_adapter("lora_v1", domain="coding", epochs=3)
    a2 = mgr.train_adapter("lora_v2", domain="coding", epochs=4)

    # 2. Activate a1
    mounted_1 = mgr.activate_adapter("lora_v1")
    assert mounted_1.is_active is True
    assert mgr.get_status().active_adapter.adapter_id == "lora_v1"

    # 3. Hot-swap to a2
    mounted_2 = mgr.activate_adapter("lora_v2")
    assert mounted_2.is_active is True
    assert mgr._adapters["lora_v1"].is_active is False
    assert mgr.get_status().active_adapter.adapter_id == "lora_v2"

    # 4. Atomic rollback to previous (a1)
    rolled_back = mgr.rollback_adapter()
    assert rolled_back is not None
    assert rolled_back.adapter_id == "lora_v1"
    assert rolled_back.is_active is True

    # 5. Rollback to base model
    base = mgr.rollback_adapter(reset_to_base=True)
    assert base is None
    assert mgr.get_status().active_adapter is None


def test_adapter_activation_blocks_quarantined():
    """Verify adapters that fail benchmark cannot be activated."""
    distiller = InstructionDistiller(dream_eng=DummyDreamEngine([]))
    mgr = LocalAdapterManager(distiller=distiller)

    # Train with 0 epochs / low benchmark score
    a_poor = mgr.train_adapter("lora_poor", domain="coding", epochs=1)
    # Manually drop score below threshold
    a_poor.benchmark_score = 0.60
    a_poor.status = AdapterStatus.QUARANTINED

    with pytest.raises(ValueError, match="failed quality threshold"):
        mgr.activate_adapter("lora_poor")


def test_adapter_manager_guardian_halt():
    """Verify Guardian halt immediately terminates adapter operations."""
    distiller = InstructionDistiller(dream_eng=DummyDreamEngine([]))
    mgr = LocalAdapterManager(distiller=distiller)

    mgr.halt()
    assert mgr.is_halted() is True

    with pytest.raises(PermissionError, match="Adapter training halted"):
        mgr.train_adapter("test", "coding")

    with pytest.raises(PermissionError, match="Adapter activation halted"):
        mgr.activate_adapter("test")

    with pytest.raises(PermissionError, match="Adapter rollback halted"):
        mgr.rollback_adapter()

    mgr.reset()
    assert mgr.is_halted() is False
