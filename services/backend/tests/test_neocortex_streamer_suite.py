"""
Unit Tests for NEURAL-NEOCORTEX Screen Diffing & Framebuffer Streamer
Milestone 44.0: Project NEURAL-NEOCORTEX (Phase 1)
"""

import time
from pathlib import Path
import numpy as np
import pytest

from services.backend.safety.guardian import guardian
from services.backend.vision.neocortex_streamer import (
    neocortex_streamer,
    MAX_RING_BUFFER_FRAMES,
)
from services.backend.schemas.neocortex import ScreenFramePayload, NeocortexTelemetry


@pytest.fixture(autouse=True)
def clean_guardian_and_streamer():
    guardian.resume()
    neocortex_streamer.resume()
    neocortex_streamer.set_active_window("Terminal", "cmd.exe", is_sensitive=False)
    yield
    guardian.resume()
    neocortex_streamer.resume()


def generate_synthetic_screen_frame(width: int = 1280, height: int = 720, pattern_val: int = 100) -> np.ndarray:
    """Generates an in-RAM synthetic screen buffer (RGB uint8 array)."""
    frame = np.full((height, width, 3), pattern_val, dtype=np.uint8)
    # Add a mock terminal block
    frame[50:400, 50:600, :] = 20
    return frame


def test_frame_diffing_latency_under_20ms():
    """Verifies that in-RAM frame downsampling and diffing completes in < 20ms SLA."""
    streamer = neocortex_streamer
    frame1 = generate_synthetic_screen_frame(pattern_val=80)
    frame2 = generate_synthetic_screen_frame(pattern_val=150)

    # Initial frame
    res1 = streamer.process_frame(frame1, window_title="Kali WSL2", process_name="wsl.exe")
    assert res1.is_diff is True
    assert res1.width == 1280
    assert res1.height == 720

    # Second frame with diff
    t0 = time.perf_counter()
    res2 = streamer.process_frame(frame2, window_title="Kali WSL2", process_name="wsl.exe")
    elapsed_ms = (time.perf_counter() - t0) * 1000.0

    assert res2.is_diff is True
    assert res2.diff_ratio > 0.02
    assert streamer.last_frame_latency_ms < 20.0, f"Frame diff latency too high: {streamer.last_frame_latency_ms}ms"
    assert elapsed_ms < 30.0


def test_frame_dropping_on_identical_screen():
    """Verifies that static/unchanged frames are dropped and do not pollute the ring buffer."""
    streamer = neocortex_streamer
    frame = generate_synthetic_screen_frame(pattern_val=120)

    # First frame registers diff
    res1 = streamer.process_frame(frame)
    assert res1.is_diff is True

    # Identical frame should be dropped
    res2 = streamer.process_frame(frame)
    assert res2.is_diff is False
    assert res2.diff_ratio == 0.0
    assert streamer.frames_dropped >= 1


def test_in_ram_ring_buffer_ceiling_and_zero_disk():
    """Verifies that ring buffer never exceeds 60 frames in RAM and zero files are written (Rule 4)."""
    streamer = neocortex_streamer

    initial_png_count = len(list(Path(".").glob("*.png")))

    # Process 100 changing frames
    for i in range(100):
        frame = generate_synthetic_screen_frame(pattern_val=(i * 2) % 255)
        streamer.process_frame(frame, force_diff=True)

    telemetry = streamer.get_telemetry()
    assert telemetry.ring_buffer_frames <= MAX_RING_BUFFER_FRAMES
    assert telemetry.ring_buffer_frames == MAX_RING_BUFFER_FRAMES

    # Verify zero disk writes (Rule 4)
    final_png_count = len(list(Path(".").glob("*.png")))
    assert final_png_count == initial_png_count


def test_sensitive_window_blinding_policy():
    """Verifies that sensitive windows (e.g. password managers) replace frames with an opaque shield."""
    streamer = neocortex_streamer
    streamer.set_active_window(title="KeePassXC - Master Password", process_name="keepassxc.exe", is_sensitive=True)

    frame = generate_synthetic_screen_frame(pattern_val=200)
    payload = streamer.process_frame(frame)

    assert payload.is_blinded is True
    assert payload.active_window_title == "KeePassXC - Master Password"
    telemetry = streamer.get_telemetry()
    assert telemetry.is_blinded is True


def test_universal_guardian_kill_switch_visual_freeze_and_zeroization():
    """Verifies Guardian kill switch halts visual capture and zeroizes buffers in < 25ms SLA."""
    streamer = neocortex_streamer

    # Ingest frames into buffer
    frame = generate_synthetic_screen_frame(pattern_val=77)
    streamer.process_frame(frame, force_diff=True)
    assert streamer.get_telemetry().ring_buffer_frames > 0

    # Trigger emergency halt
    t0 = time.perf_counter()
    guardian.trigger("Visual surveillance emergency abort")
    lat_ms = (time.perf_counter() - t0) * 1000.0

    assert lat_ms < 25.0, f"Guardian SLA violation: {lat_ms}ms >= 25.0ms"
    assert guardian.is_halted is True
    assert streamer.get_telemetry().ring_buffer_frames == 0
    assert streamer.get_telemetry().is_active is False

    # Ensure subsequent frames are rejected while halted
    res = streamer.process_frame(frame)
    assert res.is_diff is False
    assert res.is_blinded is True
    assert res.active_window_title == "HALTED"
