"""
Unit & Integration Test Suite for Milestone 17 Phase 3:
Remote Telegram Mobile Super-Companion & Bidirectional Controls (TEL-02, SAF-01, SAF-02)
"""

import asyncio
import time
import pytest
from unittest.mock import MagicMock, AsyncMock, patch

from services.backend.remote.telegram_bot import TelegramBotController
from services.backend.remote.telegram_client import TelegramClient
from services.backend.safety.guardian import guardian
from services.backend.safety.registry import registry
import services.backend.tools.telegram_tools


@pytest.fixture
def mock_client():
    client = MagicMock(spec=TelegramClient)
    client.send_message = AsyncMock(return_value={"message_id": 100})
    client.edit_message_text = AsyncMock(return_value={"message_id": 100})
    client.answer_callback_query = AsyncMock(return_value=True)
    client.send_approval_request = AsyncMock(return_value={"message_id": 101})
    client.send_photo = AsyncMock(return_value={"message_id": 102})
    client.delete_message = AsyncMock(return_value=True)
    return client


@pytest.fixture
def bot_controller(mock_client):
    owner_id = 999888777
    token = "fake_test_token"
    bot = TelegramBotController(token=token, owner_id=owner_id, client=mock_client)
    return bot


def test_telegram_v2_registered_safety_tiers():
    """
    SAF-01: Verify all Telegram companion tools are registered with strict safety tiers and preview functions.
    """
    # 1. get_telegram_companion_status (Tier 0)
    status_tool = registry.get("get_telegram_companion_status")
    assert status_tool is not None, "Tool 'get_telegram_companion_status' missing from ToolRegistry"
    assert int(status_tool.tier) == 0

    # 2. send_telegram_snapshot (Tier 1)
    snapshot_tool = registry.get("send_telegram_snapshot")
    assert snapshot_tool is not None, "Tool 'send_telegram_snapshot' missing from ToolRegistry"
    assert int(snapshot_tool.tier) == 1
    assert snapshot_tool.preview_fn is not None
    preview_snap = snapshot_tool.preview_fn({})
    assert "Send privacy-masked desktop snapshot" in preview_snap

    # 3. register_telegram_action (Tier 1)
    action_tool = registry.get("register_telegram_action")
    assert action_tool is not None, "Tool 'register_telegram_action' missing from ToolRegistry"
    assert int(action_tool.tier) == 1
    assert action_tool.preview_fn is not None
    preview_act = action_tool.preview_fn({"action_id": "chill_btn", "label": "Chill Mode"})
    assert "Register remote action button 'chill_btn'" in preview_act

    # 4. Backward compatibility: telegram_get_remote_status (Tier 0)
    legacy_status_tool = registry.get("telegram_get_remote_status")
    assert legacy_status_tool is not None
    assert int(legacy_status_tool.tier) == 0


@pytest.mark.asyncio
async def test_interactive_controls_menu_and_callbacks(bot_controller, mock_client):
    """
    TEL-02.2: Test /controls & /menu text commands and bidirectional callback dispatches.
    """
    # 1. Test /controls text command
    update_controls = {
        "update_id": 1,
        "message": {
            "message_id": 1,
            "from": {"id": bot_controller.owner_id},
            "chat": {"id": bot_controller.owner_id},
            "text": "/controls"
        }
    }
    res = await bot_controller.process_update(update_controls)
    assert res["status"] == "controls_sent"
    mock_client.send_message.assert_called()
    markup = mock_client.send_message.call_args[1].get("reply_markup", {})
    assert "inline_keyboard" in markup
    assert len(markup["inline_keyboard"]) >= 5

    # 2. Test Media Callback (Play/Pause)
    with patch("services.backend.tools.media_tools._send_virtual_key") as mock_vk:
        update_media = {
            "update_id": 2,
            "callback_query": {
                "id": "cb_media",
                "from": {"id": bot_controller.owner_id},
                "data": "cmd:media:toggle",
                "message": {"message_id": 2, "chat": {"id": bot_controller.owner_id}}
            }
        }
        res_media = await bot_controller.process_update(update_media)
        assert res_media["status"] == "media_executed"
        mock_vk.assert_called_once()
        mock_client.answer_callback_query.assert_called_with("cb_media", text="Toggled Media Play/Pause")

    # 3. Test Window Callback (Dev Mode)
    with patch("services.backend.tools.window_tiler.apply_window_layout", new_callable=AsyncMock) as mock_dev:
        update_window = {
            "update_id": 3,
            "callback_query": {
                "id": "cb_window",
                "from": {"id": bot_controller.owner_id},
                "data": "cmd:window:dev",
                "message": {"message_id": 3, "chat": {"id": bot_controller.owner_id}}
            }
        }
        res_window = await bot_controller.process_update(update_window)
        assert res_window["status"] == "window_executed"
        mock_dev.assert_called_once_with("dev_mode")

    # 4. Test Model Routing Callback (Coder)
    with patch("services.backend.router.dynamic_model_router.dynamic_model_router.set_override") as mock_model:
        update_model = {
            "update_id": 4,
            "callback_query": {
                "id": "cb_model",
                "from": {"id": bot_controller.owner_id},
                "data": "cmd:model:coder",
                "message": {"message_id": 4, "chat": {"id": bot_controller.owner_id}}
            }
        }
        res_model = await bot_controller.process_update(update_model)
        assert res_model["status"] == "model_routed"
        mock_model.assert_called_with("coder")

    # 5. Test Voice Style Callback (Whisper)
    with patch("services.backend.voice.prosody_manager.prosody_manager.set_style") as mock_voice:
        update_voice = {
            "update_id": 5,
            "callback_query": {
                "id": "cb_voice",
                "from": {"id": bot_controller.owner_id},
                "data": "cmd:voice:whisper",
                "message": {"message_id": 5, "chat": {"id": bot_controller.owner_id}}
            }
        }
        res_voice = await bot_controller.process_update(update_voice)
        assert res_voice["status"] == "voice_styled"
        mock_voice.assert_called_with("whisper")


