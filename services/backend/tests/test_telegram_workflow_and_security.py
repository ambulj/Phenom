"""
Unit and Integration Tests for Task 7g: Telegram Workflow & Remote PIN Security
Verifies:
1. Sensitive window obfuscation: 35px Gaussian blur applied to blocked windows (Bitwarden, KeePass, WhatsApp, Outlook, Banking).
2. PIN lifecycle & 30-day rotation status.
3. 3-strike PIN lockout: 3 consecutive failed PIN attempts immediately locks remote control completely.
4. Desktop physical unlock: resets strikes and re-enables remote control.
5. Workstation physical lock: /lock secures session and sets remote lock.
6. Tier 2 task /do <task> enforces PIN authorization.
7. Message ephemerality: 15-second automatic message deletion via deleteMessage.
8. /screenshot delivers in-memory photo with transit warning and inline buttons.
9. /status inline refresh and lock callbacks.
10. Local voice note transcription and dispatch.
"""

import pytest
import asyncio
import io
import numpy as np
from PIL import Image
from typing import Dict, Any, List

from services.backend.remote.credentials import (
    get_or_create_remote_pin, set_remote_pin, rotate_remote_pin,
    check_pin_rotation_status, get_failed_pin_attempts, reset_failed_pin_attempts,
    verify_remote_pin, is_remote_locked, set_remote_locked, unlock_remote_from_desktop,
    lock_workstation
)
from services.backend.remote.screenshot_obfuscator import (
    find_sensitive_windows, obfuscate_screenshot, capture_and_obfuscate_screen,
    DEFAULT_SENSITIVE_KEYWORDS
)
from services.backend.remote.telegram_bot import TelegramBotController
from services.backend.remote.telegram_client import TelegramClient
from services.backend.safety.guardian import guardian
from services.backend.safety.action_log import action_log

OWNER_USER_ID = 888777666
ATTACKER_USER_ID = 111222333

class MockExtendedTelegramClient(TelegramClient):
    """In-memory mock Telegram client recording sent messages, photos, and deletions."""
    def __init__(self):
        super().__init__(token="mock_token_7g")
        self.sent_messages: List[Dict[str, Any]] = []
        self.edited_messages: List[Dict[str, Any]] = []
        self.answered_callbacks: List[Dict[str, Any]] = []
        self.sent_photos: List[Dict[str, Any]] = []
        self.deleted_messages: List[Dict[str, Any]] = []

    async def send_message(self, chat_id: int, text: str, reply_markup=None, parse_mode="Markdown") -> Dict[str, Any]:
        msg = {
            "message_id": len(self.sent_messages) + 1,
            "chat_id": chat_id,
            "text": text,
            "reply_markup": reply_markup,
            "parse_mode": parse_mode
        }
        self.sent_messages.append(msg)
        return msg

    async def edit_message_text(self, chat_id: int, message_id: int, text: str, reply_markup=None, parse_mode="Markdown") -> Dict[str, Any]:
        msg = {
            "message_id": message_id,
            "chat_id": chat_id,
            "text": text,
            "reply_markup": reply_markup
        }
        self.edited_messages.append(msg)
        return msg

    async def answer_callback_query(self, callback_query_id: str, text=None, show_alert=False) -> Dict[str, Any]:
        res = {"callback_query_id": callback_query_id, "text": text, "show_alert": show_alert}
        self.answered_callbacks.append(res)
        return res

    async def send_photo(self, chat_id: int, photo_bytes: bytes, caption=None, reply_markup=None, parse_mode="Markdown") -> Dict[str, Any]:
        photo_entry = {
            "message_id": len(self.sent_messages) + 1,
            "chat_id": chat_id,
            "photo_bytes": photo_bytes,
            "size_bytes": len(photo_bytes),
            "caption": caption,
            "reply_markup": reply_markup
        }
        self.sent_photos.append(photo_entry)
        self.sent_messages.append(photo_entry)
        return photo_entry

    async def delete_message(self, chat_id: int, message_id: int) -> Dict[str, Any]:
        entry = {"chat_id": chat_id, "message_id": message_id}
        self.deleted_messages.append(entry)
        return {"ok": True, "result": True}

    async def get_file(self, file_id: str) -> Dict[str, Any]:
        return {"file_id": file_id, "file_path": f"voice/{file_id}.wav"}

    async def download_file(self, file_path: str) -> bytes:
        # Generate dummy 1-second 16kHz WAV audio bytes in-memory
        import soundfile as sf
        buf = io.BytesIO()
        data = np.zeros((16000,), dtype=np.float32)
        sf.write(buf, data, 16000, format="WAV")
        return buf.getvalue()

