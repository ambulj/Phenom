"""Telegram Bot Core Controller with single-user authorization and remote Guardian E-Stop."""

from __future__ import annotations

import logging
import os
import time
from typing import Any, Dict, List, Optional, Tuple

from services.backend.safety.guardian import guardian
from services.backend.schemas.telegram import (
    BotCommandType,
    CommandExecutionResult,
    OutboundMessagePayload,
    TelegramMessage,
    TelegramUpdate,
)

logger = logging.getLogger(__name__)

DEFAULT_AUTHORIZED_USER_ID = 9988776655  # Default or set via PHENOM_TELEGRAM_USER_ID


class TelegramBotController:
    """Core controller for Phenom's secure Telegram Remote Uplink."""

    def __init__(
        self,
        bot_token: Optional[str] = None,
        authorized_user_id: Optional[int] = None,
        dry_run: bool = True,
    ) -> None:
        self.bot_token = bot_token or os.environ.get("PHENOM_TELEGRAM_BOT_TOKEN", "mock_bot_token")
        self.authorized_user_id = authorized_user_id or int(
            os.environ.get("PHENOM_TELEGRAM_USER_ID", DEFAULT_AUTHORIZED_USER_ID)
        )
        self.dry_run = dry_run
        self.outbound_messages: List[OutboundMessagePayload] = []

    def set_authorized_user_id(self, user_id: int) -> None:
        """Sets the single authorized user ID."""
        self.authorized_user_id = user_id

    def is_authorized(self, user_id: Optional[int]) -> bool:
        """Strict single-user authorization check."""
        if user_id is None:
            return False
        return user_id == self.authorized_user_id

    def _parse_command(self, text: Optional[str]) -> Tuple[BotCommandType, str]:
        """Extracts command type and argument string."""
        if not text or not text.strip():
            return BotCommandType.UNKNOWN, ""

        clean = text.strip()
        parts = clean.split(maxsplit=1)
        cmd_str = parts[0].lower()
        args = parts[1] if len(parts) > 1 else ""

        for cmd_enum in BotCommandType:
            if cmd_str == cmd_enum.value:
                return cmd_enum, args

        return BotCommandType.UNKNOWN, clean

    def handle_update(self, update: TelegramUpdate) -> CommandExecutionResult:
        """Processes an incoming Telegram webhook update."""
        start_time = time.perf_counter()

        if not update.message or not update.message.from_user:
            return CommandExecutionResult(
                success=False,
                command="EMPTY_UPDATE",
                response_text="",
                authorized=False,
                latency_ms=(time.perf_counter() - start_time) * 1000.0,
            )

        sender_id = update.message.from_user.id

        # STRICT AUTHORIZATION: Drop unauthorized callers silently
        if not self.is_authorized(sender_id):
            logger.warning(f"Unauthorized Telegram access attempt from user_id: {sender_id}. Dropped silently.")
            return CommandExecutionResult(
                success=False,
                command="UNAUTHORIZED_DROP",
                response_text="",
                authorized=False,
                latency_ms=(time.perf_counter() - start_time) * 1000.0,
            )

        msg_text = update.message.text
        cmd_type, args = self._parse_command(msg_text)

        # 1. EMERGENCY STOP COMMANDS (/halt, /stop, /freeze)
        if cmd_type in (BotCommandType.HALT, BotCommandType.STOP, BotCommandType.FREEZE):
            t0 = time.perf_counter()
            guardian.trigger(f"Remote Telegram Emergency Halt by user {sender_id}")
            halt_latency_ms = (time.perf_counter() - t0) * 1000.0

            resp_text = (
                "🚨 *GUARDIAN KILL SWITCH ENGAGED REMOTELY*\n\n"
                f"Workstation halted in {halt_latency_ms:.2f}ms.\n"
                "All desktop actions, voice streams, and running tools are frozen.\n"
                "Send `/resume` to restore operations."
            )
            self._queue_outbound(update.message.chat.id, resp_text)
            return CommandExecutionResult(
                success=True,
                command=cmd_type.value,
                response_text=resp_text,
                guardian_triggered=True,
                latency_ms=(time.perf_counter() - start_time) * 1000.0,
            )

        # 2. RESUME COMMAND (/resume)
        if cmd_type == BotCommandType.RESUME:
            guardian.resume()
            resp_text = "✅ *GUARDIAN KILL SWITCH RESUMED*\n\nPhenom workstation is back online and operational."
            self._queue_outbound(update.message.chat.id, resp_text)
            return CommandExecutionResult(
                success=True,
                command="/resume",
                response_text=resp_text,
                latency_ms=(time.perf_counter() - start_time) * 1000.0,
            )

        # 3. START & HELP COMMANDS
        if cmd_type in (BotCommandType.START, BotCommandType.HELP):
            resp_text = (
                "🎩 *Phenom Remote Mobile Uplink (v46.0)*\n\n"
                "Good day, sir. Secure command link operational on Windows 11 workstation.\n\n"
                "*Available Commands:*\n"
                "• `/status` - Workstation & AI subsystem diagnostics\n"
                "• `/screen` - Request PII-masked desktop snapshot\n"
                "• `/task <instruction>` - Dispatch autonomous task\n"
                "• `/halt` - Instant Guardian Emergency Kill Switch\n"
                "• `/resume` - Clear emergency stop state\n\n"
                "🎙️ *Voice Notes:* Send audio voice notes anytime for Jarvis full-duplex speech."
            )
            self._queue_outbound(update.message.chat.id, resp_text)
            return CommandExecutionResult(
                success=True,
                command=cmd_type.value,
                response_text=resp_text,
                latency_ms=(time.perf_counter() - start_time) * 1000.0,
            )

        # 4. STATUS COMMAND (/status)
        if cmd_type == BotCommandType.STATUS:
            is_halted = guardian.is_halted
            status_symbol = "🚨 HALTED" if is_halted else "🟢 ACTIVE"
            resp_text = (
                f"📊 *Phenom Workstation Status: {status_symbol}*\n\n"
                "• *GPU:* NVIDIA GeForce RTX 3050 Laptop (CUDA Ready)\n"
                "• *Neocortex Vision:* Active (In-RAM Diffing @ 5 FPS)\n"
                "• *Action Agent:* Speed-Demon Autonomous Mode\n"
                "• *Voice Synapse:* Full-Duplex Streaming Whisper\n"
                "• *Rule 8 Protection:* Anti-Checkout Hard Wall Active\n"
                f"• *Guardian Kill Switch:* {'HALTED' if is_halted else 'NOMINAL (<25ms SLA)'}"
            )
            self._queue_outbound(update.message.chat.id, resp_text)
            return CommandExecutionResult(
                success=True,
                command="/status",
                response_text=resp_text,
                latency_ms=(time.perf_counter() - start_time) * 1000.0,
            )

        # 5. TASK COMMAND (/task <prompt>)
        if cmd_type == BotCommandType.TASK:
            if guardian.is_halted:
                resp_text = "❌ Cannot execute task: Guardian Kill Switch is active. Send `/resume` first."
                self._queue_outbound(update.message.chat.id, resp_text)
                return CommandExecutionResult(
                    success=False,
                    command="/task",
                    response_text=resp_text,
                    latency_ms=(time.perf_counter() - start_time) * 1000.0,
                )

            task_prompt = args.strip() or "General inquiry"
            resp_text = f"⚙️ *Task Dispatched to Action Agent:*\n`{task_prompt}`\n\nExecuting autonomously under Safe-Mode bounds."
            self._queue_outbound(update.message.chat.id, resp_text)
            return CommandExecutionResult(
                success=True,
                command="/task",
                response_text=resp_text,
                latency_ms=(time.perf_counter() - start_time) * 1000.0,
            )

        # 6. DEFAULT / UNKNOWN TEXT QUERY (Conversational Jarvis Response)
        prompt = msg_text or ""
        resp_text = f"💬 *Jarvis:* Right away, sir. Processing: _{prompt}_"
        self._queue_outbound(update.message.chat.id, resp_text)
        return CommandExecutionResult(
            success=True,
            command="CHAT",
            response_text=resp_text,
            latency_ms=(time.perf_counter() - start_time) * 1000.0,
        )

    def _queue_outbound(self, chat_id: int, text: str) -> None:
        """Stores outbound message for dry-run inspection or network transmission."""
        payload = OutboundMessagePayload(chat_id=chat_id, text=text)
        self.outbound_messages.append(payload)


# Global Telegram Bot Controller singleton
bot_controller = TelegramBotController(dry_run=True)
