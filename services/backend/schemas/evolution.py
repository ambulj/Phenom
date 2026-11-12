"""
Autonomous Neuro-Evolution & Dynamic LoRA Tuning Schemas (EVO-01, SAF-01, SAF-02).
Defines Pydantic v2 models for:
- Synthetic instruction distillation from dream schemas
- Local parameter-efficient LoRA adapter metadata and training metrics
- Regression benchmark evaluation reports and quality thresholds
- Safety tool argument schemas for adapter lifecycle management
"""

import time
from enum import Enum
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field, ConfigDict


class AdapterStatus(str, Enum):
    ACTIVE = "ACTIVE"
    STANDBY = "STANDBY"
    TRAINING = "TRAINING"
    EVALUATING = "EVALUATING"
    QUARANTINED = "QUARANTINED"
    ARCHIVED = "ARCHIVED"


class SyntheticInstructionPair(BaseModel):
    """Distilled instruction, context, and desired response derived from generalized cognitive schemas."""
    model_config = ConfigDict(use_enum_values=True)

    pair_id: str = Field(..., description="Unique instruction pair identifier")
    domain: str = Field(..., description="Problem domain (e.g., coding, system, planning)")
    instruction: str = Field(..., description="Target system prompt or user query")
    input_context: str = Field(default="", description="Relevant contextual parameters or code context")
    desired_response: str = Field(..., description="Exemplar output or synthesized heuristic response")
    source_schema_id: Optional[str] = Field(default=None, description="Source GeneralizedSchema ID")
    quality_score: float = Field(default=1.0, ge=0.0, le=1.0, description="Confidence rating of synthetic pair")
    created_at: float = Field(default_factory=time.time, description="Creation epoch timestamp")


class EvaluationBenchmarkReport(BaseModel):
    """Local benchmark evaluation metrics validating adapter performance against core regression sets."""
    model_config = ConfigDict(use_enum_values=True)

    report_id: str = Field(..., description="Unique evaluation report ID")
    adapter_id: str = Field(..., description="Evaluated adapter ID")
    accuracy_score: float = Field(..., ge=0.0, le=1.0, description="Task completion accuracy (0.0 - 1.0)")
    latency_ms: float = Field(..., description="Average inference latency in milliseconds")
    regression_detected: bool = Field(default=False, description="Whether core command regressions were detected")
    dataset_size: int = Field(default=50, description="Number of validation probe items tested")
    passed_threshold: bool = Field(..., description="Whether adapter passed promotion quality threshold (>= 0.85)")
    timestamp: float = Field(default_factory=time.time, description="Evaluation timestamp")


class AdapterMetadata(BaseModel):
    """Configuration and telemetry for a local parameter-efficient LoRA adapter."""
    model_config = ConfigDict(use_enum_values=True)

    adapter_id: str = Field(..., description="Unique adapter identifier (e.g., lora_coding_v1)")
    domain: str = Field(..., description="Specialization domain")
    base_model: str = Field(default="8b-instruct", description="Target base neural weights")
    lora_rank: int = Field(default=8, ge=2, le=64, description="LoRA rank r")
    lora_alpha: int = Field(default=16, ge=4, le=128, description="LoRA scaling alpha")
    training_loss: float = Field(default=0.0, description="Final training loss on local dataset")
    benchmark_score: float = Field(default=0.0, description="Regression benchmark score")
    status: AdapterStatus = Field(default=AdapterStatus.STANDBY, description="Current operational state")
    dataset_pairs_count: int = Field(default=0, description="Number of instruction pairs trained on")
    created_at: float = Field(default_factory=time.time, description="Creation epoch timestamp")
    is_active: bool = Field(default=False, description="Whether this adapter is currently mounted")


class EvolutionEngineStatus(BaseModel):
    """Comprehensive telemetry of the Autonomous Neuro-Evolution Engine."""
    model_config = ConfigDict(use_enum_values=True)

    is_running: bool = Field(default=True, description="Whether evolution engine is operational")
    is_halted: bool = Field(default=False, description="Whether engine is halted by Guardian kill switch")
    active_adapter: Optional[AdapterMetadata] = Field(default=None, description="Currently mounted active LoRA adapter")
    registered_adapters: List[AdapterMetadata] = Field(default_factory=list, description="All known local adapters")
    total_instructions_distilled: int = Field(default=0, description="Total synthetic instruction pairs distilled")
    last_tuning_timestamp: Optional[float] = Field(default=None, description="Epoch timestamp of last fine-tuning run")
    last_benchmark_report: Optional[EvaluationBenchmarkReport] = Field(default=None, description="Latest benchmark results")


# ==========================================
# Tool Argument Schemas (SAF-01)
# ==========================================

class EvolutionGetStatusArgs(BaseModel):
    """Arguments for querying neuro-evolution status and active adapters (Tier 0)."""
    model_config = ConfigDict(extra="forbid")


class EvolutionDistillInstructionsArgs(BaseModel):
    """Arguments for distilling synthetic instruction pairs from dream schemas (Tier 1)."""
    model_config = ConfigDict(extra="forbid")

    domain: Optional[str] = Field(default=None, description="Optional target domain filter (e.g. coding, system)")
    max_pairs: int = Field(default=20, ge=1, le=100, description="Maximum number of instruction pairs to distill")


class EvolutionTrainAdapterArgs(BaseModel):
    """Arguments for initiating local parameter-efficient adapter fine-tuning (Tier 1)."""
    model_config = ConfigDict(extra="forbid")

    adapter_id: str = Field(..., description="Identifier for the new or updated adapter")
    domain: str = Field(..., description="Target specialization domain")
    lora_rank: int = Field(default=8, ge=2, le=64, description="LoRA rank r (default: 8)")
    lora_alpha: int = Field(default=16, ge=4, le=128, description="LoRA alpha (default: 16)")
    epochs: int = Field(default=3, ge=1, le=10, description="Training epochs (default: 3)")


class EvolutionActivateAdapterArgs(BaseModel):
    """Arguments for activating a validated adapter (Tier 1)."""
    model_config = ConfigDict(extra="forbid")

    adapter_id: str = Field(..., description="Identifier of the adapter to mount")


class EvolutionRollbackAdapterArgs(BaseModel):
    """Arguments for rolling back to the previous stable adapter or base model (Tier 1)."""
    model_config = ConfigDict(extra="forbid")

    target_adapter_id: Optional[str] = Field(default=None, description="Optional target adapter ID (None rolls back to previous adapter)")
    reset_to_base: bool = Field(default=False, description="Reset to sovereign base model weights")
