"""
Reflection Vault Logger & Metacognitive Post-Mortem Writer.
Persists structured reflection notes into `.phenom/reflection/` with YAML frontmatter
and actionable self-improvement mitigations.

Part of Phenom 23.0 Sovereign Neural Evolution (COG-01.1).
"""

import os
import time
from typing import Dict, Any, Optional

from services.backend.safety.guardian import guardian
from services.backend.metacognition.reflective_auditor import TrajectoryAudit


class ReflectionVaultLogger:
    """
    Writes structured markdown reflection logs into the local workspace reflection directory.
    """

    def __init__(self, reflection_dir: Optional[str] = None):
        self.reflection_dir = reflection_dir or os.path.join(
            os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
            ".phenom",
            "reflection"
        )
        os.makedirs(self.reflection_dir, exist_ok=True)

    def log_reflection_note(self, audit: TrajectoryAudit) -> str:
        """
        Formats and saves a structured reflection post-mortem note.
        Strictly verifies Guardian kill switch (< 25.0ms SLA).
        """
        if guardian.is_halted:
            raise PermissionError("Guardian kill switch is active. Reflection note logging halted.")

        filename = f"REFLECTION_{audit.audit_id}.md"
        filepath = os.path.join(self.reflection_dir, filename)

        iso_time = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(audit.created_at))

        content = f"""---
audit_id: "{audit.audit_id}"
date: "{iso_time}"
epistemic_confidence: {audit.epistemic_confidence}
calibration_score: {audit.calibration_score}
successful_steps: {audit.successful_steps}
failed_steps: {audit.failed_steps}
tags:
  - metacognition
  - reflection
  - calibration
---

# Metacognitive Reflection: {audit.audit_id}

## User Intent
> {audit.user_intent}

## Execution Trajectory Summary
- **Total Steps Executed**: {audit.steps_count}
- **Successful**: {audit.successful_steps}
- **Failed**: {audit.failed_steps}
- **Calibration Accuracy**: {int(audit.calibration_score * 100)}%

## Root Cause Analysis
{audit.root_cause_analysis or "Nominal execution without failure."}

## Suggested Prompt & Planning Mitigation
{audit.suggested_prompt_mitigation or "Continue with baseline execution model."}
"""

        with open(filepath, "w", encoding="utf-8") as f:
            f.write(content)

        return filepath


# Global singleton
reflection_vault_logger = ReflectionVaultLogger()
