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
from services.backend.orchestrator.engine import orchestrator
from services.backend.voice.tts import tts_engine
from services.backend.voice.wake_word import wake_detector
from services.backend.voice.hotkeys import hotkey_manager
from services.backend.voice.voice_coordinator import voice_coordinator
import services.backend.tools.file_tools
import services.backend.tools.app_tools

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

    yield
    wake_detector.stop()

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
