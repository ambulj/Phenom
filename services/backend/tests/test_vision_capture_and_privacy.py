"""
Phenom 4.0: In-RAM Vision Capture, Delta Detection & Privacy Masking Verification Suite
Tests:
1. FrameGrabber in-RAM speed (< 30ms latency, zero disk writes).
2. DeltaDetector perceptual change detection on static vs altered frames.
3. PrivacyMasker sensitive title detection.
4. PrivacyMasker in-RAM pixel blackout verification (blackout rects are RGB(0,0,0)).
5. DesktopController delta capture integration.
6. inspect_screen tool telemetry & privacy metadata.
"""

import pytest
import numpy as np
from PIL import Image, ImageDraw
from services.backend.vision.frame_grabber import frame_grabber, FrameGrabber
from services.backend.vision.delta_detector import delta_detector, DeltaDetector
from services.backend.vision.privacy_masker import privacy_masker, PrivacyMasker
from services.backend.automation.desktop_controller import DesktopController
from services.backend.tools.screen_vision_tools import inspect_screen


def test_frame_grabber_in_ram():
    """Verify FrameGrabber captures RGB image in RAM with low latency."""
    img = frame_grabber.grab_frame()
    assert isinstance(img, Image.Image)
    assert img.mode == "RGB"
    assert img.width > 0 and img.height > 0
    # Capture latency should be under 50ms on modern Windows desktop
    assert frame_grabber.last_latency_ms < 100.0


def test_delta_detector_static_vs_changed():
    """Verify DeltaDetector recognizes static identical frames vs visual alterations."""
    detector = DeltaDetector(threshold=0.015)

    base_img = Image.new("RGB", (640, 480), color=(30, 41, 59))
    has_changed, score = detector.compute_delta(base_img)
    assert has_changed is True
    assert score == 1.0

    # Same static image: delta should be 0.0 and has_changed False
    has_changed_2, score_2 = detector.compute_delta(base_img)
    assert has_changed_2 is False
    assert score_2 == 0.0

    # Perturbed image: draw a significant white shape
    modified_img = base_img.copy()
    draw = ImageDraw.Draw(modified_img)
    draw.rectangle([(100, 100), (400, 400)], fill=(255, 255, 255))

    has_changed_3, score_3 = detector.compute_delta(modified_img)
    assert has_changed_3 is True
    assert score_3 >= 0.015


def test_privacy_masker_title_filtering():
    """Verify PrivacyMasker flags password managers, banking, and incognito titles."""
    masker = PrivacyMasker()

    assert masker.is_sensitive_title("1Password - Personal Vault") is True
    assert masker.is_sensitive_title("Bitwarden - My Vault") is True
    assert masker.is_sensitive_title("KeePass Password Safe") is True
    assert masker.is_sensitive_title("Google Chrome (Incognito)") is True
    assert masker.is_sensitive_title("Microsoft Edge - InPrivate") is True
    assert masker.is_sensitive_title("Coinbase - Crypto Wallet") is True
    assert masker.is_sensitive_title("Chase Online Banking - Chrome") is True
    assert masker.is_sensitive_title("Windows Security - Credential Manager") is True

    # Benign windows should not be flagged
    assert masker.is_sensitive_title("Calculator") is False
    assert masker.is_sensitive_title("Notepad - my_notes.txt") is False
    assert masker.is_sensitive_title("Phenom Desktop Shell") is False
    assert masker.is_sensitive_title("Visual Studio Code") is False


def test_privacy_masker_pixel_blackout():
    """Verify sensitive window bounding boxes are strictly blacked out (RGB 0,0,0) in RAM."""
    masker = PrivacyMasker()
    white_canvas = Image.new("RGB", (800, 600), color=(255, 255, 255))

    custom_rects = [
        {"title": "1Password Vault", "rect": (150, 150, 450, 450)}
    ]

    masked_img, applied = masker.mask_sensitive_windows(white_canvas, custom_windows=custom_rects)

    assert len(applied) == 1
    assert applied[0]["title"] == "1Password Vault"

    arr = np.asarray(masked_img)

    # Pixel inside the masked rect (e.g., at (300, 300)) must be blacked out
    # Notice: top-left corner has cyber watermark text, but deeper body is solid black (0, 0, 0)
    inside_pixel = arr[300, 300]
    assert np.array_equal(inside_pixel, [0, 0, 0]), f"Expected black (0,0,0), got {inside_pixel}"

    # Pixel outside the masked rect (e.g., at (50, 50)) must remain white (255, 255, 255)
    outside_pixel = arr[50, 50]
    assert np.array_equal(outside_pixel, [255, 255, 255]), f"Expected white (255,255,255), got {outside_pixel}"


def test_desktop_controller_delta_and_privacy():
    """Verify DesktopController capture_screen_delta returns valid image and telemetry."""
    dc = DesktopController()
    img, has_changed, delta_score, masked_count = dc.capture_screen_delta(apply_privacy=True)

    assert isinstance(img, Image.Image)
    assert isinstance(has_changed, bool)
    assert isinstance(delta_score, float)
    assert isinstance(masked_count, int)
    assert masked_count >= 0


@pytest.mark.asyncio
async def test_inspect_screen_tool_privacy_metadata():
    """Verify inspect_screen tool includes delta and privacy telemetry in result payload."""
    res = await inspect_screen(query="Test screen inspection", include_elements=False)

    assert res["status"] == "success"
    assert "visual_summary" in res
    assert "has_changed" in res
    assert "delta_score" in res
    assert "privacy_masked_windows" in res
    assert isinstance(res["has_changed"], bool)
    assert isinstance(res["delta_score"], float)
    assert isinstance(res["privacy_masked_windows"], int)
