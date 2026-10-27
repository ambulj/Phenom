"""
Phenom Telegram Remote Controller (Phase 6)
Enforces:
1. Strict sender whitelisting: Owner user ID only. Non-whitelisted senders silently ignored & logged.
2. Remote commands run through orchestrator and Safety layer with source='telegram'.
3. Remote approvals for Tier 1 and Tier 2 actions with exact previews. Tier 3 cannot be approved remotely.
4. Remote kill switch (/halt, /kill) halts all running tasks immediately and confirms.
5. Status, tasks, and action log summaries with private content redacted.
6. /lock command disables remote control until physically re-enabled at the desktop.
"""

import asyncio
from typing import Dict, Any, List, Optional
from services.backend.remote.credentials import (
    get_telegram_token, get_telegram_owner_id, is_remote_locked, set_remote_locked
)
from services.backend.remote.telegram_client import TelegramClient
from services.backend.safety.guardian import guardian
from services.backend.safety.engine import safety_engine
from services.backend.safety.action_log import action_log
from services.backend.modes.mode_manager import mode_manager
from services.backend.scheduler.cron import background_scheduler

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
        self.ignored_messages_log: List[Dict[str, Any]] = []

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
        # Tier 3 Remote Prohibition
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

        # If remote is locked, deny
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
        Enforces owner whitelisting, command dispatch, and inline callbacks.
        """
        # Handle Callback Queries (Inline buttons for approvals)
        if "callback_query" in update:
            cb = update["callback_query"]
            sender_id = cb.get("from", {}).get("id")
            cb_id = cb.get("id")
            data = cb.get("data", "")
            msg = cb.get("message", {})
            chat_id = msg.get("chat", {}).get("id")
            msg_id = msg.get("message_id")

            # 1. Whitelist Check
            if sender_id != self._owner_id:
                self.ignored_messages_log.append({
                    "type": "callback_query",
                    "sender_id": sender_id,
                    "data": data,
                    "reason": "non_whitelisted_sender"
                })
                print(f"[SECURITY] Silently ignored Telegram callback query from unauthorized user {sender_id}")
                return None

            # 2. Check Remote Lock
            if is_remote_locked():
                if self.client:
                    await self.client.answer_callback_query(cb_id, text="Remote control is locked at the desktop.", show_alert=True)
                return {"status": "locked"}

            # Process Approval Decision
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

            return None

        # Handle Regular Messages
        message = update.get("message")
        if not message:
            return None

        sender = message.get("from", {})
        sender_id = sender.get("id")
        text = message.get("text", "").strip()
        chat_id = message.get("chat", {}).get("id")

        # 1. Whitelist Check: strictly ignore anyone who is not the owner
        if sender_id != self._owner_id:
            self.ignored_messages_log.append({
                "type": "message",
                "sender_id": sender_id,
                "text": text,
                "reason": "non_whitelisted_sender"
            })
            print(f"[SECURITY] Silently ignored Telegram message from unauthorized user {sender_id}")
            return None

        if not text:
            return None

        # 2. Command: /lock
        if text.startswith("/lock"):
            set_remote_locked(True)
            if self.client:
                await self.client.send_message(
                    chat_id,
                    "🔒 *Remote Control Locked.*\n"
                    "Telegram remote access has been disabled. "
                    "It can only be re-enabled from the physical Phenom desktop application."
                )
            return {"status": "locked_by_user"}

        # 3. If locked, reject all incoming commands
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

        # 4. Command: /halt or /kill (Remote Kill Switch)
        if text.startswith("/halt") or text.startswith("/kill") or text == "/stop":
            guardian.trigger("Telegram remote kill switch")
            if self.client:
                await self.client.send_message(
                    chat_id,
                    "🛑 *Guardian Kill Switch Activated.*\n"
                    "All Phenom actions, running model streams, and automation tasks have been immediately halted."
                )
            return {"status": "halted"}

        # 5. Command: /resume
        if text.startswith("/resume"):
            guardian.resume()
            if self.client:
                await self.client.send_message(
                    chat_id,
                    "▶️ *Guardian Kill Switch Resumed.*\n"
                    "Phenom is back online and ready for tasks."
                )
            return {"status": "resumed"}

        # 6. Command: /status
        if text.startswith("/status"):
            current_mode = mode_manager.get_current_mode().value
            next_item = background_scheduler.get_next_scheduled_item()
            next_text = f"{next_item['title']} at {next_item['next_run_at']}" if next_item else "None scheduled"
            status_text = (
                f"🤖 *Phenom Status Summary*\n"
                f"• *Guardian State:* `{'HALTED' if guardian.is_halted else 'IDLE / READY'}`\n"
                f"• *Active Mode:* `{current_mode.upper()}`\n"
                f"• *Remote Lock:* `{'LOCKED' if is_remote_locked() else 'ACTIVE'}`\n"
                f"• *Next Reminder:* {next_text}"
            )
            if self.client:
                await self.client.send_message(chat_id, status_text)
            return {"status": "status_sent"}

        # 7. Command: /tasks
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

        # 8. Command: /logs
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

        # 9. Regular Prompt: Execute through orchestrator
        return await self._handle_remote_chat(chat_id, text)

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
            except Exception as e:
                # Sleep briefly on connection error
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

# Global Telegram controller singleton
telegram_controller = TelegramBotController()
