"""
Phenom Model Router
Implements the model routing policy from ARCHITECTURE.md Section 3:
- Default: Local model (configured in config.toml or PHENOM_LOCAL_MODEL)
- Anything labelled 'private' stays Local, unconditionally.
- Cloud Nemotron via NVIDIA API is used ONLY for long shareable inputs,
  after an explicit confirmation previewing exactly what leaves the machine.
- Cloud failure or user denial falls back to Local with chunking.
- Logs every decision with its reason.
"""

import os
import json
from typing import Optional, List, Dict, Any, Callable, Awaitable, Tuple
from services.backend.router.privacy import privacy_classifier, PrivacyLabel
from services.backend.safety.action_log import action_log

CloudApprovalHandler = Callable[[str, str, int], Awaitable[bool]] # (request_id, preview_text, token_estimate) -> approved

class ModelRouter:
    def __init__(self, ollama_model: Optional[str] = None, cloud_model: Optional[str] = None):
        self._explicit_ollama_model = ollama_model
        self._explicit_cloud_model = cloud_model
        self._cloud_approval_handler: Optional[CloudApprovalHandler] = None

    @property
    def cloud_model(self) -> str:
        if self._explicit_cloud_model:
            return self._explicit_cloud_model
        env_c = os.environ.get("PHENOM_CLOUD_MODEL") or os.environ.get("NVIDIA_CLOUD_MODEL")
        if env_c:
            return env_c
        try:
            from services.backend.memory.vault import load_config
            cfg = load_config()
            cfg_c = cfg.get("models", {}).get("cloud_model")
            if cfg_c:
                return cfg_c
        except Exception:
            pass
        return "nvidia/nemotron-3.5-bolt-e4b"

    @cloud_model.setter
    def cloud_model(self, val: Optional[str]):
        self._explicit_cloud_model = val

    @property
    def ollama_model(self) -> str:
        if self._explicit_ollama_model:
            return self._explicit_ollama_model
        env_m = os.environ.get("PHENOM_LOCAL_MODEL")
        if env_m:
            return env_m
        try:
            from services.backend.memory.vault import load_config
            cfg = load_config()
            cfg_m = cfg.get("models", {}).get("local_model")
            if cfg_m:
                return cfg_m
        except Exception:
            pass
        return "phenom-jarvis:latest"

    @ollama_model.setter
    def ollama_model(self, val: Optional[str]):
        self._explicit_ollama_model = val

    @property
    def fallback_local_model(self) -> str:
        try:
            from services.backend.memory.vault import load_config
            cfg = load_config()
            cfg_m = cfg.get("models", {}).get("fallback_local_model")
            if cfg_m:
                return cfg_m
        except Exception:
            pass
        return "phenom-jarvis:latest"

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

        # Security / Kali Mode routing (Task 6D)
        try:
            from services.backend.modes.mode_manager import mode_manager
            if mode_manager.is_security_mode_active:
                specialist = mode_manager.active_specialist_model or "hf.co/tinyopsec/Qwen3.5-4B-Uncensored-Aggressive-GGUF:Q4_K_M"
                metadata["task_type"] = "security"
                metadata["vram_estimated_mb"] = 2800
                metadata["dispatch_reason"] = f"Security / Kali mode active -> Dispatched to Specialist model ({specialist})"
                reason = f"Security / Kali mode active: requests routed to specialist model {specialist}."
                self._log_decision("local", specialist, reason, metadata)
                metadata["routing_reason"] = reason
                return specialist, "local", metadata
        except Exception:
            pass

        # Resolve specialized local model
        target_local_model = self.ollama_model
        if not self._explicit_ollama_model:
            try:
                from services.backend.router.dynamic_model_router import dynamic_model_router
                resolved, task_type, vram_mb, dispatch_reason = dynamic_model_router.resolve_target_model(prompt)
                if task_type == "chat" and not dynamic_model_router.manual_override:
                    target_local_model = self.ollama_model
                else:
                    target_local_model = resolved
                metadata["task_type"] = task_type
                metadata["vram_estimated_mb"] = vram_mb
                metadata["dispatch_reason"] = dispatch_reason
            except Exception:
                target_local_model = self.ollama_model

        # Rule 1: Private always stays Local
        if privacy_label == "private":
            reason = f"Input labelled private ({privacy_reason}). Kept local on {target_local_model}."
            self._log_decision("local", target_local_model, reason, metadata)
            metadata["routing_reason"] = reason
            return target_local_model, "local", metadata

        # Rule 2: Short shareable inputs stay Local (faster, zero network overhead)
        # Exception: When gaming mode is active, VRAM is freed (<100MB) and shareable tasks can escalate to Cloud
        from services.backend.resource.vram_manager import vram_manager
        if vram_manager.gaming_mode_active and self._cloud_approval_handler:
            preview_text = prompt[:500] + (f"\n... [TRUNCATED {len(prompt)-500} chars]" if len(prompt) > 500 else "")
            req_id = f"gaming-cloud-escalate-{os.urandom(4).hex()}"
            user_approved = await self._cloud_approval_handler(req_id, preview_text, est_tokens)
            if user_approved:
                reason = f"Gaming mode active ({vram_manager.detected_game_name}); VRAM protected (<100MB). User approved routing to cloud Nemotron."
                self._log_decision("cloud", self.cloud_model, reason, metadata)
                metadata["routing_reason"] = reason
                return self.cloud_model, "cloud", metadata

        # Threshold: 3,000 words (~4,000 tokens)
        if word_count <= 3000:
            reason = f"Shareable input is within local context capacity ({word_count} words <= 3,000). Handled locally on {target_local_model}."
            self._log_decision("local", target_local_model, reason, metadata)
            metadata["routing_reason"] = reason
            return target_local_model, "local", metadata

        # Rule 3: Long shareable input -> Requires Cloud Escalation Approval
        if not self._cloud_approval_handler:
            reason = f"Long shareable input eligible for cloud Nemotron, but approval handler unavailable. Falling back to local model {target_local_model}."
            self._log_decision("local", target_local_model, reason, metadata)
            metadata["routing_reason"] = reason
            return target_local_model, "local", metadata

        # Generate exact text preview
        preview_text = prompt[:500] + (f"\n... [TRUNCATED {len(prompt)-500} chars]" if len(prompt) > 500 else "")
        req_id = f"cloud-escalate-{os.urandom(4).hex()}"

        user_approved = await self._cloud_approval_handler(req_id, preview_text, est_tokens)
        if not user_approved:
            reason = f"User denied cloud escalation preview. Falling back to local model {target_local_model}."
            self._log_decision("local", target_local_model, reason, metadata)
            metadata["routing_reason"] = reason
            return target_local_model, "local", metadata

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
