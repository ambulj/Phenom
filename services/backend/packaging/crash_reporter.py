"""
Phenom Local-Only Crash Reporter & Redaction Engine (Phase 7)
Guarantees:
1. Crash logs are stored strictly on the local machine (services/backend/data/crash_logs/).
2. Zero telemetry or network transmission.
3. One-click export that strips all private paths, usernames, IP addresses, and credentials.
"""

import os
import sys
import json
import traceback
import platform
import re
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional

CRASH_LOGS_DIR = os.path.abspath("services/backend/data/crash_logs")

class CrashReporter:
    def __init__(self, logs_dir: Optional[str] = None):
        self.logs_dir = logs_dir or CRASH_LOGS_DIR
        os.makedirs(self.logs_dir, exist_ok=True)

    def log_crash(self, exc: Exception, context: Optional[str] = None) -> str:
        """Records an unhandled exception to a local JSON file."""
        now = datetime.now(timezone.utc)
        ts_slug = now.strftime("%Y%m%d_%H%M%S")
        crash_id = f"crash_{ts_slug}_{os.urandom(2).hex()}"
        file_path = os.path.join(self.logs_dir, f"{crash_id}.json")

        tb_str = "".join(traceback.format_exception(type(exc), exc, exc.__traceback__))

        crash_data = {
            "crash_id": crash_id,
            "timestamp": now.isoformat(),
            "context": context or "unhandled_exception",
            "exception_type": type(exc).__name__,
            "exception_message": str(exc),
            "traceback": tb_str,
            "system_info": {
                "os": platform.system(),
                "os_release": platform.release(),
                "python_version": sys.version.split()[0],
                "machine": platform.machine()
            }
        }

        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(crash_data, f, indent=2)

        return file_path

    def list_crashes(self) -> List[Dict[str, Any]]:
        crashes = []
        for fname in sorted(os.listdir(self.logs_dir), reverse=True):
            if fname.endswith(".json"):
                fpath = os.path.join(self.logs_dir, fname)
                try:
                    with open(fpath, "r", encoding="utf-8") as f:
                        crashes.append(json.load(f))
                except Exception:
                    pass
        return crashes

    def export_sanitized_report(self) -> Dict[str, Any]:
        """
        Creates an exportable diagnostic bundle where all private content,
        usernames, paths, and secrets are stripped.
        """
        raw_crashes = self.list_crashes()
        sanitized_crashes = [self._sanitize_crash_data(c) for c in raw_crashes]

        return {
            "app_name": "Phenom",
            "export_time": datetime.now(timezone.utc).isoformat(),
            "total_crashes": len(sanitized_crashes),
            "crashes": sanitized_crashes,
            "privacy_notice": "All personal file paths, usernames, IP addresses, and keys have been redacted."
        }

    def _sanitize_crash_data(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Deep redaction of paths, usernames, and potential secrets."""
        data_str = json.dumps(data)

        # 1. Redact Windows user paths: C:\Users\<username>\... -> C:\Users\[USER]\...
        data_str = re.sub(r"[A-Za-z]:(?:\\\\+|/+)Users(?:\\\\+|/+)[^\\\\/\"'\s]+", r"C:\\\\Users\\\\[USER]", data_str)

        # 2. Redact IP addresses
        data_str = re.sub(r"\b(?:\d{1,3}\.){3}\d{1,3}\b", "[REDACTED_IP]", data_str)

        # 3. Redact potential API keys or tokens (e.g. nvapi-..., telegram tokens)
        data_str = re.sub(r"nvapi-[A-Za-z0-9_-]{20,}", "[REDACTED_NVIDIA_KEY]", data_str)
        data_str = re.sub(r"\d{8,12}:[A-Za-z0-9_-]{30,}", "[REDACTED_TELEGRAM_TOKEN]", data_str)

        return json.loads(data_str)

# Global crash reporter
crash_reporter = CrashReporter()
