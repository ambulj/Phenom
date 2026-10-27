"""
Phenom Persistent Browser Controller
Uses Playwright with a persistent user profile directory.
Streams real-time live view JPEG frames to the desktop UI.
Incorporates human takeover safety checks.
"""

import os
import asyncio
import base64
from typing import Optional, Callable, Dict, Any, List
from playwright.async_api import async_playwright, BrowserContext, Page
from services.backend.automation.human_takeover import takeover_manager
from services.backend.automation.limits import AutomationLimitsManager

USER_DATA_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "user_data"))

class BrowserController:
    def __init__(self):
        self._playwright = None
        self._context: Optional[BrowserContext] = None
        self._page: Optional[Page] = None
        self._on_frame_callback: Optional[Callable[[str], None]] = None
        self._is_streaming = False
        self._stream_task: Optional[asyncio.Task] = None
        self.limits = AutomationLimitsManager()
        os.makedirs(USER_DATA_DIR, exist_ok=True)

    def set_frame_callback(self, cb: Callable[[str], None]):
        self._on_frame_callback = cb

    async def ensure_page(self) -> Page:
        if self._page is not None and not self._page.is_closed():
            return self._page

        if self._playwright is None:
            self._playwright = await async_playwright().start()

        if self._context is None:
            self._context = await self._playwright.chromium.launch_persistent_context(
                user_data_dir=USER_DATA_DIR,
                headless=False,
                args=["--disable-blink-features=AutomationControlled", "--window-size=1280,800"]
            )

        if len(self._context.pages) > 0:
            self._page = self._context.pages[0]
        else:
            self._page = await self._context.new_page()

        self._start_frame_stream()
        return self._page

    def _start_frame_stream(self):
        if self._is_streaming:
            return
        self._is_streaming = True
        self._stream_task = asyncio.create_task(self._capture_loop())

    async def _capture_loop(self):
        while self._is_streaming and self._page and not self._page.is_closed():
            try:
                if self._on_frame_callback:
                    # In-memory screenshot for live view UI (never written to disk)
                    frame_bytes = await self._page.screenshot(type="jpeg", quality=45)
                    b64 = base64.b64encode(frame_bytes).decode("utf-8")
                    self._on_frame_callback(b64)
            except Exception:
                pass
            await asyncio.sleep(0.35) # ~3 fps for UI panel live view

    async def navigate(self, url: str) -> str:
        await takeover_manager.wait_if_paused()
        self.limits.check_limits(f"navigate:{url}")
        
        page = await self.ensure_page()
        with takeover_manager.synthetic_action():
            await page.goto(url, wait_until="domcontentloaded", timeout=30000)
            
        await takeover_manager.wait_if_paused()
        return f"Navigated to {page.url} ({await page.title()})"

    async def click(self, selector: str) -> str:
        await takeover_manager.wait_if_paused()
        self.limits.check_limits(f"click:{selector}")
        
        page = await self.ensure_page()
        with takeover_manager.synthetic_action():
            await page.click(selector, timeout=10000)
            
        await takeover_manager.wait_if_paused()
        return f"Clicked element matching {selector}"

    async def type_text(self, selector: str, text: str) -> str:
        await takeover_manager.wait_if_paused()
        # Security rule: Never type or store passwords
        if "pass" in selector.lower() or "pwd" in selector.lower():
            raise PermissionError("Typing passwords is strictly prohibited by SAFETY.md.")

        self.limits.check_limits(f"type:{selector}")
        page = await self.ensure_page()
        with takeover_manager.synthetic_action():
            await page.fill(selector, text, timeout=10000)
            
        await takeover_manager.wait_if_paused()
        return f"Typed into {selector}"

    async def get_page_text(self) -> str:
        page = await self.ensure_page()
        return await page.evaluate("() => document.body.innerText.substring(0, 3000)")

    async def close(self):
        self._is_streaming = False
        if self._stream_task:
            self._stream_task.cancel()
        if self._context:
            await self._context.close()
            self._context = None
            self._page = None
        if self._playwright:
            await self._playwright.stop()
            self._playwright = None

browser_controller = BrowserController()
