"""
Phenom Backend FastAPI Application
Serves the typed WebSocket endpoint on /ws and REST utility endpoints.
Connects the desktop Electron app to the orchestrator, safety layer, router, and memory.
"""

import asyncio
import hmac
import json
import os
import time

try:
    from dotenv import load_dotenv
    _env_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '.env'))
    if os.path.exists(_env_path):
        load_dotenv(_env_path)
except ImportError:
    pass
from collections import defaultdict
from contextlib import asynccontextmanager
from typing import Dict, Any, Optional
import numpy as np
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Depends, HTTPException, Security, status, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
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
import services.backend.tools.media_tools
import services.backend.tools.utility_tools
import services.backend.tools.git_tools
import services.backend.tools.coding_tools
from services.backend.voice.sound_fx import sound_fx
from services.backend.modes.mode_manager import mode_manager
from services.backend.scheduler.cron import background_scheduler
from services.backend.integrations.finance import financial_engine
from services.backend.integrations.google_workspace import google_workspace
from services.backend.browser.browser_controller import browser_controller
from services.backend.automation.human_takeover import takeover_manager
from services.backend.remote.telegram_bot import telegram_controller
from services.backend.remote.credentials import (
    is_remote_locked, set_remote_locked, set_telegram_token, set_telegram_owner_id, get_telegram_owner_id,
    get_or_create_remote_pin, rotate_remote_pin, check_pin_rotation_status, get_failed_pin_attempts,
    unlock_remote_from_desktop
)
from services.backend.memory.vault import vault_manager
from services.backend.voice.daily_briefing import daily_briefing_manager
from services.backend.resource.vram_manager import vram_manager

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

    main_loop = asyncio.get_running_loop()

    # Setup wake word and voice command pipeline
    def on_wake_word_detected():
        asyncio.run_coroutine_threadsafe(broadcast_message({
            "id": f"wake-{os.urandom(2).hex()}",
            "type": "state.change",
            "ts": "",
            "payload": {"state": "listening", "detail": "Listening for your command, sir..."}
        }), main_loop)
    wake_detector.set_wake_callback(on_wake_word_detected)

    def on_amplitude(amp: float):
        if amp > 0.04:
            asyncio.run_coroutine_threadsafe(broadcast_message({
                "id": "amp",
                "type": "voice.amplitude",
                "ts": "",
                "payload": {"amplitude": amp}
            }), main_loop)
    wake_detector.set_amplitude_callback(on_amplitude)

    async def on_voice_token(token: str):
        await broadcast_message({
            "id": "voice-reply",
            "type": "chat.token",
            "ts": "",
            "payload": {"token": token, "index": 0}
        })

    async def on_voice_done(full_text: str):
        await broadcast_message({
            "id": "voice-reply",
            "type": "chat.done",
            "ts": "",
            "payload": {"full_text": full_text}
        })

    voice_coordinator.set_stream_callbacks(on_voice_token, on_voice_done)

    def on_command_recorded(audio_data: np.ndarray):
        async def process_spoken_turn():
            await broadcast_message({
                "id": f"stt-{os.urandom(2).hex()}",
                "type": "state.change",
                "ts": "",
                "payload": {"state": "thinking", "detail": "Transcribing speech..."}
            })

            # Process through Voice Coordinator pipeline (STT -> Orchestrator -> Piper TTS)
            await voice_coordinator.handle_spoken_audio(audio_data)

            sound_fx.play_done_chime()

            # Enter 5-second duplex follow-up conversation window
            wake_detector.enter_duplex_followup_window(5.0)

            await broadcast_message({
                "id": f"duplex-{os.urandom(2).hex()}",
                "type": "state.change",
                "ts": "",
                "payload": {"state": "listening", "detail": "Listening for follow-up..."}
            })

        asyncio.run_coroutine_threadsafe(process_spoken_turn(), main_loop)

    def on_duplex_timeout():
        asyncio.run_coroutine_threadsafe(broadcast_message({
            "id": f"duplex-end-{os.urandom(2).hex()}",
            "type": "state.change",
            "ts": "",
            "payload": {"state": "idle"}
        }), main_loop)

    wake_detector.set_command_callback(on_command_recorded)
    wake_detector.set_duplex_timeout_callback(on_duplex_timeout)
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

    # Register vault git nightly backup handler
    async def run_vault_backup_job(payload):
        return vault_manager.sync_vault_git()

    background_scheduler.register_callback("vault_backup", run_vault_backup_job)

    # Schedule 24h recurring nightly vault backup if not already present
    try:
        existing_jobs = [
            j for j in background_scheduler.list_jobs(include_disabled=False)
            if j.get("action_type") == "vault_backup"
        ]
        if not existing_jobs:
            background_scheduler.add_recurring_job(
                title="Nightly Vault Backup & Git Sync",
                interval_seconds=86400,
                action_type="vault_backup"
            )
    except Exception as e:
        print(f"[Vault] Could not schedule recurring backup: {e}")

    background_scheduler.start()
    telegram_controller.start()
    asyncio.create_task(warm_up_ollama())

    yield
    telegram_controller.stop()
    background_scheduler.stop()
    wake_detector.stop()
    await browser_controller.close()

