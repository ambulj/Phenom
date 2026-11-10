"""
Safety-Wrapped Telegram Mesh Tools.
Registers tools with ToolRegistry for interactive mobile approvals, remote voice RAG
queries, and mesh status inspection (Phase 21-03 TEL-04 / REM-02).
"""

from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field

from services.backend.safety.registry import registry
from services.backend.remote.telegram_mesh import telegram_mesh
from services.backend.remote.interactive_approvals import interactive_approval_manager


# ==========================================
# 1. Dispatch Telegram Approval Request (Tier 1)
# ==========================================

class DispatchTelegramApprovalArgs(BaseModel):
    action_name: str = Field(..., description="Action name requiring authorization")
    tier: int = Field(default=1, description="Safety tier (1 or 2)")
    preview_text: str = Field(..., description="Human-readable preview of operation")
    tool_args: Optional[Dict[str, Any]] = Field(default=None, description="Arguments for action")
    timeout_sec: float = Field(default=300.0, description="Ticket expiry timeout in seconds")

def dispatch_telegram_approval_preview(args: Dict[str, Any]) -> str:
    action = args.get("action_name", "action")
    tier = args.get("tier", 1)
    return f"Dispatch interactive Telegram approval request for Tier {tier} action '{action}'."

@registry.register(
    name="dispatch_telegram_approval_request",
    tier=1,
    description="Sends an interactive authorization ticket with Approve/Reject inline keyboard to paired Telegram mobile device.",
    args_schema=DispatchTelegramApprovalArgs,
    preview_fn=dispatch_telegram_approval_preview,
    can_remember_per_folder=False
)
def handle_dispatch_telegram_approval_request(
    action_name: str,
    tier: int = 1,
    preview_text: str = "",
    tool_args: Optional[Dict[str, Any]] = None,
    timeout_sec: float = 300.0
) -> Dict[str, Any]:
    ticket = telegram_mesh.dispatch_approval_request(
        action_name=action_name,
        tier=tier,
        preview_text=preview_text,
        tool_args=tool_args,
        timeout_sec=timeout_sec,
    )
    keyboard = interactive_approval_manager.format_inline_keyboard(ticket)
    return {
        "ticket_id": ticket.ticket_id,
        "action_name": ticket.action_name,
        "tier": ticket.tier,
        "preview_text": ticket.preview_text,
        "status": ticket.status,
        "expires_at": ticket.expires_at,
        "inline_keyboard": keyboard,
    }


# ==========================================
# 2. Handle Telegram Callback Decision (Tier 0)
# ==========================================

class HandleTelegramCallbackArgs(BaseModel):
    callback_data: str = Field(..., description="Callback data from Telegram inline button e.g. 'approve:appr_12345678'")

def handle_telegram_callback_preview(args: Dict[str, Any]) -> str:
    cb = args.get("callback_data", "")
    return f"Process Telegram inline keyboard callback: {cb}"

@registry.register(
    name="handle_telegram_callback_decision",
    tier=0,
    description="Processes remote inline button decision from Telegram to approve or reject a pending desktop ticket.",
    args_schema=HandleTelegramCallbackArgs,
    preview_fn=handle_telegram_callback_preview,
    can_remember_per_folder=False
)
def handle_handle_telegram_callback_decision(callback_data: str) -> Dict[str, Any]:
    return telegram_mesh.handle_callback_query(callback_data)


# ==========================================
# 3. Execute Remote Voice RAG (Tier 0)
# ==========================================

class ExecuteRemoteVoiceRAGArgs(BaseModel):
    query: Optional[str] = Field(default=None, description="Spoken query transcript text")
    voice_bytes_len: Optional[int] = Field(default=None, description="Length of in-memory voice buffer")

def execute_remote_voice_rag_preview(args: Dict[str, Any]) -> str:
    q = args.get("query", "voice query")
    return f"Process remote voice query '{q}' against offline Hybrid RAG and Obsidian vaults."

@registry.register(
    name="execute_remote_voice_rag",
    tier=0,
    description="Synthesizes source-grounded answers with inline citations for mobile voice note queries.",
    args_schema=ExecuteRemoteVoiceRAGArgs,
    preview_fn=execute_remote_voice_rag_preview,
    can_remember_per_folder=False
)
async def handle_execute_remote_voice_rag(
    query: Optional[str] = None,
    voice_bytes_len: Optional[int] = None
) -> Dict[str, Any]:
    voice_bytes = b"\x00" * (voice_bytes_len or 1024) if voice_bytes_len else None
    result = await telegram_mesh.handle_remote_voice_note(
        voice_bytes=voice_bytes,
        simulated_transcript=query
    )
    return result.model_dump()


# ==========================================
# 4. Get Telegram Mesh Status (Tier 0)
# ==========================================

class GetTelegramMeshStatusArgs(BaseModel):
    pass

def get_telegram_mesh_status_preview(args: Dict[str, Any]) -> str:
    return "Retrieve Telegram mobile command mesh connection and approval status."

@registry.register(
    name="get_telegram_mesh_status",
    tier=0,
    description="Retrieves live telemetry on paired mobile devices, pending approvals, and message counts.",
    args_schema=GetTelegramMeshStatusArgs,
    preview_fn=get_telegram_mesh_status_preview,
    can_remember_per_folder=False
)
def handle_get_telegram_mesh_status() -> Dict[str, Any]:
    status = telegram_mesh.get_mesh_status()
    return status.model_dump()
