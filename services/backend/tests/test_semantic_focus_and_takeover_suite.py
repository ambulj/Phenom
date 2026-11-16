"""Comprehensive Test Suite for Multi-App Semantic Focus & Human Takeover (Milestone 49 Phase 3).

Covers:
- GUI-01: WindowContext tracking, process name, PID, title, and bounding box rects.
- GUI-02: Pre-action SemanticFocusGuard verification (title, PID, proc name, bounds, minimized checks).
- GUI-03: Low-level human takeover hook (< 10ms SLA on > 15px displacement) & Rule 8/5 anti-checkout shield.
- Safety: Guardian kill switch SLA benchmark (< 25ms).
- ToolRegistry: Tier 0 verification for focus tools.
"""

import time
import pytest

from services.backend.schemas.semantic_focus import (
    BoundingRect,
    FocusVerificationRequest,
    FocusVerificationResult,
    TakeoverEvent,
    UIAElementDescriptor,
    WindowContext,
)
from services.backend.desktop.window_focus_tracker import WindowFocusTracker
from services.backend.desktop.semantic_focus_guard import SemanticFocusGuard
from services.backend.desktop.human_takeover_hook import HumanTakeoverHook
from services.backend.desktop.anti_checkout_shield import AntiCheckoutShield
from services.backend.memory.temporal_graph_engine import Rule8ViolationError
from services.backend.safety.guardian import guardian
from services.backend.safety.registry import registry
from services.backend.tools.semantic_focus_tools import (
    handle_check_anti_checkout_boundary,
    handle_get_active_window_context,
    handle_verify_window_focus,
)


@pytest.fixture
def mock_desktop_env():
    tracker = WindowFocusTracker()
    guard = SemanticFocusGuard(tracker=tracker)
    hook = HumanTakeoverHook()
    shield = AntiCheckoutShield()

    simulated_ctx = WindowContext(
        hwnd=4096,
        title="Phenom - Visual Studio Code",
        process_name="Code.exe",
        pid=1234,
        bounding_rect=BoundingRect(left=100, top=100, right=1100, bottom=900),
        is_minimized=False,
    )
    tracker.set_simulated_window(simulated_ctx)

    return {
        "tracker": tracker,
        "guard": guard,
        "hook": hook,
        "shield": shield,
        "ctx": simulated_ctx,
    }


# ============================================================================
# 1. BoundingRect & Schema Tests (GUI-01)
# ============================================================================

def test_bounding_rect_containment_and_dimensions():
    rect = BoundingRect(left=50, top=50, right=250, bottom=350)
    assert rect.width == 200
    assert rect.height == 300

    # Inside
    assert rect.contains(50, 50) is True
    assert rect.contains(150, 200) is True
    assert rect.contains(250, 350) is True

    # Outside
    assert rect.contains(49, 100) is False
    assert rect.contains(100, 40) is False
    assert rect.contains(251, 100) is False
    assert rect.contains(100, 351) is False


# ============================================================================
# 2. Window Focus Tracker & Context Retrieval (GUI-01)
# ============================================================================

def test_window_focus_tracker_retrieval(mock_desktop_env):
    tracker: WindowFocusTracker = mock_desktop_env["tracker"]
    active = tracker.get_active_window()
    assert active.hwnd == 4096
    assert "Visual Studio Code" in active.title
    assert active.process_name == "Code.exe"
    assert active.pid == 1234
    assert active.is_minimized is False


# ============================================================================
# 3. Semantic Focus Guard Pre-Action Assertions (GUI-02)
# ============================================================================

def test_semantic_focus_guard_passing_case(mock_desktop_env):
    guard: SemanticFocusGuard = mock_desktop_env["guard"]

    req = FocusVerificationRequest(
        expected_title_contains="Visual Studio Code",
        expected_pid=1234,
        expected_process_name="Code.exe",
        target_coordinates=(500, 400),
        action_type="CLICK",
    )
    result = guard.verify_focus(req)
    assert result.is_valid is True
    assert result.error_reason is None
    assert result.latency_ms < 10.0


def test_semantic_focus_guard_title_mismatch(mock_desktop_env):
    guard: SemanticFocusGuard = mock_desktop_env["guard"]

    req = FocusVerificationRequest(
        expected_title_contains="Google Chrome",
        action_type="CLICK",
    )
    result = guard.verify_focus(req)
    assert result.is_valid is False
    assert "Window title mismatch" in result.error_reason


def test_semantic_focus_guard_pid_mismatch(mock_desktop_env):
    guard: SemanticFocusGuard = mock_desktop_env["guard"]

    req = FocusVerificationRequest(
        expected_pid=9999,
        action_type="TYPE",
    )
    result = guard.verify_focus(req)
    assert result.is_valid is False
    assert "PID mismatch" in result.error_reason


def test_semantic_focus_guard_out_of_bounds_click(mock_desktop_env):
    guard: SemanticFocusGuard = mock_desktop_env["guard"]

    # Target point (50, 50) is outside window (left=100, top=100)
    req = FocusVerificationRequest(
        target_coordinates=(50, 50),
        action_type="CLICK",
    )
    result = guard.verify_focus(req)
    assert result.is_valid is False
    assert "outside active window" in result.error_reason