app = FastAPI(title="Phenom Backend", lifespan=lifespan)

PACKAGED_ORIGINS = {"file://", "null", "vscode-file://", "electron://"}
DEV_ORIGINS = {"http://localhost:5173", "http://127.0.0.1:5173"}

def get_allowed_origins() -> list[str]:
    origins = list(PACKAGED_ORIGINS)
    if os.environ.get("PHENOM_DEV") == "1":
        origins.extend(DEV_ORIGINS)
    return origins

def is_origin_allowed(origin: Optional[str]) -> bool:
    allowed = set(PACKAGED_ORIGINS)
    if os.environ.get("PHENOM_DEV") == "1":
        allowed.update(DEV_ORIGINS)
        if origin is None:
            return True
    if origin is None:
        return False
    return origin in allowed

app.add_middleware(
    CORSMiddleware,
    allow_origins=get_allowed_origins(),
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

bearer_scheme = HTTPBearer(auto_error=False)

def get_expected_session_token() -> Optional[str]:
    token = os.environ.get("PHENOM_SESSION_TOKEN")
    if token:
        return token
    appdata = os.environ.get("APPDATA") or os.path.expanduser("~")
    token_path = os.path.join(appdata, "Phenom", ".session_token")
    if os.path.exists(token_path):
        try:
            with open(token_path, "r", encoding="utf-8") as tf:
                val = tf.read().strip()
                if val:
                    os.environ["PHENOM_SESSION_TOKEN"] = val
                    return val
        except Exception:
            pass
    return None

def verify_session_token(credentials: Optional[HTTPAuthorizationCredentials] = Security(bearer_scheme)):
    expected = get_expected_session_token()
    if not expected:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Session token not configured (PHENOM_SESSION_TOKEN unset)"
        )
    if not credentials or not credentials.credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing Authorization header"
        )
    if not hmac.compare_digest(credentials.credentials, expected):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid session token"
        )
    return credentials.credentials

# Rate limiting for WebSocket failed handshakes: 5 failed handshakes per 60s per peer IP
failed_handshakes: Dict[str, list[float]] = defaultdict(list)
FAILED_HANDSHAKE_WINDOW = 60.0
MAX_FAILED_HANDSHAKES = 5

def is_peer_rate_limited(peer_ip: str) -> bool:
    now = time.time()
    valid_window = [t for t in failed_handshakes[peer_ip] if now - t < FAILED_HANDSHAKE_WINDOW]
    failed_handshakes[peer_ip] = valid_window
    return len(valid_window) >= MAX_FAILED_HANDSHAKES

def record_handshake_failure(peer_ip: str) -> None:
    now = time.time()
    valid_window = [t for t in failed_handshakes[peer_ip] if now - t < FAILED_HANDSHAKE_WINDOW]
    valid_window.append(now)
    failed_handshakes[peer_ip] = valid_window

active_websockets: set[WebSocket] = set()
pending_confirmations: Dict[str, asyncio.Future] = {}