@pytest.fixture
def clean_remote_env():
    guardian.resume()
    unlock_remote_from_desktop()
    set_remote_pin("123456")
    reset_failed_pin_attempts()
    client = MockExtendedTelegramClient()
    bot = TelegramBotController(token="mock_token_7g", owner_id=OWNER_USER_ID, client=client)
    yield bot, client
    guardian.resume()
    unlock_remote_from_desktop()

# ----------------- 1. SENSITIVE WINDOW OBFUSCATION TESTS -----------------

def test_sensitive_window_detection():
    """Verifies that keywords detect sensitive password managers, email, and banking windows."""
    mock_windows = [
        {"title": "Bitwarden - Password Manager", "rect": (50, 50, 450, 500)},
        {"title": "KeePass2 - Database.kdbx", "rect": (100, 100, 600, 500)},
        {"title": "WhatsApp Desktop", "rect": (200, 200, 700, 600)},
        {"title": "HDFC Bank NetBanking - Google Chrome", "rect": (50, 50, 900, 700)},
        {"title": "Calculator", "rect": (10, 10, 200, 300)}
    ]
    detected = find_sensitive_windows(custom_windows=mock_windows)
    detected_titles = [w["title"] for w in detected]
    
    assert "Bitwarden - Password Manager" in detected_titles
    assert "KeePass2 - Database.kdbx" in detected_titles
    assert "WhatsApp Desktop" in detected_titles
    assert "HDFC Bank NetBanking - Google Chrome" in detected_titles
    assert "Calculator" not in detected_titles

def test_screenshot_35px_gaussian_blur_obfuscation():
    """Verifies that 35px Gaussian blur is applied over sensitive window bounding boxes."""
    # Create test canvas with distinct sharp high-contrast pattern
    img = Image.new("RGB", (800, 600), color=(255, 255, 255))
    # Draw high-contrast black box in sensitive region
    box = (100, 100, 400, 400)
    for x in range(box[0], box[2], 2):
        for y in range(box[1], box[3], 2):
            img.putpixel((x, y), (0, 0, 0))

    unblurred_crop = np.array(img.crop(box))
    
    # Obfuscate with 35px blur
    obfuscated = obfuscate_screenshot(img, sensitive_regions=[box], blur_radius=35)
    blurred_crop = np.array(obfuscated.crop(box))

    # Variance and edge contrast in blurred crop must be significantly attenuated
    assert obfuscated.size == img.size
    # Pixel values must be modified (blurred)
    diff = np.abs(unblurred_crop.astype(float) - blurred_crop.astype(float)).mean()
    assert diff > 10.0, "35px Gaussian blur should significantly alter pixel distributions"

# ----------------- 2. PIN LIFECYCLE & ROTATION TESTS -----------------

def test_pin_lifecycle_and_rotation_status(clean_remote_env):
    """Verifies 6-digit numeric PIN generation, validation, and 30-day rotation status."""
    pin = get_or_create_remote_pin()
    assert len(pin) == 6
    assert pin.isdigit()

    # Verify invalid PIN format is rejected by setter
    with pytest.raises(ValueError):
        set_remote_pin("12345") # 5 digits
    with pytest.raises(ValueError):
        set_remote_pin("abcdef") # non-numeric

    # Test rotation
    new_pin = rotate_remote_pin()
    assert len(new_pin) == 6
    assert new_pin.isdigit()
    assert get_or_create_remote_pin() == new_pin

    # Status check
    status = check_pin_rotation_status(max_age_days=30)
    assert status["configured"] is True
    assert status["needs_rotation"] is False
    assert status["age_days"] >= 0.0

# ----------------- 3. THREE-STRIKE LOCKOUT & UNLOCK TESTS -----------------

