"""Phenom Autonomous Neuro-Symbolic Diagnostic & Self-Healing Kernel Subsystem.

Provides runtime traceback analysis, AST fault localization, deterministic patch
synthesis, and reversible transaction rollbacks (HEAL-01, SYM-02).
"""

from services.backend.healing.diagnostic_engine import (
    DiagnosticEngine,
    diagnostic_engine,
    DiagnosticReport,
)
from services.backend.healing.patch_synthesizer import (
    PatchSynthesizer,
    patch_synthesizer,
    HealingPatchResult,
)

__all__ = [
    "DiagnosticEngine",
    "diagnostic_engine",
    "DiagnosticReport",
    "PatchSynthesizer",
    "patch_synthesizer",
    "HealingPatchResult",
]