async def broadcast_message(msg_dict: Dict[str, Any]):
    # Broadcast safety: only authenticated sockets may receive broadcasts (especially confirm.request and log.entry)
    for ws in list(active_websockets):
        if getattr(ws, "authenticated", False) is not True:
            continue
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
    peer_ip = websocket.client.host if websocket.client else "127.0.0.1"

    # Rate limiting: close socket after 5 failed handshakes from same peer within 60s
    if is_peer_rate_limited(peer_ip):
        await websocket.close(code=4401)
        return

    expected_token = get_expected_session_token()
    if not expected_token:
        # Refuse to start WebSocket (fail closed) if PHENOM_SESSION_TOKEN is not set
        record_handshake_failure(peer_ip)
        await websocket.close(code=4401)
        return

    # Validate Origin header against allowlist
    origin = websocket.headers.get("origin")
    if not is_origin_allowed(origin):
        record_handshake_failure(peer_ip)
        await websocket.close(code=4401)
        return

    # Validate token in Sec-WebSocket-Protocol (phenom.<token>)
    subprotocols = websocket.scope.get("subprotocols", []) or []
    if not subprotocols:
        header = websocket.headers.get("sec-websocket-protocol", "")
        if header:
            subprotocols = [s.strip() for s in header.split(",")]

    provided_token = None
    accepted_subprotocol = None
    for sp in subprotocols:
        if sp.startswith("phenom."):
            provided_token = sp[len("phenom."):]
            accepted_subprotocol = sp
            break

    if not provided_token or not hmac.compare_digest(provided_token, expected_token):
        record_handshake_failure(peer_ip)
        await websocket.close(code=4401)
        return

    await websocket.accept(subprotocol=accepted_subprotocol)
    websocket.authenticated = True
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

            elif mtype == "voice.trigger":
                wake_detector.trigger_manual_listen(4.5)

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
        websocket.authenticated = False
        active_websockets.discard(websocket)
        if active_task and not active_task.done():
            active_task.cancel()

# Minimal unauthenticated health endpoints
@app.get("/")
async def root_dashboard(request: Request):
    accept = request.headers.get("accept", "")
    if "text/html" in accept:
        html_content = """<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <title>Phenom Assistant - Online</title>
  <style>
    body {
      background: #0b0f19;
      color: #e2e8f0;
      font-family: 'Segoe UI', system-ui, -apple-system, sans-serif;
      display: flex;
      align-items: center;
      justify-content: center;
      min-height: 100vh;
      margin: 0;
    }
    .card {
      background: rgba(15, 23, 42, 0.8);
      border: 1px solid rgba(0, 229, 255, 0.3);
      border-radius: 16px;
      padding: 32px 40px;
      max-width: 520px;
      box-shadow: 0 10px 30px rgba(0, 229, 255, 0.15);
      backdrop-filter: blur(12px);
    }
    h1 {
      color: #00e5ff;
      margin: 0 0 8px 0;
      font-size: 26px;
      display: flex;
      align-items: center;
      gap: 10px;
    }
    .badge {
      display: inline-block;
      background: rgba(0, 229, 255, 0.12);
      color: #00e5ff;
      border: 1px solid rgba(0, 229, 255, 0.4);
      border-radius: 999px;
      padding: 4px 12px;
      font-size: 13px;
      font-weight: 600;
      margin-bottom: 20px;
    }
    p { color: #94a3b8; font-size: 15px; line-height: 1.6; margin: 8px 0; }
    strong { color: #f8fafc; }
    code { background: rgba(255,255,255,0.08); padding: 2px 6px; border-radius: 4px; color: #38bdf8; }
    .links { margin-top: 24px; display: flex; gap: 12px; flex-wrap: wrap; }
    .btn {
      display: inline-block;
      background: #00e5ff;
      color: #0b0f19;
      text-decoration: none;
      padding: 8px 18px;
      border-radius: 8px;
      font-weight: 600;
      font-size: 14px;
      transition: opacity 0.2s;
    }
    .btn:hover { opacity: 0.9; }
    .btn-secondary {
      background: rgba(255,255,255,0.08);
      color: #cbd5e1;
      border: 1px solid rgba(255,255,255,0.15);
    }
  </style>
</head>
<body>
  <div class="card">
    <h1>⚡ Phenom Assistant</h1>
    <span class="badge">● Backend Online</span>
    <p><strong>Primary Voice:</strong> Kabir v4-flash (0.95x Deliberate Pace)</p>
    <p><strong>Offline Voice:</strong> Madhur Neural (Silent Failover)</p>
    <p><strong>Desktop UI:</strong> Connected via WebSocket (<code>/ws</code>)</p>
    <p><strong>Controls:</strong> Press <code>Alt + Space</code> for Command Bar or <code>Ctrl + Space</code> to talk to Kabir.</p>
    <div class="links">
      <a class="btn" href="/docs">API Docs (Swagger)</a>
      <a class="btn btn-secondary" href="/health">Health Check</a>
    </div>
  </div>
</body>
</html>"""
        return HTMLResponse(content=html_content)
    return {
        "app": "Phenom Assistant",
        "status": "online",
        "version": "0.1.0",
        "voice": "Kabir v4-flash (0.95x pace)",
        "websocket": "ws://127.0.0.1:8000/ws",
        "health": "/health",
        "docs": "/docs"
    }

