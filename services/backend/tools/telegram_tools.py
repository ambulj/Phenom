"""
Phenom Telegram Remote Tools (Phase 3 MOB-01 / MOB-02)
Safety-wrapped tools for remote companion interaction:
- telegram_send_mobile_alert: Tier 0 (Ambient push notification to whitelisted owner)
- telegram_get_remote_status: Tier 0 (Inspect remote connection, lock state, and owner ID)
"""

from typing import Dict, Any, Optional
from pydantic import BaseModel, Field

from services.backend.safety.registry import registry
from services.backend.remote.telegram_bot import telegram_controller
from services.backend.remote.credentials import is_remote_locked, get_telegram_owner_id


# ==========================================
# Telegram Send Mobile Alert (Tier 0)
# ==========================================

class TelegramAlertArgs(BaseModel):
    title: str = Field(description="Alert title or headline.")
    message: str = Field(description="Alert body content.")
    urgency: str = Field(default="medium", description="Urgency: low, medium, high, critical.")

def telegram_alert_preview(args: Dict[str, Any]) -> str:
    return f"Send mobile notification '{args.get('title')}' via Telegram to owner."

@registry.register(
    name="telegram_send_mobile_alert",
    tier=0,
    description="Pushes an immediate ambient notification alert to the whitelisted owner's Telegram.",
    args_schema=TelegramAlertArgs,
    preview_fn=telegram_alert_preview,
    can_remember_per_folder=False
)
async def handle_telegram_send_alert(title: str, message: str, urgency: str = "medium") -> Dict[str, Any]:
    if not telegram_controller.is_configured:
        return {
            "status": "not_configured",
            "delivered": False,
            "reason": "Telegram bot token or owner ID is not configured."
        }

    if is_remote_locked():
        return {
            "status": "remote_locked",
            "delivered": False,
            "reason": "Remote control is locked at the desktop."
        }

    delivered = await telegram_controller.broadcast_remote_alert(title=title, message=message, urgency=urgency)
    return {
        "status": "delivered" if delivered else "failed",
        "delivered": delivered,
        "title": title
    }


# ==========================================
# Telegram Get Remote Status (Tier 0)
# ==========================================

class TelegramStatusArgs(BaseModel):
    pass

@registry.register(
    name="telegram_get_remote_status",
    tier=0,
    description="Returns configuration status and lock state of the Telegram mobile companion.",
    args_schema=TelegramStatusArgs,
    preview_fn=lambda args: "Check Telegram remote status and lock state.",
    can_remember_per_folder=False
)
def handle_telegram_get_status() -> Dict[str, Any]:
    return {
        "configured": telegram_controller.is_configured,
        "locked": is_remote_locked(),
        "has_owner": bool(telegram_controller.owner_id),
        "owner_id": telegram_controller.owner_id,
        "status": "active" if (telegram_controller.is_configured and not is_remote_locked()) else "inactive"
    }


# ==========================================
# Telegram Get Companion Status (Tier 0 - Milestone 17 TEL-02)
# ==========================================

class TelegramCompanionStatusArgs(BaseModel):
    pass

@registry.register(
    name="get_telegram_companion_status",
    tier=0,
    description="Returns detailed connectivity, owner, remote lock, and registered action button telemetry for the Telegram mobile super-companion.",
    args_schema=TelegramCompanionStatusArgs,
    preview_fn=lambda args: "Check Telegram companion status and active controls.",
    can_remember_per_folder=False
)
def handle_get_telegram_companion_status() -> Dict[str, Any]:
    actions = telegram_controller.get_registered_actions()
    return {
        "configured": telegram_controller.is_configured,
        "locked": is_remote_locked(),
        "has_owner": bool(telegram_controller.owner_id),
        "owner_id": telegram_controller.owner_id,
        "status": "active" if (telegram_controller.is_configured and not is_remote_locked()) else "inactive",
        "registered_actions": actions,
        "registered_action_count": len(actions)
    }


# ==========================================
# Telegram Send Snapshot (Tier 1 - Milestone 17 TEL-02.1)
# ==========================================

class SendTelegramSnapshotArgs(BaseModel):
    pass

def send_telegram_snapshot_preview(args: Dict[str, Any]) -> str:
    return "Send privacy-masked desktop snapshot to Telegram owner."

@registry.register(
    name="send_telegram_snapshot",
    tier=1,
    description="Captures the desktop screen with 35px privacy blur over sensitive apps and transmits it to the authorized Telegram owner.",
    args_schema=SendTelegramSnapshotArgs,
    preview_fn=send_telegram_snapshot_preview,
    can_remember_per_folder=False
)
async def handle_send_telegram_snapshot() -> Dict[str, Any]:
    if not telegram_controller.is_configured:
        return {
            "status": "not_configured",
            "delivered": False,
            "reason": "Telegram bot token or owner ID is not configured."
        }
    if is_remote_locked():
        return {
            "status": "remote_locked",
            "delivered": False,
            "reason": "Remote control is locked at the desktop."
        }
    owner_id = telegram_controller.owner_id
    if not owner_id:
        return {"status": "no_owner", "delivered": False}

    res = await telegram_controller._handle_screenshot_command(owner_id)
    return {
        "status": "delivered" if res.get("status") == "screenshot_sent" else "failed",
        "delivered": res.get("status") == "screenshot_sent",
        "redacted_count": res.get("redacted_count", 0)
    }


# ==========================================
# Register Telegram Action (Tier 1 - Milestone 17 TEL-02.2)
# ==========================================

class RegisterTelegramActionArgs(BaseModel):
    action_id: str = Field(description="Unique action identifier string, e.g. 'chill_layout'.")
    label: str = Field(description="Human-readable button label on Telegram, e.g. 'Chill Layout'.")
    tool_name: str = Field(description="Backend tool name to execute when button is tapped.")
    args: Dict[str, Any] = Field(default_factory=dict, description="Arguments dictionary for the backend tool.")

def register_telegram_action_preview(args: Dict[str, Any]) -> str:
    return f"Register remote action button '{args.get('action_id')}' ({args.get('label')}) for Telegram companion."

@registry.register(
    name="register_telegram_action",
    tier=1,
    description="Registers a dynamic interactive quick-action button in the Telegram mobile companion control menu.",
    args_schema=RegisterTelegramActionArgs,
    preview_fn=register_telegram_action_preview,
    can_remember_per_folder=False
)
def handle_register_telegram_action(
    action_id: str,
    label: str,
    tool_name: str,
    args: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    action = telegram_controller.register_custom_action(
        action_id=action_id,
        label=label,
        tool_name=tool_name,
        args=args or {}
    )
    return {
        "status": "registered",
        "action": action
    }
