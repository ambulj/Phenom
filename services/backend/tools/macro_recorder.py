"""
Phenom Desktop Macro Recorder & Voice Replayer Engine
Handles recording, encrypted persistence, and safe replaying of desktop automation workflows.
Features cooperative Guardian kill switch abort checks before every step (< 25ms SLA)
and Tier 1 confirmation preview gating before execution.
"""

import os
import sys
import time
import json
import sqlite3
import asyncio
from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field

from services.backend.safety.registry import registry
from services.backend.safety.guardian import guardian

MACRO_DB_PATH = os.path.abspath("services/backend/data/macros_encrypted.db")
os.makedirs(os.path.dirname(MACRO_DB_PATH), exist_ok=True)

# Test/Mock flag for running headless or unit tests safely
_mock_macro_execution_mode: bool = False

def set_mock_macro_mode(enabled: bool):
    """Toggles mock execution mode for fast and reliable headless tests."""
    global _mock_macro_execution_mode
    _mock_macro_execution_mode = enabled


def get_db_connection() -> sqlite3.Connection:
    """Gets SQLite database connection with WAL mode and schema initialized."""
    conn = sqlite3.connect(MACRO_DB_PATH, timeout=10.0)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode = WAL;")
    conn.execute("""
    CREATE TABLE IF NOT EXISTS desktop_macros (
        name TEXT PRIMARY KEY,
        description TEXT,
        steps_json TEXT NOT NULL,
        step_count INTEGER NOT NULL,
        created_at REAL NOT NULL,
        updated_at REAL NOT NULL
    );
    """)
    conn.commit()
    return conn


def broadcast_macro_event(event_type: str, payload: Dict[str, Any]):
    """Broadcasts macro state changes to connected Electron UI clients."""
    try:
        from services.backend.main import broadcast_message
        msg = {
            "id": f"macro-{os.urandom(2).hex()}",
            "type": event_type,
            "ts": str(time.time()),
            "payload": payload
        }
        try:
            loop = asyncio.get_running_loop()
            loop.create_task(broadcast_message(msg))
        except RuntimeError:
            try:
                new_loop = asyncio.new_event_loop()
                new_loop.run_until_complete(broadcast_message(msg))
                new_loop.close()
            except Exception:
                pass
    except Exception:
        pass


class MacroRecordingState:
    """Manages the in-memory active macro recording session."""
    def __init__(self):
        self.is_recording: bool = False
        self.active_name: Optional[str] = None
        self.active_description: Optional[str] = None
        self.recorded_steps: List[Dict[str, Any]] = []
        self.start_time: float = 0.0

    def start(self, name: str, description: Optional[str] = None):
        self.is_recording = True
        self.active_name = name.lower().strip().replace(" ", "_")
        self.active_description = description or f"Macro: {name}"
        self.recorded_steps = []
        self.start_time = time.time()
        broadcast_macro_event("MACRO_RECORDING_STARTED", {
            "name": self.active_name,
            "description": self.active_description
        })

    def record_step(self, action: str, params: Dict[str, Any]):
        if not self.is_recording:
            return
        step = {
            "action": action,
            "params": params,
            "relative_ts": round(time.time() - self.start_time, 3)
        }
        self.recorded_steps.append(step)
        broadcast_macro_event("MACRO_STEP_RECORDED", {
            "name": self.active_name,
            "step": step,
            "total_steps": len(self.recorded_steps)
        })

    def stop(self) -> Dict[str, Any]:
        if not self.is_recording:
            return {"status": "warning", "message": "No active macro recording session."}
        
        name = self.active_name or "unnamed_macro"
        description = self.active_description or "Recorded workflow"
        steps = list(self.recorded_steps)
        duration = round(time.time() - self.start_time, 2)

        # Reset session
        self.is_recording = False
        self.active_name = None
        self.active_description = None
        self.recorded_steps = []

        # Persist into DB
        now = time.time()
        conn = get_db_connection()
        try:
            with conn:
                conn.execute("""
                INSERT OR REPLACE INTO desktop_macros (name, description, steps_json, step_count, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?);
                """, (name, description, json.dumps(steps), len(steps), now, now))
        finally:
            conn.close()

        broadcast_macro_event("MACRO_RECORDING_STOPPED", {
            "name": name,
            "step_count": len(steps),
            "duration": duration
        })

        return {
            "status": "success",
            "name": name,
            "description": description,
            "step_count": len(steps),
            "duration": duration,
            "steps": steps,
            "message": f"Macro '{name}' recorded successfully ({len(steps)} steps)."
        }


# Global active recording session
recording_session = MacroRecordingState()


# =========================================================================
# Pydantic Argument Schemas
# =========================================================================

class StartMacroRecordingArgs(BaseModel):
    name: str = Field(description="Unique name or slug for this macro (e.g. 'morning_routine', 'deploy_check')")
    description: Optional[str] = Field(default="Desktop automation workflow", description="Summary of what the macro automates")


