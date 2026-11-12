"""
Companion Approval Card Dispatcher and Decision Handler for Phenom P2P Mesh
Pushes Tier 1 and Tier 2 action approval requests to paired companion devices.
Enforces the Permanent Rule: Tier 3 actions can NEVER be pushed to companions.
"""

import hashlib
import hmac
import json
import logging
import time
from typing import Dict, Optional
from services.backend.schemas.mesh import (
    CompanionApprovalCard,
    CompanionApprovalDecision,
    MeshMessageType
)
from services.backend.mesh.p2p_mesh_engine import P2PMeshEngine, p2p_mesh_engine
from services.backend.safety.confirmations import (
    ConfirmationEngine,
    ConfirmationRequest,
    confirmation_engine
)
from services.backend.safety.guardian import guardian

logger = logging.getLogger("phenom.mesh.approval_cards")


class CompanionApprovalManager:
    """
    Coordinates remote confirmation approval cards over the local encrypted P2P mesh.
    Enforces HMAC-signed decisions, preconditions re-validation, and the Tier 3 block rule.
    """

    def __init__(
        self,
        engine: Optional[P2PMeshEngine] = None,
        conf_engine: Optional[ConfirmationEngine] = None
    ):
        self._engine = engine or p2p_mesh_engine
        self._conf_engine = conf_engine or confirmation_engine
        self._pending_confirmations: Dict[str, ConfirmationRequest] = {}
        self._decisions: Dict[str, CompanionApprovalDecision] = {}

    def dispatch_approval_card(
        self,
        confirmation: ConfirmationRequest,
        diff_preview: Optional[str] = None
    ) -> CompanionApprovalCard:
        """
        Push a confirmation request to paired companion devices as an approval card.
        Strict Rule: Tier 3 actions require typed desktop input and are strictly blocked here.
        """
        if confirmation.tier >= 3:
            raise ValueError(
                f"Tier {confirmation.tier} actions are strictly prohibited from remote companion approval. "
                "Explicit typed desktop confirmation is required by Phenom Safety Rule 1."
            )

        card = CompanionApprovalCard(
            request_id=confirmation.id,
            tier=confirmation.tier,
            tool_name=confirmation.tool_name,
            action_verb=confirmation.action_verb,
            item_count=confirmation.item_count,
            target_summary=confirmation.target_summary,
            one_line_summary=confirmation.one_line_summary,
            diff_preview=diff_preview,
            created_at=time.time(),
            timeout_seconds=confirmation.timeout_seconds
        )

        self._pending_confirmations[confirmation.id] = confirmation

        # Broadcast encrypted card to all paired devices with active sessions
        payload = card.model_dump_json().encode("utf-8")
        paired = self._engine.get_paired_devices(include_offline=False)
        for device in paired:
            try:
                self._engine.send_frame(
                    node_id=device.node_id,
                    msg_type=int(MeshMessageType.APPROVAL_CARD_PUSH.value == "approval_card_push"),
                    payload=payload
                )
            except Exception as e:
                logger.debug(f"Failed to push approval card to {device.node_id}: {e}")

        return card

    def compute_decision_signature(
        self,
        request_id: str,
        decision: str,
        node_id: str,
        decided_at: float,
        secret: str
    ) -> str:
        """Compute HMAC-SHA256 signature for a companion approval decision."""
        msg = f"{request_id}:{decision}:{node_id}:{int(decided_at)}".encode("utf-8")
        return hmac.new(secret.encode("utf-8"), msg, hashlib.sha256).hexdigest()

    def handle_companion_decision(
        self,
        decision: CompanionApprovalDecision,
        secret_override: Optional[str] = None,
        current_mode: str = "work"
    ) -> bool:
        """
        Validate and apply a remote approval/rejection decision from a companion device.
        Verifies companion HMAC signature and re-validates execution preconditions.
        """
        if guardian.is_halted or self._engine.is_halted:
            raise PermissionError("Approval decision rejected: Guardian Kill Switch is engaged.")

        confirmation = self._pending_confirmations.get(decision.request_id)
        if not confirmation:
            raise ValueError(f"No pending confirmation request found for ID '{decision.request_id}'")

        # 1. Retrieve device secret
        device = self._engine.device_registry.get_device(decision.node_id)
        secret = secret_override or (device.shared_secret_hash if device else "")
        if not secret:
            raise ValueError(f"Unknown or unauthorized companion device '{decision.node_id}'")

        # 2. Timing-safe HMAC signature verification
        expected_sig = self.compute_decision_signature(
            request_id=decision.request_id,
            decision=decision.decision,
            node_id=decision.node_id,
            decided_at=decision.decided_at,
            secret=secret
        )

        if not hmac.compare_digest(expected_sig, decision.signature):
            raise PermissionError(f"Cryptographic signature mismatch for decision on '{decision.request_id}'")

        # 3. Preconditions re-validation
        self._conf_engine.validate_approval(confirmation, current_mode=current_mode)

        # 4. Record and finalize
        self._decisions[decision.request_id] = decision
        del self._pending_confirmations[decision.request_id]

        return decision.decision.lower() == "approved"
