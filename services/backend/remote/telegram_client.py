"""
Phenom Telegram Bot API Client (Phase 6)
Async HTTP client for the official Telegram Bot API using httpx.
Handles updates polling, message delivery, markdown formatting,
inline confirmation buttons, and callback queries.
"""

import httpx
from typing import Dict, Any, List, Optional

TELEGRAM_API_BASE = "https://api.telegram.org/bot"

class TelegramClient:
    def __init__(self, token: Optional[str] = None, client: Optional[httpx.AsyncClient] = None):
        self.token = token
        self._custom_client = client

    def _get_url(self, method: str) -> str:
        if not self.token:
            raise ValueError("Telegram Bot Token is not configured.")
        return f"{TELEGRAM_API_BASE}{self.token}/{method}"

    async def _request(self, method: str, payload: Optional[Dict[str, Any]] = None, timeout: float = 10.0) -> Dict[str, Any]:
        url = self._get_url(method)
        if self._custom_client:
            resp = await self._custom_client.post(url, json=payload or {}, timeout=timeout)
        else:
            async with httpx.AsyncClient(timeout=timeout) as client:
                resp = await client.post(url, json=payload or {}, timeout=timeout)
        
        if resp.status_code != 200:
            raise RuntimeError(f"Telegram API error ({resp.status_code}): {resp.text}")
        data = resp.json()
        if not data.get("ok"):
            raise RuntimeError(f"Telegram returned error: {data.get('description')}")
        return data.get("result", {})

    async def get_me(self) -> Dict[str, Any]:
        """Verifies bot token and returns bot details."""
        return await self._request("getMe")

    async def get_updates(self, offset: Optional[int] = None, timeout: int = 30) -> List[Dict[str, Any]]:
        """Polls for updates via long-polling."""
        payload: Dict[str, Any] = {"timeout": timeout}
        if offset is not None:
            payload["offset"] = offset
        res = await self._request("getUpdates", payload, timeout=timeout + 5.0)
        return res if isinstance(res, list) else []

    async def send_message(
        self,
        chat_id: int,
        text: str,
        reply_markup: Optional[Dict[str, Any]] = None,
        parse_mode: Optional[str] = "Markdown"
    ) -> Dict[str, Any]:
        """Sends a text message to chat_id."""
        payload: Dict[str, Any] = {
            "chat_id": chat_id,
            "text": text
        }
        if reply_markup:
            payload["reply_markup"] = reply_markup
        if parse_mode:
            payload["parse_mode"] = parse_mode
        return await self._request("sendMessage", payload)

    async def edit_message_text(
        self,
        chat_id: int,
        message_id: int,
        text: str,
        reply_markup: Optional[Dict[str, Any]] = None,
        parse_mode: Optional[str] = "Markdown"
    ) -> Dict[str, Any]:
        """Edits an existing message (e.g. after approval button is clicked)."""
        payload: Dict[str, Any] = {
            "chat_id": chat_id,
            "message_id": message_id,
            "text": text
        }
        if reply_markup:
            payload["reply_markup"] = reply_markup
        if parse_mode:
            payload["parse_mode"] = parse_mode
        return await self._request("editMessageText", payload)

    async def answer_callback_query(
        self,
        callback_query_id: str,
        text: Optional[str] = None,
        show_alert: bool = False
    ) -> Dict[str, Any]:
        """Acknowledges an inline keyboard callback query."""
        payload: Dict[str, Any] = {
            "callback_query_id": callback_query_id,
            "show_alert": show_alert
        }
        if text:
            payload["text"] = text
        return await self._request("answerCallbackQuery", payload)

    async def send_approval_request(
        self,
        chat_id: int,
        request_id: str,
        tool: str,
        tier: int,
        preview: str,
        args: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Sends an approval request message with inline buttons.
        Shows exact preview, tier, and tool name.
        """
        tier_label = (
            "Tier 1 (Reversible Action)" if tier == 1 else
            "Tier 2 (External / Destructive Action)" if tier == 2 else
            f"Tier {tier}"
        )

        msg_lines = [
            f"🔒 *Phenom Security Confirmation Required*",
            f"*Tier:* {tier_label}",
            f"*Tool:* `{tool}`",
            "",
            f"*Preview:* {preview}",
            ""
        ]

        if args:
            redacted_preview = {k: v for k, v in args.items() if not any(s in k.lower() for s in ["key", "pass", "token", "secret"])}
            msg_lines.append(f"*Arguments:* `{redacted_preview}`")

        text = "\n".join(msg_lines)

        reply_markup = {
            "inline_keyboard": [
                [
                    {"text": "✅ Approve", "callback_data": f"approve:{request_id}"},
                    {"text": "❌ Deny", "callback_data": f"deny:{request_id}"}
                ]
            ]
        }
        return await self.send_message(chat_id, text, reply_markup=reply_markup)
