"""
Unit & Integration Tests for Screen Control Safety UX (Task 7e)
Verifies:
1. ScreenBorderOverlay event streaming:
   - Neon amber border (#f59e0b) on automation start.
   - Real-time action ticker updates.
   - 300 ms concentric click target highlight ring emission.
   - Emerald green border (#10b981) on completion.
   - Ruby red border (#ef4444) on error or killswitch.
2. Procedural automation audio cues (start chime, stop chime, halt double-beep).
3. Human takeover interruption latency (< 50 ms SLA; typically < 15 ms).
4. Human takeover 10-second auto-abort SLA.
"""

import time
import pytest
import asyncio
from services.backend.automation.desktop_controller import desktop_controller
from services.backend.automation.human_takeover import takeover_manager, HumanTakeoverAbort
from services.backend.voice.sound_fx import sound_fx

@pytest.mark.asyncio
async def test_screen_border_overlay_events_emission(monkeypatch):
    import pyautogui
    monkeypatch.setattr(pyautogui, "click", lambda *a, **k: None)

    emitted_events = []
    def record_event(etype, payload):
        emitted_events.append((etype, payload))

    desktop_controller.set_overlay_callback(record_event)

    # Step plan: focus then click
    steps = [
        {"action": "focus", "target": "Desktop"},
        {"action": "click", "coords": (500, 300)}
    ]

    results = await desktop_controller.execute_step_plan(steps)
    assert len(results) == 2

    event_types = [e[0] for e in emitted_events]

    # Verify start event
    assert "screen.overlay_state" in event_types
    start_event = emitted_events[0]
    assert start_event[0] == "screen.overlay_state"
    assert start_event[1]["state"] == "active"
    assert start_event[1]["color"] == "#f59e0b"

    # Verify action ticker emission
    assert "screen.action_ticker" in event_types
    ticker_events = [e[1] for e in emitted_events if e[0] == "screen.action_ticker"]
    assert len(ticker_events) >= 2
    assert "Focus" in ticker_events[0]["text"]
    assert "Click" in ticker_events[1]["text"]

    # Verify click target highlight ring (coords 500, 300, duration 300ms)
    assert "screen.click_highlight" in event_types
    highlight = next(e[1] for e in emitted_events if e[0] == "screen.click_highlight")
    assert highlight["x"] == 500
    assert highlight["y"] == 300
    assert highlight["duration_ms"] == 300

    # Verify success completion event
    last_event = emitted_events[-1]
    assert last_event[0] == "screen.overlay_state"
    assert last_event[1]["state"] == "success"
    assert last_event[1]["color"] == "#10b981"

@pytest.mark.asyncio
async def test_screen_control_error_state_emission():
    emitted_events = []
    desktop_controller.set_overlay_callback(lambda et, p: emitted_events.append((et, p)))

    # Step attempting to type into password field (strictly forbidden)
    steps = [
        {"action": "type", "target": "password_field", "text": "Secret123"}
    ]

    with pytest.raises(PermissionError):
        await desktop_controller.execute_step_plan(steps)

    last_event = emitted_events[-1]
    assert last_event[0] == "screen.overlay_state"
    assert last_event[1]["state"] == "error"
    assert last_event[1]["color"] == "#ef4444"

def test_human_takeover_interruption_latency():
    """Verifies physical user input halts automation within < 50ms SLA."""
    takeover_manager.start_automation()
    assert takeover_manager.is_automating is True
    assert takeover_manager.is_paused is False

    t_start = time.perf_counter()
    # Simulate user physical mouse movement triggering hook
    takeover_manager._trigger_pause("mouse_move")
    latency_ms = (time.perf_counter() - t_start) * 1000.0

    assert takeover_manager.is_paused is True
    # Verify latency < 50 ms (typically < 1 ms)
    assert latency_ms < 50.0, f"Takeover pause latency {latency_ms:.2f}ms exceeded 50ms SLA"

    # Reset via continue or catch stop abort
    takeover_manager.resolve_takeover("continue")
    assert takeover_manager.is_paused is False
    takeover_manager.end_automation()
    assert takeover_manager.is_automating is False

@pytest.mark.asyncio
async def test_human_takeover_10s_auto_abort():
    """Verifies that unhandled takeover pauses auto-abort after SLA timeout."""
    takeover_manager.start_automation()
    takeover_manager._trigger_pause("user_key_press")

    # Call wait_if_paused with short timeout simulating 10s expiration
    with pytest.raises(HumanTakeoverAbort) as exc:
        await takeover_manager.wait_if_paused(max_wait_seconds=0.1)

    assert "aborted" in str(exc.value).lower()
    assert takeover_manager.is_automating is False
    assert takeover_manager.is_paused is False

def test_procedural_automation_audio_chimes():
    """Validates that procedural audio synthesis runs without error."""
    # Play start, stop, halt cues (in-memory synthesis, non-blocking)
    sound_fx.play_automation_start()
    sound_fx.play_automation_stop()
    sound_fx.play_automation_halt()
