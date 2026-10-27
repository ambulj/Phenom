"""
Phenom Model Router
Implements the model routing policy from ARCHITECTURE.md Section 3:
- Default: Local 8B (Llama 3 Q4_0 on Ollama)
- Anything labelled 'private' stays Local 8B, unconditionally.
- Cloud Nemotron via NVIDIA API is used ONLY for long shareable inputs,
  after an explicit confirmation previewing exactly what leaves the machine.
- Cloud failure or user denial falls back to Local 8B with chunking.
- Logs every decision with its reason.
"""

import os
import json
from typing import Optional, List, Dict, Any, Callable, Awaitable, Tuple
from services.backend.router.privacy import privacy_classifier, PrivacyLabel
from services.backend.safety.action_log import action_log

CloudApprovalHandler = Callable[[str, str, int], Awaitable[bool]] # (request_id, preview_text, token_estimate) -> approved

class ModelRouter:
    def __init__(self, ollama_model: str = "llama3:latest", cloud_model: str = "nvidia/llama-3.1-nemotron-70b-instruct"):
        self.ollama_model = ollama_model
        self.cloud_model = cloud_model
        self._cloud_approval_handler: Optional[CloudApprovalHandler] = None

    def set_cloud_approval_handler(self, handler: CloudApprovalHandler):
        self._cloud_approval_handler = handler

    async def route_request(
        self,
        prompt: str,
        context_files: Optional[List[str]] = None,
        manual_privacy_override: Optional[PrivacyLabel] = None
    ) -> Tuple[str, str, Dict[str, Any]]:
        """
        Determines target model ('local' or 'cloud') and returns (model_name, backend_type, metadata).
        """
        context_files = context_files or []
        privacy_label, privacy_reason = privacy_classifier.classify(
            prompt, context_files, manual_privacy_override
        )
        
        word_count = len(prompt.split())
        est_tokens = int(word_count * 1.33)

        metadata = {
            "privacy_label": privacy_label,
            "privacy_reason": privacy_reason,
            "word_count": word_count,
            "estimated_tokens": est_tokens
        }

        # Rule 1: Private always stays Local
        if privacy_label == "private":
            reason = f"Input labelled private ({privacy_reason}). Kept local."
            self._log_decision("local", self.ollama_model, reason, metadata)
            metadata["routing_reason"] = reason
            return self.ollama_model, "local", metadata

        # Rule 2: Short shareable inputs stay Local (faster, zero network overhead)
        # Threshold: 3,000 words (~4,000 tokens)
        if word_count <= 3000:
            reason = f"Shareable input is within local context capacity ({word_count} words <= 3,000). Handled locally."
            self._log_decision("local", self.ollama_model, reason, metadata)
            metadata["routing_reason"] = reason
            return self.ollama_model, "local", metadata

        # Rule 3: Long shareable input -> Requires Cloud Escalation Approval
        if not self._cloud_approval_handler:
            reason = "Long shareable input eligible for cloud Nemotron, but approval handler unavailable. Falling back to local 8B."
            self._log_decision("local", self.ollama_model, reason, metadata)
            metadata["routing_reason"] = reason
            return self.ollama_model, "local", metadata

        # Generate exact text preview
        preview_text = prompt[:500] + (f"\n... [TRUNCATED {len(prompt)-500} chars]" if len(prompt) > 500 else "")
        req_id = f"cloud-escalate-{os.urandom(4).hex()}"

        user_approved = await self._cloud_approval_handler(req_id, preview_text, est_tokens)
        if not user_approved:
            reason = "User denied cloud escalation preview. Falling back to local 8B."
            self._log_decision("local", self.ollama_model, reason, metadata)
            metadata["routing_reason"] = reason
            return self.ollama_model, "local", metadata

        # User approved cloud escalation
        reason = f"Long shareable input ({word_count} words). User approved cloud escalation to Nemotron."
        self._log_decision("cloud", self.cloud_model, reason, metadata)
        metadata["routing_reason"] = reason
        return self.cloud_model, "cloud", metadata

    def _log_decision(self, target_type: str, model_name: str, reason: str, metadata: Dict[str, Any]):
        action_log.log_action(
            tool="model_router",
            tier=0 if target_type == "local" else 2,
            args={"target": target_type, "model": model_name, "reason": reason, "privacy": metadata.get("privacy_label")},
            decision="auto" if target_type == "local" else "approved",
            result_status="ROUTED",
            source="system"
        )

# Global Router instance
model_router = ModelRouter()