@app.get("/health")
@app.get("/api/health")
async def health_check():
    return {"status": "ok"}

# REST Endpoints protected by session token
@app.get("/api/logs", dependencies=[Depends(verify_session_token)])
async def get_logs(limit: int = 50):
    return action_log.list_entries(limit=limit)

@app.get("/api/rules", dependencies=[Depends(verify_session_token)])
async def get_rules():
    return learned_rules.list_rules()

@app.get("/api/approvals", dependencies=[Depends(verify_session_token)])
async def get_approvals():
    return approvals.list_all()

@app.get("/api/mode", dependencies=[Depends(verify_session_token)])
async def get_current_mode():
    return mode_manager.get_mode_profile()

@app.get("/api/scheduler/jobs", dependencies=[Depends(verify_session_token)])
async def get_scheduler_jobs():
    return background_scheduler.list_jobs()

@app.get("/api/scheduler/logs", dependencies=[Depends(verify_session_token)])
async def get_scheduler_logs(limit: int = 50):
    return background_scheduler.get_run_logs(limit=limit)

@app.get("/api/watchlist", dependencies=[Depends(verify_session_token)])
async def get_financial_watchlist_api():
    return financial_engine.list_watchlist()

@app.get("/api/telegram/status", dependencies=[Depends(verify_session_token)])
async def get_telegram_status():
    return {
        "configured": telegram_controller.is_configured,
        "owner_id": get_telegram_owner_id(),
        "locked": is_remote_locked(),
        "failed_attempts": get_failed_pin_attempts(),
        "pin_status": check_pin_rotation_status()
    }

@app.post("/api/telegram/unlock", dependencies=[Depends(verify_session_token)])
async def unlock_telegram_remote():
    unlock_remote_from_desktop()
    return {"locked": False, "status": "unlocked", "failed_attempts": 0}

@app.post("/api/telegram/lock", dependencies=[Depends(verify_session_token)])
async def lock_telegram_remote():
    set_remote_locked(True)
    return {"locked": True, "status": "locked"}

@app.get("/api/telegram/pin", dependencies=[Depends(verify_session_token)])
async def get_telegram_pin_status():
    rot_status = check_pin_rotation_status()
    return {
        "configured": True,
        "created_at": rot_status.get("created_at"),
        "age_days": rot_status.get("age_days"),
        "needs_rotation": rot_status.get("needs_rotation"),
        "failed_attempts": get_failed_pin_attempts(),
        "locked": is_remote_locked()
    }

@app.get("/api/telegram/pin/reveal", dependencies=[Depends(verify_session_token)])
async def reveal_telegram_pin():
    pin = get_or_create_remote_pin()
    return {"pin": pin}

@app.post("/api/telegram/pin/rotate", dependencies=[Depends(verify_session_token)])
async def rotate_telegram_pin_api():
    new_pin = rotate_remote_pin()
    return {"status": "rotated", "new_pin": new_pin}

@app.post("/api/telegram/config", dependencies=[Depends(verify_session_token)])
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

@app.get("/api/briefing/morning", dependencies=[Depends(verify_session_token)])
async def get_morning_briefing_api():
    return await daily_briefing_manager.generate_briefing(dry_run_speech=True)

@app.get("/api/orb/lod", dependencies=[Depends(verify_session_token)])
async def get_orb_lod_api():
    lod = vram_manager.get_orb_lod_quality()
    return {
        "quality_level": lod,
        "is_gaming": vram_manager.gaming_mode_active,
        "detected_game": vram_manager.detected_game_name
    }

@app.get("/api/vault/status", dependencies=[Depends(verify_session_token)])
async def get_vault_status():
    return {
        "vault_path": vault_manager.vault_path,
        "remote_url": vault_manager.get_remote_url(),
        "git_initialized": os.path.exists(os.path.join(vault_manager.vault_path, ".git")),
        "has_token": bool(vault_manager.get_vault_token()),
        "note_count": len(vault_manager.list_notes())
    }

@app.post("/api/vault/config", dependencies=[Depends(verify_session_token)])
async def update_vault_config(payload: Dict[str, Any]):
    remote_url = payload.get("remote_url")
    token = payload.get("token")
    if remote_url is not None:
        vault_manager.set_remote_url(remote_url)
    if token is not None:
        vault_manager.set_vault_token(token)
    return {
        "status": "ok",
        "remote_url": vault_manager.get_remote_url(),
        "has_token": bool(vault_manager.get_vault_token())
    }

