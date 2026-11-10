"""
Safety-Wrapped Metacognitive Auditing & Reflection Tools.
Registers tools with ToolRegistry for post-execution trajectory auditing,
calibration score calculation, and reflection note logging (Phase 23-01 META-01 / COG-01).
"""

from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field

from services.backend.safety.registry import registry
from services.backend.metacognition.reflective_auditor import (
    reflective_auditor,
    ExecutionStep,
    TrajectoryAudit,
)
from services.backend.metacognition.reflection_vault_logger import reflection_vault_logger


# ==========================================
# 1. Audit Execution Trajectory (Tier 0)
# ==========================================

class AuditExecutionTrajectoryArgs(BaseModel):
    user_intent: str = Field(..., description="Original goal or user prompt")
    steps: List[Dict[str, Any]] = Field(..., description="List of ExecutionStep dictionaries")
    prior_confidence: Optional[float] = Field(default=0.90, description="Estimated confidence before run (0.0 to 1.0)")

def audit_execution_trajectory_preview(args: Dict[str, Any]) -> str:
    intent = args.get("user_intent", "task")
    steps_len = len(args.get("steps", []))
    return f"Audit trajectory of {steps_len} steps against user intent '{intent[:45]}...'."

@registry.register(
    name="audit_execution_trajectory",
    tier=0,
    description="Audits completed tool execution trajectory, calculates epistemic confidence and calibration accuracy scores.",
    args_schema=AuditExecutionTrajectoryArgs,
    preview_fn=audit_execution_trajectory_preview,
    can_remember_per_folder=False
)
def handle_audit_execution_trajectory(
    user_intent: str,
    steps: List[Dict[str, Any]],
    prior_confidence: Optional[float] = 0.90,
) -> Dict[str, Any]:
    step_objs = [ExecutionStep(**s) for s in steps]
    audit = reflective_auditor.audit_trajectory(
        user_intent=user_intent,
        steps=step_objs,
        prior_confidence=prior_confidence or 0.90,
    )
    return audit.model_dump()


# ==========================================
# 2. Record Reflection Note (Tier 1)
# ==========================================

class RecordReflectionNoteArgs(BaseModel):
    audit_id: str = Field(..., description="Trajectory audit identifier to persist as reflection note")

def record_reflection_note_preview(args: Dict[str, Any]) -> str:
    aid = args.get("audit_id", "audit")
    return f"Persist structured metacognitive reflection note for audit '{aid}' under .phenom/reflection/."

@registry.register(
    name="record_reflection_note",
    tier=1,
    description="Writes a structured post-mortem reflection note with frontmatter metadata to .phenom/reflection/.",
    args_schema=RecordReflectionNoteArgs,
    preview_fn=record_reflection_note_preview,
    can_remember_per_folder=False
)
def handle_record_reflection_note(audit_id: str) -> Dict[str, Any]:
    audit = reflective_auditor.get_audit(audit_id)
    if not audit:
        return {"error": f"Trajectory audit '{audit_id}' not found"}

    filepath = reflection_vault_logger.log_reflection_note(audit)
    return {
        "status": "recorded",
        "audit_id": audit_id,
        "filepath": filepath,
        "calibration_score": audit.calibration_score,
    }


# ==========================================
# 3. Get Metacognitive Calibration Stats (Tier 0)
# ==========================================

class GetMetacognitiveCalibrationStatsArgs(BaseModel):
    pass

def get_metacognitive_calibration_stats_preview(args: Dict[str, Any]) -> str:
    return "Inspect aggregate metacognitive calibration scores and recent execution trajectory audits."

@registry.register(
    name="get_metacognitive_calibration_stats",
    tier=0,
    description="Returns aggregate confidence calibration metrics, audit counts, and drift statistics.",
    args_schema=GetMetacognitiveCalibrationStatsArgs,
    preview_fn=get_metacognitive_calibration_stats_preview,
    can_remember_per_folder=False
)
def handle_get_metacognitive_calibration_stats() -> Dict[str, Any]:
    return reflective_auditor.get_calibration_stats()


# Programmatic aliases
audit_execution_trajectory = handle_audit_execution_trajectory
record_reflection_note = handle_record_reflection_note
get_metacognitive_calibration_stats = handle_get_metacognitive_calibration_stats
