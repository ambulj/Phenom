"""
Phenom Telegram Remote Credentials & Configuration (Phase 6 & Hardening Task 7g)
Stores and retrieves:
- Telegram bot token: 'Phenom/telegram-token'
- Telegram owner user ID: 'Phenom/telegram-owner-id'
- Remote 6-digit numeric PIN: 'Phenom/remote-pin'
Uses Windows Credential Manager with fallback to encrypted SQLCipher DB settings.
Enforces:
1. 6-digit PIN lifecycle (generation, retrieval, rotation status).
2. 3-strike PIN lockout locking remote access completely.
3. Workstation physical lock and physical desktop unlock.
"""

import os
import secrets
from datetime import datetime, timezone
try:
    import win32cred
except ImportError:
    win32cred = None
from typing import Optional, Tuple, Dict, Any
from services.backend.memory.db import encrypted_db
from services.backend.safety.action_log import action_log

CRED_TELEGRAM_TOKEN = "Phenom/telegram-token"
CRED_TELEGRAM_OWNER_ID = "Phenom/telegram-owner-id"
CRED_REMOTE_PIN = "Phenom/remote-pin"

# ----------------- TELEGRAM TOKEN & OWNER ID -----------------

def get_telegram_token() -> Optional[str]:
    """Retrieves the Telegram bot token from Credential Manager or env."""
    env_token = os.environ.get("TELEGRAM_BOT_TOKEN")
    if env_token:
        return env_token

    if win32cred is None:
        return _get_db_setting("telegram_token")

    try:
        cred = win32cred.CredRead(CRED_TELEGRAM_TOKEN, win32cred.CRED_TYPE_GENERIC)
        blob = cred["CredentialBlob"]
        if isinstance(blob, bytes):
            return blob.decode("utf-16le")
        return str(blob)
    except Exception:
        pass

    return _get_db_setting("telegram_token")

def set_telegram_token(token: str) -> None:
    """Stores the Telegram bot token in Windows Credential Manager."""
    clean_token = token.strip()
    try:
        if win32cred:
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

    _set_db_setting("telegram_token", clean_token)

def get_telegram_owner_id() -> Optional[int]:
    """Retrieves owner Telegram user ID from Credential Manager or env."""
    env_owner = os.environ.get("TELEGRAM_OWNER_ID")
    if env_owner:
        try:
            return int(env_owner)
        except ValueError:
            pass

    if win32cred:
        try:
            cred = win32cred.CredRead(CRED_TELEGRAM_OWNER_ID, win32cred.CRED_TYPE_GENERIC)
            blob = cred["CredentialBlob"]
            val_str = blob.decode("utf-16le") if isinstance(blob, bytes) else str(blob)
            return int(val_str.strip())
        except Exception:
            pass

    db_val = _get_db_setting("telegram_owner_id")
    if db_val:
        try:
            return int(db_val)
        except ValueError:
            pass

    return None

def set_telegram_owner_id(owner_id: int) -> None:
    """Stores the owner user ID in Windows Credential Manager."""
    val_str = str(owner_id)
    try:
        if win32cred:
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

    _set_db_setting("telegram_owner_id", val_str)

# ----------------- REMOTE LOCK STATE -----------------

def is_remote_locked() -> bool:
    """Checks if remote control has been locked via /lock or 3 failed PIN strikes."""
    val = _get_db_setting("telegram_locked")
    return val == "1"

def set_remote_locked(locked: bool) -> None:
    """Sets or clears the remote control lock state."""
    val = "1" if locked else "0"
    _set_db_setting("telegram_locked", val)

# ----------------- 6-DIGIT PIN SECURITY LIFECYCLE -----------------

def get_or_create_remote_pin() -> str:
    """
    Retrieves or generates the 6-digit numeric PIN for remote Tier 2 commands.
    Stored securely in Credential Manager with encrypted DB backup.
    """
    env_pin = os.environ.get("TELEGRAM_REMOTE_PIN")
    if env_pin and len(env_pin.strip()) == 6 and env_pin.strip().isdigit():
        return env_pin.strip()

    if win32cred:
        try:
            cred = win32cred.CredRead(CRED_REMOTE_PIN, win32cred.CRED_TYPE_GENERIC)
            blob = cred["CredentialBlob"]
            val_str = blob.decode("utf-16le") if isinstance(blob, bytes) else str(blob)
            val = val_str.strip()
            if len(val) == 6 and val.isdigit():
                return val
        except Exception:
            pass

    db_pin = _get_db_setting("telegram_remote_pin")
    if db_pin and len(db_pin.strip()) == 6 and db_pin.strip().isdigit():
        return db_pin.strip()

    # Generate new random 6-digit numeric PIN
    new_pin = f"{secrets.randbelow(1000000):06d}"
    set_remote_pin(new_pin)
    return new_pin