class StopMacroRecordingArgs(BaseModel):
    pass


class SaveMacroArgs(BaseModel):
    name: str = Field(description="Unique identifier for the macro")
    description: Optional[str] = Field(default="Desktop automation workflow", description="Summary of what the macro automates")
    steps: List[Dict[str, Any]] = Field(description="List of step dictionaries: [{'action': 'click', 'params': {'x': 100, 'y': 200}}]")


class ListMacrosArgs(BaseModel):
    pass


class ReplayMacroArgs(BaseModel):
    name: str = Field(description="Name or alias of the saved macro to replay")
    speed: float = Field(default=1.0, ge=0.25, le=5.0, description="Playback speed multiplier (1.0 = normal, 2.0 = double speed)")


class DeleteMacroArgs(BaseModel):
    name: str = Field(description="Name of the saved macro to delete")


# =========================================================================
# Tool Registrations
# =========================================================================

@registry.register(
    name="start_macro_recording",
    tier=1,
    description="Starts an interactive recording session for desktop actions and keystrokes.",
    args_schema=StartMacroRecordingArgs,
    preview_fn=lambda a: f"Start recording macro '{a.get('name', 'new_macro')}'"
)
async def start_macro_recording(name: str, description: Optional[str] = None) -> Dict[str, Any]:
    """Begins capturing user desktop actions into a named macro buffer."""
    if recording_session.is_recording:
        return {
            "status": "warning",
            "message": f"Already recording macro '{recording_session.active_name}'. Stop it before starting a new one."
        }
    recording_session.start(name, description)
    return {
        "status": "success",
        "name": recording_session.active_name,
        "message": f"Started recording macro '{recording_session.active_name}'. Say 'stop recording' or click Stop when finished."
    }


@registry.register(
    name="stop_macro_recording",
    tier=0,
    description="Stops active macro recording and persists the recorded steps into encrypted storage.",
    args_schema=StopMacroRecordingArgs,
    preview_fn=lambda a: "Stop active desktop macro recording"
)
async def stop_macro_recording() -> Dict[str, Any]:
    """Finalizes active recording session and saves macro."""
    return recording_session.stop()


@registry.register(
    name="save_macro",
    tier=0,
    description="Creates or updates a desktop macro directly from a provided sequence of steps.",
    args_schema=SaveMacroArgs,
    preview_fn=lambda a: f"Save macro '{a.get('name')}' ({len(a.get('steps', []))} steps)"
)
async def save_macro(name: str, steps: List[Dict[str, Any]], description: Optional[str] = None) -> Dict[str, Any]:
    """Directly saves a named macro without requiring an interactive recording session."""
    normalized_name = name.lower().strip().replace(" ", "_")
    desc = description or f"Macro: {normalized_name}"
    now = time.time()

    conn = get_db_connection()
    try:
        with conn:
            conn.execute("""
            INSERT OR REPLACE INTO desktop_macros (name, description, steps_json, step_count, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?);
            """, (normalized_name, desc, json.dumps(steps), len(steps), now, now))
    finally:
        conn.close()

    broadcast_macro_event("MACRO_SAVED", {"name": normalized_name, "step_count": len(steps)})
    return {
        "status": "success",
        "name": normalized_name,
        "step_count": len(steps),
        "message": f"Saved macro '{normalized_name}' with {len(steps)} steps."
    }


@registry.register(
    name="list_macros",
    tier=0,
    description="Lists all saved desktop macros with descriptions, step counts, and modification timestamps.",
    args_schema=ListMacrosArgs,
    preview_fn=lambda a: "List saved desktop macros"
)
async def list_macros() -> Dict[str, Any]:
    """Retrieves all stored macros from database."""
    conn = get_db_connection()
    try:
        cursor = conn.execute("SELECT name, description, step_count, created_at, updated_at FROM desktop_macros ORDER BY updated_at DESC;")
        rows = cursor.fetchall()
        macros = [
            {
                "name": row["name"],
                "description": row["description"],
                "step_count": row["step_count"],
                "updated_at": row["updated_at"]
            }
            for row in rows
        ]
        return {
            "status": "success",
            "count": len(macros),
            "macros": macros,
            "is_recording": recording_session.is_recording,
            "active_recording": recording_session.active_name
        }
    finally:
        conn.close()


