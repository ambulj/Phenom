"""
Phenom Automation & Browser Tools
Enables screen capture, browser navigation, UI automation, and cart filling behind the Safety Layer.
Tier classification:
- Tier 0: take_screenshot, inspect_window_elements, summarize_youtube
- Tier 2: browser_navigate, browser_click, browser_type, desktop_execute_plan, fill_cart
- Tier 3: checkout_pay, enter_payment_info (PERMANENTLY BLOCKED)
"""

from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field
from services.backend.safety.registry import registry
from services.backend.safety.taint import taint_tracker
from services.backend.browser.browser_controller import browser_controller
from services.backend.browser.cart_automator import cart_automator
from services.backend.browser.youtube_summarizer import youtube_summarizer
from services.backend.automation.desktop_controller import desktop_controller

# ==========================================
# Tier 0 Tools (Read-Only)
# ==========================================

class TakeScreenshotArgs(BaseModel):
    pass

@registry.register(
    name="take_screenshot",
    tier=0,
    description="Captures primary screen in-memory for local analysis (never saved to disk)",
    args_schema=TakeScreenshotArgs,
    preview_fn=lambda a: "Capture primary screen into memory for inspection"
)
async def take_screenshot() -> Dict[str, Any]:
    b64 = desktop_controller.capture_screen_base64()
    taint_tracker.mark_tainted("ocr", "Screen OCR content ingested")
    return {
        "status": "success",
        "format": "jpeg_base64",
        "image_data": b64[:100] + "...[truncated]",
        "privacy": "local_ram_only"
    }

_EASYOCR_READER = None

def _get_ocr_reader():
    global _EASYOCR_READER
    if _EASYOCR_READER is None:
        import easyocr
        import torch
        has_cuda = torch.cuda.is_available()
        _EASYOCR_READER = easyocr.Reader(['en'], gpu=has_cuda)
    return _EASYOCR_READER

class InspectScreenOcrArgs(BaseModel):
    focus_query: Optional[str] = Field(default=None, description="Optional keyword or error term to look for on screen")

@registry.register(
    name="inspect_screen_ocr",
    tier=0,
    description="Performs in-memory optical character recognition (OCR) of the current desktop screen to read text, code, or error dialogs (strictly RAM only, zero images saved to disk)",
    args_schema=InspectScreenOcrArgs,
    preview_fn=lambda a: "Inspect visible screen text via in-memory OCR"
)
async def inspect_screen_ocr(focus_query: Optional[str] = None) -> Dict[str, Any]:
    import numpy as np
    img = desktop_controller.capture_screen_ram()
    reader = _get_ocr_reader()
    arr = np.array(img)
    results = reader.readtext(arr)

    detected_texts = [text for (bbox, text, prob) in results if prob > 0.2]
    error_keywords = ["error", "exception", "failed", "traceback", "warning", "fatal", "not found", "cannot", "denied", "bug", "crash"]
    error_candidates = [t for t in detected_texts if any(k in t.lower() for k in error_keywords)]

    matched_texts = detected_texts
    if focus_query:
        q = focus_query.lower()
        matched_texts = [t for t in detected_texts if q in t.lower()]

    taint_tracker.mark_tainted("ocr", "Screen OCR content ingested")
    return {
        "status": "success",
        "total_elements_found": len(detected_texts),
        "visible_snippets": matched_texts[:15],
        "error_candidates": error_candidates[:5],
        "privacy": "in_memory_only_never_saved_to_disk"
    }

class InspectWindowElementsArgs(BaseModel):
    name_query: str = Field(description="Sub-string to search for in UI elements")

@registry.register(
    name="inspect_window_elements",
    tier=0,
    description="Inspects active window elements using Windows UI Automation",
    args_schema=InspectWindowElementsArgs,
    preview_fn=lambda a: f"Search UI elements matching: '{a.get('name_query')}'"
)
def inspect_window_elements(name_query: str) -> Optional[Dict[str, Any]]:
    return desktop_controller.find_element_by_name(name_query)

class SummarizeYouTubeArgs(BaseModel):
    url: str = Field(description="YouTube video URL to summarize")

@registry.register(
    name="summarize_youtube",
    tier=0,
    description="Extracts captions or transcribes video audio locally and summarizes",
    args_schema=SummarizeYouTubeArgs,
    preview_fn=lambda a: f"Summarize YouTube video: '{a.get('url')}'"
)
async def summarize_youtube(url: str) -> Dict[str, Any]:
    return await youtube_summarizer.summarize_video(url)

