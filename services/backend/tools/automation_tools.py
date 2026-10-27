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
    return {
        "status": "success",
        "format": "jpeg_base64",
        "image_data": b64[:100] + "...[truncated]",
        "privacy": "local_ram_only"
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

class BrowserNavigateArgs(BaseModel):
    url: str = Field(description="URL to navigate to")

@registry.register(
    name="browser_navigate",
    tier=2,
    description="Opens or navigates the persistent browser to a URL",
    args_schema=BrowserNavigateArgs,
    preview_fn=lambda a: f"Navigate browser to: '{a.get('url')}'"
)
async def browser_navigate(url: str) -> str:
    return await browser_controller.navigate(url)

class BrowserClickArgs(BaseModel):
    selector: str = Field(description="CSS or text selector to click")

@registry.register(
    name="browser_click",
    tier=2,
    description="Clicks an element in the active browser page",
    args_schema=BrowserClickArgs,
    preview_fn=lambda a: f"Click browser element: '{a.get('selector')}'"
)
async def browser_click(selector: str) -> str:
    return await browser_controller.click(selector)

class BrowserTypeArgs(BaseModel):
    selector: str = Field(description="Selector of input field")
    text: str = Field(description="Text to type")

@registry.register(
    name="browser_type",
    tier=2,
    description="Types text into an input field in the browser",
    args_schema=BrowserTypeArgs,
    preview_fn=lambda a: f"Type text into '{a.get('selector')}'"
)
async def browser_type(selector: str, text: str) -> str:
    return await browser_controller.type_text(selector, text)

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