@app.post("/api/vault/test_connection", dependencies=[Depends(verify_session_token)])
async def test_vault_connection(payload: Optional[Dict[str, Any]] = None):
    url = (payload or {}).get("remote_url")
    return vault_manager.test_remote_connection(remote_url=url)

@app.post("/api/vault/sync", dependencies=[Depends(verify_session_token)])
async def sync_vault_now():
    return vault_manager.sync_vault_git()

# Google Workspace Integration Endpoints
@app.get("/api/workspace/status", dependencies=[Depends(verify_session_token)])
async def get_workspace_status():
    addr, _ = google_workspace.get_gmail_credentials()
    return {
        "gmail_configured": google_workspace.is_gmail_configured(),
        "calendar_configured": google_workspace.is_calendar_configured(),
        "gmail_address": addr
    }

@app.post("/api/workspace/gmail/config", dependencies=[Depends(verify_session_token)])
async def update_gmail_config(payload: Dict[str, Any]):
    address = payload.get("address", "")
    password = payload.get("password", "")
    if address and password:
        google_workspace.set_gmail_credentials(address, password)
    return {
        "gmail_configured": google_workspace.is_gmail_configured(),
        "gmail_address": address
    }

@app.post("/api/workspace/calendar/config", dependencies=[Depends(verify_session_token)])
async def update_calendar_config(payload: Dict[str, Any]):
    token = payload.get("token", "")
    if token:
        google_workspace.set_calendar_token(token)
    return {
        "calendar_configured": google_workspace.is_calendar_configured()
    }

@app.post("/api/workspace/test_connection", dependencies=[Depends(verify_session_token)])
async def test_workspace_connection():
    gmail_res = google_workspace.test_gmail_connection()
    cal_res = await google_workspace.test_calendar_connection()
    return {
        "gmail": gmail_res,
        "calendar": cal_res
    }

@app.post("/api/workspace/disconnect", dependencies=[Depends(verify_session_token)])
async def disconnect_workspace(payload: Optional[Dict[str, Any]] = None):
    target = (payload or {}).get("target", "all")
    if target in ["all", "gmail"]:
        google_workspace.clear_gmail_credentials()
    if target in ["all", "calendar"]:
        google_workspace.clear_calendar_token()
    return {
        "status": "disconnected",
        "gmail_configured": google_workspace.is_gmail_configured(),
        "calendar_configured": google_workspace.is_calendar_configured()
    }

@app.get("/api/coding/verify-package", dependencies=[Depends(verify_session_token)])
async def verify_coding_package(name: str):
    from services.backend.coding.typosquat_guard import typosquat_guard
    report = typosquat_guard.evaluate_package(name)
    return report.model_dump()

@app.get("/api/coding/workspaces", dependencies=[Depends(verify_session_token)])
async def list_coding_workspaces():
    from services.backend.coding.workspace import workspace_manager
    workspaces = []
    if os.path.exists(workspace_manager.workspaces_root):
        for entry in os.listdir(workspace_manager.workspaces_root):
            p = os.path.join(workspace_manager.workspaces_root, entry)
            if os.path.isdir(p):
                workspaces.append({"id": entry, "path": p})
    return {"workspaces_root": workspace_manager.workspaces_root, "workspaces": workspaces}

@app.get("/api/gaming/status", dependencies=[Depends(verify_session_token)])
async def get_gaming_status():
    from services.backend.automation.gaming_mode import gaming_manager
    is_game, game_name, reason = gaming_manager.detect_gaming_state()
    return {
        "gaming_mode_active": gaming_manager.gaming_mode_active,
        "active_game": gaming_manager.active_game_name or game_name,
        "detection_reason": gaming_manager.detection_reason or reason,
        "power_plan": gaming_manager.active_power_plan
    }

@app.post("/api/gaming/toggle", dependencies=[Depends(verify_session_token)])
async def toggle_gaming_mode(payload: Dict[str, Any]):
    from services.backend.automation.gaming_mode import gaming_manager
    enable = payload.get("enable", not gaming_manager.gaming_mode_active)
    if enable:
        res = await gaming_manager.enter_gaming_mode(payload.get("game_name", "manual_override"))
    else:
        res = await gaming_manager.exit_gaming_mode()
    return res

@app.get("/api/notifications/digest", dependencies=[Depends(verify_session_token)])
async def get_notifications_digest():
    from services.backend.automation.notification_digest import notification_digest_manager
    digest = notification_digest_manager.generate_spoken_digest()
    return digest

