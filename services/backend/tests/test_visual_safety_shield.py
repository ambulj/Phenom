"""
Unit tests for Active Visual Safety Shield & Anti-Checkout Barrier (Phase 50-03)
Tests:
1. High-frequency sub-25ms evaluation SLA benchmark (100 iterations)
2. Rule 8 payment and checkout barrier trips (CVV, Card Number, Pay Now)
3. Rule 11 credential & OTP barrier trips (Password, OTP, 2FA)
4. Rule 8 cart filling allowance ("Fill carts and stop" passes safely)
5. Anti-checkout guard emergency halt and tamper-evident audit logging
6. Tool registry verification (Tier 0 read-only safety inspection tools)
"""

import pytest
import time
from services.backend.safety.visual_shield import (
    ActiveVisualSafetyShield,
    ShieldTriggerCategory,
    VisualSafetyBarrierError,
    VisualScanResult,
    visual_safety_shield,
)
from services.backend.safety.anti_checkout_guard import (
    AntiCheckoutGuard,
    anti_checkout_guard,
)
from services.backend.safety.guardian import guardian
from services.backend.tools.visual_safety_tools import (
    inspect_visual_safety_barrier,
    verify_anti_checkout_boundary,
)
from services.backend.safety.registry import registry


def test_visual_shield_latency_benchmark_under_25ms_sla():
    """Verify 100 consecutive visual scans execute well below the 25ms hard SLA."""
    shield = ActiveVisualSafetyShield()
    sample_text = (
        "Welcome to our online store. Browse through hundreds of books, electronics, "
        "and personal accessories. Add your favorite items to the shopping cart and "
        "explore exclusive seasonal discounts available today."
    )

    latencies = []
    for _ in range(100):
        start = time.perf_counter()
        res = shield.scan_frame(sample_text, window_title="Store Catalog", halt_on_violation=False)
        lat = (time.perf_counter() - start) * 1000.0
        latencies.append(lat)
        assert res.safe is True

    avg_lat = sum(latencies) / len(latencies)
    max_lat = max(latencies)

    # SLA requirements: Mean < 5.0ms, Max < 25.0ms
    assert avg_lat < 5.0
    assert max_lat < 25.0


def test_rule_8_payment_and_checkout_triggers():
    """Verify payment and checkout terms instantly trip the visual barrier."""
    shield = ActiveVisualSafetyShield()

    triggers = [
        ("Please enter your CVV to proceed", "CVV"),
        ("Click here to Pay Now with credit card", "Pay Now"),
        ("Enter your Card Number to continue", "Card Number"),
        ("Redirecting to PayPal Checkout...", "PayPal Checkout"),
        ("Review items and Complete Purchase", "Complete Purchase"),
    ]

    for text, expected_match in triggers:
        res = shield.scan_frame(text, window_title="Payment Portal", halt_on_violation=False)
        assert res.safe is False
        assert res.violation_detected is True
        assert res.category == ShieldTriggerCategory.PAYMENT_CHECKOUT
        assert res.scan_latency_ms < 25.0

        with pytest.raises(VisualSafetyBarrierError) as exc_info:
            shield.assert_frame_safe(text, window_title="Payment Portal")
        assert exc_info.value.category == ShieldTriggerCategory.PAYMENT_CHECKOUT


def test_rule_11_password_and_otp_triggers():
    """Verify password, OTP, and 2FA credential fields trip the visual shield."""
    shield = ActiveVisualSafetyShield()

    triggers = [
        ("Please enter password for your banking account", ShieldTriggerCategory.CREDENTIAL_PASSWORD),
        ("Enter your 6-digit one-time password sent via SMS", ShieldTriggerCategory.OTP_AUTHENTICATION),
        ("Input your 2FA code from authenticator", ShieldTriggerCategory.OTP_AUTHENTICATION),
    ]

    for text, expected_cat in triggers:
        res = shield.scan_frame(text, window_title="Authentication Window", halt_on_violation=False)
        assert res.safe is False
        assert res.category == expected_cat
        assert res.scan_latency_ms < 25.0

        with pytest.raises(VisualSafetyBarrierError):
            shield.assert_frame_safe(text, window_title="Auth")


def test_rule_8_cart_filling_allowed():
    """Verify cart inspection and adding items to cart is permitted under Rule 8."""
    shield = ActiveVisualSafetyShield()

    allowed_contexts = [
        "Item added to cart successfully.",
        "Your shopping cart contains 3 items. Total: $45.99",
        "View Cart & Saved Items",
        "Shopping Bag (1)",
    ]

    for text in allowed_contexts:
        res = shield.scan_frame(text, window_title="Product Page", halt_on_violation=False)
        assert res.safe is True
        assert res.violation_detected is False


def test_anti_checkout_guard_emergency_halt_and_audit_log():
    """Verify runtime guard halts execution via Guardian and logs audit event."""
    # Ensure guardian is not halted initially
    guardian._halted = False

    guard = AntiCheckoutGuard()
    violating_text = "Billing summary: Please enter credit card number and CVV to pay now."

    with pytest.raises(VisualSafetyBarrierError):
        guard.inspect_and_guard(violating_text, window_title="Checkout Gateway", step_id="step_4")

    # Assert Guardian kill switch was triggered
    assert guardian.is_halted is True

    # Assert audit log entry created
    history = guard.get_trip_history()
    assert len(history) >= 1
    latest = history[-1]
    assert latest["category"] == ShieldTriggerCategory.PAYMENT_CHECKOUT.value
    assert latest["window_title"] == "Checkout Gateway"
    assert latest["guardian_halted"] is True

    # Clean up guardian state for following tests
    guardian._halted = False


def test_visual_safety_tool_registrations():
    """Verify tool safety registrations, tier 0 status, and boundary responses."""
    t_inspect = registry.get("inspect_visual_safety_barrier")
    assert t_inspect is not None
    assert t_inspect.tier == 0
    assert callable(t_inspect.preview_fn)
    preview = t_inspect.preview_fn({"window_title": "Store"})
    assert "Store" in preview

    # Test tool invocation directly
    res = inspect_visual_safety_barrier("View Cart (2 items)", "Store")
    assert res["safe"] is True
    assert res["violation_detected"] is False

    t_verify = registry.get("verify_anti_checkout_boundary")
    assert t_verify is not None
    assert t_verify.tier == 0

    # Clean URL
    res_clean = verify_anti_checkout_boundary("https://shop.example.com/cart", "Items in cart")
    assert res_clean["url_safe"] is True
    assert res_clean["is_checkout_or_payment"] is False

    # Violating checkout URL
    res_violating = verify_anti_checkout_boundary("https://shop.example.com/checkout", "Proceed to checkout")
    assert res_violating["url_safe"] is False
    assert res_violating["is_checkout_or_payment"] is True
    assert "checkout" in res_violating["trigger"].lower()