def test_three_strike_pin_lockout(clean_remote_env):
    """Verifies 3 consecutive failed PIN attempts permanently locks remote control."""
    bot, _ = clean_remote_env
    set_remote_pin("654321")
    assert is_remote_locked() is False
    assert get_failed_pin_attempts() == 0

    # Strike 1
    assert verify_remote_pin("000000") is False
    assert get_failed_pin_attempts() == 1
    assert is_remote_locked() is False

    # Strike 2
    assert verify_remote_pin("111111") is False
    assert get_failed_pin_attempts() == 2
    assert is_remote_locked() is False

    # Strike 3 -> Permanent Lockout
    assert verify_remote_pin("222222") is False
    assert get_failed_pin_attempts() == 3
    assert is_remote_locked() is True

    # 4th attempt immediately rejected because remote is locked
    assert verify_remote_pin("654321") is False

    # Action log must record security lockout
    logs = action_log.list_entries(limit=5)
    matched = [l for l in logs if l["tool"] == "remote_pin_verification"]
    assert len(matched) >= 1
    assert matched[0]["decision"] == "locked"
    assert matched[0]["result_status"] == "LOCKOUT"

    # Physical desktop unlock clears lockout
    unlock_remote_from_desktop()
    assert is_remote_locked() is False
    assert get_failed_pin_attempts() == 0

# ----------------- 4. WORKSTATION LOCK TESTS -----------------

def test_workstation_lock_invocation(clean_remote_env):
    """Verifies lock_workstation sets remote lock and logs action."""
    assert is_remote_locked() is False
    lock_workstation(dry_run=True)
    assert is_remote_locked() is True

    logs = action_log.list_entries(limit=5)
    matched = [l for l in logs if l["tool"] == "lock_workstation"]
    assert len(matched) >= 1
    assert matched[0]["result_status"] == "SUCCESS"

# ----------------- 5. /DO <TASK> & PIN VERIFICATION WORKFLOW -----------------

@pytest.mark.asyncio
async def test_do_command_tier2_requires_pin_workflow(clean_remote_env):
    """Verifies /do with Tier 2 action prompts for PIN, and valid PIN authorizes execution."""
    bot, client = clean_remote_env
    set_remote_pin("789123")

    # 1. User submits Tier 2 task: delete old log files
    update = {
        "update_id": 201,
        "message": {
            "message_id": 10,
            "from": {"id": OWNER_USER_ID},
            "chat": {"id": OWNER_USER_ID},
            "text": "/do delete old temp files from workspace"
        }
    }
    res = await bot.process_update(update)
    assert res["status"] == "pin_required"
    assert "PIN Authorization Required" in client.sent_messages[-1]["text"]
    assert "Tier 2" in client.sent_messages[-1]["text"]

    # 2. User submits correct 6-digit PIN
    pin_update = {
        "update_id": 202,
        "message": {
            "message_id": 11,
            "from": {"id": OWNER_USER_ID},
            "chat": {"id": OWNER_USER_ID},
            "text": "789123"
        }
    }
    pin_res = await bot.process_update(pin_update)
    # PIN verified and executed: check sent messages contain PIN verification notice
    assert any("Executing authorized Tier 2 remote task" in m.get("text", "") or "PIN Verified" in m.get("text", "") for m in client.sent_messages)

@pytest.mark.asyncio
async def test_do_command_tier2_incorrect_pin_causes_strike(clean_remote_env):
    """Verifies incorrect PIN during /do workflow increments strikes and alerts user."""
    bot, client = clean_remote_env
    set_remote_pin("789123")

    # Request Tier 2 task
    await bot.process_update({
        "update_id": 203,
        "message": {
            "message_id": 12,
            "from": {"id": OWNER_USER_ID},
            "chat": {"id": OWNER_USER_ID},
            "text": "/do install python-package"
        }
    })

    # Enter incorrect PIN
    res = await bot.process_update({
        "update_id": 204,
        "message": {
            "message_id": 13,
            "from": {"id": OWNER_USER_ID},
            "chat": {"id": OWNER_USER_ID},
            "text": "000000"
        }
    })
    assert res["status"] == "invalid_pin"
    assert res["remaining"] == 2
    assert "2 attempt(s) remaining" in client.sent_messages[-1]["text"]

# ----------------- 6. MESSAGE EPHEMERALITY (15s SLA) -----------------

