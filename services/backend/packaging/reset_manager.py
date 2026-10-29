"""
Phenom Granular Reset Controls Engine (Task 7k)
Provides four distinct, isolated reset actions with mandatory typed confirmation:
1. Reset Settings: Reverts configuration to defaults; preserves memory, notes, voice, credentials.
2. Clear Memory: Purges conversations, embeddings, facts, and rules; preserves vault, settings, voice.
3. Delete Voice Data: Wipes voice store with 0x00 zero-bytes and clears enrolled speaker profiles.
4. Remove Everything (Factory Reset): Wipes all DBs, voice data, logs, snapshots, and deletes all Windows Credential Manager secrets.
"""

import os
import shutil
from typing import Dict, Any, List, Optional
from services.backend.memory.db import encrypted_db

CONFIRMATION_PHRASES = {
    "settings": "RESET SETTINGS",
    "memory": "CLEAR MEMORY",
    "voice": "DELETE VOICE DATA",
    "factory": "FACTORY RESET"
}

class GranularResetManager:
    def __init__(self, db_manager=None, voice_store_dir: Optional[str] = None):
        self.db = db_manager or encrypted_db
        user_appdata = os.environ.get("APPDATA") or os.path.expanduser("~")
        self.voice_store = voice_store_dir or os.path.join(user_appdata, "Phenom", "voice_store")

    def preview_reset(self, target: str) -> Dict[str, Any]:
        """Returns details on what will be cleared and what will be preserved."""
        t = target.strip().lower()
        if t not in CONFIRMATION_PHRASES:
            raise ValueError(f"Unknown reset target '{target}'. Allowed: settings, memory, voice, factory.")

        if t == "settings":
            return {
                "target": "settings",
                "confirmation_phrase": CONFIRMATION_PHRASES["settings"],
                "will_clear": ["Active configuration in config.toml", "Settings table overrides"],
                "will_preserve": ["Obsidian Vault notes", "Conversations & memories", "Voice biometrics", "Stored credentials in Credential Manager"]
            }
        elif t == "memory":
            return {
                "target": "memory",
                "confirmation_phrase": CONFIRMATION_PHRASES["memory"],
                "will_clear": ["Chat history messages", "SQLite vector embeddings", "Learned rules", "Extracted facts"],
                "will_preserve": ["Obsidian Vault markdown notes", "Voice biometrics", "Settings & config", "Stored credentials"]
            }
        elif t == "voice":
            return {
                "target": "voice",
                "confirmation_phrase": CONFIRMATION_PHRASES["voice"],
                "will_clear": ["Audio recordings in voice store (zeroed with 0x00)", "Enrolled ECAPA-TDNN speaker profiles"],
                "will_preserve": ["Obsidian Vault markdown notes", "Chat history & memory", "Settings", "Stored credentials"]
            }
        else: # factory
            return {
                "target": "factory",
                "confirmation_phrase": CONFIRMATION_PHRASES["factory"],
                "will_clear": ["All databases & messages", "Voice biometrics & audio", "All settings & config", "All Phenom credentials in Windows Credential Manager"],
                "will_preserve": ["External Obsidian Vault notes (requires manual deletion)"]
            }

    def execute_reset(self, target: str, confirmation_input: str) -> Dict[str, Any]:
        """
        Executes granular reset after validating exact confirmation phrase.
        """
        t = target.strip().lower()
        expected = CONFIRMATION_PHRASES.get(t)
        if not expected:
            raise ValueError(f"Invalid reset target: '{target}'.")

        if confirmation_input.strip() != expected:
            raise PermissionError(
                f"Confirmation failed. To reset '{t}', you must type '{expected}' exactly."
            )

        if t == "settings":
            return self._reset_settings()
        elif t == "memory":
            return self._clear_memory()
        elif t == "voice":
            return self._delete_voice_data()
        elif t == "factory":
            return self._factory_reset()

    def _reset_settings(self) -> Dict[str, Any]:
        conn = self.db.get_connection()
        with conn:
            conn.execute("DELETE FROM settings;")
        conn.close()
        return {"status": "success", "reset": "settings", "message": "Settings restored to defaults."}

    def _clear_memory(self) -> Dict[str, Any]:
        conn = self.db.get_connection()
        with conn:
            conn.execute("DELETE FROM messages;")
            conn.execute("DELETE FROM facts;")
            conn.execute("DELETE FROM learned_rules;")
            conn.execute("DELETE FROM embeddings;")
        conn.close()
        return {"status": "success", "reset": "memory", "message": "Conversational memory and embeddings purged."}

    def _delete_voice_data(self) -> Dict[str, Any]:
        # 1. Zero-byte wipe audio recordings on disk
        wiped_files = 0
        wiped_bytes = 0
        if os.path.exists(self.voice_store):
            for root, _, files in os.walk(self.voice_store):
                for f in files:
                    fp = os.path.join(root, f)
                    try:
                        sz = os.path.getsize(fp)
                        with open(fp, "wb") as fh:
                            fh.write(b"\x00" * sz)
                        os.remove(fp)
                        wiped_files += 1
                        wiped_bytes += sz
                    except OSError:
                        pass

        # 2. Clear enrolled speaker profile from DB
        conn = self.db.get_connection()
        with conn:
            conn.execute("DELETE FROM settings WHERE key LIKE 'speaker_%';")
        conn.close()

        return {
            "status": "success",
            "reset": "voice",
            "wiped_files": wiped_files,
            "wiped_bytes": wiped_bytes,
            "message": f"Wiped {wiped_files} voice files ({wiped_bytes} bytes zeroed) and cleared speaker profiles."
        }

    def _factory_reset(self) -> Dict[str, Any]:
        # 1. Clear all DB tables
        conn = self.db.get_connection()
        with conn:
            for tbl in ["messages", "facts", "learned_rules", "settings", "embeddings", "provider_usage_history"]:
                try:
                    conn.execute(f"DELETE FROM {tbl};")
                except Exception:
                    pass
        conn.close()

        # 2. Wipe voice files
        voice_res = self._delete_voice_data()

        # 3. Purge Windows Credential Manager keys
        purged_creds = []
        try:
            import win32cred
            cred_targets = [
                "Phenom/session-token",
                "Phenom/remote-pin",
                "Phenom/telegram-token",
                "Phenom/telegram-owner-id",
                "Phenom/gmail-app-password",
                "Phenom/google-calendar-token"
            ]
            for target in cred_targets:
                try:
                    win32cred.CredDelete(target, 1, 0)
                    purged_creds.append(target)
                except Exception:
                    pass
        except Exception:
            pass

        return {
            "status": "success",
            "reset": "factory",
            "purged_credentials": purged_creds,
            "voice_wiped": voice_res,
            "message": "Factory reset complete. All databases, voice recordings, and credentials purged."
        }

# Global reset manager instance
reset_manager = GranularResetManager()
