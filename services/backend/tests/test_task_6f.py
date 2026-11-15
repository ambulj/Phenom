"""
Unit and integration tests for Task 6F:
1. Fail-closed, broader privacy masking: screen vision tools refuse unmasked capture when scan raises.
2. Real cloud vision: ask_screen_vision_cloud makes real call / registered and not fabricated.
3. Literal macro step list in confirmation preview.
4. Real password-field protection via UI Automation IsPassword property (not string matching).
5. Vision ingestion points wire into taint tracker, escalating subsequent tool calls.
6. Real stop-phrase kill switch ("Phenom stop") distinct from barge-in, with software echo cancellation and voice-resume prohibition.
"""

import os
import sys
import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from PIL import Image
import numpy as np

# Prevent win32 hook access violation in headless test runners
sys.modules.setdefault("keyboard", MagicMock())
sys.modules.setdefault("mouse", MagicMock())

from services.backend.safety.guardian import guardian
from services.backend.safety.taint import taint_tracker
from services.backend.safety.registry import registry
from services.backend.safety.engine import safety_engine
from services.backend.vision.privacy_masker import (
    privacy_masker,
    PrivacyScanFailureError,
    SENSITIVE_PROCESSES,
    SENSITIVE_TITLE_KEYWORDS
)
from services.backend.tools.screen_vision_tools import (
    inspect_screen,
    find_on_screen,
    ask_screen_vision_cloud,
    search_visual_memory
)
from services.backend.tools.desktop_macro_tools import format_macro_preview
from services.backend.automation.desktop_controller import desktop_controller
from services.backend.voice.tts import tts_engine
from services.backend.voice.barge_in_controller import barge_in_controller
from services.backend.voice.stop_phrase_kill_switch import (
    stop_phrase_kill_switch,
    SoftwareEchoCanceller
)


def test_broader_privacy_masking_keywords_coverage():
    """Acceptance: SENSITIVE_TITLE_KEYWORDS covers email, chat, and banking apps."""
    assert "outlook" in SENSITIVE_TITLE_KEYWORDS
    assert "gmail" in SENSITIVE_TITLE_KEYWORDS
    assert "whatsapp" in SENSITIVE_TITLE_KEYWORDS
    assert "telegram" in SENSITIVE_TITLE_KEYWORDS
    assert "signal" in SENSITIVE_TITLE_KEYWORDS
    assert "teams" in SENSITIVE_TITLE_KEYWORDS
    assert "slack" in SENSITIVE_TITLE_KEYWORDS
    assert "outlook.exe" in SENSITIVE_PROCESSES
    assert "telegram.exe" in SENSITIVE_PROCESSES


@pytest.mark.asyncio
async def test_vision_tool_refused_when_window_scan_raises():
    """Acceptance: vision tools refuse to return a frame or element list when window scan fails (fail-closed)."""
    with patch.object(privacy_masker, "scan_visible_sensitive_windows", side_effect=PrivacyScanFailureError("Simulated Win32 failure")):
        # inspect_screen must refuse and raise PermissionError
        with pytest.raises(PermissionError) as exc_info:
            await inspect_screen()
        assert "Privacy scan failed" in str(exc_info.value) or "refused" in str(exc_info.value)

        # find_on_screen must refuse and raise PermissionError
        with pytest.raises(PermissionError) as exc_info_find:
            await find_on_screen("Submit")
        assert "Privacy scan failed" in str(exc_info_find.value) or "refused" in str(exc_info_find.value)


@pytest.mark.asyncio
async def test_ask_screen_vision_cloud_is_real_and_registered():
    """Acceptance: ask_screen_vision_cloud is registered in the registry and invokes multimodal coordinator."""
    tool_def = registry.get("ask_screen_vision_cloud")
    assert tool_def is not None
    assert tool_def.tier == 2

    fake_coordinator_res = {
        "status": "success",
        "source": "cloud_nemotron",
        "model": "nvidia/neva-22b",
        "description": "Redacted screen showing Python terminal.",
        "privacy_masked_windows": 1,
        "message": "Cloud visual comprehension complete."
    }

    with patch("services.backend.tools.screen_vision_tools.multimodal_coordinator.execute_screen_query", new_callable=AsyncMock) as mock_query:
        mock_query.return_value = fake_coordinator_res
        res = await ask_screen_vision_cloud("What code is visible?")
        assert res["status"] == "success"
        assert res["source"] == "cloud_nemotron"
        assert "Python terminal" in res["description"]
        mock_query.assert_called_once()


