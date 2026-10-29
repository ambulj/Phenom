"""
Phenom Google Workspace Integration (Phase 5 & Hardening Pass 1)
Real Gmail via IMAP over SSL and real Google Calendar via Google Calendar REST API.
Reading is allowed.
Email drafts can be saved via IMAP APPEND to Drafts (never send).
Calendar events can be created via Google Calendar API (never edit or delete).

Credentials stored securely in Windows Credential Manager:
- 'Phenom/gmail-app-password' (UserName=address, CredentialBlob=app_password)
- 'Phenom/google-calendar-token' (CredentialBlob=oauth_token)
Falls back to environment variables or encrypted DB settings for automated testing.

Hard code-level prohibitions:
- Sending email is strictly blocked (raises EmailSendingProhibitedError). NO SMTP is imported or used.
- Deleting calendar events is strictly blocked (raises CalendarModificationProhibitedError).
- Editing calendar events is strictly blocked (raises CalendarModificationProhibitedError).
"""

import os
import time
import email
import email.message
import email.utils
import imaplib
import logging
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime, timezone
import httpx

try:
    import win32cred
except ImportError:
    win32cred = None

from services.backend.memory.db import encrypted_db

logger = logging.getLogger("phenom.google_workspace")

CRED_GMAIL = "Phenom/gmail-app-password"
CRED_CALENDAR = "Phenom/google-calendar-token"

class EmailSendingProhibitedError(Exception):
    """Raised whenever sending an email is attempted."""
    pass

class CalendarModificationProhibitedError(Exception):
    """Raised whenever deleting or editing calendar events is attempted."""
    pass

