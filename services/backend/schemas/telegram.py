"""Pydantic schemas for Phenom Secure Telegram Remote Uplink."""

from __future__ import annotations

from enum import Enum
from typing import Any, Dict, Optional
from pydantic import BaseModel, Field, ConfigDict


class TelegramUser(BaseModel):
    """Telegram user object."""
    id: int
    is_bot: bool = False
    first_name: str
    username: Optional[str] = None


class TelegramChat(BaseModel):
    """Telegram chat object."""
    id: int
    type: str = "private"
    title: Optional[str] = None


class TelegramVoice(BaseModel):
    """Telegram incoming voice note object."""
    file_id: str
    file_unique_id: str
    duration: int
    mime_type: str = "audio/ogg"
    file_size: Optional[int] = None


class TelegramMessage(BaseModel):
    """Telegram incoming message object."""
    model_config = ConfigDict(populate_by_name=True)

    message_id: int
    from_user: Optional[TelegramUser] = Field(None, alias="from")
    chat: TelegramChat
    date: int
    text: Optional[str] = None
    voice: Optional[TelegramVoice] = None


class TelegramUpdate(BaseModel):
    """Telegram webhook update object."""
    update_id: int
    message: Optional[TelegramMessage] = None


class BotCommandType(str, Enum):
    """Supported Telegram bot commands."""
    START = "/start"
    HELP = "/help"
    STATUS = "/status"
    HALT = "/halt"
    STOP = "/stop"
    FREEZE = "/freeze"
    RESUME = "/resume"
    TASK = "/task"
    SCREEN = "/screen"
    VOICE = "/voice"
    UNKNOWN = "UNKNOWN"


class OutboundMessagePayload(BaseModel):
    """Payload for sending outbound text messages to Telegram."""
    chat_id: int
    text: str
    parse_mode: str = "Markdown"
    reply_to_message_id: Optional[int] = None


class CommandExecutionResult(BaseModel):
    """Result of processing a remote Telegram command."""
    success: bool
    command: str
    response_text: str
    guardian_triggered: bool = False
    latency_ms: float = 0.0
    authorized: bool = True