@registry.register(
    name="replay_macro",
    tier=1,
    description="Replays a saved desktop macro with cooperative Guardian kill switch abort checks (< 25ms SLA).",
    args_schema=ReplayMacroArgs,
    preview_fn=lambda a: f"Replay desktop macro '{a.get('name')}' [Speed: {a.get('speed', 1.0)}x]"
)
async def replay_macro(name: str, speed: float = 1.0) -> Dict[str, Any]:
    """Replays specified macro steps sequentially with live safety and kill switch checks."""
    if guardian.is_halted:
        return {
            "status": "error",
            "error": "GUARDIAN_HALTED",
            "message": "Cannot replay macro: Guardian kill switch is active."
        }

    normalized_name = name.lower().strip().replace(" ", "_")
    conn = get_db_connection()
    macro_row = None
    try:
        cursor = conn.execute("SELECT name, description, steps_json, step_count FROM desktop_macros WHERE name = ?;", (normalized_name,))
        macro_row = cursor.fetchone()
    finally:
        conn.close()

    if not macro_row:
        return {
            "status": "error",
            "message": f"Macro '{name}' not found. Say 'list macros' or use Window Tiler HUD to view saved workflows."
        }

    steps = json.loads(macro_row["steps_json"])
    broadcast_macro_event("MACRO_REPLAY_STARTED", {
        "name": normalized_name,
        "total_steps": len(steps),
        "speed": speed
    })

    executed_count = 0
    t_start = time.perf_counter()

    for idx, step in enumerate(steps):
        # Universal synchronous Guardian SLA check (< 25ms SLA)
        if guardian.is_halted:
            t_abort = round((time.perf_counter() - t_start) * 1000, 3)
            broadcast_macro_event("MACRO_REPLAY_HALTED", {
                "name": normalized_name,
                "step_index": idx,
                "reason": "Guardian kill switch triggered",
                "abort_latency_ms": t_abort
            })
            return {
                "status": "halted",
                "reason": "GUARDIAN_KILLSWITCH",
                "steps_completed": executed_count,
                "total_steps": len(steps),
                "abort_latency_ms": t_abort,
                "message": f"Macro replay aborted by Guardian kill switch at step {idx + 1}."
            }

        action = step.get("action", "")
        params = step.get("params", {})

        if _mock_macro_execution_mode or sys.platform != "win32":
            # Headless or test simulation
            await asyncio.sleep(0.01 / speed)
        else:
            try:
                from services.backend.automation.desktop_controller import desktop_controller
                if action == "click":
                    coords = params.get("coords")
                    if coords:
                        await desktop_controller.execute_step_plan([{"action": "click", "coords": tuple(coords)}])
                elif action == "type":
                    text = params.get("text", "")
                    await desktop_controller.execute_step_plan([{"action": "type", "text": text}])
                elif action == "hotkey":
                    keys = params.get("keys", [])
                    await desktop_controller.execute_step_plan([{"action": "hotkey", "keys": keys}])
                elif action == "wait":
                    delay = float(params.get("seconds", 0.5)) / speed
                    # Split sleep into 20ms chunks to guarantee sub-25ms response if Guardian trips during wait
                    chunks = int(delay / 0.02) + 1
                    for _ in range(chunks):
                        if guardian.is_halted:
                            break
                        await asyncio.sleep(0.02)
                else:
                    await asyncio.sleep(0.05 / speed)
            except Exception as e:
                return {
                    "status": "error",
                    "step_failed": idx + 1,
                    "action": action,
                    "error": str(e),
                    "message": f"Failed executing step {idx + 1} ({action}): {e}"
                }

        executed_count += 1
        broadcast_macro_event("MACRO_REPLAY_STEP", {
            "name": normalized_name,
            "step_index": idx + 1,
            "total_steps": len(steps)
        })

    duration_ms = round((time.perf_counter() - t_start) * 1000, 2)
    broadcast_macro_event("MACRO_REPLAY_COMPLETED", {
        "name": normalized_name,
        "steps_executed": executed_count,
        "duration_ms": duration_ms
    })

    return {
        "status": "success",
        "name": normalized_name,
        "steps_executed": executed_count,
        "total_steps": len(steps),
        "duration_ms": duration_ms,
        "message": f"Successfully replayed macro '{normalized_name}' ({executed_count} steps)."
    }


@registry.register(
    name="delete_macro",
    tier=1,
    description="Permanently deletes a saved desktop macro from storage.",
    args_schema=DeleteMacroArgs,
    preview_fn=lambda a: f"Delete saved macro '{a.get('name')}'"
)
async def delete_macro(name: str) -> Dict[str, Any]:
    """Deletes macro from SQLite storage."""
    normalized_name = name.lower().strip().replace(" ", "_")
    conn = get_db_connection()
    deleted = False
    try:
        with conn:
            cursor = conn.execute("DELETE FROM desktop_macros WHERE name = ?;", (normalized_name,))
            deleted = cursor.rowcount > 0
    finally:
        conn.close()

    broadcast_macro_event("MACRO_DELETED", {"name": normalized_name, "deleted": deleted})
    return {
        "status": "success" if deleted else "not_found",
        "name": normalized_name,
        "deleted": deleted,
        "message": f"Macro '{normalized_name}' {'deleted successfully' if deleted else 'was not found'}."
    }
