"""
Phenom Headless Background Worker
Executes web scraping, text extraction, data crawling, and CLI analysis headlessly in the background.
Strictly zero focus disruption: runs in headless Playwright contexts without opening windows or moving the cursor.
Enforces Rule 8: Permanently blocks any payment, checkout, or card submission attempts.
"""

import sys
import re
import asyncio
import logging
from typing import Dict, Any, List, Optional
from playwright.async_api import async_playwright, Browser, BrowserContext, Page

logger = logging.getLogger("phenom.headless_worker")

BLOCKED_PAYMENT_KEYWORDS = [
    "place order", "place your order", "pay now", "proceed to pay",
    "make payment", "complete payment", "buy now", "checkout", "cvv", "otp"
]

DESTRUCTIVE_CLI_PATTERNS = [
    re.compile(r"\bformat\s+[a-z]:", re.IGNORECASE),
    re.compile(r"\bdel\s+/[fsq]\s+[a-z]:\\windows", re.IGNORECASE),
    re.compile(r"\brm\s+-rf\s+/[^\s]*", re.IGNORECASE),
]


class HeadlessBrowserWorker:
    """
    Isolated headless browser worker executing research, scraping, and documentation pipelines.
    Never steals user OS focus, never moves the physical mouse pointer.
    """

    def __init__(self, worker_id: str = "worker-headless-1"):
        self.worker_id = worker_id
        self._playwright = None
        self._browser: Optional[Browser] = None
        self._context: Optional[BrowserContext] = None
        self.is_running: bool = False
        self.is_aborted: bool = False

    async def _ensure_browser(self):
        if self._playwright is None:
            self._playwright = await async_playwright().start()
        if self._browser is None:
            self._browser = await self._playwright.chromium.launch(
                headless=True,
                args=["--disable-blink-features=AutomationControlled", "--no-sandbox"]
            )
        if self._context is None:
            self._context = await self._browser.new_context(
                viewport={"width": 1280, "height": 800},
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) PhenomHeadless/6.0"
            )

    def _verify_safety(self, text_or_url: str):
        """Hard code-level check ensuring payment actions are blocked (Rule 8)."""
        lower = text_or_url.lower()
        for kw in BLOCKED_PAYMENT_KEYWORDS:
            if kw in lower:
                raise PermissionError(
                    f"Action '{text_or_url}' blocked: Payment and checkout completion are prohibited by SAFETY.md (Rule 8)."
                )

    async def scrape_page(
        self,
        url: str,
        selectors: Optional[List[str]] = None,
        timeout_ms: int = 15000
    ) -> Dict[str, Any]:
        """
        Navigates to URL headlessly, extracts page title and text content.
        Enforces Rule 8 safety check.
        """
        self._verify_safety(url)
        if self.is_aborted:
            return {"status": "aborted", "worker_id": self.worker_id, "url": url}

        self.is_running = True
        page: Optional[Page] = None
        try:
            await self._ensure_browser()
            page = await self._context.new_page()
            await page.goto(url, timeout=timeout_ms, wait_until="domcontentloaded")

            title = await page.title()
            extracted_data = {}

            if selectors:
                for sel in selectors:
                    try:
                        elem = await page.query_selector(sel)
                        extracted_data[sel] = await elem.inner_text() if elem else None
                    except Exception:
                        extracted_data[sel] = None

            # Get main body text (limited to 5000 chars to avoid memory bloat)
            body_text = await page.evaluate("() => document.body.innerText")
            body_snippet = body_text[:5000].strip() if body_text else ""

            return {
                "status": "completed",
                "worker_id": self.worker_id,
                "url": url,
                "title": title,
                "extracted_selectors": extracted_data,
                "text_snippet": body_snippet
            }
        except PermissionError:
            raise
        except Exception as e:
            logger.warning(f"Headless scrape error for {url}: {e}")
            return {
                "status": "error",
                "worker_id": self.worker_id,
                "url": url,
                "error": str(e)
            }
        finally:
            self.is_running = False
            if page and not page.is_closed():
                try:
                    await page.close()
                except Exception:
                    pass

    async def execute_steps(self, steps: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Executes a sequence of headless browser steps (navigate, extract, wait).
        Aborts immediately if checkout or payment is requested.
        """
        results = []
        for step in steps:
            if self.is_aborted:
                return {"status": "aborted", "executed_steps": results}

            action = step.get("action", "")
            target = step.get("target", "")

            # Rule 8 check on every target and action
            self._verify_safety(f"{action} {target}")

            if action == "navigate":
                res = await self.scrape_page(target)
                results.append(res)
            elif action == "wait":
                delay = float(step.get("duration", 1.0))
                await asyncio.sleep(min(delay, 5.0))
                results.append({"status": "waited", "duration": delay})
            else:
                results.append({"status": "unknown_action", "action": action})

        return {
            "status": "completed",
            "worker_id": self.worker_id,
            "steps_count": len(results),
            "step_results": results
        }

    def abort(self):
        """Immediately halts worker operations."""
        self.is_aborted = True
        self.is_running = False

    async def close(self):
        """Releases all browser contexts and resources."""
        self.is_running = False
        if self._context:
            try:
                await self._context.close()
            except Exception:
                pass
            self._context = None
        if self._browser:
            try:
                await self._browser.close()
            except Exception:
                pass
            self._browser = None
        if self._playwright:
            try:
                await self._playwright.stop()
            except Exception:
                pass
            self._playwright = None


class SubprocessCLIWorker:
    """
    Executes background CLI commands, linters, and analysis scripts detached from user focus.
    """

    def __init__(self, worker_id: str = "worker-cli-1"):
        self.worker_id = worker_id
        self.is_running: bool = False
        self.is_aborted: bool = False
        self._proc: Optional[asyncio.subprocess.Process] = None

    def _verify_safety(self, command: str):
        for pattern in DESTRUCTIVE_CLI_PATTERNS:
            if pattern.search(command):
                raise PermissionError(f"Destructive CLI command blocked by safety rule: '{command}'")

    async def execute_command(
        self,
        command: str,
        cwd: Optional[str] = None,
        timeout_sec: float = 30.0
    ) -> Dict[str, Any]:
        """Runs a command in a detached subprocess with timeout and safety validation."""
        self._verify_safety(command)
        if self.is_aborted:
            return {"status": "aborted", "worker_id": self.worker_id, "command": command}

        self.is_running = True
        try:
            self._proc = await asyncio.create_subprocess_shell(
                command,
                cwd=cwd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            stdout_data, stderr_data = await asyncio.wait_for(
                self._proc.communicate(),
                timeout=timeout_sec
            )
            out_str = stdout_data.decode("utf-8", errors="replace").strip()
            err_str = stderr_data.decode("utf-8", errors="replace").strip()

            return {
                "status": "completed",
                "worker_id": self.worker_id,
                "command": command,
                "returncode": self._proc.returncode,
                "stdout": out_str[:5000],
                "stderr": err_str[:2000]
            }
        except asyncio.TimeoutError:
            if self._proc:
                try:
                    self._proc.kill()
                except Exception:
                    pass
            return {
                "status": "timeout",
                "worker_id": self.worker_id,
                "command": command,
                "error": f"Command timed out after {timeout_sec} seconds"
            }
        except Exception as e:
            return {
                "status": "error",
                "worker_id": self.worker_id,
                "command": command,
                "error": str(e)
            }
        finally:
            self.is_running = False
            self._proc = None

    def abort(self):
        """Immediately aborts running subprocess."""
        self.is_aborted = True
        self.is_running = False
        if self._proc:
            try:
                self._proc.kill()
            except Exception:
                pass