@app.post("/api/notifications/digest/clear", dependencies=[Depends(verify_session_token)])
async def clear_notifications_digest():
    from services.backend.automation.notification_digest import notification_digest_manager
    cleared = notification_digest_manager.clear_buffer()
    return {"status": "cleared", "cleared_count": cleared}

@app.get("/api/usage/summary", dependencies=[Depends(verify_session_token)])
async def get_usage_summary(date: Optional[str] = None):
    from services.backend.router.usage_tracker import usage_tracker
    daily = usage_tracker.get_daily_summary(date)
    recent = usage_tracker.get_recent_load_history(limit=20)
    return {"daily": daily, "recent_history": recent}

@app.get("/api/help/capabilities", dependencies=[Depends(verify_session_token)])
async def get_capabilities_help(q: Optional[str] = None):
    from services.backend.tools.self_help import self_help_engine
    if q:
        return self_help_engine.answer_query(q)
    return self_help_engine.get_capabilities_manifest()

@app.post("/api/system/reset", dependencies=[Depends(verify_session_token)])
async def perform_system_reset(payload: Dict[str, Any]):
    from services.backend.packaging.reset_manager import reset_manager
    target = payload.get("target", "")
    confirmation = payload.get("confirmation", "")
    preview_only = payload.get("preview_only", False)
    if preview_only:
        return reset_manager.preview_reset(target)
    return reset_manager.execute_reset(target, confirmation)

@app.post("/api/system/export", dependencies=[Depends(verify_session_token)])
async def perform_data_export(payload: Optional[Dict[str, Any]] = None):
    from services.backend.packaging.export_manager import export_manager
    out_dir = (payload or {}).get("output_dir")
    return export_manager.export_data(output_dir=out_dir)

@app.get("/api/meeting/status", dependencies=[Depends(verify_session_token)])
async def get_meeting_status():
    from services.backend.automation.meeting_mode import meeting_manager
    is_meeting, app_name, reason = meeting_manager.detect_meeting()
    return {
        "meeting_mode_active": meeting_manager.meeting_mode_active,
        "meeting_app": meeting_manager.active_meeting_app or app_name,
        "detection_source": meeting_manager.detection_source or reason,
        "display_affinity": "WDA_EXCLUDEFROMCAPTURE" if meeting_manager.meeting_mode_active else "WDA_NONE"
    }

@app.post("/api/meeting/toggle", dependencies=[Depends(verify_session_token)])
async def toggle_meeting_mode(payload: Dict[str, Any]):
    from services.backend.automation.meeting_mode import meeting_manager
    enable = payload.get("enable", not meeting_manager.meeting_mode_active)
    if enable:
        res = meeting_manager.enter_meeting_mode(payload.get("app_name", "manual_meeting"))
    else:
        res = meeting_manager.exit_meeting_mode()
    return res

@app.get("/api/system/self-check", dependencies=[Depends(verify_session_token)])
async def run_daily_self_check():
    from services.backend.packaging.self_check import self_check_engine
    report = self_check_engine.run_diagnostic_suite()
    return report

@app.get("/api/system/safe-mode", dependencies=[Depends(verify_session_token)])
async def get_safe_mode_status():
    from services.backend.packaging.safe_mode import safe_mode_manager
    return {"safe_mode_active": safe_mode_manager.safe_mode_active}

@app.post("/api/system/safe-mode/toggle", dependencies=[Depends(verify_session_token)])
async def toggle_safe_mode(payload: Dict[str, Any]):
    from services.backend.packaging.safe_mode import safe_mode_manager
    enable = payload.get("enable", not safe_mode_manager.safe_mode_active)
    if enable:
        safe_mode_manager.enable_safe_mode()
    else:
        safe_mode_manager.disable_safe_mode()
    return {"safe_mode_active": safe_mode_manager.safe_mode_active}

@app.get("/api/system/setup-status")
async def get_system_setup_status():
    """Returns whether the initial first-run setup wizard has been completed."""
    env_done = os.environ.get("PHENOM_FIRST_RUN_DONE", "true").lower() in ("true", "1")
    return {"first_run_completed": env_done}

@app.post("/api/system/complete-setup")
async def complete_system_setup():
    """Permanently records that the first-run setup wizard has been finished."""
    os.environ["PHENOM_FIRST_RUN_DONE"] = "true"
    return {"status": "ok", "first_run_completed": True}

