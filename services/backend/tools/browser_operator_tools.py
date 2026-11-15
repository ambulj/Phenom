"""
Phenom Sovereign Browser Operator Tools (Milestone 18 - Phase 2)
Wraps BrowserController into formal Safety Engine ToolDefinitions:
- browser_navigate (Tier 1): Navigate active tab to URL
- browser_click (Tier 1): Semantic element clicking with Rule 8 payment protection
- browser_type (Tier 1): Semantic input typing with Rule 8 password protection
- browser_scroll (Tier 0): Viewport vertical scrolling
- browser_extract_content (Tier 0): Deep structured DOM scraping (H1-H4, tables, paragraphs)
- browser_manage_tabs (Tier 0/1): Multi-tab lifecycle (list, new, switch, close)
- browser_takeover_control (Tier 0): Human takeover pause/resume/takeover controls
"""

import os
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field

from services.backend.safety.registry import registry
from services.backend.safety.guardian import guardian
from services.backend.safety.taint import taint_tracker
from services.backend.browser.browser_controller import browser_controller
from services.backend.automation.human_takeover import takeover_manager


# ---------------- 1. BROWSER NAVIGATE ----------------

class BrowserNavigateArgs(BaseModel):
    url: str = Field(description="Target website URL or domain (e.g. 'https://news.ycombinator.com', 'arxiv.org')")


def preview_browser_navigate(args: Dict[str, Any]) -> str:
    url = args.get("url", "unknown")
    return f"[Tier 2] Browser Navigate: Open web destination '{url}'"


@registry.register(
    name="browser_navigate",
    tier=2,
    description="Navigate sovereign Playwright browser to a specified website URL or web application",
    args_schema=BrowserNavigateArgs,
    preview_fn=preview_browser_navigate
)
async def browser_navigate(url: str) -> Dict[str, Any]:
    if guardian.is_halted:
        raise RuntimeError("Browser operation halted by Guardian Kill Switch")
    return await browser_controller.navigate(url)


# ---------------- 2. BROWSER CLICK ----------------

class BrowserClickArgs(BaseModel):
    target: str = Field(description="CSS selector or visible button text to click (Rule 8 blocks payment/checkout buttons)")


def preview_browser_click(args: Dict[str, Any]) -> str:
    target = args.get("target", "unknown")
    return f"[Tier 2] Browser Click: Click element or button matching '{target}'"


@registry.register(
    name="browser_click",
    tier=2,
    description="Click a button, link, or semantic element in the browser (strictly enforces Rule 8 payment block)",
    args_schema=BrowserClickArgs,
    preview_fn=preview_browser_click
)
async def browser_click(target: str) -> Dict[str, Any]:
    if guardian.is_halted:
        raise RuntimeError("Browser operation halted by Guardian Kill Switch")
    return await browser_controller.click_semantic(target)


# ---------------- 3. BROWSER TYPE ----------------

class BrowserTypeArgs(BaseModel):
    selector: str = Field(description="Input selector (Rule 8 strictly prohibits password, credit card, and CVV fields)")
    text: str = Field(description="Text to type into the field")


def preview_browser_type(args: Dict[str, Any]) -> str:
    selector = args.get("selector", "unknown")
    text = args.get("text", "")
    return f"[Tier 2] Browser Type: Type {len(text)} characters into '{selector}'"


@registry.register(
    name="browser_type",
    tier=2,
    description="Type text into an input field or search bar in the browser (strictly enforces Rule 8 password/CVV block)",
    args_schema=BrowserTypeArgs,
    preview_fn=preview_browser_type
)
async def browser_type(selector: str, text: str) -> Dict[str, Any]:
    if guardian.is_halted:
        raise RuntimeError("Browser operation halted by Guardian Kill Switch")
    return await browser_controller.type_semantic(selector, text)


# ---------------- 4. BROWSER SCROLL ----------------

class BrowserScrollArgs(BaseModel):
    direction: str = Field(default="down", description="Scroll direction: 'down' or 'up'")
    amount: int = Field(default=500, description="Pixel scroll offset")


@registry.register(
    name="browser_scroll",
    tier=0,
    description="Scroll the active browser viewport up or down",
    args_schema=BrowserScrollArgs,
    preview_fn=lambda a: f"Scroll browser viewport {a.get('direction', 'down')} by {a.get('amount', 500)}px"
)
async def browser_scroll(direction: str = "down", amount: int = 500) -> Dict[str, Any]:
    if guardian.is_halted:
        raise RuntimeError("Browser operation halted by Guardian Kill Switch")
    return await browser_controller.scroll_page(direction=direction, amount=amount)