@pytest.mark.asyncio
async def test_privacy_masked_desktop_snapshot_command_and_tool(bot_controller, mock_client):
    """
    TEL-02.1 & Rule 4: Verify desktop snapshot applies 35px privacy blur and sends photo preview.
    """
    from PIL import Image

    # Mock screen capture with 1 redacted window
    mock_img = Image.new("RGB", (640, 480), color=(30, 30, 30))
    redacted = [{"title": "Banking Portal", "rect": (0, 0, 100, 100)}]

    with patch("services.backend.remote.telegram_bot.capture_and_obfuscate_screen", return_value=(mock_img, redacted)):
        # 1. Test /snapshot command
        update_snap = {
            "update_id": 6,
            "message": {
                "message_id": 6,
                "from": {"id": bot_controller.owner_id},
                "chat": {"id": bot_controller.owner_id},
                "text": "/snapshot"
            }
        }
        res = await bot_controller.process_update(update_snap)
        assert res["status"] == "screenshot_sent"
        assert res["redacted_count"] == 1
        mock_client.send_photo.assert_called_once()
        caption = mock_client.send_photo.call_args[1].get("caption", "")
        assert "Image transits Telegram servers" in caption
        assert "35px Gaussian Blur applied to sensitive windows" in caption


@pytest.mark.asyncio
async def test_dynamic_custom_action_registration_and_execution(bot_controller, mock_client):
    """
    TEL-02.2 & TEL-02.3: Test dynamic registration of custom action buttons and invocation.
    """
    # 1. Register custom action
    action = bot_controller.register_custom_action(
        action_id="quick_mute",
        label="Quick Mute",
        tool_name="get_telegram_companion_status",
        args={}
    )
    assert action["action_id"] == "quick_mute"
    assert len(bot_controller.get_registered_actions()) == 1

    # 2. Verify registered action appears in controls markup
    markup = bot_controller._build_controls_markup()
    action_button_found = False
    for row in markup["inline_keyboard"]:
        for btn in row:
            if btn.get("callback_data") == "action:quick_mute":
                action_button_found = True
                assert "Quick Mute" in btn.get("text", "")
    assert action_button_found is True

    # 3. Invoke custom action via callback
    update_custom = {
        "update_id": 7,
        "callback_query": {
            "id": "cb_custom",
            "from": {"id": bot_controller.owner_id},
            "data": "action:quick_mute",
            "message": {"message_id": 7, "chat": {"id": bot_controller.owner_id}}
        }
    }
    res_custom = await bot_controller.process_update(update_custom)
    assert res_custom["status"] == "action_executed"
    assert res_custom["action_id"] == "quick_mute"


@pytest.mark.asyncio
async def test_concurrent_callback_burst_safety(bot_controller, mock_client):
    """
    SAF-02.2: Concurrency burst simulating 20 simultaneous callback queries to verify thread/asyncio safety.
    """
    with patch("services.backend.tools.media_tools._send_virtual_key"):
        tasks = []
        for i in range(20):
            update = {
                "update_id": 100 + i,
                "callback_query": {
                    "id": f"cb_{i}",
                    "from": {"id": bot_controller.owner_id},
                    "data": "cmd:media:toggle" if i % 2 == 0 else "status:refresh",
                    "message": {"message_id": 100 + i, "chat": {"id": bot_controller.owner_id}}
                }
            }
            tasks.append(bot_controller.process_update(update))

        results = await asyncio.gather(*tasks)
        assert len(results) == 20
        for r in results:
            assert r["status"] in ("media_executed", "status_refreshed")


def test_remote_kill_switch_sla_benchmark(bot_controller, mock_client):
    """
    TEL-02.4 & SAF-02.1: Universal Guardian kill switch synchronous halt SLA benchmark (< 25.0ms SLA).
    """
    guardian.resume()
    assert guardian.is_halted is False

    latencies = []
    # Benchmark 50 consecutive synchronous halt cycles
    for i in range(50):
        t0 = time.perf_counter()
        guardian.trigger("Telegram benchmark remote halt")
        t1 = time.perf_counter()
        latencies.append((t1 - t0) * 1000.0)
        guardian.resume()

    avg_latency = sum(latencies) / len(latencies)
    max_latency = max(latencies)

    print(f"\n[Milestone 17 Phase 3 SLA Benchmark] Remote Kill Switch: Avg={avg_latency:.4f}ms, Max={max_latency:.4f}ms across 50 runs")
    assert avg_latency < 25.0, f"Average kill switch latency {avg_latency:.4f}ms exceeded 25.0ms SLA"
    assert max_latency < 25.0, f"Maximum kill switch latency {max_latency:.4f}ms exceeded 25.0ms SLA"
