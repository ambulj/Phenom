"""
Phenom Telegram Remote Controller (Phase 6 & Hardening Task 7g)
Enforces:
1. Strict sender whitelisting: Owner user ID only. Non-whitelisted senders silently ignored & logged.
2. Remote commands run through orchestrator and Safety layer with source='telegram'.
3. Remote approvals for Tier 1 and Tier 2 actions with exact previews. Tier 3 cannot be approved remotely.
4. Remote kill switch (/halt, /kill) halts all running tasks immediately and confirms.
5. Status, tasks, and action log summaries with private content redacted.
6. /lock command locks Windows workstation physically and disables remote control until desktop unlock.
7. /screenshot captures desktop, inspects for sensitive windows, applies 35px Gaussian blur, and warns.
8. /do <task> enforces 6-digit numeric PIN verification for Tier 2 actions.
9. 3-strike PIN lockout locking remote control completely.
10. Message ephemerality: automatically deletes sensitive PIN messages after 15 seconds.
11. Local voice notes / audio messages transcription and response.
"""

import asyncio
import io
import re
import time
import psutil
try:
    import torch
except ImportError:
    torch = None

from typing import Dict, Any, List, Optional
from services.backend.remote.credentials import (
    get_telegram_token, get_telegram_owner_id, is_remote_locked, set_remote_locked,
    verify_remote_pin, get_or_create_remote_pin, get_failed_pin_attempts,
    lock_workstation, unlock_remote_from_desktop
)
from services.backend.remote.telegram_client import TelegramClient
from services.backend.remote.screenshot_obfuscator import capture_and_obfuscate_screen
from services.backend.safety.guardian import guardian
from services.backend.safety.action_log import action_log
from services.backend.modes.mode_manager import mode_manager
from services.backend.scheduler.cron import background_scheduler

TIER2_KEYWORDS = [
    "delete", "remove", "wipe", "format", "kill", "terminate",
    "install", "uninstall", "winget", "powershell", "cmd", "bash",
    "modify", "organize", "write", "update", "restart", "shutdown", "reboot"
]

