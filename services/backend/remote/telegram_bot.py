"""
Phenom Telegram Remote Controller (Phase 6, Hardening Task 7g, and Phase 3 MOB-01/MOB-02)
Enforces:
1. Strict sender whitelisting: Owner user ID only. Non-whitelisted senders silently ignored & logged.
2. Inbound prompt injection defense: Taint tracking and sanitization on all messages.
3. Remote commands run through orchestrator and Safety layer with source='telegram'.
4. Dual-Presence 1-Click Action Approval Gateway: Desktop & Telegram approvals synchronized in real time.
5. Remote kill switch (/halt, /kill) halts all running tasks immediately (< 25ms SLA).
6. Operational queries: /status, /git, /agenda, /emails, /briefing, /diff, /tasks, /logs.
7. /lock command locks Windows workstation physically and disables remote control until desktop unlock.
8. /screenshot captures desktop, inspects for sensitive windows, applies 35px Gaussian blur, and warns.
9. /do <task> enforces 6-digit numeric PIN verification for Tier 2 actions.
10. 3-strike PIN lockout locking remote control completely.
11. Message ephemerality: automatically deletes sensitive PIN messages after 15 seconds.
12. Local voice notes / audio messages transcription and response.
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
from services.backend.safety.taint import taint_tracker
from services.backend.modes.mode_manager import mode_manager
from services.backend.scheduler.cron import background_scheduler
from services.backend.coding.workspace_sentinel import workspace_sentinel

TIER2_KEYWORDS = [
    "delete", "remove", "wipe", "format", "kill", "terminate",
    "install", "uninstall", "winget", "powershell", "cmd", "bash",
    "modify", "organize", "write", "update", "restart", "shutdown", "reboot"
]

PROHIBITED_PAYMENT_KEYWORDS = [
    "pay", "checkout", "buy_now", "place_order", "complete_purchase",
    "credit_card", "debit_card", "cvv", "otp", "upi_pin", "netbanking"
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
        self._pending_diffs: Dict[str, str] = {}
        self._pending_pin_tasks: Dict[int, Dict[str, Any]] = {}
        self.ignored_messages_log: List[Dict[str, Any]] = []
        self._active_timers: List[asyncio.Task] = []
        self._registered_actions: Dict[str, Dict[str, Any]] = {}
        self._is_polling = False
        self._last_poll_time = 0.0
        self._poll_error_count = 0

    @property
    def is_polling(self) -> bool:
        return self._running and self._is_polling

    @property
    def last_poll_time(self) -> float:
        return self._last_poll_time

    def register_custom_action(
        self,
        action_id: str,
        label: str,
        tool_name: str,
        args: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Registers a dynamic custom action button for the Telegram mobile companion."""
        action_data = {
            "action_id": action_id,
            "label": label,
            "tool_name": tool_name,
            "args": args or {},
            "registered_at": time.time()
        }
        self._registered_actions[action_id] = action_data
        return action_data

    def unregister_custom_action(self, action_id: str) -> bool:
        """Removes a registered custom action button."""
        return self._registered_actions.pop(action_id, None) is not None

    def get_registered_actions(self) -> List[Dict[str, Any]]:
        """Returns all currently registered custom actions."""
        return list(self._registered_actions.values())

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

    # ----------------- STATUS & OPERATIONAL HELPERS -----------------
    def _build_status_text(self) -> str:
        current_mode = mode_manager.get_current_mode().value
        next_item = background_scheduler.get_next_scheduled_item()
        next_text = f"{next_item['title']} at {next_item['next_run_at']}" if next_item else "None scheduled"

        cpu_usage = f"{psutil.cpu_percent()}%"
        ram_usage = f"{psutil.virtual_memory().percent}%"
        gpu_info = "Integrated / CPU"
        if torch and torch.cuda.is_available():
            gpu_info = f"{torch.cuda.get_device_name(0)}"

        # Query developer workspace state
        ws_state = workspace_sentinel.get_current_state()
        if not ws_state:
            try:
                ws_state = workspace_sentinel.inspect_workspace(r"C:\Phenom")
            except Exception:
                ws_state = None

        lines = [
            "🤖 *Phenom Operational Status*",
            f"• *CPU:* `{cpu_usage}` | *RAM:* `{ram_usage}`",
            f"• *GPU:* `{gpu_info}`",
            f"• *Guardian:* `{'HALTED' if guardian.is_halted else 'READY / ACTIVE'}`",
            f"• *Mode:* `{current_mode.upper()}`",
            f"• *Remote:* `{'LOCKED' if is_remote_locked() else 'ACTIVE'}`",
        ]

        if ws_state and ws_state.is_git:
            lines.extend([
                "",
                "💻 *Developer Workspace:*",
                f"• *IDE:* `{(ws_state.ide_name or 'VSCode').upper()}` | *Project:* `{ws_state.name}`",
                f"• *Branch:* `{ws_state.branch or 'HEAD'}` (`+{ws_state.lines_added}/-{ws_state.lines_deleted}`)",
                f"• *Uncommitted Files:* `{len(ws_state.modified_files)}`",
            ])
        else:
            lines.extend([
                "",
                "💻 *Developer Workspace:* `No active IDE session`"
            ])

        lines.extend([
            "",
            f"• *Next Reminder:* {next_text}"
        ])
        return "\n".join(lines)

    def _get_status_markup(self) -> Dict[str, Any]:
        return {
            "inline_keyboard": [
                [
                    {"text": "🔄 Refresh", "callback_data": "status:refresh"},
                    {"text": "🎛️ Controls", "callback_data": "cmd:controls"},
                    {"text": "🌿 Git", "callback_data": "cmd:git"},
                    {"text": "🔒 Lock Remote", "callback_data": "lock:remote"}
                ]
            ]
        }

    def _build_controls_markup(self) -> Dict[str, Any]:
        """Builds rich bidirectional control keyboard for media, windows, models, voice, and macros."""
        buttons = [
            # Row 1: Media Controls
            [
                {"text": "⏯️ Play/Pause", "callback_data": "cmd:media:toggle"},
                {"text": "⏭️ Next", "callback_data": "cmd:media:next"},
                {"text": "🔇 Mute", "callback_data": "cmd:media:mute"}
            ],
            # Row 2: Window Staging
            [
                {"text": "💻 Dev Mode (60/40)", "callback_data": "cmd:window:dev"},
                {"text": "☕ Chill Mode", "callback_data": "cmd:window:chill"},
                {"text": "📐 Restore Layout", "callback_data": "cmd:window:restore"}
            ],
            # Row 3: AI Model Routing
            [
                {"text": "🧠 Coder (14B)", "callback_data": "cmd:model:coder"},
                {"text": "⚡ Fast (4B)", "callback_data": "cmd:model:fast"},
                {"text": "🔄 Auto Router", "callback_data": "cmd:model:auto"}
            ],
            # Row 4: Voice Persona Style
            [
                {"text": "🎩 Witty Jarvis", "callback_data": "cmd:voice:jarvis"},
                {"text": "🤫 Whisper Mode", "callback_data": "cmd:voice:whisper"},
                {"text": "🧘 Calm Mode", "callback_data": "cmd:voice:calm"}
            ],
            # Row 5: Quick Utilities & Macros
            [
                {"text": "📸 Screen Snapshot", "callback_data": "cmd:snapshot"},
                {"text": "📜 List Macros", "callback_data": "cmd:macro:list"},
                {"text": "🛑 Halt (Kill)", "callback_data": "cmd:kill"}
            ]
        ]

        if self._registered_actions:
            action_row = []
            for action in list(self._registered_actions.values())[:4]:
                action_row.append({
                    "text": f"⚡ {action['label']}",
                    "callback_data": f"action:{action['action_id']}"
                })
            buttons.append(action_row)

        return {"inline_keyboard": buttons}

    def _build_git_text(self) -> str:
        """Returns dedicated developer git repository tracker report."""
        ws_state = workspace_sentinel.get_current_state()
        if not ws_state:
            try:
                ws_state = workspace_sentinel.inspect_workspace(r"C:\Phenom")
            except Exception:
                ws_state = None

        if not ws_state or not ws_state.is_git:
            return "📁 *Git Workspace Status:*\nNo active git repository detected in current workspace."

        lines = [
            f"🌿 *Git Workspace Tracker: {ws_state.name}*",
            f"• *Root:* `{ws_state.root_path}`",
            f"• *Branch:* `{ws_state.branch or 'detached'}`",
            f"• *Diff Lines:* `+{ws_state.lines_added} / -{ws_state.lines_deleted}`",
            f"• *Dirty:* `{'YES (uncommitted changes)' if ws_state.is_dirty else 'Clean working tree'}`",
            f"• *Untracked Files:* `{ws_state.untracked_count}`",
        ]

        if ws_state.modified_files:
            lines.append("\n*Modified Files:*")
            for f in ws_state.modified_files[:10]:
                status_icon = "📝" if f.status == "M" else ("✨" if f.status == "A" else "🗑️")
                lines.append(f"  {status_icon} `{f.path}` (+{f.lines_added}/-{f.lines_deleted})")
            if len(ws_state.modified_files) > 10:
                lines.append(f"  _...and {len(ws_state.modified_files) - 10} more files_")
        else:
            lines.append("\n✅ *Working tree clean, no uncommitted changes.*")

        return "\n".join(lines)

    async def _build_agenda_text(self) -> str:
        """Returns upcoming Google Calendar meetings for the next 24 hours."""
        from datetime import datetime, timedelta, timezone
        from services.backend.integrations.google_workspace import google_workspace

        if not google_workspace.is_calendar_configured():
            return "📅 *Upcoming Agenda:*\nGoogle Calendar is not configured or authenticated."

        now_utc = datetime.now(timezone.utc)
        max_utc = now_utc + timedelta(hours=24)
        try:
            events = await asyncio.to_thread(
                google_workspace.get_calendar_events,
                time_min=now_utc.isoformat(),
                time_max=max_utc.isoformat()
            )
        except Exception as e:
            return f"📅 *Upcoming Agenda:*\nError fetching calendar events: {e}"

        if not events:
            return "📅 *Upcoming Agenda:*\nNo meetings or events scheduled in the next 24 hours. Clear schedule!"

        lines = [f"📅 *Upcoming Agenda ({len(events)} events in next 24h):*"]
        for ev in events[:8]:
            summary = ev.get("summary") or "Untitled Meeting"
            start = ev.get("start", {}).get("dateTime") or ev.get("start", {}).get("date") or ""
            link = ev.get("hangoutLink") or ""
            attendees = ev.get("attendees", [])
            att_count = len(attendees)
            time_part = start[11:16] if "T" in start else start
            entry = f"• *{time_part}* — *{summary}*"
            if att_count > 0:
                entry += f" ({att_count} attendees)"
            if link:
                entry += f" [Join]({link})"
            lines.append(entry)

        return "\n".join(lines)

    async def _build_emails_text(self) -> str:
        """Returns unread priority emails from Gmail triage."""
        from services.backend.triage.gmail_triage import gmail_triage
        from services.backend.integrations.google_workspace import google_workspace

        if not google_workspace.is_gmail_configured():
            return "📬 *Email Triage:*\nGmail credentials not configured."

        try:
            items = await gmail_triage.triage_unread_emails(max_emails=5)
        except Exception as e:
            return f"📬 *Email Triage:*\nError triaging inbox: {e}"

        if not items:
            return "📬 *Email Triage:*\nInbox zero! No unread high-priority emails."

        lines = [f"📬 *Priority Email Triage ({len(items)} unread):*"]
        for it in items:
            prio_badge = "🚨 URGENT" if it.priority_score >= 3 else ("⚠️ PRIORITY" if it.priority_score == 2 else "ℹ️ NORMAL")
            lines.append(
                f"• [{prio_badge}] *From:* `{it.sender[:25]}`\n"
                f"  *Subject:* {it.subject[:45]}\n"
                f"  *Snippet:* _{it.snippet[:80]}..._\n"
                f"  *Draft:* `{'Saved in [Gmail]/Drafts' if it.draft_saved else 'None'}`"
            )
        return "\n".join(lines)

    async def _build_briefing_text(self) -> str:
        """Generates executive briefing on-demand."""
        from services.backend.triage.executive_briefing import ExecutiveBriefingSynthesizer
        synth = ExecutiveBriefingSynthesizer()
        try:
            briefing = await synth.generate_briefing(force_refresh=True)
            if briefing and briefing.markdown_content:
                content = briefing.markdown_content
                if len(content) > 3800:
                    content = content[:3800] + "\n\n... [Briefing truncated]"
                return f"📋 *Executive Briefing:*\n\n{content}"
            return "📋 *Executive Briefing:*\nCould not compile daily briefing."
        except Exception as e:
            return f"📋 *Executive Briefing:*\nError generating briefing: {e}"

    def _get_pending_diff_text(self, target_id: Optional[str] = None) -> str:
        """Returns unified diff for target or most recent pending request."""
        if target_id and target_id in self._pending_diffs:
            diff = self._pending_diffs[target_id]
            req_label = target_id[:8]
        elif self._pending_diffs:
            target_id, diff = list(self._pending_diffs.items())[-1]
            req_label = target_id[:8]
        else:
            return "🔍 *Diff Viewer:*\nNo pending diffs available."

        if len(diff) > 3500:
            diff = diff[:3500] + "\n\n... [diff truncated]"
        return f"🔍 *Unified Diff Preview (`{req_label}`):*\n```diff\n{diff}\n```"

    # ----------------- DUAL-PRESENCE APPROVAL GATEWAY -----------------
    async def notify_desktop_approval_request(
        self,
        request_id: str,
        tool: str,
        tier: int,
        preview: str,
        args: Dict[str, Any],
        diff: Optional[str] = None
    ) -> bool:
        """
        Pushes a pending desktop approval request to the Telegram owner with inline buttons.
        Enables 1-click approval from mobile (MOB-02).
        """
        if not self.client or not self._owner_id or is_remote_locked():
            return False

        if diff:
            self._pending_diffs[request_id] = diff

        try:
            await self.client.send_approval_request(
                chat_id=self._owner_id,
                request_id=request_id,
                tool=tool,
                tier=tier,
                preview=preview,
                args=args,
                has_diff=bool(diff)
            )
            return True
        except Exception as e:
            print(f"[TelegramBot] Failed to send desktop approval to Telegram: {e}")
            return False

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
        Invoked by SafetyExecutionEngine when a tool requires approval initiated over Telegram.
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

        diff_text = args.get("patch") or args.get("diff") or args.get("content") or ""
        if diff_text:
            self._pending_diffs[request_id] = diff_text

        try:
            await self.client.send_approval_request(
                chat_id=self._owner_id,
                request_id=request_id,
                tool=tool,
                tier=tier,
                preview=preview,
                args=args,
                has_diff=bool(diff_text)
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
            self._pending_diffs.pop(request_id, None)

    # ----------------- UPDATE DISPATCHER -----------------
    async def process_update(self, update: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Processes a single incoming Telegram update.
        Enforces owner whitelisting, taint inspection, command dispatch, inline callbacks, and PIN security.
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

            # Approvals (Dual-Presence: syncs with both bot approvals and desktop pending_confirmations)
            if data.startswith("approve:"):
                req_id = data.split(":", 1)[1]
                
                # Resolve bot internal pending approvals
                if req_id in self._pending_approvals and not self._pending_approvals[req_id].done():
                    self._pending_approvals[req_id].set_result(("approved", False))

                # Resolve desktop pending confirmations in main
                try:
                    from services.backend.main import pending_confirmations, broadcast_message
                    if req_id in pending_confirmations and not pending_confirmations[req_id].done():
                        pending_confirmations[req_id].set_result(("approved", False))
                        asyncio.create_task(broadcast_message({
                            "type": "confirm.resolved",
                            "payload": {
                                "request_id": req_id,
                                "decision": "approved",
                                "source": "telegram"
                            }
                        }))
                except Exception as e:
                    print(f"[TelegramBot] Error resolving desktop confirmation: {e}")

                self._pending_diffs.pop(req_id, None)

                if self.client:
                    await self.client.answer_callback_query(cb_id, text="Approved!")
                    await self.client.edit_message_text(chat_id, msg_id, "✅ *Action Approved by Owner via Telegram.*")
                return {"status": "approved", "request_id": req_id}

            elif data.startswith("deny:"):
                req_id = data.split(":", 1)[1]

                if req_id in self._pending_approvals and not self._pending_approvals[req_id].done():
                    self._pending_approvals[req_id].set_result(("denied", False))

                try:
                    from services.backend.main import pending_confirmations, broadcast_message
                    if req_id in pending_confirmations and not pending_confirmations[req_id].done():
                        pending_confirmations[req_id].set_result(("denied", False))
                        asyncio.create_task(broadcast_message({
                            "type": "confirm.resolved",
                            "payload": {
                                "request_id": req_id,
                                "decision": "denied",
                                "source": "telegram"
                            }
                        }))
                except Exception as e:
                    print(f"[TelegramBot] Error resolving desktop confirmation: {e}")

                self._pending_diffs.pop(req_id, None)

                if self.client:
                    await self.client.answer_callback_query(cb_id, text="Denied.")
                    await self.client.edit_message_text(chat_id, msg_id, "❌ *Action Denied by Owner via Telegram.*")
                return {"status": "denied", "request_id": req_id}

            elif data.startswith("diff:"):
                req_id = data.split(":", 1)[1]
                diff = self._pending_diffs.get(req_id, "No unified diff preview available for this request.")
                if len(diff) > 3500:
                    diff = diff[:3500] + "\n\n... [diff truncated]"
                diff_msg = f"🔍 *Unified Diff Preview (`{req_id[:8]}`):*\n```diff\n{diff}\n```"
                if self.client:
                    await self.client.answer_callback_query(cb_id, text="Diff retrieved.")
                    await self.client.send_message(chat_id, diff_msg)
                return {"status": "diff_viewed", "request_id": req_id}

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

            # Git Callback
            elif data == "cmd:git":
                if self.client:
                    await self.client.answer_callback_query(cb_id, text="Fetching Git status...")
                    await self.client.send_message(chat_id, self._build_git_text())
                return {"status": "git_sent_by_callback"}

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

            # Controls Menu Callback
            elif data == "cmd:controls":
                if self.client:
                    await self.client.answer_callback_query(cb_id, text="Opening Mobile Controls...")
                    await self.client.send_message(
                        chat_id=chat_id,
                        text="🎛️ *Phenom Mobile Executive Controls*\nTap any action below to control your desktop session:",
                        reply_markup=self._build_controls_markup()
                    )
                return {"status": "controls_sent"}

            # Snapshot Preview Callback
            elif data == "cmd:snapshot":
                if self.client:
                    await self.client.answer_callback_query(cb_id, text="Capturing privacy snapshot...")
                res_snap = await self._handle_screenshot_command(chat_id)
                return {"status": "snapshot_sent", "details": res_snap}

            # Remote Kill Switch Callback
            elif data == "cmd:kill":
                guardian.trigger("Telegram mobile button kill switch")
                reply_markup = {
                    "inline_keyboard": [
                        [{"text": "▶️ Resume Desktop", "callback_data": "guardian:resume"}]
                    ]
                }
                if self.client:
                    await self.client.answer_callback_query(cb_id, text="Guardian Halted!", show_alert=True)
                    await self.client.send_message(
                        chat_id,
                        "🛑 *Guardian Kill Switch Activated via Mobile Button.*\nAll Phenom operations halted immediately (< 25ms SLA).",
                        reply_markup=reply_markup
                    )
                return {"status": "halted_by_button"}

            # Media Controls
            elif data.startswith("cmd:media:"):
                action = data.split(":", 2)[2]
                from services.backend.tools.media_tools import _send_virtual_key, VK_MEDIA_PLAY_PAUSE, VK_MEDIA_NEXT_TRACK, VK_VOLUME_MUTE
                if action == "toggle":
                    _send_virtual_key(VK_MEDIA_PLAY_PAUSE)
                    feedback = "Toggled Media Play/Pause"
                elif action == "next":
                    _send_virtual_key(VK_MEDIA_NEXT_TRACK)
                    feedback = "Skipped to Next Track"
                elif action == "mute":
                    _send_virtual_key(VK_VOLUME_MUTE)
                    feedback = "Toggled System Volume Mute"
                else:
                    feedback = f"Unknown media command: {action}"

                if self.client:
                    await self.client.answer_callback_query(cb_id, text=feedback)
                return {"status": "media_executed", "action": action}

            # Window Staging
            elif data.startswith("cmd:window:"):
                mode = data.split(":", 2)[2]
                from services.backend.tools.window_tiler import apply_window_layout
                layout_map = {
                    "dev": "dev_mode",
                    "chill": "chill_mode",
                    "restore": "default"
                }
                layout_name = layout_map.get(mode, mode)
                await apply_window_layout(layout_name)
                feedback = f"Applied window layout '{layout_name}'"

                if self.client:
                    await self.client.answer_callback_query(cb_id, text=feedback)
                return {"status": "window_executed", "mode": mode}

            # Model Routing
            elif data.startswith("cmd:model:"):
                target_model = data.split(":", 2)[2]
                from services.backend.router.dynamic_model_router import dynamic_model_router
                if target_model == "auto":
                    dynamic_model_router.set_override(None)
                    feedback = "Model router set to Auto"
                else:
                    dynamic_model_router.set_override(target_model)
                    feedback = f"Model locked to {target_model.upper()}"

                if self.client:
                    await self.client.answer_callback_query(cb_id, text=feedback)
                return {"status": "model_routed", "target": target_model}

            # Voice Persona Style
            elif data.startswith("cmd:voice:"):
                style = data.split(":", 2)[2]
                from services.backend.voice.prosody_manager import prosody_manager
                prosody_manager.set_style(style)
                feedback = f"Voice persona set to {style.replace('_', ' ').title()}"

                if self.client:
                    await self.client.answer_callback_query(cb_id, text=feedback)
                return {"status": "voice_styled", "style": style}

            # Macro Controls
            elif data == "cmd:macro:list":
                from services.backend.tools.macro_recorder import macro_recorder
                macros = macro_recorder.list_macros()
                if not macros:
                    if self.client:
                        await self.client.answer_callback_query(cb_id, text="No macros recorded.")
                        await self.client.send_message(chat_id, "📜 *Saved Macros:*\nNo desktop macros currently saved.")
                    return {"status": "macros_empty"}

                macro_buttons = []
                for m in macros[:6]:
                    name = m.get("name", "macro")
                    macro_buttons.append([{"text": f"▶️ {name}", "callback_data": f"cmd:macro:run:{name}"}])

                if self.client:
                    await self.client.answer_callback_query(cb_id, text=f"Found {len(macros)} macros.")
                    await self.client.send_message(
                        chat_id,
                        "📜 *Select a Macro to Replay:*",
                        reply_markup={"inline_keyboard": macro_buttons}
                    )
                return {"status": "macro_list_sent", "count": len(macros)}

            elif data.startswith("cmd:macro:run:"):
                macro_name = data.split("cmd:macro:run:", 1)[1]
                from services.backend.tools.macro_recorder import macro_recorder
                if self.client:
                    await self.client.answer_callback_query(cb_id, text=f"Replaying macro '{macro_name}'...")
                res_macro = macro_recorder.replay_macro(macro_name)
                if self.client:
                    await self.client.send_message(chat_id, f"✅ *Macro Replayed:* `{macro_name}` ({res_macro.get('status', 'done')})")
                return {"status": "macro_replayed", "macro_name": macro_name}

            # Custom Registered Action Callback
            elif data.startswith("action:"):
                action_id = data.split("action:", 1)[1]
                action_spec = self._registered_actions.get(action_id)
                if not action_spec:
                    if self.client:
                        await self.client.answer_callback_query(cb_id, text=f"Action '{action_id}' not found.", show_alert=True)
                    return {"status": "action_not_found", "action_id": action_id}

                tool_name = action_spec.get("tool_name")
                args = action_spec.get("args", {})
                from services.backend.safety.registry import registry
                tool = registry.get(tool_name)
                if not tool:
                    if self.client:
                        await self.client.answer_callback_query(cb_id, text=f"Tool '{tool_name}' missing.", show_alert=True)
                    return {"status": "tool_missing", "tool_name": tool_name}

                if self.client:
                    await self.client.answer_callback_query(cb_id, text=f"Executing {action_spec.get('label')}...")

                try:
                    res_tool = tool.handler_fn(**args)
                    if asyncio.iscoroutine(res_tool):
                        res_tool = await res_tool
                    if self.client:
                        await self.client.send_message(chat_id, f"✅ *Action Executed:* `{action_spec.get('label')}`\nResult: `{res_tool}`")
                    return {"status": "action_executed", "action_id": action_id, "result": res_tool}
                except Exception as ex:
                    if self.client:
                        await self.client.send_message(chat_id, f"❌ *Action Failed:* `{action_spec.get('label')}`\nError: `{ex}`")
                    return {"status": "action_failed", "action_id": action_id, "error": str(ex)}

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

        # 1. IMMEDIATE GUARDIAN KILL SWITCH & RESUME (SAF-02.1 - SLA < 25ms)
        # Kill switch has absolute priority: executes synchronously before DB queries or taint inspection
        if text.startswith("/halt") or text.startswith("/kill") or text == "/stop":
            guardian.trigger("Telegram remote kill switch")
            reply_markup = {
                "inline_keyboard": [
                    [{"text": "▶️ Resume Desktop", "callback_data": "guardian:resume"}]
                ]
            }
            if self.client:
                try:
                    await self.client.send_message(
                        chat_id,
                        "🛑 *Guardian Kill Switch Activated.*\n"
                        "All Phenom actions, running model streams, and automation tasks have been immediately halted.",
                        reply_markup=reply_markup
                    )
                except Exception:
                    pass
            return {"status": "halted"}

        if text.startswith("/resume"):
            guardian.resume()
            if self.client:
                try:
                    await self.client.send_message(
                        chat_id,
                        "▶️ *Guardian Kill Switch Resumed.*\n"
                        "Phenom is back online and ready for tasks."
                    )
                except Exception:
                    pass
            return {"status": "resumed"}

        # INBOUND TAINT & PROMPT INJECTION DEFENSE (Rule 1, Rule 4)
        sanitized_text, has_injection, matches = taint_tracker.inspect_and_sanitize(text, source="telegram")
        if has_injection:
            action_log.log_action(
                tool="telegram_message",
                tier=3,
                args={"raw_text": text[:200]},
                decision="blocked",
                result_status="BLOCKED",
                source="telegram",
                error=f"Prompt injection detected: {matches}"
            )
            if self.client:
                await self.client.send_message(
                    chat_id,
                    "🛡️ *Security Alert: Untrusted Input Quarantined*\n"
                    f"Inbound message contained prompt injection signatures: `{', '.join(matches[:3])}`.\n"
                    "The payload was safely quarantined and blocked from execution."
                )
            return {"status": "quarantined_injection", "matches": matches}

        # 3. Message Ephemerality Check for PIN Submissions
        is_pin_like = bool(re.match(r"^\s*\d{6}\s*$", text) or text.startswith("/pin "))
        if is_pin_like:
            self.schedule_message_deletion(chat_id, msg_id, delay_seconds=15.0)

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

        # 6. Command: /status
        if text.startswith("/status"):
            status_text = self._build_status_text()
            if self.client:
                await self.client.send_message(
                    chat_id=chat_id,
                    text=status_text,
                    reply_markup=self._get_status_markup()
                )
            return {"status": "status_sent"}

        # 9. Command: /git (Developer Workspace Git Tracker)
        if text.startswith("/git"):
            git_text = self._build_git_text()
            if self.client:
                await self.client.send_message(chat_id=chat_id, text=git_text)
            return {"status": "git_status_sent"}

        # 10. Command: /agenda (Upcoming Calendar Meetings)
        if text.startswith("/agenda"):
            agenda_text = await self._build_agenda_text()
            if self.client:
                await self.client.send_message(chat_id=chat_id, text=agenda_text)
            return {"status": "agenda_sent"}

        # 11. Command: /emails (Gmail Triage)
        if text.startswith("/emails"):
            emails_text = await self._build_emails_text()
            if self.client:
                await self.client.send_message(chat_id=chat_id, text=emails_text)
            return {"status": "emails_sent"}

        # 12. Command: /briefing (Executive Morning/Evening Briefing)
        if text.startswith("/briefing"):
            briefing_text = await self._build_briefing_text()
            if self.client:
                await self.client.send_message(chat_id=chat_id, text=briefing_text)
            return {"status": "briefing_sent"}

        # 13. Command: /diff (View pending unified diff)
        if text.startswith("/diff"):
            parts = text.split(maxsplit=1)
            target_id = parts[1].strip() if len(parts) > 1 else None
            diff_text = self._get_pending_diff_text(target_id)
            if self.client:
                await self.client.send_message(chat_id=chat_id, text=diff_text)
            return {"status": "diff_sent"}

        # 14. Command: /screenshot or /snapshot (Captures screen, blurs sensitive apps, generates preview)
        if text.startswith("/screenshot") or text.startswith("/snapshot"):
            return await self._handle_screenshot_command(chat_id)

        # 14b. Command: /controls or /menu (Interactive Executive Control Hub)
        if text.startswith("/controls") or text.startswith("/menu"):
            if self.client:
                await self.client.send_message(
                    chat_id=chat_id,
                    text="🎛️ *Phenom Mobile Executive Controls*\nTap any action below to control your desktop session:",
                    reply_markup=self._build_controls_markup()
                )
            return {"status": "controls_sent"}

        # 15. Command: /do <task> (Executes remote task with Tier 2 PIN protection)
        if text.startswith("/do "):
            task_cmd = text[4:].strip()
            return await self._handle_do_command(chat_id, task_cmd)

        # 16. Command: /tasks
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

        # 17. Command: /logs
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

        # 18. Regular Prompt: Execute through orchestrator turn
        return await self._handle_remote_chat(chat_id, text)

    # ----------------- COMMAND HANDLERS -----------------
    async def _handle_screenshot_command(self, chat_id: int) -> Dict[str, Any]:
        """Captures primary screen, applies 35px blur over sensitive apps, sends photo."""
        from services.backend.automation.desktop_controller import desktop_controller
        from services.backend.vision.privacy_masker import PrivacyScanFailureError

        desktop_controller._emit_overlay_event("telegram.screenshot_requested", {
            "message": "Telegram screenshot requested. Obfuscating sensitive windows..."
        })

        try:
            img, redacted_windows = capture_and_obfuscate_screen(blur_radius=35)
        except (PrivacyScanFailureError, Exception) as e:
            await self.client.send_message(
                chat_id,
                f"❌ *Screenshot capture refused:* Privacy masking scan failed ({e}). Unmasked screen cannot be transmitted (Fail-Closed)."
            )
            return {"status": "error", "reason": str(e)}

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

        # Strict Rule 8 Payment Invariant
        if any(pk in lower_task for pk in PROHIBITED_PAYMENT_KEYWORDS):
            action_log.log_action(
                tool="telegram_do",
                tier=3,
                args={"task": task},
                decision="blocked",
                result_status="BLOCKED",
                source="telegram",
                error="Payment and checkout actions are strictly prohibited by SAFETY.md Rule #8."
            )
            if self.client:
                await self.client.send_message(
                    chat_id,
                    "🛑 *Action Prohibited by Safety Invariant (Rule 8):*\n"
                    f"Task `{task}` involves financial transactions or checkout completion. "
                    "Phenom is prohibited from executing purchases or entering payment details by construction."
                )
            return {"status": "payment_prohibited", "task": task}

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
            return await self._handle_remote_chat(chat_id, task)

    async def _handle_voice_update(self, chat_id: int, msg_id: int, voice: Dict[str, Any]) -> Dict[str, Any]:
        """Downloads audio note in RAM, transcribes locally via faster-whisper, processes command, and returns audio voice note + companion text."""
        file_id = voice.get("file_id")
        if not file_id or not self.client:
            return {"status": "voice_failed", "reason": "no_file_id"}

        try:
            file_info = await self.client.get_file(file_id)
            file_path = file_info.get("file_path", "")
            audio_bytes = await self.client.download_file(file_path)

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

            return await self._handle_remote_chat(chat_id, transcribed_text, is_voice=True)

        except Exception as e:
            err = f"Voice note processing error: {e}"
            if self.client:
                await self.client.send_message(chat_id, f"⚠️ {err}")
            return {"status": "voice_error", "error": str(e)}

    async def _handle_remote_chat(self, chat_id: int, prompt: str, is_voice: bool = False) -> Dict[str, Any]:
        """Runs prompt through orchestrator turn and replies back to Telegram (with synthesized voice note if is_voice is True)."""
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

            full_reply = "".join(tokens).strip() or "Sab set hai Bro! Task completed."
            
            # 1. Deliver text companion message
            if self.client:
                await self.client.send_message(chat_id, full_reply)

            # 2. If prompt arrived as a voice note, synthesize and deliver response voice note (TEL-03.4)
            voice_delivered = False
            if is_voice and self.client:
                try:
                    from services.backend.voice.madhur_tts import madhur_tts
                    voice_bytes = madhur_tts.synthesize(full_reply)
                    if voice_bytes:
                        await self.client.send_voice(chat_id, voice_bytes, caption="🎙️ Phenom Voice Response")
                        voice_delivered = True
                except Exception as e:
                    print(f"[Telegram] Failed to generate/send response voice note: {e}")

            return {
                "status": "chat_replied",
                "reply": full_reply,
                "is_voice": is_voice,
                "voice_delivered": voice_delivered
            }

        except Exception as e:
            err_msg = f"Error processing remote request: {str(e)}"
            if self.client:
                await self.client.send_message(chat_id, f"⚠️ {err_msg}")
            return {"status": "error", "error": err_msg}

    async def broadcast_remote_alert(self, title: str, message: str, urgency: str = "medium") -> bool:
        """Pushes ambient notifications and meeting alerts directly to the whitelisted owner."""
        if not self.client or not self._owner_id or is_remote_locked():
            return False
        icon = "🚨" if urgency == "critical" else ("⚠️" if urgency == "high" else "🔔")
        text = f"{icon} *{title}*\n{message}"
        try:
            await self.client.send_message(chat_id=self._owner_id, text=text)
            return True
        except Exception:
            return False

    # ----------------- LONG POLLING LOOP -----------------
    async def _poll_loop(self):
        self._is_polling = True
        backoff = 1.0
        while self._running:
            if not self.client or not self._owner_id:
                await asyncio.sleep(2.0)
                continue

            try:
                self._last_poll_time = time.time()
                updates = await self.client.get_updates(offset=self._last_update_id + 1, timeout=30)
                backoff = 1.0
                self._poll_error_count = 0
                if not updates:
                    await asyncio.sleep(0.05)
                for update in updates:
                    u_id = update.get("update_id", 0)
                    if u_id > self._last_update_id:
                        self._last_update_id = u_id
                    await self.process_update(update)
            except Exception as e:
                self._poll_error_count += 1
                await asyncio.sleep(backoff)
                backoff = min(backoff * 2.0, 30.0)
        self._is_polling = False

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
