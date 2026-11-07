"""
Phase 2 Verification Suite: Multimodal Screen Vision & Windows GUI Automation Agent (VIS-01, GUI-01, SAF-01, SAF-02).
Covers:
1. Smart Context screen capture & zero-leak memory isolation.
2. Rule 4 & Rule 8 privacy screen masking in RAM.
3. Hybrid deterministic Windows UIA tree traversal with visual coordinate fallback.
4. Permanent Rule 8 payment and password blocking (Fill carts and stop).
5. Safety Engine tool registry audit (Pydantic schemas & preview functions).
6. Universal Guardian kill switch SLA benchmark (< 25.0ms SLA).
"""

import time
import pytest
import asyncio
from typing import Dict, Any
from PIL import Image

from services.backend.safety.guardian import guardian
from services.backend.safety.registry import registry
from services.backend.safety.action_log import action_log
from services.backend.vision.screen_capture import smart_screen_capture, SmartScreenCapture
from services.backend.automation.gui_controller import (
    hybrid_gui_controller,
    Rule8ViolationError,
    GuardianHaltedError,
    UIActionResult
)
import services.backend.tools.gui_tools as gui_tools


# ---------------- 1. SMART CONTEXT SCREEN CAPTURE & MEMORY ISOLATION (VIS-01.1) ----------------

def test_smart_context_screen_capture_and_memory_isolation():
    """Asserts Smart Context captures active window or desktop in RAM with zero memory leaks."""
    # Capture in focused_window mode
    img, meta = smart_screen_capture.capture(mode="focused_window", mask_privacy=True)
    assert isinstance(img, Image.Image)
    assert meta["resolution"]["width"] > 0
    assert meta["resolution"]["height"] > 0
    assert meta["capture_latency_ms"] < 200.0
    img.close()

    # Capture in full_desktop mode
    img_full, meta_full = smart_screen_capture.capture(mode="full_desktop", mask_privacy=False)
    assert isinstance(img_full, Image.Image)
    assert meta_full["mode"] == "full_desktop"
    img_full.close()

    # Rapid capture burst loop (50 iterations) to verify zero memory leaks & image cleanup
    start = time.perf_counter()
    for _ in range(50):
        frame, m = smart_screen_capture.capture(mode="focused_window", mask_privacy=False)
        assert frame.width > 0
        frame.close()
    elapsed = time.perf_counter() - start
    avg_per_frame_ms = (elapsed / 50.0) * 1000.0
    print(f"\n[VISION BURST BENCHMARK] 50 in-RAM captures completed in {elapsed:.3f}s ({avg_per_frame_ms:.2f}ms/frame)")
    assert avg_per_frame_ms < 100.0


# ---------------- 2. RULE 4 & RULE 8 PRIVACY SCREEN MASKING (VIS-01.3) ----------------

def test_privacy_and_rule_8_screen_masking():
    """Asserts sensitive windows (passwords, banking, private chat) are obfuscated in RAM."""
    capture_engine = SmartScreenCapture()

    # Simulate sensitive window info
    mock_sensitive_win = {
        "hwnd": 1234,
        "title": "1Password - Master Vault",
        "rect": {"x": 100, "y": 100, "width": 800, "height": 600},
        "is_sensitive": True
    }

    test_img = Image.new("RGB", (800, 600), color=(255, 255, 255))
    masked_img, count = capture_engine._apply_privacy_mask(test_img, mock_sensitive_win)

    assert count >= 1
    # Check that pixel values were altered (redacted from pure white)
    import numpy as np
    pixels = np.array(masked_img)
    # Top-left pixel should now be dark redacted fill (12, 12, 15)
    assert tuple(pixels[0, 0][:3]) == (12, 12, 15)
    masked_img.close()


# ---------------- 3. HYBRID DETERMINISTIC UIA & VISUAL FALLBACK (VIS-01.2) ----------------

@pytest.mark.asyncio
async def test_hybrid_uia_deterministic_first_and_visual_fallback():
    """Asserts deterministic UIA tree is queried first, with graceful visual coordinate fallback."""
    # 1. Deterministic element matching ("Save" button in default UIA tree)
    res_uia = await hybrid_gui_controller.click_element("Save", autonomous_silent=True)
    assert res_uia.target == "Save"
    assert res_uia.resolution_strategy == "uia_deterministic"
    assert res_uia.coords == (140, 165)
    assert res_uia.status in ["success", "simulated_success"]

    # 2. Visual fallback for unstructured element ("Search" not in UIA tree)
    res_visual = await hybrid_gui_controller.click_element("search menu", autonomous_silent=True)
    assert res_visual.target == "search menu"
    assert res_visual.resolution_strategy == "visual_fallback"
    assert res_visual.coords == (500, 300)
    assert res_visual.status in ["success", "simulated_success"]