def set_remote_pin(pin: str) -> None:
    """Stores the 6-digit numeric PIN in Credential Manager and DB settings."""
    clean_pin = pin.strip()
    if len(clean_pin) != 6 or not clean_pin.isdigit():
        raise ValueError("Remote PIN must be exactly 6 numeric digits (000000-999999).")

    try:
        if win32cred:
            cred = {
                "Type": win32cred.CRED_TYPE_GENERIC,
                "TargetName": CRED_REMOTE_PIN,
                "CredentialBlob": clean_pin,
                "Persist": win32cred.CRED_PERSIST_LOCAL_MACHINE,
                "Comment": "Phenom Telegram Remote 6-Digit PIN"
            }
            win32cred.CredWrite(cred, 0)
    except Exception as e:
        print(f"[TelegramCredentials] Failed to write PIN to Credential Manager: {e}")

    now_iso = datetime.now(timezone.utc).isoformat()
    _set_db_setting("telegram_remote_pin", clean_pin)
    _set_db_setting("telegram_pin_created_at", now_iso)
    reset_failed_pin_attempts()

def rotate_remote_pin() -> str:
    """Generates and sets a new 6-digit PIN, resetting failed attempts."""
    new_pin = f"{secrets.randbelow(1000000):06d}"
    set_remote_pin(new_pin)
    return new_pin

def check_pin_rotation_status(max_age_days: int = 30) -> Dict[str, Any]:
    """Checks the age of the active PIN against the 30-day rotation policy."""
    created_at_str = _get_db_setting("telegram_pin_created_at")
    if not created_at_str:
        return {
            "configured": True,
            "created_at": None,
            "age_days": 0.0,
            "needs_rotation": False
        }

    try:
        created_at = datetime.fromisoformat(created_at_str)
        now = datetime.now(timezone.utc)
        age_days = (now - created_at).total_seconds() / 86400.0
        return {
            "configured": True,
            "created_at": created_at_str,
            "age_days": round(age_days, 1),
            "needs_rotation": age_days >= max_age_days
        }
    except Exception:
        return {
            "configured": True,
            "created_at": created_at_str,
            "age_days": 0.0,
            "needs_rotation": False
        }

def get_failed_pin_attempts() -> int:
    """Returns the current consecutive failed PIN attempt counter."""
    val = _get_db_setting("telegram_failed_pin_attempts")
    if val:
        try:
            return int(val)
        except ValueError:
            pass
    return 0

def increment_failed_pin_attempts() -> int:
    """Increments the failed PIN attempt counter and returns the new value."""
    current = get_failed_pin_attempts()
    new_val = current + 1
    _set_db_setting("telegram_failed_pin_attempts", str(new_val))
    return new_val

def reset_failed_pin_attempts() -> None:
    """Resets failed PIN attempt counter to zero."""
    _set_db_setting("telegram_failed_pin_attempts", "0")

def verify_remote_pin(entered_pin: str) -> bool:
    """
    Verifies 6-digit PIN for remote Tier 2 actions.
    If 3 consecutive failures occur, remote control is locked immediately.
    """
    if is_remote_locked():
        return False

    stored = get_or_create_remote_pin()
    clean_entered = str(entered_pin).strip()

    if clean_entered == stored:
        reset_failed_pin_attempts()
        return True
    else:
        strikes = increment_failed_pin_attempts()
        if strikes >= 3:
            set_remote_locked(True)
            action_log.log_action(
                tool="remote_pin_verification",
                tier=2,
                args={"attempts": strikes},
                decision="locked",
                result_status="LOCKOUT",
                source="telegram",
                error="3 consecutive incorrect PIN entries. Remote control locked."
            )
        return False

def unlock_remote_from_desktop() -> None:
    """
    Physically unlocks remote control from the local desktop application.
    Resets failed attempts and re-enables Telegram remote controller.
    """
    reset_failed_pin_attempts()
    set_remote_locked(False)
    action_log.log_action(
        tool="desktop_unlock",
        tier=1,
        args={},
        decision="unlocked",
        result_status="SUCCESS",
        source="desktop"
    )

def lock_workstation(dry_run: bool = False) -> bool:
    """
    Immediately locks the Windows desktop session physically via LockWorkStation
    and sets remote lock state.
    """
    set_remote_locked(True)
    if not dry_run:
        try:
            import ctypes
            if hasattr(ctypes, "windll") and hasattr(ctypes.windll, "user32"):
                ctypes.windll.user32.LockWorkStation()
        except Exception as e:
            print(f"[WorkstationLock] Failed to call LockWorkStation: {e}")

    action_log.log_action(
        tool="lock_workstation",
        tier=1,
        args={"dry_run": dry_run},
        decision="locked",
        result_status="SUCCESS",
        source="telegram"
    )
    return True

# ----------------- DB HELPERS -----------------

def _get_db_setting(key: str) -> Optional[str]:
    try:
        conn = encrypted_db.get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT value FROM settings WHERE key = ?;", (key,))
        row = cursor.fetchone()
        conn.close()
        if row:
            return row[0]
    except Exception:
        pass
    return None

def _set_db_setting(key: str, value: str) -> None:
    try:
        conn = encrypted_db.get_connection()
        with conn:
            conn.execute(
                "INSERT INTO settings (key, value) VALUES (?, ?) "
                "ON CONFLICT(key) DO UPDATE SET value = excluded.value;",
                (key, value)
            )
        conn.close()
    except Exception as e:
        print(f"[TelegramCredentials] Failed to update setting '{key}': {e}")
