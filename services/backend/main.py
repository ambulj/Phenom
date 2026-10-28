"""
Phenom Backend FastAPI Application
Serves the typed WebSocket endpoint on /ws and REST utility endpoints.
Connects the desktop Electron app to the orchestrator, safety layer, router, and memory.
"""

import asyncio
import json
import os
from contextlib import asynccontextmanager
from typing import Dict, Any, Optional
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from services.backend.schemas.protocol import (
    OrbState, RiskTier, DecisionType,
    ConfirmRequestMsg, ConfirmRequestPayload,
    StateChangeMsg, StateChangePayload,
    LogEntryMsg, LogEntryPayload,
    RulesUpdatedMsg, RulesUpdatedPayload,
    LearnedRuleItem
)
from services.backend.safety.guardian import guardian
from services.backend.safety.engine import safety_engine
from services.backend.safety.action_log import action_log
from services.backend.safety.approvals import approvals
from services.backend.memory.rules import learned_rules
from services.backend.memory.db import encrypted_db
from services.backend.orchestrator.engine import orchestrator, warm_up_ollama
from services.backend.voice.tts import tts_engine
from services.backend.voice.wake_word import wake_detector
from services.backend.voice.hotkeys import hotkey_manager
from services.backend.voice.voice_coordinator import voice_coordinator
import services.backend.tools.file_tools
import services.backend.tools.app_tools
import services.backend.tools.automation_tools
import services.backend.tools.memory_tools
import services.backend.tools.integration_tools
from services.backend.modes.mode_manager import mode_manager
from services.backend.scheduler.cron import background_scheduler
from services.backend.integrations.finance import financial_engine
from services.backend.integrations.google_workspace import google_workspace
from services.backend.browser.browser_controller import browser_controller
from services.backend.automation.human_takeover import takeover_manager
from services.backend.remote.telegram_bot import telegram_controller
from services.backend.remote.credentials import (
    is_remote_locked, set_remote_locked, set_telegram_token, set_telegram_owner_id, get_telegram_owner_id
)

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Setup global hotkey in background
    guardian.setup_global_hotkey("ctrl+alt+pause")
    
    # Setup amplitude callback for TTS speech animation
    def on_tts_amplitude(amp: float):
        asyncio.create_task(broadcast_message({
            "id": f"tts-amp-{os.urandom(2).hex()}",
            "type": "voice.amplitude",
            "ts": "",
            "payload": {"amplitude": amp}
        }))
    tts_engine.set_amplitude_callback(on_tts_amplitude)

    # Setup wake word callback
    def on_wake_word_detected():
        asyncio.create_task(broadcast_message({
            "id": f"wake-{os.urandom(2).hex()}",
            "type": "state.change",
            "ts": "",
            "payload": {"state": "listening", "detail": "Wake word triggered"}
        }))
    wake_detector.set_wake_callback(on_wake_word_detected)
    wake_detector.start()

    # Setup browser live view streaming callback
    def on_browser_frame(b64: str):
        asyncio.create_task(broadcast_message({
            "id": f"frame-{os.urandom(2).hex()}",
            "type": "browser.frame",
            "ts": "",
            "payload": {"image_data": b64}
        }))
    browser_controller.set_frame_callback(on_browser_frame)

    # Setup human takeover callback
    def on_takeover():
        asyncio.create_task(broadcast_message({
            "id": f"takeover-{os.urandom(2).hex()}",
            "type": "automation.takeover_prompt",
            "ts": "",
            "payload": {"reason": "User input detected. Automation paused for safety."}
        }))
    takeover_manager.set_takeover_callback(on_takeover)

    # Setup background scheduler reminders callback
    def on_scheduler_reminder(evt: Dict[str, Any]):
        asyncio.create_task(broadcast_message({
            "id": f"rem-{os.urandom(2).hex()}",
            "type": "scheduler.reminder",
            "ts": "",
            "payload": evt
        }))
    background_scheduler.add_listener(on_scheduler_reminder)
    background_scheduler.start()
    telegram_controller.start()
    asyncio.create_task(warm_up_ollama())

    yield
    telegram_controller.stop()
    background_scheduler.stop()
    wake_detector.stop()
    await browser_controller.close()

