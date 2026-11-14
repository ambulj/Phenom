"""Master Safety Audit, Chaos Concurrency Battery & Release Verification (Milestone 46.0 Phase 5)."""

import concurrent.futures
import time
import pytest
from services.backend.safety.guardian import guardian
from services.backend.schemas.telegram import (
    TelegramChat,
    TelegramMessage,
    TelegramUpdate,
    TelegramUser,
)
from services.backend.telegram.bot_controller import bot_controller
from services.backend.telegram.screen_snapshot import telegram_snapshot_provider
from services.backend.telegram.voice_pipeline import telegram_voice_pipeline
from services.backend.tools.telegram_tools import (
    handle_dispatch_telegram_notification,
    handle_send_telegram_voice_note,
)

AUTH_USER_ID = 888999000


@pytest.fixture(autouse=True)
def clean_guardian_and_telegram():
    """Ensure guardian and bot controller are clean before and after each test."""
    guardian.resume()
    bot_controller.set_authorized_user_id(AUTH_USER_ID)
    bot_controller.outbound_messages.clear()
    yield
    guardian.resume()


def create_msg_update(user_id: int, text: str) -> TelegramUpdate:
    return TelegramUpdate(
        update_id=5000,
        message=TelegramMessage(
            message_id=6000,
            from_user=TelegramUser(id=user_id, first_name="Owner"),
            chat=TelegramChat(id=user_id, type="private"),
            date=int(time.time()),
            text=text,
        )
    )


def test_100_cycle_remote_guardian_kill_switch_sla_under_telegram_load():
    """Executes 100 consecutive remote Guardian kill switch cycles under active Telegram command load.
    Hard SLA: max latency strictly < 25.0 ms (Rule 3).
    """
    latencies = []
    update_halt = create_msg_update(AUTH_USER_ID, "/halt")
    update_resume = create_msg_update(AUTH_USER_ID, "/resume")

    for _ in range(100):
        guardian.resume()
        assert guardian.is_halted is False

        # Measure synchronous remote trigger latency
        t0 = time.perf_counter()
        res = bot_controller.handle_update(update_halt)
        elapsed_ms = (time.perf_counter() - t0) * 1000.0

        assert res.success is True
        assert res.guardian_triggered is True
        assert guardian.is_halted is True
        latencies.append(elapsed_ms)

        # Clear state
        bot_controller.handle_update(update_resume)
        assert guardian.is_halted is False

    max_lat = max(latencies)
    avg_lat = sum(latencies) / len(latencies)

    assert max_lat < 25.0, f"Remote Guardian SLA breached: max={max_lat:.3f}ms >= 25.0ms"
    assert avg_lat < 5.0, f"Average trigger latency unusually high: {avg_lat:.3f}ms"


def test_50_worker_remote_uplink_chaos_concurrency():
    """Stress tests the Remote Uplink with 50 concurrent worker threads executing 500 operations.
    Validates re-entrancy, zero deadlocks, and zero unhandled exceptions.
    """
    mock_audio = b"OGG_CHAOS_TEST_STREAM"

    def worker_task(worker_id: int) -> int:
        success_count = 0
        for cycle in range(10):
            op = (worker_id + cycle) % 5

            if op == 0:
                # Bot command update
                up = create_msg_update(AUTH_USER_ID, "/status")
                res = bot_controller.handle_update(up)
                if res.success:
                    success_count += 1
            elif op == 1:
                # Voice note ingestion
                _, _, reply_audio, halted = telegram_voice_pipeline.process_incoming_voice_note(
                    audio_bytes=mock_audio,
                    mock_transcription=f"Worker {worker_id} status query",
                )
                if reply_audio is not None and not halted:
                    success_count += 1
            elif op == 2:
                # Screen snapshot capture
                img, shielded, _ = telegram_snapshot_provider.capture_snapshot(
                    active_window_title="VS Code",
                    active_window_process="code.exe",
                )
                if img and not shielded:
                    success_count += 1
            elif op == 3:
                # Notification tool
                n_res = handle_dispatch_telegram_notification(text=f"Worker {worker_id} heartbeat")
                if n_res["success"]:
                    success_count += 1
            elif op == 4:
                # Voice note tool
                v_res = handle_send_telegram_voice_note(text=f"Worker {worker_id} synthesized response")
                if v_res["success"]:
                    success_count += 1

        return success_count

    with concurrent.futures.ThreadPoolExecutor(max_workers=50) as executor:
        futures = [executor.submit(worker_task, w_id) for w_id in range(50)]
        results = [f.result(timeout=15.0) for f in futures]

    assert len(results) == 50
    total_successful_ops = sum(results)
    assert total_successful_ops == 500, f"Expected 500 successful ops, got {total_successful_ops}"


def test_unauthorized_sender_silent_rejection_security_audit():
    """Verifies that unauthorized sender IDs are consistently dropped silently with zero leakage."""
    unauthorized_ids = [
        111111111, 222222222, 333333333, 444444444, 555555555,
        666666666, 777777777, 888888888, 123456789, 987654321,
    ]

    for uid in unauthorized_ids:
        up = create_msg_update(uid, "/status")
        res = bot_controller.handle_update(up)
        assert res.authorized is False
        assert res.success is False
        assert res.command == "UNAUTHORIZED_DROP"
        assert len(bot_controller.outbound_messages) == 0
