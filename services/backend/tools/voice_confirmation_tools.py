"""Voice Confirmation & Conversational Dispatch Tools for Phenom (Milestone 29 Phase 3).

Registers 3 voice confirmation tools in ToolRegistry:
1. dispatch_conversational_confirmation (Tier 0)
2. process_voice_approval_response (Tier 1)
3. get_active_voice_confirmations (Tier 0)
"""

from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field

from services.backend.safety.registry import registry
from services.backend.safety.voice_confirmation_dispatcher import (
    voice_confirmation_dispatcher,
)


# ==========================================
# 1. Dispatch Conversational Confirmation (Tier 0)
# ==========================================

class DispatchConversationalConfirmationArgs(BaseModel):
    tool_name: str = Field(..., description="Target tool name requiring confirmation.")
    arguments: Dict[str, Any] = Field(default_factory=dict, description="Tool execution arguments to synthesize confirmation question for.")
    tier: int = Field(default=2, ge=1, le=3, description="Risk tier of the target operation (Default 2).")


def preview_dispatch_conversational_confirmation(args: Dict[str, Any]) -> str:
    tool_name = args.get("tool_name", "unknown_action")
    return f"Synthesize spoken conversational confirmation prompt for '{tool_name}'."


@registry.register(
    name="dispatch_conversational_confirmation",
    tier=0,
    description="Synthesizes a friendly, spoken conversational confirmation question for a pending high-risk action.",
    args_schema=DispatchConversationalConfirmationArgs,
    preview_fn=preview_dispatch_conversational_confirmation,
    can_remember_per_folder=False,
)
def handle_dispatch_conversational_confirmation(
    tool_name: str,
    arguments: Optional[Dict[str, Any]] = None,
    tier: int = 2,
) -> Dict[str, Any]:
    prompt = voice_confirmation_dispatcher.dispatch_confirmation(
        tool_name=tool_name,
        args=arguments or {},
        tier=tier,
    )
    return prompt.model_dump()


# ==========================================
# 2. Process Voice Approval Response (Tier 1)
# ==========================================

class ProcessVoiceApprovalResponseArgs(BaseModel):
    prompt_id: str = Field(..., description="Unique ID of the pending voice confirmation.")
    user_response: str = Field(..., description="Spoken or typed user response (e.g. 'yes', 'proceed', 'no', 'cancel').")


def preview_process_voice_approval_response(args: Dict[str, Any]) -> str:
    pid = args.get("prompt_id", "unknown")
    resp = args.get("user_response", "")
    return f"Process conversational approval response for [{pid}]: '{resp}'"


@registry.register(
    name="process_voice_approval_response",
    tier=1,
    description="Parses spoken user approval or denial intent and updates pending confirmation state.",
    args_schema=ProcessVoiceApprovalResponseArgs,
    preview_fn=preview_process_voice_approval_response,
    can_remember_per_folder=False,
)
def handle_process_voice_approval_response(
    prompt_id: str,
    user_response: str,
) -> Dict[str, Any]:
    result = voice_confirmation_dispatcher.resolve_confirmation(
        prompt_id=prompt_id,
        user_response=user_response,
    )
    return result


# ==========================================
# 3. Get Active Voice Confirmations (Tier 0)
# ==========================================

class GetActiveVoiceConfirmationsArgs(BaseModel):
    pass


def preview_get_active_voice_confirmations(args: Dict[str, Any]) -> str:
    return "Inspect currently pending conversational voice confirmations."


@registry.register(
    name="get_active_voice_confirmations",
    tier=0,
    description="Retrieves active pending conversational voice confirmations and remaining timeout seconds.",
    args_schema=GetActiveVoiceConfirmationsArgs,
    preview_fn=preview_get_active_voice_confirmations,
    can_remember_per_folder=False,
)
def handle_get_active_voice_confirmations() -> Dict[str, Any]:
    active = voice_confirmation_dispatcher.get_active_confirmations()
    return {
        "active_confirmations": active,
        "count": len(active),
    }
