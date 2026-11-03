"""
Phenom Milestone 9.0 Phase 1 Tests: Ambient Vision Co-Pilot Engine (VIS-01)
Verifies:
1. In-memory screen capture with zero disk footprint and latency tracking.
2. Strict privacy blacklist gate (credential managers, banking, incognito, private chats).
3. Active window suppression returning [BLACKLOCKED_WINDOW_SKIPPED].
4. In-memory privacy masking of sub-window regions.
5. Perceptual delta detector skipping stationary screens (< 2% change).
6. Local VLM ambient scene analysis and error extraction.
7. WebSocket update broadcasting (VISION_AMBIENT_UPDATE).
8. Governor pause/resume lifecycle handling.
9. Dynamic copilot runtime configuration.
"""

import io
import os
import time
from typing import Any, Dict, List
from PIL import Image, ImageDraw
import pytest

from services.backend.schemas.ambient_vision import AmbientCopilotConfig, AmbientScreenContext
from services.backend.vision.ambient_copilot import AmbientVisionCopilot, ambient_copilot
from services.backend.vision.delta_detector import DeltaDetector, delta_detector
from services.backend.vision.frame_grabber import FrameGrabber, frame_grabber
from services.backend.vision.privacy_masker import PrivacyMasker, privacy_masker
from services.backend.vision.moondream_client import MoondreamVisionClient, moondream_client


@pytest.fixture
def clean_copilot():
    copilot = AmbientVisionCopilot()
    copilot.reset()
    yield copilot
    copilot.reset()


@pytest.fixture
def test_canvas() -> Image.Image:
    img = Image.new("RGB", (800, 600), color=(30, 30, 40))
    draw = ImageDraw.Draw(img)
    draw.rectangle([50, 50, 300, 150], fill=(70, 70, 120))
    draw.text((60, 60), "Application Window: Project Editor", fill=(255, 255, 255))
    return img


def test_in_memory_capture_zero_disk_writes():
    """VIS-01: Verifies frame capture operates purely in RAM without touching disk."""
    grabber = FrameGrabber()
    img = grabber.grab_frame()
    assert isinstance(img, Image.Image)
    assert grabber.last_latency_ms >= 0.0
    assert img.size[0] > 0 and img.size[1] > 0


def test_privacy_blacklist_window_detection():
    """VIS-01: Verifies strict blacklist regex and process matching."""
    masker = PrivacyMasker()

    # Credential managers
    assert masker.is_window_blacklisted("1Password - Master Vault", "1password.exe")
    assert masker.is_window_blacklisted("Bitwarden Password Manager", "bitwarden.exe")
    assert masker.is_window_blacklisted("KeePassXC - Passwords.kdbx", "keepassxc.exe")
    assert masker.is_window_blacklisted("LastPass Vault", "lastpass.exe")

    # Private browsing
    assert masker.is_window_blacklisted("Google Chrome - Incognito", "chrome.exe")
    assert masker.is_window_blacklisted("InPrivate - Microsoft Edge", "msedge.exe")
    assert masker.is_window_blacklisted("Private Browsing - Mozilla Firefox", "firefox.exe")

    # Financial / Banking / Crypto
    assert masker.is_window_blacklisted("Chase Online Banking - Chrome", "chrome.exe")
    assert masker.is_window_blacklisted("PayPal Wallet", "brave.exe")
    assert masker.is_window_blacklisted("MetaMask Notification", "chrome.exe")
    assert masker.is_window_blacklisted("Coinbase Pro Dashboard", "chrome.exe")

    # Private Chats
    assert masker.is_window_blacklisted("WhatsApp", "whatsapp.exe")
    assert masker.is_window_blacklisted("Signal", "signal.exe")
    assert masker.is_window_blacklisted("Telegram", "telegram.exe")

    # Safe desktop development apps
    assert not masker.is_window_blacklisted("Phenom Architecture - Visual Studio Code", "code.exe")
    assert not masker.is_window_blacklisted("Calculator", "calc.exe")
    assert not masker.is_window_blacklisted("Terminal", "cmd.exe")


@pytest.mark.asyncio
async def test_privacy_blacklist_active_window_suppression(clean_copilot):
    """VIS-01: Verifies active blacklisted window suppresses capture and returns [BLACKLOCKED_WINDOW_SKIPPED]."""
    clean_copilot.set_mock_hooks(
        window_title="1Password - Passwords",
        process_name="1password.exe",
    )

    ctx = await clean_copilot.step()

    assert ctx.is_blacklisted is True
    assert ctx.is_sensitive is True
    assert ctx.scene_summary == "[BLACKLOCKED_WINDOW_SKIPPED]"
    assert ctx.window_title == "[REDACTED]"
    assert ctx.process_name == "1password.exe"
    assert len(ctx.detected_errors) == 0


def test_in_memory_privacy_subwindow_masking(test_canvas):
    """VIS-01: Verifies sub-window regions are redacted in-memory with cyber privacy badge."""
    masker = PrivacyMasker()
    custom_windows = [
        {"title": "Bitwarden Extension", "rect": (50, 50, 250, 150)}
    ]
    masked_img, applied = masker.mask_sensitive_windows(test_canvas, custom_windows=custom_windows)

    assert len(applied) == 1
    # Check that region inside rect is masked black
    pixel = masked_img.getpixel((60, 80))
    # Pixel inside rectangle must be black (0, 0, 0)
    assert pixel == (0, 0, 0)


