"""
Unit Tests for Proactive Sensory Event Bus (PRX-01, SAF-02).
Verifies:
- Event ingestion with automatic privacy scrubbing
- Type subscriptions and global subscriptions dispatch
- Buffer bounding (max 200 events)
- Broadcaster notification callback
- Synchronous Guardian halt and reset
"""

import pytest
from services.backend.proactive.event_bus import ProactiveEventBus
from services.backend.proactive.privacy_scrubber import PrivacyScrubber
from services.backend.schemas.proactive_bus import Win32EventType


def test_event_bus_ingest_and_scrub():
    """Verify event ingestion automatically sanitizes credentials."""
    scrubber = PrivacyScrubber()
    bus = ProactiveEventBus(scrubber=scrubber)

    ev = bus.ingest_event(
        event_type=Win32EventType.WINDOW_CRASH,
        process_name="app.exe",
        pid=1234,
        window_title="Exception with token sk-abcdef1234567890abcdef123456",
        details={"error_log": "Dumped password: mySecretPassword123!"},
    )

    assert ev.event_type == Win32EventType.WINDOW_CRASH
    assert "sk-abcdef" not in ev.window_title
    assert "[REDACTED_OPENAI_KEY]" in ev.window_title
    assert "mySecretPassword123!" not in ev.details["error_log"]
    assert "password=[REDACTED_SECRET]" in ev.details["error_log"]
    assert ev.is_scrubbed is True
    assert len(ev.scrubbed_fields) == 2


def test_event_bus_subscriptions():
    """Verify type-targeted and global subscriber callbacks."""
    bus = ProactiveEventBus()

    crash_events = []
    all_events = []

    def on_crash(e):
        crash_events.append(e)

    def on_any(e):
        all_events.append(e)

    bus.subscribe(on_crash, event_type=Win32EventType.WINDOW_CRASH)
    bus.subscribe(on_any)

    # Ingest focus change
    bus.ingest_event(event_type=Win32EventType.FOCUS_CHANGE, window_title="Browser")
    assert len(crash_events) == 0
    assert len(all_events) == 1

    # Ingest crash
    bus.ingest_event(event_type=Win32EventType.WINDOW_CRASH, window_title="Fatal Error")
    assert len(crash_events) == 1
    assert len(all_events) == 2

    # Unsubscribe
    bus.unsubscribe(on_crash, event_type=Win32EventType.WINDOW_CRASH)
    bus.ingest_event(event_type=Win32EventType.WINDOW_CRASH, window_title="Crash 2")
    assert len(crash_events) == 1
    assert len(all_events) == 3


def test_event_bus_buffer_bounding():
    """Verify event buffer does not grow indefinitely."""
    bus = ProactiveEventBus()

    for i in range(250):
        bus.ingest_event(
            event_type=Win32EventType.BACKGROUND_MILESTONE,
            window_title=f"Milestone {i}",
        )

    status = bus.get_status()
    assert status.total_events_ingested == 250
    assert len(bus._recent_events) == 200
    assert bus._recent_events[-1].window_title == "Milestone 249"


def test_event_bus_broadcaster():
    """Verify WebSocket state broadcast callback."""
    bus = ProactiveEventBus()
    dispatched = []
    bus.register_broadcaster(lambda msg: dispatched.append(msg))

    bus.ingest_event(event_type=Win32EventType.SYSTEM_ALERT, window_title="Low Battery")
    assert len(dispatched) == 1
    assert dispatched[0]["type"] == "proactive_bus_event"
    assert dispatched[0]["payload"]["window_title"] == "Low Battery"


def test_event_bus_guardian_halt():
    """Verify Guardian halt immediately blocks ingestion."""
    bus = ProactiveEventBus()
    bus.halt()
    assert bus.is_halted() is True

    with pytest.raises(PermissionError, match="Event bus ingestion halted"):
        bus.ingest_event(event_type=Win32EventType.SYSTEM_ALERT, window_title="Test")

    bus.reset()
    assert bus.is_halted() is False
    ev = bus.ingest_event(event_type=Win32EventType.SYSTEM_ALERT, window_title="Test 2")
    assert ev.window_title == "Test 2"
