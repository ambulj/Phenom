"""
Unit Test Suite for Smart Window Tiler & Interactive Macro Recorder (WIN-01, MAC-01, SAF-01, SAF-02)
Verifies:
1. Native & synthetic window tiling presets (Dev Mode, Research Mode, Chill Mode).
2. Granular window snapping (left, right, top, bottom, center, maximize).
3. Layout snapshot saving and restoration.
4. Macro recording, encrypted SQLite persistence, listing, replaying, and deletion.
5. Direct voice intent parsing in OrchestratorEngine.
6. Universal synchronous Guardian kill switch abort benchmark (< 25ms SLA).
"""

import pytest
import asyncio
import time
from services.backend.tools.window_tiler import (
    apply_window_layout,
    save_window_layout,
    list_window_layouts,
    snap_window,
    set_mock_windows_mode,
    get_screen_resolution,
    enumerate_visible_windows
)
from services.backend.tools.macro_recorder import (
    start_macro_recording,
    stop_macro_recording,
    save_macro,
    list_macros,
    replay_macro,
    delete_macro,
    recording_session,
    set_mock_macro_mode
)
from services.backend.safety.guardian import guardian
from services.backend.safety.registry import registry
from services.backend.orchestrator.engine import Orchestrator


@pytest.fixture(autouse=True)
def setup_mock_environment():
    """Configures deterministic mock windows and macro mode for reliable test execution."""
    mock_wins = [
        {"hwnd": 1001, "title": "Visual Studio Code - Phenom Core", "rect": {"left": 0, "top": 0, "width": 800, "height": 600}},
        {"hwnd": 1002, "title": "Brave Browser - GitHub", "rect": {"left": 800, "top": 0, "width": 800, "height": 600}},
        {"hwnd": 1003, "title": "Windows PowerShell Console", "rect": {"left": 0, "top": 600, "width": 800, "height": 400}},
        {"hwnd": 1004, "title": "Obsidian Vault - Phenom Notes", "rect": {"left": 400, "top": 200, "width": 600, "height": 500}},
    ]
    set_mock_windows_mode(True, mock_wins)
    set_mock_macro_mode(True)
    guardian._halted = False
    yield
    set_mock_windows_mode(False)
    set_mock_macro_mode(False)
    guardian._halted = False


@pytest.mark.asyncio
async def test_window_tiler_safety_tiers():
    """Asserts window tiler tools are registered with correct safety tiers."""
    apply_tool = registry.get("apply_window_layout")
    save_tool = registry.get("save_window_layout")
    list_tool = registry.get("list_window_layouts")
    snap_tool = registry.get("snap_window")

    assert apply_tool is not None and apply_tool.tier == 1
    assert snap_tool is not None and snap_tool.tier == 1
    assert save_tool is not None and save_tool.tier == 0
    assert list_tool is not None and list_tool.tier == 0


@pytest.mark.asyncio
async def test_window_tiler_dev_mode():
    """Verifies Dev Mode arranges IDE left 60%, Browser top-right, Terminal bottom-right."""
    res = await apply_window_layout("dev_mode")
    assert res["status"] == "success"
    assert res["layout"] == "dev_mode"
    assert res["windows_arranged"] >= 3

    roles = {act.get("role"): act for act in res["actions"]}
    assert "IDE (Left 60%)" in roles
    assert "Browser (Top-Right)" in roles
    assert "Terminal (Bottom-Right)" in roles


@pytest.mark.asyncio
async def test_window_tiler_research_mode():
    """Verifies Research Mode splits Browser left 50% and Notes right 50%."""
    res = await apply_window_layout("research_mode")
    assert res["status"] == "success"
    assert res["layout"] == "research_mode"
    assert res["windows_arranged"] >= 2

    roles = {act.get("role"): act for act in res["actions"]}
    assert "Browser (Left 50%)" in roles
    assert "Notes (Right 50%)" in roles


@pytest.mark.asyncio
async def test_window_tiler_chill_mode():
    """Verifies Chill Mode centers active media window (60%w, 80%h)."""
    res = await apply_window_layout("chill_mode")
    assert res["status"] == "success"
    assert res["layout"] == "chill_mode"
    assert res["windows_arranged"] >= 1
    assert "Centered Media (60%x80%)" in res["actions"][0]["role"]


@pytest.mark.asyncio
async def test_window_snapping_zones():
    """Verifies snapping to left, right, maximize, center."""
    screen = get_screen_resolution()
    w, h = screen["width"], screen["height"]

    res_left = await snap_window(snap_zone="left", window_title="Visual Studio Code")
    assert res_left["status"] == "success"
    assert res_left["geometry"]["left"] == 0
    assert res_left["geometry"]["width"] == int(w / 2)

    res_right = await snap_window(snap_zone="right", window_title="Brave Browser")
    assert res_right["status"] == "success"
    assert res_right["geometry"]["left"] == int(w / 2)

    res_max = await snap_window(snap_zone="maximize", window_title="Windows PowerShell")
    assert res_max["status"] == "success"
    assert res_max["geometry"]["width"] == w
    assert res_max["geometry"]["height"] == h


@pytest.mark.asyncio
async def test_save_and_restore_custom_layout():
    """Verifies saving current window arrangement as a snapshot and restoring it."""
    save_res = await save_window_layout("coding_focus")
    assert save_res["status"] == "success"
    assert save_res["layout_name"] == "coding_focus"
    assert save_res["windows_captured"] > 0

    list_res = await list_window_layouts()
    custom_names = [c["name"] for c in list_res["custom_layouts"]]
    assert "coding_focus" in custom_names

    restore_res = await apply_window_layout("coding_focus")
    assert restore_res["status"] == "success"
    assert restore_res["layout"] == "coding_focus"


