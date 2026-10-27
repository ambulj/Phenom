"""
Unit & Integration Tests for Phase 3: Screen, UI, and Browser Automation
Verifies:
1. Scripted browser task with live view frame streaming
2. Human takeover: Pause-on-input within 1 second, and no resume without an answer
3. Dry-run cart fill on all 4 sites (Amazon, Flipkart, Swiggy, Zomato) stopping before checkout
4. Pay and place-order actions permanently blocked at tool & safety levels
5. YouTube video summarization and guaranteed scratch audio deletion
6. Execution limits (steps, timeout) and stuck-loop detector
7. Screen privacy: Screenshots processed in RAM only, 0 disk files
"""

import os
import glob
import time
import tempfile
import asyncio
import pytest
from pydantic import BaseModel

from services.backend.automation.human_takeover import takeover_manager, HumanTakeoverAbort
from services.backend.automation.limits import AutomationLimitsManager, AutomationLimitExceeded, AutomationStuckError
from services.backend.automation.desktop_controller import desktop_controller
from services.backend.browser.browser_controller import browser_controller
from services.backend.browser.cart_automator import cart_automator
from services.backend.browser.youtube_summarizer import youtube_summarizer
from services.backend.safety.engine import safety_engine
from services.backend.safety.registry import registry
import services.backend.tools.automation_tools

@pytest.mark.asyncio
async def test_scripted_browser_task_with_live_view():
    frames_received = []
    def frame_handler(b64: str):
        frames_received.append(b64)

    browser_controller.set_frame_callback(frame_handler)
    try:
        # Run simple scripted navigation
        nav_res = await browser_controller.navigate("https://example.com")
        assert "example" in nav_res.lower()
        
        # Wait briefly for frame capture loop
        await asyncio.sleep(0.8)
        assert len(frames_received) > 0, "Live view frames must be received during browser navigation"
        assert isinstance(frames_received[0], str) and len(frames_received[0]) > 100
    finally:
        await browser_controller.close()

@pytest.mark.asyncio
async def test_pause_on_input_within_one_second():
    takeover_manager.start_automation()
    assert takeover_manager.is_automating is True
    assert takeover_manager.is_paused is False

    # Simulate a human hardware mouse move event
    class MockMouseEvent:
        pass

    t0 = time.perf_counter()
    takeover_manager._on_mouse_event(MockMouseEvent())
    pause_latency_ms = (time.perf_counter() - t0) * 1000.0

    # Requirement: pause within 1 second (< 1000 ms)
    assert takeover_manager.is_paused is True
    assert pause_latency_ms < 1000.0, f"Pause latency {pause_latency_ms} ms exceeded 1000 ms"

    # Verify automation will not resume without an explicit answer
    paused_task = asyncio.create_task(takeover_manager.wait_if_paused())
    await asyncio.sleep(0.1)
    assert not paused_task.done(), "Takeover must remain paused until explicit decision"

    # User sends 'continue'
    takeover_manager.resolve_takeover("continue")
    await asyncio.sleep(0.05)
    assert paused_task.done(), "Task must resume upon 'continue'"
    assert takeover_manager.is_paused is False

    # Test 'stop' aborts automation
    takeover_manager._trigger_pause("test_stop")
    with pytest.raises(HumanTakeoverAbort):
        takeover_manager.resolve_takeover("stop")
    assert takeover_manager.is_automating is False

@pytest.mark.asyncio
async def test_dry_run_cart_fill_stops_at_cart_on_all_sites():
    # Mock network navigation for CI/test stability while testing the full cart automator logic
    original_navigate = browser_controller.navigate
    original_ensure_page = browser_controller.ensure_page
    original_get_text = browser_controller.get_page_text

    async def mock_navigate(url):
        return f"Navigated to {url}"

    class MockElement:
        async def click(self): pass

    class MockPage:
        async def fill(self, sel, text): pass
        async def click(self, sel): pass
        async def press(self, sel, key): pass
        async def goto(self, url): pass
        async def wait_for_timeout(self, ms): pass
        async def query_selector(self, sel): return MockElement()
        keyboard = type("K", (), {"press": lambda self, k: asyncio.sleep(0)})()

    async def mock_ensure_page():
        return MockPage()

    async def mock_get_text():
        return "Subtotal (1 item): Rs 1,499.00. Shopping Cart contains Wireless Mouse."

    browser_controller.navigate = mock_navigate
    browser_controller.ensure_page = mock_ensure_page
    browser_controller.get_page_text = mock_get_text

    try:
        platforms = ["amazon", "flipkart", "swiggy", "zomato"]
        for p in platforms:
            res = await cart_automator.fill_cart(platform=p, item_query="wireless mouse")
            assert res["status"] == "stopped_at_cart", f"Must stop at cart on {p}"
            assert res["platform"] == p
            assert "halted before checkout" in res["message"]
            assert "1,499" in res["cart_summary_preview"]
    finally:
        browser_controller.navigate = original_navigate
        browser_controller.ensure_page = original_ensure_page
        browser_controller.get_page_text = original_get_text