# ==========================================
# Tier 2 Tools (Interactive / Destructive)
# ==========================================

# Milestone 18: Browser actions upgraded to services.backend.tools.browser_operator_tools
from services.backend.tools.browser_operator_tools import (
    browser_navigate,
    browser_click,
    browser_type,
    BrowserNavigateArgs,
    BrowserClickArgs,
    BrowserTypeArgs
)

class DesktopExecutePlanArgs(BaseModel):
    steps: List[Dict[str, Any]] = Field(description="Ordered list of action steps")

@registry.register(
    name="desktop_execute_plan",
    tier=2,
    description="Executes a multi-step desktop automation plan with target highlighting and takeover protection",
    args_schema=DesktopExecutePlanArgs,
    preview_fn=lambda a: f"Execute {len(a.get('steps', []))} desktop automation steps: {', '.join([s.get('action', '') + ' ' + s.get('target', '') for s in a.get('steps', [])[:3]])}..."
)
async def desktop_execute_plan(steps: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    return await desktop_controller.execute_step_plan(steps)

class FillCartArgs(BaseModel):
    platform: str = Field(description="Platform: amazon, flipkart, swiggy, or zomato")
    item_query: str = Field(description="Product or food item to search and add to cart")

@registry.register(
    name="fill_cart",
    tier=2,
    description="Searches, adds item to cart, and halts at cart. Never enters payment or completes checkout.",
    args_schema=FillCartArgs,
    preview_fn=lambda a: f"Search '{a.get('item_query')}' on {a.get('platform')}, add to cart, and stop before checkout"
)
async def fill_cart(platform: str, item_query: str) -> Dict[str, Any]:
    return await cart_automator.fill_cart(platform, item_query)

# ==========================================
# Tier 3 Tools (Permanently Blocked by Safety)
# ==========================================

class CheckoutPayArgs(BaseModel):
    payment_method: str = Field(default="card")

@registry.register(
    name="checkout_pay",
    tier=3,
    description="Attempts to place an order or complete checkout. Blocked by default.",
    args_schema=CheckoutPayArgs,
    preview_fn=lambda a: "ATTEMPT TO PLACE ORDER / EXECUTE PAYMENT"
)
def checkout_pay(payment_method: str = "card"):
    raise PermissionError("Payment and order placement are strictly prohibited by SAFETY.md.")

class EnterPaymentInfoArgs(BaseModel):
    card_details: str = Field(description="Card or UPI details")

@registry.register(
    name="enter_payment_info",
    tier=3,
    description="Attempts to input payment credentials or OTP. Blocked by default.",
    args_schema=EnterPaymentInfoArgs,
    preview_fn=lambda a: "ATTEMPT TO ENTER PAYMENT CREDENTIALS"
)
def enter_payment_info(card_details: str):
    raise PermissionError("Entering card details or credentials is strictly prohibited by SAFETY.md.")


# ==========================================
# Autonomous Execution Tool (Tier 2)
# ==========================================

class ExecuteAutonomousTaskArgs(BaseModel):
    goal: str = Field(description="High-level goal or multi-step workflow intent")


def _preview_autonomous_task(args: Dict[str, Any]) -> str:
    goal = args.get("goal", "Autonomous workflow")
    try:
        from services.backend.automation.goal_planner import goal_planner
        plan = goal_planner.plan_goal(goal)
        steps_preview = "\n".join([f"  {s.step_number}. {s.description}" for s in plan.steps])
        return f"Autonomous Task Preview for '{goal}':\n{steps_preview}\n(Supervised execution with sub-second takeover pause)"
    except Exception as e:
        return f"Autonomous Task: '{goal}' (Error generating step preview: {e})"


@registry.register(
    name="execute_autonomous_task",
    tier=2,
    description="Decomposes a high-level goal into a multi-step GUI and browser workflow, executes steps continuously with live HUD telemetry and sub-second takeover pauses. Requires Tier 2 confirmation.",
    args_schema=ExecuteAutonomousTaskArgs,
    preview_fn=_preview_autonomous_task
)
async def execute_autonomous_task(goal: str) -> Dict[str, Any]:
    from services.backend.automation.goal_planner import goal_planner
    from services.backend.automation.autonomous_engine import autonomous_engine
    plan = goal_planner.plan_goal(goal)
    return await autonomous_engine.execute_plan(plan)