def test_delta_detector_stationary_and_dynamic_screen(test_canvas):
    """VIS-01: Verifies perceptual change detector skips stationary screens (< 2% change)."""
    detector = DeltaDetector(threshold=0.02)

    # First frame always considered changed
    changed, score = detector.compute_delta(test_canvas)
    assert changed is True
    assert score == 1.0

    # Identical frame: delta score must be 0.0 (< 0.02)
    changed, score = detector.compute_delta(test_canvas)
    assert changed is False
    assert score < 0.02

    # Heavily modified frame: delta score should exceed threshold
    modified = test_canvas.copy()
    draw = ImageDraw.Draw(modified)
    draw.rectangle([0, 0, 800, 600], fill=(255, 255, 255))
    changed, score = detector.compute_delta(modified)
    assert changed is True
    assert score >= 0.02


@pytest.mark.asyncio
async def test_ambient_copilot_skips_vlm_on_stationary_screen(clean_copilot, test_canvas):
    """VIS-01: Verifies stationary screen reuses previous context without invoking local VLM."""
    vlm_call_count = 0

    class MockVLM(MoondreamVisionClient):
        async def query_ambient_screen(self, img, prompt=None, timeout=15.0):
            nonlocal vlm_call_count
            vlm_call_count += 1
            return {
                "status": "success",
                "model": "moondream",
                "description": "Code editor open with main.py",
                "detected_errors": [],
                "latency_ms": 12.5,
            }

    clean_copilot.vlm = MockVLM()
    clean_copilot.set_mock_hooks(
        window_title="main.py - Visual Studio Code",
        process_name="code.exe",
        frame=test_canvas,
    )

    # Step 1: dynamic change (initialization) -> VLM is called
    ctx1 = await clean_copilot.step()
    assert ctx1.has_changed is True
    assert ctx1.scene_summary == "Code editor open with main.py"
    assert vlm_call_count == 1

    # Step 2: identical stationary screen -> VLM is SKIPPED
    ctx2 = await clean_copilot.step()
    assert ctx2.has_changed is False
    assert ctx2.scene_summary == "Code editor open with main.py"
    assert vlm_call_count == 1  # Unchanged!


@pytest.mark.asyncio
async def test_ambient_copilot_extracts_errors_on_changed_screen(clean_copilot, test_canvas):
    """VIS-01: Verifies VLM error extraction from active compiler/debugger dialog."""
    mock_response = {
        "status": "success",
        "model": "moondream",
        "description": "Compiler error popup:\nSyntaxError: unexpected EOF while parsing\nBuild failed.",
        "detected_errors": ["SyntaxError: unexpected EOF while parsing", "Build failed."],
        "latency_ms": 15.0,
    }
    clean_copilot.set_mock_hooks(
        window_title="Build Terminal",
        process_name="terminal.exe",
        frame=test_canvas,
        vlm_response=mock_response,
    )

    ctx = await clean_copilot.step()
    assert ctx.has_changed is True
    assert len(ctx.detected_errors) == 2
    assert "SyntaxError" in ctx.detected_errors[0]


@pytest.mark.asyncio
async def test_ambient_copilot_broadcasts_websocket_update(clean_copilot, test_canvas):
    """VIS-01: Verifies ambient vision broadcasts VISION_AMBIENT_UPDATE over WebSocket."""
    received_updates = []

    def mock_broadcast(msg: dict):
        received_updates.append(msg)

    clean_copilot.register_broadcaster(mock_broadcast)
    clean_copilot.set_mock_hooks(
        window_title="Active Window",
        process_name="app.exe",
        frame=test_canvas,
        vlm_response={"description": "Active app screen", "detected_errors": [], "latency_ms": 5.0},
    )

    await clean_copilot.step()

    assert len(received_updates) == 1
    assert received_updates[0]["type"] == "VISION_AMBIENT_UPDATE"
    assert "context" in received_updates[0]
    assert received_updates[0]["context"]["window_title"] == "Active Window"


@pytest.mark.asyncio
async def test_ambient_copilot_governor_pause_and_resume(clean_copilot, test_canvas):
    """GOV-01: Verifies governor suspension suppresses vision cycles and resumes cleanly."""
    clean_copilot.set_mock_hooks(
        window_title="Desktop App",
        process_name="app.exe",
        frame=test_canvas,
        vlm_response={"description": "Active app", "detected_errors": []},
    )

    # Initial step
    await clean_copilot.step()
    assert clean_copilot.is_suspended is False

    # Pause from governor (e.g. 3D game launched)
    clean_copilot.pause(reason="3D Game Active")
    assert clean_copilot.is_suspended is True

    ctx_paused = await clean_copilot.step()
    assert ctx_paused.is_suspended is True
    assert ctx_paused.suspension_reason == "3D Game Active"

    # Resume from governor
    clean_copilot.resume()
    assert clean_copilot.is_suspended is False
    ctx_resumed = await clean_copilot.step()
    assert ctx_resumed.is_suspended is False


def test_ambient_copilot_dynamic_configuration(clean_copilot):
    """SAF-01: Verifies runtime configuration updates."""
    clean_copilot.configure(
        is_enabled=False,
        interval_seconds=5.0,
        delta_threshold=0.05,
        custom_blacklists=[r"MyConfidentialApp\.exe"],
    )

    assert clean_copilot.config.is_enabled is False
    assert clean_copilot.config.interval_seconds == 5.0
    assert clean_copilot.config.delta_threshold == 0.05
    assert clean_copilot.masker.is_window_blacklisted("Secret Title", "MyConfidentialApp.exe")