app = FastAPI(title="Phenom Backend", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

active_websockets: set[WebSocket] = set()
pending_confirmations: Dict[str, asyncio.Future] = {}

async def broadcast_message(msg_dict: Dict[str, Any]):
    for ws in list(active_websockets):
        try:
            await ws.send_text(json.dumps(msg_dict))
        except Exception:
            pass

def on_guardian_state_change(new_state: str):
    # Broadcast to all connected clients
    asyncio.create_task(broadcast_message({
        "id": f"guardian-{os.urandom(4).hex()}",
        "type": "state.change",
        "ts": "",
        "payload": {"state": new_state, "detail": "Triggered by Guardian override"}
    }))

guardian.add_state_callback(on_guardian_state_change)

async def websocket_confirmation_handler(
    request_id: str,
    tool: str,
    tier: RiskTier,
    preview: str,
    args: Dict[str, Any],
    can_remember: bool,
    folder_path: Optional[str],
    timeout_seconds: int
) -> tuple[str, bool]:
    """Safety engine hook to solicit user approval via WebSocket."""
    future = asyncio.get_event_loop().create_future()
    pending_confirmations[request_id] = future

    req_msg = {
        "id": request_id,
        "type": "confirm.request",
        "ts": "",
        "payload": {
            "request_id": request_id,
            "tool": tool,
            "tier": tier,
            "preview": preview,
            "args": args,
            "can_remember": can_remember,
            "folder_path": folder_path,
            "timeout_seconds": timeout_seconds
        }
    }
    await broadcast_message(req_msg)

    try:
        decision, remember_choice = await asyncio.wait_for(future, timeout=timeout_seconds)
        return decision, remember_choice
    finally:
        pending_confirmations.pop(request_id, None)

safety_engine.set_confirmation_handler(websocket_confirmation_handler)

async def remote_confirmation_handler(
    request_id: str,
    tool: str,
    tier: RiskTier,
    preview: str,
    args: Dict[str, Any],
    can_remember: bool,
    folder_path: Optional[str],
    timeout_seconds: int
) -> tuple[str, bool]:
    return await telegram_controller.handle_remote_approval_request(
        request_id=request_id,
        tool=tool,
        tier=tier,
        preview=preview,
        args=args,
        timeout_seconds=timeout_seconds
    )

safety_engine.set_remote_confirmation_handler(remote_confirmation_handler)

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    active_websockets.add(websocket)
    session_cancel_event = asyncio.Event()
    active_task: Optional[asyncio.Task] = None

    try:
        # Send initial state and rules
        initial_rules = [
            LearnedRuleItem(id=r["id"], rule_text=r["rule_text"], created_at=r["created_at"], enabled=r["enabled"])
            for r in learned_rules.list_rules()
        ]
        await websocket.send_json({
            "id": "init-rules",
            "type": "rules.updated",
            "ts": "",
            "payload": {"rules": [r.model_dump() for r in initial_rules]}
        })

        await websocket.send_json({
            "id": "init-state",
            "type": "state.change",
            "ts": "",
            "payload": {"state": "halted" if guardian.is_halted else "idle"}
        })

        # Send initial mode
        await websocket.send_json({
            "id": "init-mode",
            "type": "mode.changed",
            "ts": "",
            "payload": mode_manager.get_mode_profile()
        })

        # Send initial scheduler jobs
        await websocket.send_json({
            "id": "init-scheduler",
            "type": "scheduler.list_result",
            "ts": "",
            "payload": {"jobs": background_scheduler.list_jobs()}
        })

        # Send initial financial watchlist
        await websocket.send_json({
            "id": "init-watchlist",
            "type": "watchlist.list_result",
            "ts": "",
            "payload": {"items": financial_engine.list_watchlist()}
        })

        while True:
            text = await websocket.receive_text()
            try:
                msg = json.loads(text)
            except json.JSONDecodeError:
                continue

            mtype = msg.get("type")
            msg_id = msg.get("id", "msg")
            payload = msg.get("payload", {})

            if mtype == "chat.send":
                session_cancel_event.clear()
                prompt = payload.get("prompt", "")
                context_files = payload.get("context_files", [])
                privacy_override = payload.get("privacy_override")

                async def stream_turn():
                    async for event in orchestrator.run_conversation_turn(
                        prompt=prompt,
                        context_files=context_files,
                        manual_privacy_override=privacy_override,
                        cancel_event=session_cancel_event
                    ):
                        event["id"] = msg_id
                        event["ts"] = ""
                        await websocket.send_text(json.dumps(event))

                if active_task and not active_task.done():
                    active_task.cancel()
                active_task = asyncio.create_task(stream_turn())
                guardian.track_task(active_task)

            elif mtype == "chat.cancel":
                session_cancel_event.set()
                if active_task and not active_task.done():
                    active_task.cancel()
                await websocket.send_json({
                    "id": msg_id,
                    "type": "chat.cancelled",
                    "ts": "",
                    "payload": {}
                })
                await websocket.send_json({
                    "id": msg_id,
                    "type": "state.change",
                    "ts": "",
                    "payload": {"state": "idle"}
                })

            elif mtype == "confirm.reply":
                req_id = payload.get("request_id")
                decision = payload.get("decision", "denied")
                remember = payload.get("remember_choice", False)
                if req_id in pending_confirmations and not pending_confirmations[req_id].done():
                    pending_confirmations[req_id].set_result((decision, remember))

            elif mtype == "killswitch.trigger":
                guardian.trigger("UI button trigger")

            elif mtype == "killswitch.resume":
                guardian.resume()

            elif mtype == "voice.toggle":
                enabled = payload.get("enabled", True)
                wake_detector.set_enabled(enabled)
                await broadcast_message({
                    "id": "voice-status",
                    "type": "voice.status",
                    "ts": "",
                    "payload": {"enabled": wake_detector.is_enabled, "muted": wake_detector.is_muted}
                })

            elif mtype == "voice.mute":
                muted = payload.get("muted", True)
                wake_detector.set_muted(muted)
                await broadcast_message({
                    "id": "voice-status",
                    "type": "voice.status",
                    "ts": "",
                    "payload": {"enabled": wake_detector.is_enabled, "muted": wake_detector.is_muted}
                })

            elif mtype == "hotkeys.update":
                action = payload.get("action")
                key_combo = payload.get("key_combo")
                if action and key_combo:
                    success, err = hotkey_manager.update_hotkey(action, key_combo)
                    await websocket.send_json({
                        "id": msg_id,
                        "type": "hotkeys.result",
                        "ts": "",
                        "payload": {"success": success, "error": err, "hotkeys": hotkey_manager.get_hotkeys()}
                    })

            elif mtype == "settings.update":
                settings_dict = payload.get("settings", {})
                if "wake_phrase" in settings_dict:
                    wake_detector.set_wake_phrase(settings_dict["wake_phrase"])

            elif mtype == "automation.takeover_reply":
                decision = payload.get("decision", "stop")
                try:
                    takeover_manager.resolve_takeover(decision)
                except Exception as e:
                    pass

            elif mtype == "rules.delete":
                rule_id = payload.get("rule_id")
                if rule_id:
                    learned_rules.delete_rule(rule_id)
                    all_rules = [
                        LearnedRuleItem(id=r["id"], rule_text=r["rule_text"], created_at=r["created_at"], enabled=r["enabled"])
                        for r in learned_rules.list_rules()
                    ]
                    await broadcast_message({
                        "id": "rules-updated",
                        "type": "rules.updated",
                        "ts": "",
                        "payload": {"rules": [r.model_dump() for r in all_rules]}
                    })

            elif mtype == "rules.edit":
                rule_id = payload.get("rule_id")
                new_text = payload.get("rule_text")
                if rule_id and new_text:
                    learned_rules.edit_rule(rule_id, new_text)
                    all_rules = [
                        LearnedRuleItem(id=r["id"], rule_text=r["rule_text"], created_at=r["created_at"], enabled=r["enabled"])
                        for r in learned_rules.list_rules()
                    ]
                    await broadcast_message({
                        "id": "rules-updated",
                        "type": "rules.updated",
                        "ts": "",
                        "payload": {"rules": [r.model_dump() for r in all_rules]}
                    })

            elif mtype == "mode.set":
                target_mode = payload.get("mode", "work")
                profile = mode_manager.set_mode(target_mode)
                await broadcast_message({
                    "id": msg_id,
                    "type": "mode.changed",
                    "ts": "",
                    "payload": profile
                })

            elif mtype == "mode.cycle":
                profile = mode_manager.cycle_mode()
                await broadcast_message({
                    "id": msg_id,
                    "type": "mode.changed",
                    "ts": "",
                    "payload": profile
                })

            elif mtype == "scheduler.list":
                jobs = background_scheduler.list_jobs()
                await websocket.send_json({
                    "id": msg_id,
                    "type": "scheduler.list_result",
                    "ts": "",
                    "payload": {"jobs": jobs}
                })

            elif mtype == "scheduler.add_reminder":
                title = payload.get("title", "Reminder")
                delay = payload.get("delay_seconds")
                due_at = payload.get("due_at")
                res = background_scheduler.add_reminder(title, delay_seconds=delay, due_at=due_at)
                jobs = background_scheduler.list_jobs()
                await broadcast_message({
                    "id": msg_id,
                    "type": "scheduler.list_result",
                    "ts": "",
                    "payload": {"jobs": jobs, "new_job": res}
                })

            elif mtype == "scheduler.cancel":
                job_id = payload.get("job_id")
                if job_id:
                    background_scheduler.cancel_job(job_id)
                jobs = background_scheduler.list_jobs()
                await broadcast_message({
                    "id": msg_id,
                    "type": "scheduler.list_result",
                    "ts": "",
                    "payload": {"jobs": jobs}
                })

            elif mtype == "watchlist.list":
                items = financial_engine.list_watchlist()
                await websocket.send_json({
                    "id": msg_id,
                    "type": "watchlist.list_result",
                    "ts": "",
                    "payload": {"items": items}
                })

            elif mtype == "watchlist.add":
                symbol = payload.get("symbol")
                target = payload.get("target_price", 0.0)
                cond = payload.get("condition", "above")
                atype = payload.get("asset_type", "stock")
                if symbol:
                    financial_engine.add_to_watchlist(symbol, target, cond, atype)
                items = financial_engine.list_watchlist()
                await broadcast_message({
                    "id": msg_id,
                    "type": "watchlist.list_result",
                    "ts": "",
                    "payload": {"items": items}
                })

            elif mtype == "watchlist.remove":
                symbol = payload.get("symbol")
                if symbol:
                    financial_engine.remove_from_watchlist(symbol)
                items = financial_engine.list_watchlist()
                await broadcast_message({
                    "id": msg_id,
                    "type": "watchlist.list_result",
                    "ts": "",
                    "payload": {"items": items}
                })

    except WebSocketDisconnect:
        pass
    finally:
        active_websockets.discard(websocket)
        if active_task and not active_task.done():
            active_task.cancel()

# REST Endpoints for Diagnostics and Logs
@app.get("/api/health")
async def health_check():
    return {"status": "ok", "service": "phenom-backend", "halted": guardian.is_halted}

@app.get("/api/logs")
async def get_logs(limit: int = 50):
    return action_log.list_entries(limit=limit)

@app.get("/api/rules")
async def get_rules():
    return learned_rules.list_rules()

@app.get("/api/approvals")
async def get_approvals():
    return approvals.list_all()

@app.get("/api/mode")
async def get_current_mode():
    return mode_manager.get_mode_profile()

@app.get("/api/scheduler/jobs")
async def get_scheduler_jobs():
    return background_scheduler.list_jobs()

@app.get("/api/scheduler/logs")
async def get_scheduler_logs(limit: int = 50):
    return background_scheduler.get_run_logs(limit=limit)

@app.get("/api/watchlist")
async def get_financial_watchlist_api():
    return financial_engine.list_watchlist()

@app.get("/api/telegram/status")
async def get_telegram_status():
    return {
        "configured": telegram_controller.is_configured,
        "owner_id": get_telegram_owner_id(),
        "locked": is_remote_locked()
    }

@app.post("/api/telegram/unlock")
async def unlock_telegram_remote():
    set_remote_locked(False)
    return {"locked": False, "status": "unlocked"}

@app.post("/api/telegram/lock")
async def lock_telegram_remote():
    set_remote_locked(True)
    return {"locked": True, "status": "locked"}

@app.post("/api/telegram/config")
async def update_telegram_config(payload: Dict[str, Any]):
    token = payload.get("token")
    owner_id = payload.get("owner_id")
    if token:
        set_telegram_token(token)
    if owner_id:
        set_telegram_owner_id(int(owner_id))
    if token and owner_id:
        telegram_controller.set_credentials(token, int(owner_id))
    return {
        "configured": telegram_controller.is_configured,
        "owner_id": get_telegram_owner_id(),
        "locked": is_remote_locked()
    }
