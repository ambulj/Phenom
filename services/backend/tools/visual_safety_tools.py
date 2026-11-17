"""
Phenom Visual Safety & Anti-Checkout Barrier Tool Registrations (WKF-03)
Registers:
- inspect_visual_safety_barrier (Tier 0)
- verify_anti_checkout_boundary (Tier 0)
"""

from typing import Dict, Any, Optional
from pydantic import BaseModel, Field

from services.backend.safety.registry import registry
from services.backend.safety.visual_shield import visual_safety_shield


class InspectVisualSafetyBarrierArgs(BaseModel):
    surface_text: str = Field(description="Visible text or OCR output to scan for prohibited barriers")
    window_title: Optional[str] = Field(default="", description="Active window title")


class VerifyAntiCheckoutBoundaryArgs(BaseModel):
    target_url: Optional[str] = Field(default="", description="Target URL being visited")
    page_text: Optional[str] = Field(default="", description="Visible page text or summary")


@registry.register(
    name="inspect_visual_safety_barrier",
    tier=0,
    description="Inspects active screen surface or DOM for checkout, CVV, OTP, and password barriers (<25ms SLA).",
    args_schema=InspectVisualSafetyBarrierArgs,
    preview_fn=lambda a: f"Scan screen text in '{a.get('window_title') or 'active window'}' for visual safety barriers"
)
def inspect_visual_safety_barrier(surface_text: str, window_title: Optional[str] = "") -> Dict[str, Any]:
    res = visual_safety_shield.scan_frame(surface_text, window_title or "", halt_on_violation=False)
    return res.model_dump()


@registry.register(
    name="verify_anti_checkout_boundary",
    tier=0,
    description="Verifies a target URL and page summary strictly respect Rule 8 (fill carts and stop; never checkout).",
    args_schema=VerifyAntiCheckoutBoundaryArgs,
    preview_fn=lambda a: f"Verify Rule 8 boundary for '{a.get('target_url') or 'target page'}'"
)
def verify_anti_checkout_boundary(
    target_url: Optional[str] = "",
    page_text: Optional[str] = ""
) -> Dict[str, Any]:
    combined = f"{target_url} {page_text}"
    res = visual_safety_shield.scan_frame(combined, "", halt_on_violation=False)
    return {
        "url_safe": res.safe,
        "is_checkout_or_payment": not res.safe,
        "trigger": res.trigger_term,
        "category": res.category.value if res.category else None,
        "message": (
            f"Rule 8 boundary breached: Prohibited checkout term '{res.trigger_term}' detected."
            if not res.safe else "Rule 8 boundary verified: Target is free of payment and checkout triggers."
        )
    }
