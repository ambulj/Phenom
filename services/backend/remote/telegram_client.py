"""
Phenom Telegram Bot API Client (Phase 6 & Hardening Task 7g)
Async HTTP client for the official Telegram Bot API using httpx.
Handles:
1. Long-polling updates retrieval (getUpdates).
2. Text message delivery with markdown and inline keyboards (sendMessage, editMessageText).
3. In-memory photo transmission with multipart upload (sendPhoto).
4. Ephemeral message deletion for PIN security (deleteMessage).
5. File metadata inspection and downloading for voice notes (getFile, download_file).
"""

import json
import httpx
from typing import Dict, Any, List, Optional

TELEGRAM_API_BASE = "https://api.telegram.org/bot"
TELEGRAM_FILE_BASE = "https://api.telegram.org/file/bot"

class TelegramClient:
    def __init__(self, token: Optional[str] = None, client: Optional[httpx.AsyncClient] = None):
        self.token = token
        self._custom_client = client

    def _get_url(self, method: str) -> str:
        if not self.token:
            raise ValueError("Telegram Bot Token is not configured.")
        return f"{TELEGRAM_API_BASE}{self.token}/{method}"

    def _get_file_download_url(self, file_path: str) -> str:
        if not self.token:
            raise ValueError("Telegram Bot Token is not configured.")
        return f"{TELEGRAM_FILE_BASE}{self.token}/{file_path}"

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

    async def send_photo(
        self,
        chat_id: int,
        photo_bytes: bytes,
        caption: Optional[str] = None,
        reply_markup: Optional[Dict[str, Any]] = None,
        parse_mode: Optional[str] = "Markdown"
    ) -> Dict[str, Any]:
        """
        Sends an in-memory photo (e.g. obfuscated desktop screenshot) via multipart upload.
        Never touches the disk.
        """
        url = self._get_url("sendPhoto")
        data: Dict[str, Any] = {"chat_id": str(chat_id)}
        if caption:
            data["caption"] = caption
        if parse_mode:
            data["parse_mode"] = parse_mode
        if reply_markup:
            data["reply_markup"] = json.dumps(reply_markup)

        files = {"photo": ("screenshot.jpg", photo_bytes, "image/jpeg")}

        if self._custom_client:
            resp = await self._custom_client.post(url, data=data, files=files, timeout=20.0)
        else:
            async with httpx.AsyncClient(timeout=20.0) as client:
                resp = await client.post(url, data=data, files=files, timeout=20.0)

        if resp.status_code != 200:
            raise RuntimeError(f"Telegram API sendPhoto error ({resp.status_code}): {resp.text}")
        result = resp.json()
        if not result.get("ok"):
            raise RuntimeError(f"Telegram sendPhoto failed: {result.get('description')}")
        return result.get("result", {})

    async def delete_message(self, chat_id: int, message_id: int) -> Dict[str, Any]:
        """
        Deletes a message from chat.
        Used for 15-second ephemeral message deletion of sensitive PINs.
        """
        payload = {"chat_id": chat_id, "message_id": message_id}
        return await self._request("deleteMessage", payload)

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

    async def get_file(self, file_id: str) -> Dict[str, Any]:
        """Retrieves file metadata from Telegram (e.g. file_path for voice audio)."""
        return await self._request("getFile", {"file_id": file_id})

    async def download_file(self, file_path: str) -> bytes:
        """Downloads file bytes in-memory from Telegram file API."""
        url = self._get_file_download_url(file_path)
        if self._custom_client:
            resp = await self._custom_client.get(url, timeout=20.0)
        else:
            async with httpx.AsyncClient(timeout=20.0) as client:
                resp = await client.get(url, timeout=20.0)

        if resp.status_code != 200:
            raise RuntimeError(f"Failed to download Telegram file ({resp.status_code})")
        return resp.content

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
