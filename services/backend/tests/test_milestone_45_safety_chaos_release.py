"""Master Safety Audit, Chaos Concurrency Battery & Release Verification (Milestone 45.0 Phase 5)."""

import concurrent.futures
import time
import pytest
from services.backend.actions.synthetic_input import synthetic_input
from services.backend.actions.uia_driver import uia_driver, UIElementNode, UIRect
from services.backend.actions.visual_grounder import visual_grounder, Rule8ViolationError
from services.backend.safety.guardian import guardian
from services.backend.schemas.computer_use import (
    ActionSequencePayload,
    ClickAction,
    Point2D,
    TypeAction,
)
from services.backend.tools.computer_use_tools import (
    handle_execute_desktop_click,
    handle_execute_desktop_keystrokes,
    handle_resolve_visual_target_coordinates,
)


@pytest.fixture(autouse=True)
def clean_guardian_state():
    """Ensure guardian and synthetic input are clean before and after each test."""
    guardian.resume()
    synthetic_input.dry_run = True
    synthetic_input.recorded_events.clear()
    yield
    guardian.resume()
    synthetic_input.dry_run = False


def test_100_cycle_guardian_kill_switch_sla_under_input_load():
    """Executes 100 consecutive Guardian kill switch cycles under active input sequence load.
    Hard SLA: max latency strictly < 25.0 ms (Rule 3).
    """
    latencies = []
    payload = ActionSequencePayload(
        actions=[
            ClickAction(target=Point2D(x=100, y=100)),
            TypeAction(text="phenom autonomous action test"),
        ]
    )

    for i in range(100):
        guardian.resume()
        assert guardian.is_halted is False

        # Measure synchronous trigger latency
        t0 = time.perf_counter()
        guardian.trigger(f"Milestone 45 Guardian SLA Benchmark Cycle {i}")
        trigger_elapsed_ms = (time.perf_counter() - t0) * 1000.0

        assert guardian.is_halted is True
        latencies.append(trigger_elapsed_ms)

        # Verify synthetic input immediately refuses execution
        result = synthetic_input.execute_sequence(payload)
        assert result.success is False
        assert result.guardian_halted is True

    max_lat = max(latencies)
    avg_lat = sum(latencies) / len(latencies)

    assert max_lat < 25.0, f"Guardian kill switch SLA breached: max={max_lat:.3f}ms >= 25.0ms"
    assert avg_lat < 5.0, f"Average trigger latency unusually high: {avg_lat:.3f}ms"


def test_50_worker_action_chaos_concurrency():
    """Stress tests the Action Agent with 50 concurrent worker threads executing 500 operations.
    Validates re-entrancy, zero deadlocks, and zero unhandled exceptions.
    """
    # Seed mock UIA tree
    sample_tree = [
        UIElementNode(
            name="Main Window",
            automation_id="main_win",
            control_type="Window",
            class_name="WindowClass",
            rect=UIRect(left=0, top=0, right=1920, bottom=1080),
            children=[
                UIElementNode(
                    name="Submit Code",
                    automation_id="btn_submit",
                    control_type="Button",
                    class_name="ButtonClass",
                    rect=UIRect(left=500, top=300, right=600, bottom=340),
                    supports_invoke=True,
                )
            ]
        )
    ]
    uia_driver.set_mock_tree(sample_tree)

    def worker_task(worker_id: int) -> int:
        success_count = 0
        for cycle in range(10):
            op = (worker_id + cycle) % 5

            if op == 0:
                # Synthetic input sequence
                payload = ActionSequencePayload(
                    actions=[
                        ClickAction(target=Point2D(x=100 + cycle, y=200 + cycle)),
                    ]
                )
                res = synthetic_input.execute_sequence(payload)
                if res.success:
                    success_count += 1
            elif op == 1:
                # UIA search
                elems = uia_driver.find_elements(control_type="Button")
                if len(elems) > 0:
                    success_count += 1
            elif op == 2:
                # Grounding resolve
                pt, layer, _ = visual_grounder.resolve_target("settings gear icon", allow_cloud_escalation=True)
                if pt is not None:
                    success_count += 1
            elif op == 3:
                # Tool click
                c_res = handle_execute_desktop_click(target_x=200, target_y=300)
                if c_res["success"]:
                    success_count += 1
            elif op == 4:
                # Tool keystrokes
                t_res = handle_execute_desktop_keystrokes(text=f"worker_{worker_id}_cmd")
                if t_res["success"]:
                    success_count += 1

        return success_count

    with concurrent.futures.ThreadPoolExecutor(max_workers=50) as executor:
        futures = [executor.submit(worker_task, w_id) for w_id in range(50)]
        results = [f.result(timeout=15.0) for f in futures]

    assert len(results) == 50
    total_successful_ops = sum(results)
    assert total_successful_ops == 500, f"Expected 500 successful ops, got {total_successful_ops}"


def test_anti_checkout_tamper_resistance_rule_8():
    """Verifies that all variations of checkout / payment terms are blocked under Rule 8."""
    forbidden_terms = [
        "CHECKOUT",
        "  Buy Now  ",
        "complete purchase",
        "pay with credit card",
        "submit order and CVV",
        "place order",
    ]

    for term in forbidden_terms:
        # Direct grounder check
        with pytest.raises(Rule8ViolationError):
            visual_grounder.resolve_target(term)

        # Tool-level check
        tool_res = handle_resolve_visual_target_coordinates(query=term)
        assert tool_res["success"] is False
        assert tool_res.get("rule_8_violation") is True