# ---------------- 5. BROWSER EXTRACT CONTENT (RES-01) ----------------

class BrowserExtractContentArgs(BaseModel):
    pass


@registry.register(
    name="browser_extract_content",
    tier=0,
    description="Extract structured headings, body paragraphs, tables, and references from the active web page without fabrication",
    args_schema=BrowserExtractContentArgs,
    preview_fn=lambda a: "Extract structured DOM content, tables, and links from active browser page"
)
async def browser_extract_content() -> Dict[str, Any]:
    if guardian.is_halted:
        raise RuntimeError("Browser operation halted by Guardian Kill Switch")
    taint_tracker.mark_tainted("web_scrape", "Extracted content from external web page")
    res = await browser_controller.extract_page_content()
    if isinstance(res, dict) and "text" in res:
        wrapped, _, _ = taint_tracker.inspect_and_sanitize(res["text"], source="web_scrape")
        res["text"] = wrapped
    return res


# ---------------- 6. BROWSER MANAGE TABS ----------------

class BrowserManageTabsArgs(BaseModel):
    action: str = Field(default="list", description="Tab action: 'list', 'new', 'switch', or 'close'")
    url: Optional[str] = Field(default=None, description="Optional URL when opening a new tab")
    tab_id: Optional[str] = Field(default=None, description="Target tab ID for 'switch' or 'close'")


def preview_browser_manage_tabs(args: Dict[str, Any]) -> str:
    act = args.get("action", "list").lower()
    if act == "close":
        return f"[Tier 1] Browser Tab: Close tab '{args.get('tab_id', 'active')}'"
    return f"Browser Tab: {act.title()} tabs"


def dynamic_tab_tier(args: Dict[str, Any]) -> int:
    """Closing a tab is Tier 1; listing, opening, or switching is Tier 0."""
    return 1 if args.get("action", "").lower() == "close" else 0


@registry.register(
    name="browser_manage_tabs",
    tier=dynamic_tab_tier,
    description="Manage browser tabs: list active tabs, open new tabs, switch tabs, or close tabs",
    args_schema=BrowserManageTabsArgs,
    preview_fn=preview_browser_manage_tabs
)
async def browser_manage_tabs(
    action: str = "list",
    url: Optional[str] = None,
    tab_id: Optional[str] = None
) -> Dict[str, Any]:
    if guardian.is_halted:
        raise RuntimeError("Browser operation halted by Guardian Kill Switch")

    act = action.lower()
    if act == "list":
        tabs = await browser_controller.list_tabs()
        return {"status": "success", "action": "list_tabs", "count": len(tabs), "tabs": tabs}
    elif act == "new":
        return await browser_controller.new_tab(url=url)
    elif act == "switch":
        if not tab_id:
            raise ValueError("tab_id parameter is required for 'switch' action")
        return await browser_controller.switch_tab(tab_id=tab_id)
    elif act == "close":
        if not tab_id:
            raise ValueError("tab_id parameter is required for 'close' action")
        return await browser_controller.close_tab(tab_id=tab_id)
    else:
        raise ValueError(f"Unsupported tab action '{action}'. Expected 'list', 'new', 'switch', or 'close'.")


# ---------------- 7. BROWSER TAKEOVER CONTROL ----------------

class BrowserTakeoverControlArgs(BaseModel):
    action: str = Field(description="Takeover control action: 'pause', 'resume', 'takeover', or 'status'")


@registry.register(
    name="browser_takeover_control",
    tier=0,
    description="Control human-in-the-loop takeover for autonomous browser operations (pause, resume, manual takeover)",
    args_schema=BrowserTakeoverControlArgs,
    preview_fn=lambda a: f"Browser Takeover Control: {a.get('action', 'status').title()}"
)
async def browser_takeover_control(action: str) -> Dict[str, Any]:
    act = action.lower().strip()
    if act == "pause":
        takeover_manager.request_pause(reason="user_browser_hud_pause")
        return {"status": "success", "state": "paused", "message": "Browser automation paused."}
    elif act in ("resume", "continue"):
        takeover_manager.resume_from_user()
        return {"status": "success", "state": "running", "message": "Browser automation resumed."}
    elif act == "takeover":
        takeover_manager.trigger_takeover(reason="user_manual_takeover_requested")
        return {"status": "success", "state": "manual_takeover", "message": "Manual human takeover activated."}
    elif act == "status":
        return {
            "status": "success",
            "is_paused": takeover_manager.is_paused,
            "is_takeover": takeover_manager.is_takeover_active
        }
    else:
        raise ValueError(f"Unsupported takeover action '{action}'. Expected 'pause', 'resume', 'takeover', or 'status'.")