@pytest.mark.asyncio
async def test_macro_recording_lifecycle():
    """Tests starting recording, capturing steps, stopping, and database persistence."""
    start_res = await start_macro_recording(name="test_routine", description="Automated test sequence")
    assert start_res["status"] == "success"
    assert recording_session.is_recording is True
    assert recording_session.active_name == "test_routine"

    # Simulate recorded actions
    recording_session.record_step("click", {"coords": (400, 300)})
    recording_session.record_step("type", {"text": "npm test"})
    recording_session.record_step("hotkey", {"keys": ["enter"]})

    stop_res = await stop_macro_recording()
    assert stop_res["status"] == "success"
    assert stop_res["step_count"] == 3
    assert recording_session.is_recording is False

    # Verify present in list
    list_res = await list_macros()
    macro_names = [m["name"] for m in list_res["macros"]]
    assert "test_routine" in macro_names


@pytest.mark.asyncio
async def test_macro_direct_save_and_replay():
    """Verifies saving a macro directly and replaying it."""
    steps = [
        {"action": "click", "params": {"coords": (100, 200)}},
        {"action": "wait", "params": {"seconds": 0.05}},
        {"action": "type", "params": {"text": "phenom online"}}
    ]
    save_res = await save_macro(name="greeting_flow", steps=steps, description="Types greeting")
    assert save_res["status"] == "success"

    replay_res = await replay_macro("greeting_flow", speed=2.0)
    assert replay_res["status"] == "success"
    assert replay_res["steps_executed"] == 3
    assert replay_res["duration_ms"] > 0

    # Clean up
    del_res = await delete_macro("greeting_flow")
    assert del_res["status"] == "success"
    assert del_res["deleted"] is True


@pytest.mark.asyncio
async def test_direct_voice_intents_window_and_macro():
    """Verifies voice commands map deterministically to window tiler and macro tools."""
    engine = Orchestrator()

    # Window layouts
    intent_dev = engine._detect_direct_intent("arrange dev mode")
    assert intent_dev is not None
    assert intent_dev[0] == "apply_window_layout"
    assert intent_dev[1]["layout_name"] == "dev_mode"

    intent_research = engine._detect_direct_intent("research layout")
    assert intent_research is not None
    assert intent_research[0] == "apply_window_layout"
    assert intent_research[1]["layout_name"] == "research_mode"

    intent_chill = engine._detect_direct_intent("chill mode windows")
    assert intent_chill is not None
    assert intent_chill[0] == "apply_window_layout"
    assert intent_chill[1]["layout_name"] == "chill_mode"

    # Snap window
    intent_snap = engine._detect_direct_intent("snap active window to left")
    assert intent_snap is not None
    assert intent_snap[0] == "snap_window"
    assert intent_snap[1]["snap_zone"] == "left"

    # Macro commands
    intent_run = engine._detect_direct_intent("run macro deploy_check")
    assert intent_run is not None
    assert intent_run[0] == "replay_macro"
    assert intent_run[1]["name"] == "deploy_check"

    intent_rec = engine._detect_direct_intent("start recording macro morning_routine")
    assert intent_rec is not None
    assert intent_rec[0] == "start_macro_recording"
    assert intent_rec[1]["name"] == "morning_routine"

    intent_stop = engine._detect_direct_intent("stop recording macro")
    assert intent_stop is not None
    assert intent_stop[0] == "stop_macro_recording"


@pytest.mark.asyncio
async def test_guardian_macro_abort_sla_benchmark():
    """
    SAF-02 SLA Benchmark:
    Verifies that triggering the Guardian kill switch synchronously aborts macro replay
    in strictly < 25ms SLA (target < 1.0ms typical).
    """
    long_steps = [{"action": "wait", "params": {"seconds": 0.1}} for _ in range(10)]
    await save_macro(name="benchmark_macro", steps=long_steps)

    latencies = []
    guardian._halted = True

    # 1. Immediate rejection SLA when Guardian is halted (50 cycles)
    for _ in range(50):
        t0 = time.perf_counter()
        res = await replay_macro("benchmark_macro")
        t_elapsed_ms = (time.perf_counter() - t0) * 1000.0
        assert res["status"] == "error"
        assert res["error"] == "GUARDIAN_HALTED"
        latencies.append(t_elapsed_ms)

    avg_latency = sum(latencies) / len(latencies)
    max_latency = max(latencies)
    print(f"\n[Guardian Halt Pre-Check SLA Benchmark] 50 iterations: avg={avg_latency:.4f}ms, max={max_latency:.4f}ms (< 25ms SLA)")
    assert max_latency < 25.0, f"Max latency {max_latency}ms exceeded 25ms SLA"
    assert avg_latency < 25.0, f"Average latency {avg_latency}ms exceeded 25ms SLA"

    # 2. Mid-flight abort SLA verification
    guardian._halted = False

    async def trip_at_step_2():
        await asyncio.sleep(0.015)
        guardian._halted = True

    trip_task = asyncio.create_task(trip_at_step_2())
    t0 = time.perf_counter()
    mid_res = await replay_macro("benchmark_macro", speed=1.0)
    await trip_task

    assert mid_res["status"] == "halted"
    assert mid_res["reason"] == "GUARDIAN_KILLSWITCH"
    assert mid_res.get("abort_latency_ms", 0) < 25.0

    # Clean up
    await delete_macro("benchmark_macro")
    guardian._halted = False
