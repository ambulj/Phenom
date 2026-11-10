"""
Autonomous Instruction Tuning Dataset Synthesizer.
Extracts validated user corrections and high-confidence tool traces into privacy-preserving
JSONL datasets for local parameter-efficient fine-tuning (PEFT / LoRA).

Part of Phenom 23.0 Sovereign Neural Evolution (ADA-01.1 / MOD-02.1).
"""

import os
import time
import json
import uuid
import re
from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field

from services.backend.safety.guardian import guardian
from services.backend.automation.gui_controller import Rule8ViolationError

RULE_8_PAYMENT_RE = re.compile(
    r"\b(?:checkout|place\s+order|pay\s+now|buy\s+now|complete\s+purchase|complete\s+payment|payment|credit\s+card|cvv|password)\b",
    re.IGNORECASE
)

# Rule 11 credential scrubbing patterns
CREDENTIAL_SCRUB_PATTERNS = [
    (re.compile(r"(Bearer\s+)[A-Za-z0-9_\-\.]{16,}", re.IGNORECASE), r"\1[SCRUBBED_TOKEN]"),
    (re.compile(r"(api[_\-]?key\s*[:=]\s*['\"])[^'\"]+(['\"])", re.IGNORECASE), r"\1[SCRUBBED_API_KEY]\2"),
    (re.compile(r"(password\s*[:=]\s*['\"])[^'\"]+(['\"])", re.IGNORECASE), r"\1[SCRUBBED_PASSWORD]\2"),
    (re.compile(r"(ghp_[A-Za-z0-9]{30,})", re.IGNORECASE), r"[SCRUBBED_GITHUB_TOKEN]"),
]


class TuningSample(BaseModel):
    sample_id: str
    instruction: str
    input_context: str = ""
    output_response: str
    category: str = Field(default="coding", description="coding, reasoning, persona, tools")
    created_at: float = Field(default_factory=time.time)


class DatasetGenerator:
    """
    Collects, scrubs, and persists fine-tuning datasets for local LoRA training.
    """

    def __init__(self, dataset_dir: Optional[str] = None):
        self.dataset_dir = dataset_dir or os.path.join(
            os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
            ".phenom",
            "datasets"
        )
        os.makedirs(self.dataset_dir, exist_ok=True)
        self._samples: Dict[str, TuningSample] = {}

    def _scrub_text(self, text: str) -> str:
        scrubbed = text
        for pat, repl in CREDENTIAL_SCRUB_PATTERNS:
            scrubbed = pat.sub(repl, scrubbed)
        return scrubbed

    def add_tuning_sample(
        self,
        instruction: str,
        output_response: str,
        input_context: str = "",
        category: str = "coding",
    ) -> TuningSample:
        """Adds and sanitizes an instruction tuning sample."""
        if guardian.is_halted:
            raise PermissionError("Guardian kill switch is active. Dataset synthesis halted.")

        if RULE_8_PAYMENT_RE.search(instruction) or RULE_8_PAYMENT_RE.search(output_response):
            raise Rule8ViolationError(f"Rule 8 Violation: Cannot synthesize dataset sample containing payment/checkout directives.")

        sid = f"sample_{uuid.uuid4().hex[:8]}"
        clean_inst = self._scrub_text(instruction)
        clean_ctx = self._scrub_text(input_context)
        clean_out = self._scrub_text(output_response)

        sample = TuningSample(
            sample_id=sid,
            instruction=clean_inst,
            input_context=clean_ctx,
            output_response=clean_out,
            category=category,
            created_at=time.time(),
        )
        self._samples[sid] = sample
        return sample

    def export_dataset_jsonl(self, category: Optional[str] = None) -> str:
        """
        Exports active samples into a JSONL file in `.phenom/datasets/`.
        Returns the absolute filepath.
        """
        if guardian.is_halted:
            raise PermissionError("Guardian kill switch is active. Dataset export halted.")

        cat_slug = category or "all"
        filename = f"phenom_lora_dataset_{cat_slug}.jsonl"
        filepath = os.path.join(self.dataset_dir, filename)

        filtered = [s for s in self._samples.values() if category is None or s.category == category]

        with open(filepath, "w", encoding="utf-8") as f:
            for s in filtered:
                line = json.dumps({
                    "instruction": s.instruction,
                    "input": s.input_context,
                    "output": s.output_response,
                    "metadata": {"sample_id": s.sample_id, "category": s.category}
                }, ensure_ascii=False)
                f.write(line + "\n")

        return filepath

    def get_dataset_stats(self) -> Dict[str, Any]:
        categories = {}
        for s in self._samples.values():
            categories[s.category] = categories.get(s.category, 0) + 1

        return {
            "total_samples": len(self._samples),
            "categories": categories,
            "dataset_dir": self.dataset_dir,
        }


# Global singleton
dataset_generator = DatasetGenerator()
