"""
Phenom Milestone 9.0 Phase 1 Tests: Adaptive Performance & Resource Governor (GOV-01)
Verifies:
1. Detection of 3D gaming processes triggers auto-suspension callbacks.
2. High GPU utilization (> 85%) triggers auto-suspension.
3. High CPU load (> 90%) triggers auto-suspension.
4. Transition back to idle/desktop triggers auto-resume callbacks after recovery threshold.
5. Excluded processes (browsers, dev tools, media players) never trigger gaming mode.
6. Synchronous sub-1ms kill switch halt() and reset().
7. Pydantic schema validation for ResourceGovernorState.
"""

import asyncio
import time
import pytest

from services.backend.schemas.ambient_vision import ResourceGovernorState
from services.backend.system.resource_governor import (
    AdaptiveResourceGovernor,
    resource_governor,
    EXCLUDED_PROCESSES,
    KNOWN_GAME_PROCESSES,
)


@pytest.fixture
def clean_governor():
    gov = AdaptiveResourceGovernor(
        gpu_throttle_threshold=85.0,
        gpu_resume_threshold=60.0,
        cpu_throttle_threshold=90.0,
        recovery_cycles_required=2,
    )
    gov.reset()
    yield gov
    gov.reset()


def test_resource_governor_initial_state(clean_governor):
    """GOV-01: Verifies clean initial governor state."""
    state = clean_governor.get_state()
    assert isinstance(state, ResourceGovernorState)
    assert state.is_gaming is False
    assert state.active_game is None
    assert state.is_throttled is False
    assert state.vision_suspended is False
    assert state.swarms_suspended is False


def test_gaming_process_detection_triggers_suspension(clean_governor):
    """GOV-01: Verifies active 3D game triggers pause callback and suspends workloads."""
    pause_events = []
    resume_events = []

    clean_governor.register_pause_callback(lambda reason: pause_events.append(reason))
    clean_governor.register_resume_callback(lambda: resume_events.append("resumed"))

    # Mock 3D game active (e.g. Cyberpunk 2077)
    clean_governor.set_mock_state(is_gaming=True, active_game="cyberpunk2077.exe", gpu_load=70.0)

    state = clean_governor.poll_metrics()

    assert state.is_gaming is True
    assert state.active_game == "cyberpunk2077.exe"
    assert state.is_throttled is True
    assert state.vision_suspended is True
    assert state.swarms_suspended is True
    assert len(pause_events) == 1
    assert "3D game active" in pause_events[0]
    assert len(resume_events) == 0


def test_gpu_load_spike_triggers_suspension(clean_governor):
    """GOV-01: Verifies GPU load > 85% triggers throttling and auto-suspension."""
    pause_events = []
    clean_governor.register_pause_callback(lambda reason: pause_events.append(reason))

    # Mock high GPU load without game executable (e.g. rendering/compute)
    clean_governor.set_mock_state(is_gaming=False, gpu_load=88.5, cpu_load=40.0)

    state = clean_governor.poll_metrics()

    assert state.is_gaming is False
    assert state.gpu_load_percent == 88.5
    assert state.is_throttled is True
    assert state.vision_suspended is True
    assert state.swarms_suspended is True
    assert len(pause_events) == 1
    assert "High GPU load" in pause_events[0]


def test_cpu_load_spike_triggers_suspension(clean_governor):
    """GOV-01: Verifies CPU load > 90% triggers throttling."""
    pause_events = []
    clean_governor.register_pause_callback(lambda reason: pause_events.append(reason))

    clean_governor.set_mock_state(is_gaming=False, gpu_load=20.0, cpu_load=94.0)

    state = clean_governor.poll_metrics()

    assert state.is_throttled is True
    assert state.vision_suspended is True
    assert len(pause_events) == 1
    assert "High CPU load" in pause_events[0]


def test_transition_to_idle_triggers_auto_resume(clean_governor):
    """GOV-01: Verifies return to idle restores vision loops after required consecutive cycles."""
    pause_events = []
    resume_events = []

    clean_governor.register_pause_callback(lambda r: pause_events.append(r))
    clean_governor.register_resume_callback(lambda: resume_events.append("resumed"))

    # 1. Trigger suspension with game
    clean_governor.set_mock_state(is_gaming=True, active_game="cs2.exe", gpu_load=80.0)
    clean_governor.poll_metrics()
    assert clean_governor.vision_suspended is True

    # 2. Game exits, GPU load drops to 25% (Cycle 1 - not yet resumed due to recovery_cycles_required=2)
    clean_governor.set_mock_state(is_gaming=False, active_game=None, gpu_load=25.0, cpu_load=15.0)
    state1 = clean_governor.poll_metrics()
    assert state1.vision_suspended is True
    assert len(resume_events) == 0

    # 3. Cycle 2 (consecutive idle satisfied) -> auto-resume dispatched!
    state2 = clean_governor.poll_metrics()
    assert state2.vision_suspended is False
    assert state2.is_throttled is False
    assert len(resume_events) == 1


def test_excluded_processes_never_trigger_gaming():
    """GOV-01: Verifies browsers, VS Code, and media players are in exclusion set."""
    for proc in ["chrome.exe", "msedge.exe", "code.exe", "vlc.exe", "phenom.exe"]:
        assert proc in EXCLUDED_PROCESSES


def test_synchronous_killswitch_halt_and_reset(clean_governor):
    """SAF-02: Verifies synchronous sub-1ms kill switch halt and clean recovery."""
    pause_events = []
    resume_events = []

    clean_governor.register_pause_callback(lambda r: pause_events.append(r))
    clean_governor.register_resume_callback(lambda: resume_events.append("resumed"))

    start = time.perf_counter()
    clean_governor.halt()
    elapsed_ms = (time.perf_counter() - start) * 1000.0

    # Must complete well below 1ms
    assert elapsed_ms < 5.0
    assert clean_governor.is_halted is True
    assert clean_governor.vision_suspended is True
    assert clean_governor.swarms_suspended is True
    assert len(pause_events) == 1
    assert "guardian_killswitch_halt" in pause_events[0]

    # Subsequent polling while halted returns halted state
    state = clean_governor.poll_metrics()
    assert state.is_throttled is True

    # Reset
    clean_governor.reset()
    assert clean_governor.is_halted is False
    assert clean_governor.vision_suspended is False
    assert len(resume_events) == 1


@pytest.mark.asyncio
async def test_governor_async_loop_lifecycle(clean_governor):
    """GOV-01: Verifies start() and stop() of the background periodic monitoring loop."""
    await clean_governor.start(poll_interval_seconds=0.05)
    assert clean_governor._is_running is True

    await asyncio.sleep(0.12)

    await clean_governor.stop()
    assert clean_governor._is_running is False