def test_semantic_focus_guard_minimized_window(mock_desktop_env):
    tracker: WindowFocusTracker = mock_desktop_env["tracker"]
    guard: SemanticFocusGuard = mock_desktop_env["guard"]

    # Set window to minimized
    minimized_ctx = WindowContext(
        hwnd=4096,
        title="Phenom - Visual Studio Code",
        process_name="Code.exe",
        pid=1234,
        bounding_rect=BoundingRect(left=0, top=0, right=0, bottom=0),
        is_minimized=True,
    )
    tracker.set_simulated_window(minimized_ctx)

    req = FocusVerificationRequest(expected_title_contains="Visual Studio Code")
    result = guard.verify_focus(req)
    assert result.is_valid is False
    assert "is minimized" in result.error_reason


# ============================================================================
# 4. Human Takeover Detection & Sub-10ms SLA (GUI-03)
# ============================================================================

def test_human_takeover_detection_and_sla(mock_desktop_env):
    hook: HumanTakeoverHook = mock_desktop_env["hook"]

    takeover_events: list[TakeoverEvent] = []
    hook.register_callback(lambda ev: takeover_events.append(ev))

    # Start automation at (500, 500)
    hook.start_monitoring((500, 500))

    # 1. Micro-jitter (3px) should NOT trigger takeover
    ev1 = hook.check_takeover((502, 501))
    assert ev1 is None
    assert len(takeover_events) == 0

    # 2. Significant physical displacement (50px move to 550, 500) MUST trigger takeover
    t0 = time.perf_counter()
    ev2 = hook.check_takeover((550, 500))
    t1 = time.perf_counter()

    detect_latency_ms = (t1 - t0) * 1000.0

    assert ev2 is not None
    assert ev2.displacement_px >= 50.0
    assert detect_latency_ms < 10.0, f"Takeover detection latency {detect_latency_ms:.3f}ms exceeded 10.0ms SLA"
    assert len(takeover_events) == 1
    assert takeover_events[0].event_id == ev2.event_id


# ============================================================================
# 5. Anti-Checkout & Trading Shield (GUI-03)
# ============================================================================

def test_anti_checkout_shield_blocks_payment_screens(mock_desktop_env):
    shield: AntiCheckoutShield = mock_desktop_env["shield"]

    # Title check
    with pytest.raises(Rule8ViolationError, match="Rule 8 Violation"):
        shield.inspect_window_title("Amazon.com - Checkout & Payment Step 2")

    with pytest.raises(Rule8ViolationError, match="Rule 8 Violation"):
        shield.inspect_window_title("Robinhood - Place Order (Buy Order)")

    # UIA Element check
    elem = UIAElementDescriptor(
        automation_id="btn_complete_purchase",
        name="Complete Purchase ($49.99)",
        control_type="Button",
    )
    with pytest.raises(Rule8ViolationError, match="Rule 8 Violation"):
        shield.inspect_element(elem)

    # Normal development window should pass
    safe_ctx = WindowContext(
        hwnd=1001,
        title="Phenom Repository - GitHub Pull Requests",
        process_name="chrome.exe",
        pid=5555,
        bounding_rect=BoundingRect(left=0, top=0, right=1920, bottom=1080),
    )
    assert shield.is_safe_context(safe_ctx) is True


# ============================================================================
# 6. Guardian Kill Switch SLA Benchmark (< 25.0ms)
# ============================================================================

def test_guardian_kill_switch_sla_focus(mock_desktop_env):
    guard: SemanticFocusGuard = mock_desktop_env["guard"]
    req = FocusVerificationRequest(expected_title_contains="Code")

    durations_ms = []
    for _ in range(100):
        t0 = time.perf_counter()
        guardian._halted = True
        try:
            guard.verify_focus(req)
        except PermissionError:
            pass
        finally:
            guardian._halted = False
        t1 = time.perf_counter()
        durations_ms.append((t1 - t0) * 1000.0)

    max_ms = max(durations_ms)
    avg_ms = sum(durations_ms) / len(durations_ms)

    assert max_ms < 25.0, f"Guardian SLA exceeded: max={max_ms:.3f}ms"
    assert avg_ms < 5.0, f"Guardian SLA avg too high: {avg_ms:.3f}ms"


# ============================================================================
# 7. ToolRegistry Registrations & Handlers
# ============================================================================

def test_semantic_focus_tool_registrations():
    tool_verify = registry.get("verify_window_focus")
    assert tool_verify is not None
    assert tool_verify.tier == 0

    tool_active = registry.get("get_active_window_context")
    assert tool_active is not None
    assert tool_active.tier == 0

    tool_checkout = registry.get("check_anti_checkout_boundary")
    assert tool_checkout is not None
    assert tool_checkout.tier == 0


def test_semantic_focus_tool_handlers_execution():
    # 1. Active window context
    ctx = handle_get_active_window_context()
    assert "title" in ctx
    assert "pid" in ctx

    # 2. Focus verification
    res_verify = handle_verify_window_focus(expected_title_contains=ctx["title"])
    assert res_verify["status"] == "success"
    assert res_verify["is_valid"] is True

    # 3. Anti-checkout check safe
    res_safe = handle_check_anti_checkout_boundary(window_title="Development Workspace")
    assert res_safe["status"] == "safe"
    assert res_safe["is_safe"] is True

    # 4. Anti-checkout check blocked
    res_blocked = handle_check_anti_checkout_boundary(window_title="Stripe Payment Checkout Portal")
    assert res_blocked["status"] == "blocked"
    assert res_blocked["is_safe"] is False