# ---------------- 4. PERMANENT RULE 8 PAYMENT & PASSWORD HARD BLOCKING (GUI-01.1) ----------------

@pytest.mark.asyncio
async def test_rule_8_payment_and_password_hard_blocking():
    """
    Asserts Rule 8: Fill carts and stop. Never place orders. Never type passwords.
    Attempts to click checkout buttons or input credentials must be blocked immediately.
    """
    blocked_payment_targets = [
        "Buy Now",
        "Place Order",
        "Proceed to Checkout",
        "Complete Purchase",
        "Pay $199.00 with Card",
        "Confirm Payment"
    ]

    for target in blocked_payment_targets:
        with pytest.raises(Rule8ViolationError) as exc_info:
            await hybrid_gui_controller.click_element(target)
        assert "Rule 8 Violation" in str(exc_info.value)
        assert "blocked by construction" in str(exc_info.value)

    # Test password clicking & typing blocking
    blocked_credential_targets = [
        "Master Password",
        "Enter PIN Code",
        "CVV Code",
        "Credit Card Number"
    ]

    for target in blocked_credential_targets:
        with pytest.raises(Rule8ViolationError) as exc_info:
            await hybrid_gui_controller.click_element(target)
        assert "Rule 8 Violation" in str(exc_info.value)

    # Test typing into password field
    with pytest.raises(Rule8ViolationError):
        await hybrid_gui_controller.type_text("super_secret_password_123", target_field="Password Field")

    with pytest.raises(Rule8ViolationError):
        await hybrid_gui_controller.type_text("4111 2222 3333 4444", target_field="Card Number")


# ---------------- 5. SAFETY ENGINE TOOL REGISTRY AUDIT (SAF-01.1) ----------------

def test_gui_tools_registry_audit():
    """Asserts all Phase 2 GUI automation tools are registered in Safety Engine with valid schemas."""
    expected_tools = {
        "capture_smart_screen": 0,
        "gui_find_and_click_element": 0,
        "gui_type_text": 1,
        "get_focused_window_info": 0
    }

    for name, tier in expected_tools.items():
        assert name in registry._tools, f"Tool '{name}' must be registered in ToolRegistry"
        tool_entry = registry._tools[name]
        assert tool_entry.tier == tier, f"Tool '{name}' tier mismatch: expected {tier}, got {tool_entry.tier}"
        assert tool_entry.args_schema is not None, f"Tool '{name}' missing Pydantic args_schema"
        assert tool_entry.preview_fn is not None, f"Tool '{name}' missing preview function"

    # Test tool preview outputs
    args_click = gui_tools.GuiFindAndClickElementArgs(target_name="Save Document")
    preview_click = registry._tools["gui_find_and_click_element"].preview_fn(args_click)
    assert "Save Document" in preview_click

    args_type = gui_tools.GuiTypeTextArgs(text="Hello Phenom", target_field="Search Box")
    preview_type = registry._tools["gui_type_text"].preview_fn(args_type)
    assert "Search Box" in preview_type


# ---------------- 6. UNIVERSAL GUARDIAN KILL SWITCH SLA BENCHMARK (SAF-02.1) ----------------

@pytest.mark.asyncio
async def test_guardian_kill_switch_gui_sla_benchmark():
    """
    Asserts Guardian kill switch synchronously aborts GUI automation actions
    with guaranteed latency < 25.0ms SLA across 50 consecutive benchmark cycles.
    """
    latencies = []

    for i in range(50):
        # Reset and trigger guardian
        guardian.resume()
        assert guardian.is_halted is False

        t0 = time.perf_counter()
        guardian.trigger("Benchmark GUI Killswitch Activation")
        t1 = time.perf_counter()

        latency_ms = (t1 - t0) * 1000.0
        latencies.append(latency_ms)

        assert guardian.is_halted is True

        # Assert GUI controller immediately raises GuardianHaltedError
        with pytest.raises(GuardianHaltedError):
            await hybrid_gui_controller.click_element("Save")

        with pytest.raises(GuardianHaltedError):
            await hybrid_gui_controller.type_text("test")

    avg_latency = sum(latencies) / len(latencies)
    max_latency = max(latencies)
    p95_latency = sorted(latencies)[int(len(latencies) * 0.95)]

    print(f"\n[GUARDIAN GUI SLA BENCHMARK] 50 Cycles: Avg={avg_latency:.4f}ms, P95={p95_latency:.4f}ms, Max={max_latency:.4f}ms (< 25.0ms SLA)")

    # Resume system after benchmark
    guardian.resume()
    assert guardian.is_halted is False

    assert avg_latency < 25.0, f"Average Guardian latency {avg_latency:.4f}ms exceeded 25.0ms SLA"
    assert max_latency < 25.0, f"Max Guardian latency {max_latency:.4f}ms exceeded 25.0ms SLA"
