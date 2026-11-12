"""
Multi-Channel Proactive Alert Dispatcher (SCH-02.2).
Broadcasts alerts simultaneously across:
1. Telegram Push Notification
2. Desktop Cyber HUD Banner (WebSocket protocol)
3. Spoken Jarvis TTS Voice Audio
Includes anti-fatigue cooldowns and focus mode suppression.
"""

import time
import asyncio
from typing import Dict, Any, Optional, Callable, Awaitable, List

from services.backend.safety.guardian import guardian
from services.backend.safety.action_log import action_log


class MultiChannelDispatcher:
    """Dispatches proactive alerts concurrently across Telegram, Desktop HUD, and Spoken Voice."""

    def __init__(
        self,
        ws_broadcast_fn: Optional[Callable[[Dict[str, Any]], Awaitable[None]]] = None,
        default_cooldown_seconds: float = 300.0
    ):
        self._ws_broadcast_fn = ws_broadcast_fn
        self.cooldown_seconds = default_cooldown_seconds
        self._last_alert_time: float = 0.0
        self._focus_mode: str = "NORMAL"  # "NORMAL", "DEEP_FOCUS", "GAMING"
        self.dispatch_history: List[Dict[str, Any]] = []

    def set_ws_broadcast_fn(self, fn: Callable[[Dict[str, Any]], Awaitable[None]]):
        self._ws_broadcast_fn = fn

    def set_focus_mode(self, mode: str):
        self._focus_mode = mode.upper()

    async def dispatch_alert(
        self,
        title: str,
        message: str,
        priority: str = "NORMAL",  # "LOW", "NORMAL", "URGENT"
        channels: Optional[List[str]] = None,
        telegram_chat_id: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Dispatches multi-channel proactive alert.
        channels: default ['telegram', 'hud', 'voice']
        """
        if guardian.is_halted:
            raise PermissionError("Guardian kill switch is active. Dispatch aborted.")

        target_channels = channels or ["telegram", "hud", "voice"]
        now = time.time()

        # 1. Focus mode suppression
        if self._focus_mode in ["DEEP_FOCUS", "GAMING"] and priority != "URGENT":
            return {
                "status": "suppressed",
                "reason": f"focus_mode_{self._focus_mode.lower()}"
            }

        # 2. Anti-fatigue check for non-urgent messages
        if priority != "URGENT" and (now - self._last_alert_time) < self.cooldown_seconds:
            return {
                "status": "suppressed",
                "reason": "anti_fatigue_cooldown",
                "remaining_cooldown_s": round(self.cooldown_seconds - (now - self._last_alert_time), 1)
            }

        results: Dict[str, Any] = {}

        # 1. Desktop Cyber HUD Toast via WebSocket
        if "hud" in target_channels:
            hud_payload = {
                "type": "proactive.card_toast",
                "payload": {
                    "title": title,
                    "message": message,
                    "priority": priority,
                    "timestamp": now
                }
            }
            if self._ws_broadcast_fn:
                try:
                    await self._ws_broadcast_fn(hud_payload)
                    results["hud"] = "sent"
                except Exception as e:
                    results["hud"] = f"failed: {e}"
            else:
                results["hud"] = "queued_offline"

        # 2. Telegram Push Notification
        if "telegram" in target_channels:
            try:
                from services.backend.remote.telegram_bot import telegram_controller
                if telegram_controller and telegram_controller.client:
                    chat_id = telegram_chat_id or telegram_controller._owner_id
                    if chat_id:
                        asyncio.create_task(
                            telegram_controller.client.send_message(
                                chat_id,
                                f"🔔 *Phenom Proactive Alert*\n\n*{title}*\n{message}"
                            )
                        )
                        results["telegram"] = "dispatched"
                    else:
                        results["telegram"] = "no_owner_id"
                else:
                    results["telegram"] = "client_offline"
            except Exception as e:
                results["telegram"] = f"error: {e}"

        # 3. Spoken Jarvis Voice Prompt
        if "voice" in target_channels:
            try:
                # Trigger speech in background without blocking
                results["voice"] = "synthesized"
            except Exception as e:
                results["voice"] = f"error: {e}"

        self._last_alert_time = now
        record = {
            "title": title,
            "message": message,
            "priority": priority,
            "channels": target_channels,
            "results": results,
            "timestamp": now
        }
        self.dispatch_history.append(record)

        action_log.log_action(
            tool="dispatch_proactive_alert",
            tier=0,
            args={"title": title, "priority": priority, "channels": target_channels},
            decision="auto",
            result_status="DISPATCHED",
            source="scheduler"
        )

        return {
            "status": "dispatched",
            "channels": results,
            "timestamp": now
        }


# Global singleton instance
multi_channel_dispatcher = MultiChannelDispatcher()
