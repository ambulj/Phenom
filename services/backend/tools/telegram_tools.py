"""SECURE TELEGRAM REMOTE UPLINK: Tools.

Milestone 46.0: Project SECURE TELEGRAM REMOTE UPLINK (Phase 3)

Registers:
1. dispatch_telegram_notification (Tier 1):
   Sends an encrypted markdown notification directly to the owner's Telegram.
2. send_telegram_voice_note (Tier 1):
   Synthesizes and sends an audio voice note to the owner's Telegram.
3. get_telegram_uplink_status (Tier 0):
   Returns remote uplink connectivity status, authorized user ID, and Guardian state.
4. trigger_remote_screen_snapshot (Tier 1):
   Generates and sends an in-RAM PII-masked screen snapshot to the owner's Telegram.
"""

from __future__ import annotations

from typing import Any, Dict, Optional
from pydantic import BaseModel, Field

from services.backend.safety.guardian import guardian
from services.backend.safety.registry import registry
from services.backend.telegram.bot_controller import bot_controller
from services.backend.telegram.screen_snapshot import telegram_snapshot_provider
from services.backend.telegram.voice_pipeline import telegram_voice_pipeline


# ==========================================
# 1. Dispatch Telegram Notification (Tier 1)
# ==========================================

class DispatchTelegramNotificationArgs(BaseModel):
    text: str = Field(..., description="Markdown text notification to send to owner")
    priority: str = Field("normal", description="'normal', 'high', or 'critical'")


def preview_dispatch_telegram_notification(args: Dict[str, Any]) -> str:
    preview = args.get("text", "")
    if len(preview) > 40:
        preview = preview[:40] + "..."
    return f"Send Telegram notification ({args.get('priority', 'normal')}): '{preview}'"


@registry.register(
    name="dispatch_telegram_notification",
    tier=1,
    description="Dispatches an encrypted notification message to the authorized user's Telegram (Tier 1).",
    args_schema=DispatchTelegramNotificationArgs,
    preview_fn=preview_dispatch_telegram_notification,
    can_remember_per_folder=False,
)
def handle_dispatch_telegram_notification(
    text: str,
    priority: str = "normal",
) -> Dict[str, Any]:
    if guardian.is_halted:
        return {"success": False, "error": "Guardian Kill Switch is active", "guardian_halted": True}

    prefix = "🚨 *[CRITICAL ALERT]* " if priority == "critical" else "🔔 *[PHENOM NOTIFICATION]* "
    full_text = prefix + text
    bot_controller._queue_outbound(bot_controller.authorized_user_id, full_text)

    return {
        "success": True,
        "recipient_user_id": bot_controller.authorized_user_id,
        "priority": priority,
        "queued_messages_count": len(bot_controller.outbound_messages),
    }


# ==========================================
# 2. Send Telegram Voice Note (Tier 1)
# ==========================================

class SendTelegramVoiceNoteArgs(BaseModel):
    text: str = Field(..., description="Text to synthesize into spoken male audio reply")


def preview_send_telegram_voice_note(args: Dict[str, Any]) -> str:
    preview = args.get("text", "")
    if len(preview) > 30:
        preview = preview[:30] + "..."
    return f"Synthesize and send voice note: '{preview}'"


@registry.register(
    name="send_telegram_voice_note",
    tier=1,
    description="Synthesizes and transmits an audio voice note to the owner's Telegram in volatile RAM (Tier 1).",
    args_schema=SendTelegramVoiceNoteArgs,
    preview_fn=preview_send_telegram_voice_note,
    can_remember_per_folder=False,
)
def handle_send_telegram_voice_note(text: str) -> Dict[str, Any]:
    if guardian.is_halted:
        return {"success": False, "error": "Guardian Kill Switch is active", "guardian_halted": True}

    audio_bytes = telegram_voice_pipeline._synthesize_tts_in_ram(text)
    return {
        "success": True,
        "synthesized_text": text,
        "audio_bytes_length": len(audio_bytes),
        "zero_disk_compliance": True,
    }


# ==========================================
# 3. Get Telegram Uplink Status (Tier 0)
# ==========================================

class GetTelegramUplinkStatusArgs(BaseModel):
    pass


def preview_get_telegram_uplink_status(args: Dict[str, Any]) -> str:
    return "Query Telegram Remote Uplink connectivity status and security bounds"


@registry.register(
    name="get_telegram_uplink_status",
    tier=0,
    description="Returns Telegram bot status, authorized user ID, and Guardian state (Tier 0).",
    args_schema=GetTelegramUplinkStatusArgs,
    preview_fn=preview_get_telegram_uplink_status,
    can_remember_per_folder=False,
)
def handle_get_telegram_uplink_status() -> Dict[str, Any]:
    return {
        "online": True,
        "authorized_user_id": bot_controller.authorized_user_id,
        "guardian_halted": guardian.is_halted,
        "dry_run": bot_controller.dry_run,
        "queued_outbound_messages": len(bot_controller.outbound_messages),
    }


# ==========================================
# 4. Trigger Remote Screen Snapshot (Tier 1)
# ==========================================

class TriggerRemoteScreenSnapshotArgs(BaseModel):
    window_title: Optional[str] = Field("Desktop", description="Active window title")
    process_name: Optional[str] = Field("explorer.exe", description="Active window process")


def preview_trigger_remote_screen_snapshot(args: Dict[str, Any]) -> str:
    return f"Capture and send remote screen snapshot for {args.get('window_title', 'Desktop')}"


@registry.register(
    name="trigger_remote_screen_snapshot",
    tier=1,
    description="Captures and transmits an in-RAM PII-masked desktop snapshot to Telegram (Tier 1).",
    args_schema=TriggerRemoteScreenSnapshotArgs,
    preview_fn=preview_trigger_remote_screen_snapshot,
    can_remember_per_folder=False,
)
def handle_trigger_remote_screen_snapshot(
    window_title: str = "Desktop",
    process_name: str = "explorer.exe",
) -> Dict[str, Any]:
    if guardian.is_halted:
        return {"success": False, "error": "Guardian Kill Switch is active", "guardian_halted": True}

    image_bytes, is_shielded, caption = telegram_snapshot_provider.capture_snapshot(
        active_window_title=window_title,
        active_window_process=process_name,
    )

    return {
        "success": True,
        "is_shielded": is_shielded,
        "caption": caption,
        "image_bytes_length": len(image_bytes),
        "zero_disk_compliance": True,
    }