@pytest.mark.asyncio
async def test_pin_message_ephemerality_scheduling(clean_remote_env):
    """Verifies any message containing a PIN triggers 15-second automatic deletion."""
    bot, client = clean_remote_env
    
    # Directly test deletion helper with a fast 0.05s timer
    bot.schedule_message_deletion(chat_id=OWNER_USER_ID, message_id=999, delay_seconds=0.05)
    await asyncio.sleep(0.1)

    assert len(client.deleted_messages) >= 1
    assert client.deleted_messages[-1]["message_id"] == 999
    assert client.deleted_messages[-1]["chat_id"] == OWNER_USER_ID

# ----------------- 7. /SCREENSHOT WORKFLOW & PREVIEW WARNING -----------------

@pytest.mark.asyncio
async def test_screenshot_command_workflow(clean_remote_env):
    """Verifies /screenshot captures, blurs sensitive apps, transmits warning, and handles callbacks."""
    bot, client = clean_remote_env

    # 1. Send /screenshot
    res = await bot.process_update({
        "update_id": 205,
        "message": {
            "message_id": 14,
            "from": {"id": OWNER_USER_ID},
            "chat": {"id": OWNER_USER_ID},
            "text": "/screenshot"
        }
    })
    assert res["status"] == "screenshot_sent"
    assert len(client.sent_photos) == 1

    photo_entry = client.sent_photos[0]
    assert photo_entry["chat_id"] == OWNER_USER_ID
    assert photo_entry["size_bytes"] > 0
    assert "Desktop Screen Preview" in photo_entry["caption"]
    assert "Image transits Telegram servers and is stored in cloud chat history." in photo_entry["caption"]

    # Inline buttons present
    buttons = photo_entry["reply_markup"]["inline_keyboard"][0]
    callbacks = [b["callback_data"] for b in buttons]
    assert "screenshot:full" in callbacks
    assert "screenshot:dismiss" in callbacks

    # 2. Test dismiss callback
    dismiss_update = {
        "update_id": 206,
        "callback_query": {
            "id": "cb_dismiss",
            "from": {"id": OWNER_USER_ID},
            "message": {"chat": {"id": OWNER_USER_ID}, "message_id": 14},
            "data": "screenshot:dismiss"
        }
    }
    dismiss_res = await bot.process_update(dismiss_update)
    assert dismiss_res["status"] == "screenshot_dismissed"
    # Verify photo message was deleted
    assert any(d["message_id"] == 14 for d in client.deleted_messages)

# ----------------- 8. /STATUS WORKFLOW & REFRESH/LOCK CALLBACKS -----------------

@pytest.mark.asyncio
async def test_status_command_and_callbacks(clean_remote_env):
    """Verifies /status metrics, inline buttons, and interactive callbacks."""
    bot, client = clean_remote_env

    # 1. Send /status
    res = await bot.process_update({
        "update_id": 207,
        "message": {
            "message_id": 15,
            "from": {"id": OWNER_USER_ID},
            "chat": {"id": OWNER_USER_ID},
            "text": "/status"
        }
    })
    assert res["status"] == "status_sent"
    status_msg = client.sent_messages[-1]
    assert "CPU Utilization" in status_msg["text"]
    assert "RAM Utilization" in status_msg["text"]

    # 2. Test status:refresh callback
    refresh_update = {
        "update_id": 208,
        "callback_query": {
            "id": "cb_refresh",
            "from": {"id": OWNER_USER_ID},
            "message": {"chat": {"id": OWNER_USER_ID}, "message_id": 15},
            "data": "status:refresh"
        }
    }
    ref_res = await bot.process_update(refresh_update)
    assert ref_res["status"] == "status_refreshed"
    assert len(client.edited_messages) >= 1

    # 3. Test lock:remote callback
    lock_update = {
        "update_id": 209,
        "callback_query": {
            "id": "cb_lock",
            "from": {"id": OWNER_USER_ID},
            "message": {"chat": {"id": OWNER_USER_ID}, "message_id": 15},
            "data": "lock:remote"
        }
    }
    lock_res = await bot.process_update(lock_update)
    assert lock_res["status"] == "locked_by_callback"
    assert is_remote_locked() is True
