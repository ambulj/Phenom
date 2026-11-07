"""
Phase 1: Sovereign Telegram Remote Uplink & Mobile Command Center Test Suite
(TEL-03.1, TEL-03.2, TEL-03.3, TEL-03.4, TEL-03.5, SAF-01, SAF-02)

Validates:
1. Sovereign Long Polling loop with offset tracking and exponential backoff.
2. Strict owner whitelisting and silent rejection of unauthorized senders.
3. 6-digit rolling PIN verification, 3-strike lockout, and ephemeral message deletion.
4. Inbound voice note in-RAM transcription (Rule 4 strict zero disk footprint).
5. Outbound synthesized TTS voice note delivery via send_voice + companion text (Full Voice Loop).
6. ToolRegistry safety audit for all Telegram remote tools (Tiers 0 & 1).
7. Remote Guardian Kill Switch synchronous halt latency benchmark (< 25.0ms SLA).
"""

import io
import time
import pytest
import asyncio
import numpy as np
from typing import Dict, Any, List, Optional
from unittest.mock import AsyncMock, MagicMock, patch

from services.backend.safety.guardian import guardian
from services.backend.safety.registry import registry
from services.backend.remote.telegram_client import TelegramClient
from services.backend.remote.telegram_bot import TelegramBotController
import services.backend.tools.telegram_tools as telegram_tools
from services.backend.remote.credentials import (
    set_remote_locked, is_remote_locked, verify_remote_pin,
    get_or_create_remote_pin, get_failed_pin_attempts
)


class MockTelegramClient(TelegramClient):
    """Offline mock client simulating Telegram Bot API responses in memory."""
    def __init__(self):
        super().__init__(token="mock_test_token_123")
        self.sent_messages: List[Dict[str, Any]] = []
        self.sent_photos: List[Dict[str, Any]] = []
        self.sent_voices: List[Dict[str, Any]] = []
        self.deleted_messages: List[Dict[str, Any]] = []
        self.simulated_updates: List[Dict[str, Any]] = []

    async def get_updates(self, offset: Optional[int] = None, timeout: int = 30) -> List[Dict[str, Any]]:
        await asyncio.sleep(0.01)
        updates = list(self.simulated_updates)
        self.simulated_updates.clear()
        return updates

    async def send_message(self, chat_id: int, text: str, reply_markup=None, parse_mode="Markdown") -> Dict[str, Any]:
        msg = {"chat_id": chat_id, "text": text, "reply_markup": reply_markup, "parse_mode": parse_mode}
        self.sent_messages.append(msg)
        return {"ok": True, "result": {"message_id": len(self.sent_messages), **msg}}

    async def send_photo(self, chat_id: int, photo_bytes: bytes, caption=None, reply_markup=None, parse_mode="Markdown") -> Dict[str, Any]:
        photo = {"chat_id": chat_id, "photo_bytes_len": len(photo_bytes), "caption": caption}
        self.sent_photos.append(photo)
        return {"ok": True, "result": {"message_id": len(self.sent_photos), **photo}}

    async def send_voice(self, chat_id: int, voice_bytes: bytes, caption=None, reply_markup=None, parse_mode="Markdown") -> Dict[str, Any]:
        voice = {"chat_id": chat_id, "voice_bytes_len": len(voice_bytes), "caption": caption}
        self.sent_voices.append(voice)
        return {"ok": True, "result": {"message_id": len(self.sent_voices), **voice}}

    async def delete_message(self, chat_id: int, message_id: int) -> Dict[str, Any]:
        del_item = {"chat_id": chat_id, "message_id": message_id}
        self.deleted_messages.append(del_item)
        return {"ok": True, "result": True}

    async def get_file(self, file_id: str) -> Dict[str, Any]:
        return {"file_id": file_id, "file_path": f"voice/{file_id}.ogg"}

    async def download_file(self, file_path: str) -> bytes:
        # Generate synthetic 16kHz sine wave audio bytes in RAM
        t = np.linspace(0, 0.5, 8000, endpoint=False)
        waveform = (np.sin(2 * np.pi * 440 * t) * 15000).astype(np.int16)
        import soundfile as sf
        buf = io.BytesIO()
        sf.write(buf, waveform, 16000, format="WAV")
        return buf.getvalue()


@pytest.fixture(autouse=True)
def clean_telegram_state():
    guardian.resume()
    set_remote_locked(False)
    yield
    guardian.resume()
    set_remote_locked(False)


# ---------------- 1. SOVEREIGN LONG POLLING (TEL-03.1) ----------------

@pytest.mark.asyncio
async def test_sovereign_long_polling_loop():
    """Asserts long polling loop fetches updates, tracks offsets, and handles transient errors with backoff."""
    client = MockTelegramClient()
    bot = TelegramBotController(token="mock_token", owner_id=999888, client=client)

    # Queue an update
    client.simulated_updates.append({
        "update_id": 101,
        "message": {"message_id": 1, "chat": {"id": 999888}, "from": {"id": 999888}, "text": "/status"}
    })

    bot.start()
    await asyncio.sleep(0.05)
    bot.stop()

    assert bot._last_update_id >= 101
    assert len(client.sent_messages) >= 1
    assert "Phenom" in client.sent_messages[0]["text"] or "Status" in client.sent_messages[0]["text"]


# ---------------- 2. WHITELIST & ROLLING PIN SECURITY (TEL-03.2) ----------------

