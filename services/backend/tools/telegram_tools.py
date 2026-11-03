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