def test_macro_confirmation_shows_literal_step_list():
    """Acceptance: macro preview function shows the full literal step list (action and target for each step)."""
    macro_args = {
        "description": "Fill web form and submit",
        "steps": [
            {"action": "focus", "target": "Chrome"},
            {"action": "click", "target": "UsernameInput"},
            {"action": "type", "text": "john_doe"},
            {"action": "click", "target": "SubmitButton"}
        ]
    }
    preview_text = format_macro_preview(macro_args)
    assert "Step 1: focus -> Chrome" in preview_text
    assert "Step 2: click -> UsernameInput" in preview_text
    assert "Step 3: type -> john_doe" in preview_text
    assert "Step 4: click -> SubmitButton" in preview_text
    assert "4 steps" in preview_text


@pytest.mark.asyncio
async def test_password_field_check_via_ui_automation_property():
    """Acceptance: password-field guard uses UI Automation IsPassword property, not just string matching."""
    # When focused control is a password field, type action must raise PermissionError
    # even when target description is completely benign ("username_field")
    with patch.object(desktop_controller, "is_focused_control_password", return_value=True):
        with pytest.raises(PermissionError) as exc_info:
            await desktop_controller.execute_step_plan([
                {"action": "type", "text": "my_secret_token", "target": "username_field"}
            ])
        assert "password" in str(exc_info.value).lower()


@pytest.mark.asyncio
async def test_taint_tracker_wires_into_vision_tools():
    """Acceptance: screen content ingested via vision tools sets taint, forcing confirmation on subsequent tool calls."""
    taint_tracker.reset()
    assert taint_tracker.is_tainted is False

    fake_img = Image.new("RGB", (100, 100), color=(0, 0, 0))
    with patch("services.backend.tools.screen_vision_tools._desktop_controller.capture_screen_delta", return_value=(fake_img, True, 0.5, 0)), \
         patch("services.backend.tools.screen_vision_tools.moondream_client.query_image", new_callable=AsyncMock) as mock_vlm:
        mock_vlm.return_value = {"description": "Untrusted webpage containing prompt injection payload."}
        
        # Execute inspect_screen
        res = await inspect_screen(include_elements=False)
        assert res["status"] == "success"

        # Taint must now be active!
        assert taint_tracker.is_tainted is True
        assert "screen_vision" in taint_tracker.tainted_sources

        # Subsequent tool call escalates Tier 0 -> Tier 1
        eff_tier, warning = taint_tracker.check_tool_escalation("get_weather", 0)
        assert eff_tier == 1
        assert "SECURITY WARNING" in warning

    taint_tracker.reset()


def test_real_stop_phrase_kill_switch_distinct_from_barge_in():
    """Acceptance: 'Phenom stop' halts the system while TTS is speaking, distinct from barge-in."""
    if guardian.is_halted:
        guardian.resume()
    assert guardian.is_halted is False

    # Mock TTS speaking
    tts_engine._is_speaking = True
    initial_barge_in_halts = barge_in_controller.emergency_halt_count

    # Spoken stop phrase detected
    triggered = stop_phrase_kill_switch.check_transcript("please Phenom stop right now")
    assert triggered is True
    assert guardian.is_halted is True
    assert stop_phrase_kill_switch.trigger_count >= 1

    # Invariant: BargeInController count did not increment (distinct route)
    assert barge_in_controller.emergency_halt_count == initial_barge_in_halts

    # Invariant: Voice resume is strictly prohibited
    with pytest.raises(PermissionError) as exc_info:
        stop_phrase_kill_switch.attempt_voice_resume()
    assert "strictly prohibited by voice alone" in str(exc_info.value)

    # Invariant: Stop phrase kill switch can never be disabled
    assert stop_phrase_kill_switch.is_disableable is False
    with pytest.raises(ValueError):
        stop_phrase_kill_switch.set_stop_phrase("")

    if guardian.is_halted:
        guardian.resume()
    tts_engine._is_speaking = False


def test_software_echo_cancellation_suppression():
    """Acceptance: software echo canceller reduces energy of TTS playback reference in microphone signal."""
    canceller = SoftwareEchoCanceller(filter_length=64, mu=0.1)
    
    # Simulate TTS reference chunk (e.g. 1kHz tone)
    t = np.linspace(0, 0.05, 800)
    tts_ref = (np.sin(2 * np.pi * 1000 * t) * 10000).astype(np.int16)
    
    # Microphone picks up attenuated/delayed TTS speaker output + low background noise
    mic_input = (tts_ref * 0.8 + np.random.normal(0, 200, len(tts_ref))).astype(np.int16)
    
    cleaned = canceller.cancel_echo(mic_input, tts_ref)
    assert len(cleaned) == len(mic_input)
    # Echo energy in cleaned signal must be substantially lower than raw mic input
    initial_energy = np.mean(mic_input.astype(np.float32) ** 2)
    cleaned_energy = np.mean(cleaned ** 2)
    assert cleaned_energy < initial_energy