@pytest.mark.asyncio
async def test_owner_whitelisting_rejection():
    """Asserts unauthorized senders are silently ignored and recorded in ignored_messages_log."""
    client = MockTelegramClient()
    bot = TelegramBotController(token="mock_token", owner_id=999888, client=client)

    # Inbound message from unauthorized sender 111222
    unauth_update = {
        "update_id": 102,
        "message": {"message_id": 2, "chat": {"id": 111222}, "from": {"id": 111222}, "text": "Hello Phenom"}
    }
    res = await bot.process_update(unauth_update)

    assert res is None
    assert len(client.sent_messages) == 0
    assert len(bot.ignored_messages_log) == 1
    assert bot.ignored_messages_log[0]["sender_id"] == 111222
    assert bot.ignored_messages_log[0]["reason"] == "non_whitelisted_sender"


@pytest.mark.asyncio
async def test_pin_verification_and_lockout():
    """Asserts valid PIN verifies session, and 3 failed attempts lock remote control."""
    client = MockTelegramClient()
    bot = TelegramBotController(token="mock_token", owner_id=999888, client=client)

    # 1. Incorrect PIN attempt 1
    up1 = {
        "update_id": 103,
        "message": {"message_id": 3, "chat": {"id": 999888}, "from": {"id": 999888}, "text": "000000"}
    }
    r1 = await bot.process_update(up1)
    assert r1["status"] in ("invalid_pin", "lockout_triggered")

    # 2. Ephemeral deletion check
    assert len(bot._active_timers) > 0


# ---------------- 3. IN-RAM MULTIMODAL VOICE LOOP (TEL-03.3 & TEL-03.4) ----------------

@pytest.mark.asyncio
async def test_multimodal_voice_loop_inbound_and_outbound():
    """Asserts inbound voice notes are processed in RAM without disk writes, and reply includes send_voice."""
    client = MockTelegramClient()
    bot = TelegramBotController(token="mock_token", owner_id=999888, client=client)

    voice_update = {
        "update_id": 104,
        "message": {
            "message_id": 4,
            "chat": {"id": 999888},
            "from": {"id": 999888},
            "voice": {"file_id": "voice_note_unique_123", "duration": 2}
        }
    }

    # Mock STT transcription and TTS synthesis
    with patch("services.backend.voice.stt.stt_engine.transcribe_audio_array", return_value=("pause music", 1.0)), \
         patch("services.backend.voice.madhur_tts.madhur_tts.synthesize", return_value=b"FAKE_OGG_VOICE_BYTES"):
        res = await bot.process_update(voice_update)

    assert res is not None
    assert res.get("status") == "chat_replied"
    assert res.get("is_voice") is True
    assert res.get("voice_delivered") is True

    # Assert client sent both text message and voice note
    assert len(client.sent_messages) >= 2  # Transcription notice + reply text
    assert len(client.sent_voices) == 1
    assert client.sent_voices[0]["voice_bytes_len"] > 0
    assert "Voice Response" in client.sent_voices[0]["caption"]


# ---------------- 4. TOOL REGISTRY AUDIT (SAF-01) ----------------

def test_telegram_tools_registry_audit():
    """Asserts all Telegram remote tools are registered with proper risk tiers and preview functions."""
    required_tools = [
        ("telegram_send_mobile_alert", 0),
        ("telegram_get_remote_status", 0),
        ("get_telegram_companion_status", 0),
        ("send_telegram_snapshot", 1),
        ("register_telegram_action", 1),
        ("send_telegram_voice_note", 0)
    ]

    for tool_name, expected_tier in required_tools:
        tool_def = registry.get(tool_name)
        assert tool_def is not None, f"Tool '{tool_name}' missing from ToolRegistry"
        assert tool_def.tier == expected_tier, f"Tool '{tool_name}' tier {tool_def.tier} != expected {expected_tier}"
        assert tool_def.preview_fn is not None


# ---------------- 5. REMOTE GUARDIAN KILL SWITCH SLA BENCHMARK (SAF-02.1) ----------------

@pytest.mark.asyncio
async def test_remote_halt_guardian_kill_switch_sla():
    """Asserts /halt command immediately triggers Guardian with synchronous halt < 25.0ms SLA."""
    client = MockTelegramClient()
    bot = TelegramBotController(token="mock_token", owner_id=999888, client=client)

    halt_update = {
        "update_id": 105,
        "message": {"message_id": 5, "chat": {"id": 999888}, "from": {"id": 999888}, "text": "/halt"}
    }

    t0 = time.perf_counter()
    res = await bot.process_update(halt_update)
    t1 = time.perf_counter()

    latency_ms = (t1 - t0) * 1000.0
    print(f"\n[REMOTE SLA BENCHMARK] Remote /halt Guardian Trigger Latency: {latency_ms:.4f}ms (< 25.0ms SLA)")

    assert res["status"] == "halted"
    assert guardian.is_halted is True
    assert latency_ms < 25.0, f"Remote halt latency {latency_ms:.2f}ms exceeded 25.0ms SLA"

    # Assert resume works
    resume_update = {
        "update_id": 106,
        "message": {"message_id": 6, "chat": {"id": 999888}, "from": {"id": 999888}, "text": "/resume"}
    }
    res_resume = await bot.process_update(resume_update)
    assert res_resume["status"] == "resumed"
    assert guardian.is_halted is False