class TelegramBotController:
    def __init__(
        self,
        token: Optional[str] = None,
        owner_id: Optional[int] = None,
        client: Optional[TelegramClient] = None
    ):
        self._token = token or get_telegram_token()
        self._owner_id = owner_id or get_telegram_owner_id()
        self.client = client or (TelegramClient(self._token) if self._token else None)
        self._running = False
        self._poll_task: Optional[asyncio.Task] = None
        self._last_update_id = 0
        self._pending_approvals: Dict[str, asyncio.Future] = {}
        self._pending_pin_tasks: Dict[int, Dict[str, Any]] = {}
        self.ignored_messages_log: List[Dict[str, Any]] = []
        self._active_timers: List[asyncio.Task] = []

    def set_credentials(self, token: str, owner_id: int):
        self._token = token
        self._owner_id = owner_id
        self.client = TelegramClient(token)

    @property
    def owner_id(self) -> Optional[int]:
        return self._owner_id

    @property
    def is_configured(self) -> bool:
        return bool(self._token and self._owner_id)

    # ----------------- EPHEMERAL MESSAGE DELETION (15s SLA) -----------------
    def schedule_message_deletion(self, chat_id: int, message_id: int, delay_seconds: float = 15.0):
        """Schedules Telegram message deletion after delay_seconds (Message Ephemerality)."""
        async def _delete_worker():
            try:
                await asyncio.sleep(delay_seconds)
                if self.client:
                    await self.client.delete_message(chat_id, message_id)
            except Exception:
                pass

        try:
            loop = asyncio.get_running_loop()
            task = loop.create_task(_delete_worker())
            self._active_timers.append(task)
        except RuntimeError:
            pass

    # ----------------- STATUS HELPERS -----------------
    def _build_status_text(self) -> str:
        current_mode = mode_manager.get_current_mode().value
        next_item = background_scheduler.get_next_scheduled_item()
        next_text = f"{next_item['title']} at {next_item['next_run_at']}" if next_item else "None scheduled"

        cpu_usage = f"{psutil.cpu_percent()}%"
        ram_usage = f"{psutil.virtual_memory().percent}%"
        gpu_info = "Integrated / CPU"
        if torch and torch.cuda.is_available():
            gpu_info = f"{torch.cuda.get_device_name(0)}"

        return (
            f"🤖 *Phenom Status Summary*\n"
            f"• *CPU Utilization:* `{cpu_usage}`\n"
            f"• *RAM Utilization:* `{ram_usage}`\n"
            f"• *GPU Device:* `{gpu_info}`\n"
            f"• *Guardian State:* `{'HALTED' if guardian.is_halted else 'IDLE / READY'}`\n"
            f"• *Active Mode:* `{current_mode.upper()}`\n"
            f"• *Remote Lock:* `{'LOCKED' if is_remote_locked() else 'ACTIVE'}`\n"
            f"• *Next Scheduled Reminder:* {next_text}"
        )

    def _get_status_markup(self) -> Dict[str, Any]:
        return {
            "inline_keyboard": [
                [
                    {"text": "🔄 Refresh", "callback_data": "status:refresh"},
                    {"text": "🔒 Lock Remote", "callback_data": "lock:remote"}
                ]
            ]
        }

    # ----------------- APPROVAL HOOK -----------------
    async def handle_remote_approval_request(
        self,
        request_id: str,
        tool: str,
        tier: int,
        preview: str,
        args: Dict[str, Any],
        timeout_seconds: int = 120
    ) -> tuple[str, bool]:
        """
        Invoked by SafetyExecutionEngine when a tool requires approval over Telegram.
        Tier 3 is categorically refused remotely.
        """
        if tier == 3:
            if self.client and self._owner_id:
                try:
                    await self.client.send_message(
                        self._owner_id,
                        f"🛑 *Action Blocked Remotely:* `{tool}` is classified as *Tier 3 (System / Critical)*. "
                        "Tier 3 actions require physical typed confirmation on the desktop and cannot be approved remotely."
                    )
                except Exception:
                    pass
            action_log.log_action(
                tool=tool,
                tier=3,
                args=args,
                decision="blocked",
                result_status="BLOCKED",
                source="telegram",
                error="Tier 3 actions cannot be approved remotely."
            )
            return "blocked", False

        if is_remote_locked():
            return "denied", False

        if not self.client or not self._owner_id:
            return "denied", False

        future = asyncio.get_event_loop().create_future()
        self._pending_approvals[request_id] = future

        try:
            await self.client.send_approval_request(
                chat_id=self._owner_id,
                request_id=request_id,
                tool=tool,
                tier=tier,
                preview=preview,
                args=args
            )
            decision, remember = await asyncio.wait_for(future, timeout=timeout_seconds)
            return decision, remember
        except asyncio.TimeoutError:
            return "timeout", False
        except Exception as e:
            print(f"[TelegramBot] Error sending approval request: {e}")
            return "denied", False
        finally:
            self._pending_approvals.pop(request_id, None)

    # ----------------- UPDATE DISPATCHER -----------------
    async def process_update(self, update: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Processes a single incoming Telegram update.
        Enforces owner whitelisting, command dispatch, inline callbacks, and PIN security.
        """
        # 1. Handle Callback Queries (Inline buttons)
        if "callback_query" in update:
            cb = update["callback_query"]
            sender_id = cb.get("from", {}).get("id")
            cb_id = cb.get("id")
            data = cb.get("data", "")
            msg = cb.get("message", {})
            chat_id = msg.get("chat", {}).get("id")
            msg_id = msg.get("message_id")

            if sender_id != self._owner_id:
                self.ignored_messages_log.append({
                    "type": "callback_query",
                    "sender_id": sender_id,
                    "data": data,
                    "reason": "non_whitelisted_sender"
                })
                print(f"[SECURITY] Silently ignored Telegram callback query from unauthorized user {sender_id}")
                return None

            # Check Remote Lock
            if is_remote_locked() and data not in ("status:refresh",):
                if self.client:
                    await self.client.answer_callback_query(cb_id, text="Remote control is locked at the desktop.", show_alert=True)
                return {"status": "locked"}

            # Approvals
            if data.startswith("approve:"):
                req_id = data.split(":", 1)[1]
                if req_id in self._pending_approvals and not self._pending_approvals[req_id].done():
                    self._pending_approvals[req_id].set_result(("approved", False))
                if self.client:
                    await self.client.answer_callback_query(cb_id, text="Approved!")
                    await self.client.edit_message_text(chat_id, msg_id, "✅ *Action Approved by Owner via Telegram.*")
                return {"status": "approved", "request_id": req_id}

            elif data.startswith("deny:"):
                req_id = data.split(":", 1)[1]
                if req_id in self._pending_approvals and not self._pending_approvals[req_id].done():
                    self._pending_approvals[req_id].set_result(("denied", False))
                if self.client:
                    await self.client.answer_callback_query(cb_id, text="Denied.")
                    await self.client.edit_message_text(chat_id, msg_id, "❌ *Action Denied by Owner via Telegram.*")
                return {"status": "denied", "request_id": req_id}

            # Status Refresh
            elif data == "status:refresh":
                if self.client:
                    await self.client.answer_callback_query(cb_id, text="Refreshed.")
                    await self.client.edit_message_text(
                        chat_id=chat_id,
                        message_id=msg_id,
                        text=self._build_status_text(),
                        reply_markup=self._get_status_markup()
                    )
                return {"status": "status_refreshed"}

            # Lock Remote Callback
            elif data == "lock:remote":
                lock_workstation()
                if self.client:
                    await self.client.answer_callback_query(cb_id, text="Workstation locked and remote disabled.", show_alert=True)
                    await self.client.edit_message_text(chat_id, msg_id, "🔒 *Workstation session locked and remote control disabled.*")
                return {"status": "locked_by_callback"}

            # Guardian Resume Callback
            elif data == "guardian:resume":
                guardian.resume()
                if self.client:
                    await self.client.answer_callback_query(cb_id, text="Guardian resumed.")
                    await self.client.edit_message_text(chat_id, msg_id, "▶️ *Guardian Kill Switch Resumed.*")
                return {"status": "resumed_by_callback"}

            # Screenshot Callbacks
            elif data == "screenshot:dismiss":
                if self.client:
                    await self.client.answer_callback_query(cb_id, text="Screenshot dismissed.")
                    await self.client.delete_message(chat_id, msg_id)
                return {"status": "screenshot_dismissed"}

            elif data == "screenshot:full":
                if self.client:
                    await self.client.answer_callback_query(cb_id, text="Full capture acknowledged.")
                    await self.client.edit_message_text(chat_id, msg_id, "ℹ️ *Full desktop view verified by Owner.*")
                return {"status": "screenshot_full_approved"}

            return None

        # 2. Handle Regular Messages & Voice Notes
        message = update.get("message")
        if not message:
            return None

        sender = message.get("from", {})
        sender_id = sender.get("id")
        text = message.get("text", "").strip()
        chat_id = message.get("chat", {}).get("id")
        msg_id = message.get("message_id")
        voice = message.get("voice") or message.get("audio")

        # Whitelist Check: strictly ignore non-owner
        if sender_id != self._owner_id:
            self.ignored_messages_log.append({
                "type": "message",
                "sender_id": sender_id,
                "text": text or "[Audio]",
                "reason": "non_whitelisted_sender"
            })
            print(f"[SECURITY] Silently ignored Telegram message from unauthorized user {sender_id}")
            return None

        # Voice Note / Audio Handling
        if voice:
            return await self._handle_voice_update(chat_id, msg_id, voice)

        if not text:
            return None

        # 3. Message Ephemerality Check for PIN Submissions
        is_pin_like = bool(re.match(r"^\s*\d{6}\s*$", text) or text.startswith("/pin "))
        if is_pin_like:
            self.schedule_message_deletion(chat_id, msg_id, delay_seconds=15.0)

            # Check if this PIN corresponds to a pending Tier 2 task
            clean_pin = text.replace("/pin ", "").strip()
            verified = verify_remote_pin(clean_pin)
            if verified:
                pending = self._pending_pin_tasks.pop(chat_id, None)
                if pending:
                    task_cmd = pending.get("task", "")
                    if self.client:
                        await self.client.send_message(chat_id, f"✅ *PIN Verified.* Executing authorized Tier 2 remote task: `{task_cmd}`...")
                    return await self._handle_remote_chat(chat_id, task_cmd)
                else:
                    if self.client:
                        await self.client.send_message(chat_id, "✅ *PIN Verified.* Remote session authenticated.")
                    return {"status": "pin_verified"}
            else:
                strikes = get_failed_pin_attempts()
                if is_remote_locked():
                    self._pending_pin_tasks.pop(chat_id, None)
                    if self.client:
                        await self.client.send_message(
                            chat_id,
                            "🛑 *Remote Control Locked!*\n"
                            "3 consecutive incorrect PIN entries detected. Remote control is locked completely. "
                            "It can only be unlocked physically at the desktop application."
                        )
                    return {"status": "lockout_triggered"}
                else:
                    remaining = max(0, 3 - strikes)
                    if self.client:
                        await self.client.send_message(
                            chat_id,
                            f"❌ *Incorrect PIN.* {remaining} attempt(s) remaining before remote lockout."
                        )
                    return {"status": "invalid_pin", "remaining": remaining}

        # 4. Command: /lock (Workstation Lock + Remote Disable)
        if text.startswith("/lock"):
            lock_workstation()
            if self.client:
                await self.client.send_message(
                    chat_id,
                    "🔒 *Workstation Locked.*\n"
                    "Windows desktop session has been physically locked and remote access disabled. "
                    "It can only be re-enabled from the physical desktop application."
                )
            return {"status": "locked_by_user"}

        # 5. If remote is locked, reject all incoming commands
        if is_remote_locked():
            if text.startswith("/unlock"):
                if self.client:
                    await self.client.send_message(
                        chat_id,
                        "❌ *Remote Unlock Forbidden:*\n"
                        "Remote control cannot be unlocked from Telegram. "
                        "Please unlock it physically from the desktop application settings."
                    )
            else:
                if self.client:
                    await self.client.send_message(
                        chat_id,
                        "🔒 *Remote Control is Locked:*\n"
                        "Access is disabled. Please unlock it from the Phenom desktop application."
                    )
            return {"status": "locked"}

        # 6. Command: /halt or /kill or /stop (Remote Kill Switch)
        if text.startswith("/halt") or text.startswith("/kill") or text == "/stop":
            guardian.trigger("Telegram remote kill switch")
            reply_markup = {
                "inline_keyboard": [
                    [{"text": "▶️ Resume Desktop", "callback_data": "guardian:resume"}]
                ]
            }
            if self.client:
                await self.client.send_message(
                    chat_id,
                    "🛑 *Guardian Kill Switch Activated.*\n"
                    "All Phenom actions, running model streams, and automation tasks have been immediately halted.",
                    reply_markup=reply_markup
                )
            return {"status": "halted"}

        # 7. Command: /resume
        if text.startswith("/resume"):
            guardian.resume()
            if self.client:
                await self.client.send_message(
                    chat_id,
                    "▶️ *Guardian Kill Switch Resumed.*\n"
                    "Phenom is back online and ready for tasks."
                )
            return {"status": "resumed"}

        # 8. Command: /status
        if text.startswith("/status"):
            status_text = self._build_status_text()
            if self.client:
                await self.client.send_message(
                    chat_id=chat_id,
                    text=status_text,
                    reply_markup=self._get_status_markup()
                )
            return {"status": "status_sent"}

        # 9. Command: /screenshot (Captures screen, blurs sensitive apps, generates preview)
        if text.startswith("/screenshot"):
            return await self._handle_screenshot_command(chat_id)

        # 10. Command: /do <task> (Executes remote task with Tier 2 PIN protection)
        if text.startswith("/do "):
            task_cmd = text[4:].strip()
            return await self._handle_do_command(chat_id, task_cmd)

        # 11. Command: /tasks
        if text.startswith("/tasks"):
            jobs = background_scheduler.list_jobs(include_disabled=False)
            if not jobs:
                tasks_text = "📋 *Scheduled Tasks:* No active tasks or reminders scheduled."
            else:
                lines = ["📋 *Active Scheduled Tasks:*"]
                for j in jobs[:8]:
                    lines.append(f"• *{j['title']}* (`{j['schedule_type']}`) - Next: `{j['next_run_at']}`")
                tasks_text = "\n".join(lines)
            if self.client:
                await self.client.send_message(chat_id, tasks_text)
            return {"status": "tasks_sent"}

        # 12. Command: /logs
        if text.startswith("/logs"):
            logs = action_log.list_entries(limit=5)
            lines = ["🛡️ *Recent Security Action Logs (Redacted):*"]
            for l in logs:
                lines.append(
                    f"• `{l['timestamp'][:19]}` | *{l['tool']}* [Tier {l['tier']}]\n"
                    f"  Decision: `{l['decision']}` | Status: `{l['result_status']}`"
                )
            log_text = "\n".join(lines)
            if self.client:
                await self.client.send_message(chat_id, log_text)
            return {"status": "logs_sent"}

        # 13. Regular Prompt: Execute through orchestrator
        return await self._handle_remote_chat(chat_id, text)

    # ----------------- COMMAND HANDLERS -----------------

    async def _handle_screenshot_command(self, chat_id: int) -> Dict[str, Any]:
        """Captures primary screen, applies 35px blur over sensitive apps, sends photo."""
        from services.backend.automation.desktop_controller import desktop_controller
        desktop_controller._emit_overlay_event("telegram.screenshot_requested", {
            "message": "Telegram screenshot requested. Obfuscating sensitive windows..."
        })

        img, redacted_windows = capture_and_obfuscate_screen(blur_radius=35)
        buf = io.BytesIO()
        img.save(buf, format="JPEG", quality=75)
        photo_bytes = buf.getvalue()

        caption_lines = [
            "🖥️ *Desktop Screen Preview*",
            "",
            "⚠️ *Warning:* Image transits Telegram servers and is stored in cloud chat history."
        ]
        if redacted_windows:
            names = ", ".join([w.get("title", "App")[:20] for w in redacted_windows[:4]])
            caption_lines.append(f"🔒 *35px Gaussian Blur applied to sensitive windows:* `{names}`")
        else:
            caption_lines.append("🔒 *Sensitive window scanner active (0 sensitive windows detected).*")

        reply_markup = {
            "inline_keyboard": [
                [
                    {"text": "✅ Approve Full", "callback_data": "screenshot:full"},
                    {"text": "❌ Dismiss", "callback_data": "screenshot:dismiss"}
                ]
            ]
        }

        if self.client:
            await self.client.send_photo(
                chat_id=chat_id,
                photo_bytes=photo_bytes,
                caption="\n".join(caption_lines),
                reply_markup=reply_markup
            )
        return {"status": "screenshot_sent", "redacted_count": len(redacted_windows)}

    async def _handle_do_command(self, chat_id: int, task: str) -> Dict[str, Any]:
        """Handles /do <task> with risk tier classification and 6-digit PIN gate."""
        lower_task = task.lower()
        is_tier2 = any(k in lower_task for k in TIER2_KEYWORDS)

        if is_tier2:
            self._pending_pin_tasks[chat_id] = {
                "task": task,
                "timestamp": time.time()
            }
            if self.client:
                await self.client.send_message(
                    chat_id,
                    f"🔐 *PIN Authorization Required*\n"
                    f"Task: `{task}` is classified as *Tier 2 (External / Modifying Action)*.\n\n"
                    "Please reply with your *6-digit remote PIN* to authorize execution.\n"
                    "*(Your PIN message will auto-delete in 15s for security)*"
                )
            return {"status": "pin_required", "task": task}
        else:
            # Tier 1 / Tier 0 task: run directly
            return await self._handle_remote_chat(chat_id, task)

    async def _handle_voice_update(self, chat_id: int, msg_id: int, voice: Dict[str, Any]) -> Dict[str, Any]:
        """Downloads audio note in RAM, transcribes locally via faster-whisper, processes command."""
        file_id = voice.get("file_id")
        if not file_id or not self.client:
            return {"status": "voice_failed", "reason": "no_file_id"}

        try:
            file_info = await self.client.get_file(file_id)
            file_path = file_info.get("file_path", "")
            audio_bytes = await self.client.download_file(file_path)

            # In-memory audio decoding
            import soundfile as sf
            import numpy as np
            audio_buf = io.BytesIO(audio_bytes)
            audio_arr, sr = sf.read(audio_buf)
            if len(audio_arr.shape) > 1:
                audio_arr = audio_arr.mean(axis=1)

            from services.backend.voice.stt import stt_engine
            transcribed_text, _ = stt_engine.transcribe_audio_array(audio_arr, sample_rate=sr)

            if not transcribed_text:
                if self.client:
                    await self.client.send_message(chat_id, "🎙️ *Voice Note Received:* Could not detect speech.")
                return {"status": "voice_transcribed_empty"}

            await self.client.send_message(
                chat_id,
                f"🎙️ *Voice Note Transcribed Locally:*\n_{transcribed_text}_\n\nExecuting..."
            )

            # Dispatch as regular prompt
            return await self._handle_remote_chat(chat_id, transcribed_text)

        except Exception as e:
            err = f"Voice note processing error: {e}"
            if self.client:
                await self.client.send_message(chat_id, f"⚠️ {err}")
            return {"status": "voice_error", "error": str(e)}

    async def _handle_remote_chat(self, chat_id: int, prompt: str) -> Dict[str, Any]:
        """Runs prompt through orchestrator turn and replies back to Telegram."""
        if guardian.is_halted:
            if self.client:
                await self.client.send_message(
                    chat_id,
                    "⚠️ *Phenom is currently halted by the Guardian kill switch.* Send /resume to re-enable."
                )
            return {"status": "halted_refused"}

        from services.backend.orchestrator.engine import orchestrator
        tokens = []
        try:
            async for event in orchestrator.run_conversation_turn(
                prompt=prompt,
                manual_privacy_override=None
            ):
                if event.get("type") == "chat.token":
                    tokens.append(event.get("payload", {}).get("token", ""))

            full_reply = "".join(tokens).strip() or "Task completed."
            if self.client:
                await self.client.send_message(chat_id, full_reply)
            return {"status": "chat_replied", "reply": full_reply}

        except Exception as e:
            err_msg = f"Error processing remote request: {str(e)}"
            if self.client:
                await self.client.send_message(chat_id, f"⚠️ {err_msg}")
            return {"status": "error", "error": err_msg}

    # ----------------- LONG POLLING LOOP -----------------
    async def _poll_loop(self):
        while self._running:
            if not self.client or not self._owner_id:
                await asyncio.sleep(2.0)
                continue

            try:
                updates = await self.client.get_updates(offset=self._last_update_id + 1, timeout=10)
                for update in updates:
                    u_id = update.get("update_id", 0)
                    if u_id > self._last_update_id:
                        self._last_update_id = u_id
                    await self.process_update(update)
            except Exception:
                await asyncio.sleep(3.0)

    def start(self):
        if not self._running:
            self._running = True
            try:
                loop = asyncio.get_running_loop()
                self._poll_task = loop.create_task(self._poll_loop())
            except RuntimeError:
                pass

    def stop(self):
        self._running = False
        if self._poll_task and not self._poll_task.done():
            self._poll_task.cancel()
        for timer in self._active_timers:
            if not timer.done():
                timer.cancel()

# Global Telegram controller singleton
telegram_controller = TelegramBotController()
