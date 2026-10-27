"""
Phenom Telegram Remote Credentials & Configuration (Phase 6)
Stores and retrieves Telegram bot token and owner user ID securely
using Windows Credential Manager under:
- 'Phenom/telegram-token'
- 'Phenom/telegram-owner-id'
Falls back to environment variables (TELEGRAM_BOT_TOKEN, TELEGRAM_OWNER_ID)
or DB settings for development/testing.
"""

import os
import win32cred
from typing import Optional, Tuple
from services.backend.memory.db import encrypted_db

CRED_TELEGRAM_TOKEN = "Phenom/telegram-token"
CRED_TELEGRAM_OWNER_ID = "Phenom/telegram-owner-id"

def get_telegram_token() -> Optional[str]:
    """Retrieves the Telegram bot token from Credential Manager or env."""
    env_token = os.environ.get("TELEGRAM_BOT_TOKEN")
    if env_token:
        return env_token

    try:
        cred = win32cred.CredRead(CRED_TELEGRAM_TOKEN, win32cred.CRED_TYPE_GENERIC)
        blob = cred["CredentialBlob"]
        if isinstance(blob, bytes):
            return blob.decode("utf-16le")
        return str(blob)
    except Exception:
        pass

    # Check DB settings
    try:
        conn = encrypted_db.get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT value FROM settings WHERE key = 'telegram_token';")
        row = cursor.fetchone()
        conn.close()
        if row:
            return row[0]
    except Exception:
        pass

    return None

def set_telegram_token(token: str) -> None:
    """Stores the Telegram bot token in Windows Credential Manager."""
    clean_token = token.strip()
    try:
        cred = {
            "Type": win32cred.CRED_TYPE_GENERIC,
            "TargetName": CRED_TELEGRAM_TOKEN,
            "CredentialBlob": clean_token,
            "Persist": win32cred.CRED_PERSIST_LOCAL_MACHINE,
            "Comment": "Phenom Telegram Bot API Token"
        }
        win32cred.CredWrite(cred, 0)
    except Exception as e:
        print(f"[TelegramCredentials] Failed to write token to Credential Manager: {e}")

    # Also persist to encrypted DB settings
    try:
        conn = encrypted_db.get_connection()
        with conn:
            conn.execute(
                "INSERT INTO settings (key, value) VALUES ('telegram_token', ?) "
                "ON CONFLICT(key) DO UPDATE SET value = excluded.value;",
                (clean_token,)
            )
        conn.close()
    except Exception:
        pass

def get_telegram_owner_id() -> Optional[int]:
    """Retrieves owner Telegram user ID from Credential Manager or env."""
    env_owner = os.environ.get("TELEGRAM_OWNER_ID")
    if env_owner:
        try:
            return int(env_owner)
        except ValueError:
            pass

    try:
        cred = win32cred.CredRead(CRED_TELEGRAM_OWNER_ID, win32cred.CRED_TYPE_GENERIC)
        blob = cred["CredentialBlob"]
        val_str = blob.decode("utf-16le") if isinstance(blob, bytes) else str(blob)
        return int(val_str.strip())
    except Exception:
        pass

    try:
        conn = encrypted_db.get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT value FROM settings WHERE key = 'telegram_owner_id';")
        row = cursor.fetchone()
        conn.close()
        if row and row[0]:
            return int(row[0])
    except Exception:
        pass

    return None

def set_telegram_owner_id(owner_id: int) -> None:
    """Stores the owner user ID in Windows Credential Manager."""
    val_str = str(owner_id)
    try:
        cred = {
            "Type": win32cred.CRED_TYPE_GENERIC,
            "TargetName": CRED_TELEGRAM_OWNER_ID,
            "CredentialBlob": val_str,
            "Persist": win32cred.CRED_PERSIST_LOCAL_MACHINE,
            "Comment": "Phenom Telegram Owner User ID"
        }
        win32cred.CredWrite(cred, 0)
    except Exception as e:
        print(f"[TelegramCredentials] Failed to write owner ID to Credential Manager: {e}")

    try:
        conn = encrypted_db.get_connection()
        with conn:
            conn.execute(
                "INSERT INTO settings (key, value) VALUES ('telegram_owner_id', ?) "
                "ON CONFLICT(key) DO UPDATE SET value = excluded.value;",
                (val_str,)
            )
        conn.close()
    except Exception:
        pass

def is_remote_locked() -> bool:
    """Checks if remote control has been locked via /lock."""
    try:
        conn = encrypted_db.get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT value FROM settings WHERE key = 'telegram_locked';")
        row = cursor.fetchone()
        conn.close()
        if row and row[0] == "1":
            return True
    except Exception:
        pass
    return False

def set_remote_locked(locked: bool) -> None:
    """Sets or clears the remote control lock state."""
    val = "1" if locked else "0"
    try:
        conn = encrypted_db.get_connection()
        with conn:
            conn.execute(
                "INSERT INTO settings (key, value) VALUES ('telegram_locked', ?) "
                "ON CONFLICT(key) DO UPDATE SET value = excluded.value;",
                (val,)
            )
        conn.close()
    except Exception as e:
        print(f"[TelegramCredentials] Failed to update remote lock state: {e}")