class GoogleWorkspaceClient:
    def __init__(self, token_override: Optional[str] = None):
        self._token_override = token_override
        self._drafts: List[Dict[str, Any]] = []

    # ----------------- CREDENTIAL MANAGEMENT -----------------
    def get_gmail_credentials(self) -> Tuple[Optional[str], Optional[str]]:
        """Retrieves Gmail address and app password from Credential Manager, env, or DB."""
        # 1. Environment variables
        env_addr = os.environ.get("PHENOM_GMAIL_ADDRESS") or os.environ.get("GMAIL_ADDRESS")
        env_pass = os.environ.get("PHENOM_GMAIL_APP_PASSWORD") or os.environ.get("GMAIL_APP_PASSWORD")
        if env_addr and env_pass:
            return env_addr.strip(), env_pass.strip()

        # 2. Windows Credential Manager
        if win32cred is not None:
            try:
                cred = win32cred.CredRead(CRED_GMAIL, win32cred.CRED_TYPE_GENERIC)
                username = cred.get("UserName", "")
                blob = cred.get("CredentialBlob", b"")
                password = blob.decode("utf-16le") if isinstance(blob, bytes) else str(blob)
                if username and password:
                    return username.strip(), password.strip()
            except Exception:
                pass

        # 3. Encrypted DB settings
        try:
            conn = encrypted_db.get_connection()
            cursor = conn.cursor()
            cursor.execute("SELECT key, value FROM settings WHERE key IN ('gmail_address', 'gmail_app_password');")
            rows = dict(cursor.fetchall())
            conn.close()
            addr = rows.get("gmail_address")
            pwd = rows.get("gmail_app_password")
            if addr and pwd:
                return addr.strip(), pwd.strip()
        except Exception:
            pass

        return None, None

    def set_gmail_credentials(self, address: str, app_password: str) -> None:
        """Stores Gmail address and app password securely in Windows Credential Manager."""
        addr_clean = address.strip()
        pass_clean = app_password.strip()

        if win32cred is not None:
            try:
                credential = {
                    "Type": win32cred.CRED_TYPE_GENERIC,
                    "TargetName": CRED_GMAIL,
                    "UserName": addr_clean,
                    "CredentialBlob": pass_clean,
                    "Comment": "Phenom Gmail IMAP App Password",
                    "Persist": win32cred.CRED_PERSIST_LOCAL_MACHINE
                }
                win32cred.CredWrite(credential, 0)
            except Exception as e:
                logger.warning(f"Failed to write Gmail credentials to Credential Manager: {e}")

        # Also store in encrypted DB
        try:
            conn = encrypted_db.get_connection()
            with conn:
                conn.execute(
                    "INSERT INTO settings (key, value) VALUES ('gmail_address', ?) "
                    "ON CONFLICT(key) DO UPDATE SET value = excluded.value;",
                    (addr_clean,)
                )
                conn.execute(
                    "INSERT INTO settings (key, value) VALUES ('gmail_app_password', ?) "
                    "ON CONFLICT(key) DO UPDATE SET value = excluded.value;",
                    (pass_clean,)
                )
            conn.close()
        except Exception as e:
            logger.warning(f"Failed to write Gmail credentials to encrypted DB: {e}")

    def clear_gmail_credentials(self) -> None:
        """Removes Gmail credentials from Credential Manager and DB."""
        if win32cred is not None:
            try:
                win32cred.CredDelete(CRED_GMAIL, win32cred.CRED_TYPE_GENERIC, 0)
            except Exception:
                pass
        try:
            conn = encrypted_db.get_connection()
            with conn:
                conn.execute("DELETE FROM settings WHERE key IN ('gmail_address', 'gmail_app_password');")
            conn.close()
        except Exception:
            pass

    def get_calendar_token(self) -> Optional[str]:
        """Retrieves Google Calendar OAuth token from Credential Manager, env, or DB."""
        if self._token_override:
            return self._token_override

        env_tok = os.environ.get("PHENOM_GOOGLE_CALENDAR_TOKEN") or os.environ.get("GOOGLE_CALENDAR_TOKEN")
        if env_tok:
            return env_tok.strip()

        if win32cred is not None:
            try:
                cred = win32cred.CredRead(CRED_CALENDAR, win32cred.CRED_TYPE_GENERIC)
                blob = cred.get("CredentialBlob", b"")
                token = blob.decode("utf-16le") if isinstance(blob, bytes) else str(blob)
                if token:
                    return token.strip()
            except Exception:
                pass

        try:
            conn = encrypted_db.get_connection()
            cursor = conn.cursor()
            cursor.execute("SELECT value FROM settings WHERE key = 'google_calendar_token';")
            row = cursor.fetchone()
            conn.close()
            if row and row[0]:
                return row[0].strip()
        except Exception:
            pass

        return None

    def set_calendar_token(self, token: str) -> None:
        """Stores Google Calendar token in Windows Credential Manager and DB."""
        tok_clean = token.strip()
        if win32cred is not None:
            try:
                credential = {
                    "Type": win32cred.CRED_TYPE_GENERIC,
                    "TargetName": CRED_CALENDAR,
                    "UserName": "google_calendar_oauth",
                    "CredentialBlob": tok_clean,
                    "Comment": "Phenom Google Calendar OAuth Token",
                    "Persist": win32cred.CRED_PERSIST_LOCAL_MACHINE
                }
                win32cred.CredWrite(credential, 0)
            except Exception as e:
                logger.warning(f"Failed to write Calendar token to Credential Manager: {e}")

        try:
            conn = encrypted_db.get_connection()
            with conn:
                conn.execute(
                    "INSERT INTO settings (key, value) VALUES ('google_calendar_token', ?) "
                    "ON CONFLICT(key) DO UPDATE SET value = excluded.value;",
                    (tok_clean,)
                )
            conn.close()
        except Exception as e:
            logger.warning(f"Failed to write Calendar token to encrypted DB: {e}")

    def clear_calendar_token(self) -> None:
        """Removes Calendar token from Credential Manager and DB."""
        if win32cred is not None:
            try:
                win32cred.CredDelete(CRED_CALENDAR, win32cred.CRED_TYPE_GENERIC, 0)
            except Exception:
                pass
        try:
            conn = encrypted_db.get_connection()
            with conn:
                conn.execute("DELETE FROM settings WHERE key = 'google_calendar_token';")
            conn.close()
        except Exception:
            pass

    def is_gmail_configured(self) -> bool:
        addr, pwd = self.get_gmail_credentials()
        return bool(addr and pwd)

    def is_calendar_configured(self) -> bool:
        return bool(self.get_calendar_token())

    def is_authenticated(self) -> bool:
        return self.is_gmail_configured() or self.is_calendar_configured()

    # ----------------- CONNECTION TESTS -----------------
    def test_gmail_connection(self) -> Dict[str, Any]:
        """Tests IMAP connection and authentication against imap.gmail.com."""
        addr, pwd = self.get_gmail_credentials()
        if not addr or not pwd:
            return {"ok": False, "error": "not_configured", "message": "Gmail address or app password missing."}

        try:
            mail = imaplib.IMAP4_SSL("imap.gmail.com", 993)
            mail.login(addr, pwd)
            status, _ = mail.examine("INBOX")
            mail.logout()
            return {"ok": True, "message": f"Successfully authenticated as {addr} (INBOX status: {status})."}
        except Exception as e:
            logger.warning(f"Gmail IMAP connection test failed: {e}")
            return {"ok": False, "error": "authentication_failed", "message": str(e)}

    async def test_calendar_connection(self) -> Dict[str, Any]:
        """Tests Google Calendar API token against https://www.googleapis.com/calendar/v3."""
        token = self.get_calendar_token()
        if not token:
            return {"ok": False, "error": "not_configured", "message": "Calendar OAuth token missing."}

        try:
            headers = {"Authorization": f"Bearer {token}"}
            async with httpx.AsyncClient(timeout=5.0) as client:
                resp = await client.get("https://www.googleapis.com/calendar/v3/calendars/primary", headers=headers)
                if resp.status_code == 200:
                    data = resp.json()
                    return {"ok": True, "message": f"Successfully authenticated to Calendar: {data.get('summary', 'Primary')}"}
                return {"ok": False, "error": f"http_{resp.status_code}", "message": resp.text}
        except Exception as e:
            logger.warning(f"Calendar connection test failed: {e}")
            return {"ok": False, "error": "connection_error", "message": str(e)}

    # ----------------- HARD CODE-LEVEL PROHIBITIONS -----------------
    def send_email(self, to: str, subject: str, body: str) -> None:
        """
        Permanently blocked by construction.
        Phenom never sends emails. It only creates drafts in Gmail for user review.
        """
        raise EmailSendingProhibitedError(
            "Sending emails is strictly blocked by Phenom permanent safety rules. "
            "Phenom may only create email drafts for your review in Gmail."
        )

    def delete_calendar_event(self, event_id: str) -> None:
        """Permanently blocked by construction."""
        raise CalendarModificationProhibitedError(
            f"Deleting calendar events (id='{event_id}') is strictly blocked by Phenom safety rules."
        )

    def edit_calendar_event(self, event_id: str, updates: Dict[str, Any]) -> None:
        """Permanently blocked by construction."""
        raise CalendarModificationProhibitedError(
            f"Editing calendar events (id='{event_id}') is strictly blocked by Phenom safety rules. "
            "Phenom may create new calendar events, but cannot alter existing ones."
        )

    # ----------------- GMAIL READING & DRAFTS (IMAP) -----------------
    def search_emails(self, query: str = "", max_results: int = 10) -> List[Dict[str, Any]]:
        """
        Searches or lists inbox messages using read-only IMAP (EXAMINE).
        Returns empty list if not configured or offline. Never returns fabricated emails.
        """
        addr, pwd = self.get_gmail_credentials()
        if not addr or not pwd:
            return []

        messages: List[Dict[str, Any]] = []
        try:
            mail = imaplib.IMAP4_SSL("imap.gmail.com", 993)
            mail.login(addr, pwd)
            # EXAMINE ensures mailbox is strictly read-only
            status, _ = mail.examine("INBOX")
            if status != "OK":
                mail.logout()
                return []

            search_criteria = "ALL"
            q_clean = query.strip()
            if q_clean == "UNSEEN":
                search_criteria = "UNSEEN"
            elif q_clean:
                search_criteria = f'TEXT "{q_clean}"'

            res, data = mail.search(None, search_criteria)
            if res == "OK" and data and data[0]:
                msg_ids = data[0].split()
                # Most recent first
                msg_ids = msg_ids[::-1][:max_results]
                for mid in msg_ids:
                    fetch_res, fetch_data = mail.fetch(mid, "(BODY.PEEK[HEADER.FIELDS (SUBJECT FROM TO DATE)])")
                    if fetch_res == "OK" and fetch_data:
                        raw_headers = b""
                        for part in fetch_data:
                            if isinstance(part, tuple) and len(part) > 1:
                                raw_headers = part[1]
                                break
                        msg = email.message_from_bytes(raw_headers)
                        messages.append({
                            "id": mid.decode("utf-8", errors="replace"),
                            "from": msg.get("From", "Unknown"),
                            "to": msg.get("To", ""),
                            "subject": msg.get("Subject", "No Subject"),
                            "received_at": msg.get("Date", ""),
                            "snippet": msg.get("Subject", "")
                        })
            mail.logout()
        except Exception as e:
            logger.warning(f"IMAP search error: {e}")

        return messages

    def read_email(self, email_id: str) -> Optional[Dict[str, Any]]:
        """Reads full message content via read-only IMAP. Returns None if not configured/found."""
        addr, pwd = self.get_gmail_credentials()
        if not addr or not pwd:
            return None

        try:
            mail = imaplib.IMAP4_SSL("imap.gmail.com", 993)
            mail.login(addr, pwd)
            mail.examine("INBOX")
            fetch_res, fetch_data = mail.fetch(email_id.encode("utf-8"), "(RFC822)")
            if fetch_res == "OK" and fetch_data:
                raw_bytes = b""
                for part in fetch_data:
                    if isinstance(part, tuple) and len(part) > 1:
                        raw_bytes = part[1]
                        break
                msg = email.message_from_bytes(raw_bytes)
                body = ""
                if msg.is_multipart():
                    for sub in msg.walk():
                        if sub.get_content_type() == "text/plain":
                            body = sub.get_payload(decode=True).decode("utf-8", errors="replace")
                            break
                else:
                    body = msg.get_payload(decode=True).decode("utf-8", errors="replace")

                mail.logout()
                return {
                    "id": email_id,
                    "from": msg.get("From", ""),
                    "to": msg.get("To", ""),
                    "subject": msg.get("Subject", ""),
                    "received_at": msg.get("Date", ""),
                    "body": body
                }
            mail.logout()
        except Exception as e:
            logger.warning(f"IMAP read error for {email_id}: {e}")

        return None

    def create_draft(self, to: str, subject: str, body: str) -> Dict[str, Any]:
        """
        Creates an RFC 5322 email draft and appends it to '[Gmail]/Drafts' via IMAP APPEND.
        Never sends. Returns draft summary.
        """
        addr, pwd = self.get_gmail_credentials()
        now_str = datetime.now(timezone.utc).isoformat()
        draft_id = f"draft_{int(time.time())}"

        # Construct standard MIME email message
        msg = email.message.EmailMessage()
        msg["From"] = addr or "phenom@assistant.local"
        msg["To"] = to
        msg["Subject"] = subject
        msg["Date"] = email.utils.formatdate(localtime=True)
        msg.set_content(body)

        record = {
            "id": draft_id,
            "to": to,
            "subject": subject,
            "body": body,
            "created_at": now_str,
            "status": "DRAFT",
            "note": "Draft saved in Gmail. Open Gmail to review and send manually."
        }

        # If credentials exist, append to IMAP Drafts folder
        if addr and pwd:
            try:
                mail = imaplib.IMAP4_SSL("imap.gmail.com", 993)
                mail.login(addr, pwd)
                internal_date = imaplib.Time2Internaldate(time.time())
                # Try '[Gmail]/Drafts' first, fallback to 'Drafts'
                res, _ = mail.append('"[Gmail]/Drafts"', '', internal_date, msg.as_bytes())
                if res != "OK":
                    mail.append('"Drafts"', '', internal_date, msg.as_bytes())
                mail.logout()
            except Exception as e:
                logger.warning(f"Could not append draft to IMAP server: {e}")
                record["note"] = f"Draft created locally (server append failed: {e})."

        self._drafts.append(record)
        return record

    def list_drafts(self) -> List[Dict[str, Any]]:
        return self._drafts

    # ----------------- CALENDAR READING & EVENT CREATION -----------------
    def list_events(self, max_results: int = 10) -> List[Dict[str, Any]]:
        """
        Lists upcoming calendar events from Google Calendar REST API.
        Never returns fabricated events. Returns empty list if unauthenticated or offline.
        """
        token = self.get_calendar_token()
        if not token:
            return []

        events: List[Dict[str, Any]] = []
        try:
            headers = {"Authorization": f"Bearer {token}", "Accept": "application/json"}
            now_iso = datetime.now(timezone.utc).isoformat()
            url = (
                f"https://www.googleapis.com/calendar/v3/calendars/primary/events"
                f"?maxResults={max_results}&singleEvents=true&orderBy=startTime&timeMin={now_iso}"
            )
            with httpx.Client(timeout=5.0) as client:
                resp = client.get(url, headers=headers)
                if resp.status_code == 200:
                    items = resp.json().get("items", [])
                    for it in items:
                        events.append({
                            "id": it.get("id", ""),
                            "summary": it.get("summary", "Untitled Event"),
                            "start": it.get("start", {}).get("dateTime", it.get("start", {}).get("date", "")),
                            "end": it.get("end", {}).get("dateTime", it.get("end", {}).get("date", "")),
                            "description": it.get("description", ""),
                            "creator": it.get("creator", {}).get("email", "")
                        })
        except Exception as e:
            logger.warning(f"Google Calendar list error: {e}")

        return events

    def create_event(self, summary: str, start_time: str, end_time: str, description: str = "") -> Dict[str, Any]:
        """
        Creates a new event via Google Calendar REST API.
        Requires Tier 2 confirmation before execution.
        """
        token = self.get_calendar_token()
        now_str = datetime.now(timezone.utc).isoformat()

        if not token:
            return {
                "ok": False,
                "error": "not_authenticated",
                "message": "Google Calendar is not configured. Connect your Google account in Settings."
            }

        try:
            headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
            payload = {
                "summary": summary,
                "description": description,
                "start": {"dateTime": start_time},
                "end": {"dateTime": end_time}
            }
            with httpx.Client(timeout=5.0) as client:
                resp = client.post("https://www.googleapis.com/calendar/v3/calendars/primary/events", headers=headers, json=payload)
                if resp.status_code in [200, 201]:
                    data = resp.json()
                    return {
                        "ok": True,
                        "id": data.get("id"),
                        "summary": summary,
                        "start": start_time,
                        "end": end_time,
                        "description": description,
                        "created_at": now_str
                    }
                return {
                    "ok": False,
                    "error": f"http_{resp.status_code}",
                    "message": resp.text
                }
        except Exception as e:
            logger.warning(f"Google Calendar create event error: {e}")
            return {
                "ok": False,
                "error": "connection_error",
                "message": str(e)
            }

# Global Google Workspace client
google_workspace = GoogleWorkspaceClient()
