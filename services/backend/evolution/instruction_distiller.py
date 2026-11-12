"""
Autonomous Synthetic Instruction Distiller (EVO-01, SAF-01).
Transforms high-confidence GeneralizedSchema heuristic rules and past execution traces
into structured instruction-response training pairs for parameter-efficient adapter tuning.
"""

import logging
import time
import uuid
from typing import Dict, List, Optional

from services.backend.memory.dream_engine import DreamConsolidationEngine, dream_engine
from services.backend.schemas.dream import GeneralizedSchema
from services.backend.schemas.evolution import SyntheticInstructionPair

logger = logging.getLogger(__name__)


class InstructionDistiller:
    """Distills structured training samples from abstracted cognitive schemas."""

    def __init__(self, dream_eng: Optional[DreamConsolidationEngine] = None) -> None:
        self._dream_engine = dream_eng or dream_engine
        self._distilled_pairs: Dict[str, SyntheticInstructionPair] = {}

    def distill_from_schemas(
        self,
        domain_filter: Optional[str] = None,
        max_pairs: int = 20,
    ) -> List[SyntheticInstructionPair]:
        """
        Extract generalized heuristics from dream engine memory and synthesize instruction pairs.
        """
        schemas = self._dream_engine.get_schemas()
        distilled: List[SyntheticInstructionPair] = []

        for schema in schemas:
            if len(distilled) >= max_pairs:
                break

            if domain_filter and schema.domain.lower() != domain_filter.lower():
                continue

            # Quality gate: only distill high-confidence schemas
            if schema.confidence < 0.7:
                continue

            pair = self._generate_pair_from_schema(schema)
            self._distilled_pairs[pair.pair_id] = pair
            distilled.append(pair)

        # If few schemas exist, synthesize baseline domain training pairs from system heuristics
        if len(distilled) == 0:
            fallback = self._generate_baseline_pair(domain_filter or "coding")
            self._distilled_pairs[fallback.pair_id] = fallback
            distilled.append(fallback)

        logger.info(f"[InstructionDistiller] Distilled {len(distilled)} synthetic instruction pairs.")
        return distilled

    def _generate_pair_from_schema(self, schema: GeneralizedSchema) -> SyntheticInstructionPair:
        """Create a single high-quality instruction pair from a schema."""
        pair_id = f"inst_{uuid.uuid4().hex[:8]}"
        instruction = f"Apply domain heuristic for {schema.domain}: {schema.heuristic_rule}"
        input_context = f"Domain: {schema.domain} | Confidence: {schema.confidence:.2f}"
        desired_response = (
            f"Based on established pattern '{schema.heuristic_rule}', execute the action "
            f"within strict safety bounds and return structured outcome telemetry."
        )

        return SyntheticInstructionPair(
            pair_id=pair_id,
            domain=schema.domain,
            instruction=instruction,
            input_context=input_context,
            desired_response=desired_response,
            source_schema_id=schema.schema_id,
            quality_score=min(1.0, max(0.5, schema.confidence)),
            created_at=time.time(),
        )

    def _generate_baseline_pair(self, domain: str) -> SyntheticInstructionPair:
        """Generate baseline domain instruction pair for bootstrapping."""
        pair_id = f"inst_base_{uuid.uuid4().hex[:8]}"
        return SyntheticInstructionPair(
            pair_id=pair_id,
            domain=domain,
            instruction=f"Standard protocol for {domain} autonomous task execution",
            input_context="Base system invariant validation",
            desired_response=f"Verify risk tier, query safety registry, and execute safely with fail-closed halt.",
            source_schema_id=None,
            quality_score=0.95,
            created_at=time.time(),
        )

    def get_all_pairs(self) -> List[SyntheticInstructionPair]:
        return list(self._distilled_pairs.values())

    def clear(self) -> None:
        self._distilled_pairs.clear()


# Global singleton instance
instruction_distiller = InstructionDistiller()