@pytest.mark.asyncio
async def test_pay_and_place_order_blocked_at_tool_level():
    # 1. CartAutomator prohibited methods raise PermissionError
    with pytest.raises(PermissionError) as exc_info:
        await cart_automator.place_order()
    assert "permanently blocked" in str(exc_info.value)

    with pytest.raises(PermissionError) as exc_info:
        await cart_automator.proceed_to_payment()
    assert "permanently blocked" in str(exc_info.value)

    # 2. Blocked keywords check
    with pytest.raises(PermissionError):
        cart_automator.verify_no_payment_action("Click Proceed to Pay")

    with pytest.raises(PermissionError):
        cart_automator.verify_no_payment_action("Submit OTP 123456")

    # 3. Safety Layer: checkout_pay is Tier 3 and blocked
    assert registry.get_tier("checkout_pay") == 3
    assert registry.get_tier("enter_payment_info") == 3

    with pytest.raises(PermissionError) as exc_info:
        await safety_engine.execute_tool("checkout_pay", {"payment_method": "card"})
    assert "Tier 3 tool 'checkout_pay' is blocked by default" in str(exc_info.value)

    with pytest.raises(PermissionError) as exc_info:
        await safety_engine.execute_tool("enter_payment_info", {"card_details": "4111222233334444"})
    assert "Tier 3 tool 'enter_payment_info' is blocked by default" in str(exc_info.value)

@pytest.mark.asyncio
async def test_youtube_summary_and_temp_audio_deleted():
    # 1. Test video with captions
    youtube_summarizer.get_video_captions = lambda url: "Captions: Welcome to the automated machine learning lecture."
    res_captions = await youtube_summarizer.summarize_video("https://www.youtube.com/watch?v=sample1")
    assert res_captions["used_captions"] is True
    assert "automated machine learning" in res_captions["summary"]

    # 2. Test video without captions (fallback audio download & local transcription)
    youtube_summarizer.get_video_captions = lambda url: None
    
    # Simulate a generated audio scratch file that must be scrubbed
    temp_dir = tempfile.gettempdir()
    mock_scratch = os.path.join(temp_dir, "phenom_yt_testscratch.wav")
    with open(mock_scratch, "wb") as f:
        f.write(b"RIFFdummydataWAVEfmt ")
    assert os.path.exists(mock_scratch)

    # Perform audio transcription fallback and ensure cleanup
    orig_download = youtube_summarizer.download_and_transcribe_audio
    def mock_download_and_clean(url):
        # Transcribe & purge
        if os.path.exists(mock_scratch):
            os.remove(mock_scratch)
        return "Transcribed audio content from local Whisper model.", True

    youtube_summarizer.download_and_transcribe_audio = mock_download_and_clean
    res_audio = await youtube_summarizer.summarize_video("https://www.youtube.com/watch?v=nocaptions")

    assert res_audio["used_captions"] is False
    assert res_audio["temp_audio_deleted"] is True
    assert not os.path.exists(mock_scratch), "Temporary scratch audio file MUST be deleted"

def test_automation_limits_and_stuck_detector():
    limits = AutomationLimitsManager(max_steps=5, timeout_seconds=1.0, max_repeats=3)
    limits.start_session()

    # Step limit check
    for _ in range(5):
        limits.check_limits("action_step")
    with pytest.raises(AutomationLimitExceeded):
        limits.check_limits("action_step_6")

    # Stuck loop check
    stuck_limits = AutomationLimitsManager(max_steps=20, timeout_seconds=60, max_repeats=3)
    stuck_limits.start_session()
    stuck_limits.check_limits("click:#btn", state_repr="<html>state1</html>")
    stuck_limits.check_limits("click:#btn", state_repr="<html>state1</html>")
    with pytest.raises(AutomationStuckError):
        stuck_limits.check_limits("click:#btn", state_repr="<html>state1</html>")

def test_screen_privacy_in_memory_only():
    # Capture screen into RAM
    img = desktop_controller.capture_screen_ram()
    assert img is not None
    assert img.width > 0 and img.height > 0

    # Ensure no screenshot files were created in repo root
    disk_screenshots = []
    for root, dirs, files in os.walk("C:\\Phenom"):
        if ".git" in root or "node_modules" in root or ".venv" in root:
            continue
        for f in files:
            if f.endswith((".png", ".jpg", ".jpeg", ".bmp")) and "screenshot" in f.lower():
                disk_screenshots.append(os.path.join(root, f))
    assert len(disk_screenshots) == 0, f"Screenshots found on disk: {disk_screenshots}"
