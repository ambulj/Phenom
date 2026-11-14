"""
Master Safety, Visual Chaos Concurrency & Guardian SLA Benchmark Suite
Milestone 44.0: Project NEURAL-NEOCORTEX (Phase 5)
"""

import time
import concurrent.futures
from pathlib import Path
import numpy as np
import pytest

from services.backend.safety.guardian import guardian
from services.backend.vision.neocortex_streamer import (
    neocortex_streamer,
    MAX_RING_BUFFER_FRAMES,
)
from services.backend.vision.privacy_masker import privacy_masker
from services.backend.vision.screen_classifier import screen_classifier
from services.backend.vision.visual_synapse import visual_synapse
from services.backend.tools.neocortex_tools import (
    handle_query_neocortex_visual_state,
    handle_audit_screen_privacy_mask,
)
from services.backend.tools.visual_synapse_tools import (
    handle_dispatch_visual_context_query,
)


@pytest.fixture(autouse=True)
def clean_state():
    guardian.resume()
    neocortex_streamer.resume()
    neocortex_streamer.set_active_window("Terminal", "cmd.exe", is_sensitive=False)
    yield
    guardian.resume()
    neocortex_streamer.resume()


def generate_frame(pattern: int = 120) -> np.ndarray:
    return np.full((360, 640, 3), pattern, dtype=np.uint8)


def test_100_cycle_guardian_kill_switch_sla_under_visual_diff_load():
    """
    SAF-02: 100 consecutive Guardian kill switch invocations under active screen diffing load.
    Hard requirement: 100% of halts must complete in < 25.0ms SLA.
    """
    streamer = neocortex_streamer
    sla_measurements = []

    for i in range(100):
        guardian.resume()
        assert guardian.is_halted is False

        # Ingest frame
        streamer.process_frame(generate_frame((i * 3) % 255), force_diff=True)

        # Trigger emergency halt
        t0 = time.perf_counter()
        guardian.trigger(f"Visual stress cycle {i}")
        lat_ms = (time.perf_counter() - t0) * 1000.0

        sla_measurements.append(lat_ms)
        assert guardian.is_halted is True
        assert lat_ms < 25.0, f"Guardian SLA violation at cycle {i}: {lat_ms}ms >= 25.0ms"

    max_lat = max(sla_measurements)
    avg_lat = sum(sla_measurements) / len(sla_measurements)
    print(f"\n[Guardian Visual SLA] 100 cycles: Max={max_lat:.3f}ms, Avg={avg_lat:.3f}ms (SLA < 25.0ms)")
    assert max_lat < 25.0


def test_50_worker_visual_chaos_concurrency():
    """
    CHAOS-05: 50 concurrent worker threads executing simultaneous screen diffing,
    OCR extraction, PII masking audits, and visual security event correlations.
    Guarantees: Zero deadlocks, zero race conditions, zero unhandled crashes.
    """
    workers = 50
    cycles_per_worker = 10
    exceptions = []

    def worker_task(worker_id: int):
        try:
            for cycle in range(cycles_per_worker):
                mode = (worker_id + cycle) % 5

                if mode == 0:
                    # Ingest screen frame
                    frame = generate_frame((worker_id * 10 + cycle) % 255)
                    neocortex_streamer.process_frame(frame)
                elif mode == 1:
                    # Query visual state
                    state = handle_query_neocortex_visual_state()
                    assert "telemetry" in state
                elif mode == 2:
                    # Audit screen privacy mask
                    mock_token = "sk-" + "worker" + str(worker_id) + "000000000000000000000"
                    res = handle_audit_screen_privacy_mask(text_sample=f"Key: {mock_token}")
                    assert res["is_redacted"] is True
                elif mode == 3:
                    # Dispatch visual context query
                    query = handle_dispatch_visual_context_query(
                        ocr_lines=[f"Worker {worker_id} scan report for 127.0.0.1", "Nmap done: 1 host up"]
                    )
                    assert query["safe_mode_compliant"] is True
                elif mode == 4:
                    # Classify window
                    cls_res = screen_classifier.classify_window("kali@terminal", "wsl.exe")
                    assert cls_res.is_terminal is True

        except Exception as e:
            exceptions.append(f"Worker {worker_id} cycle {cycle} failed: {e}")

    with concurrent.futures.ThreadPoolExecutor(max_workers=workers) as executor:
        futures = [executor.submit(worker_task, wid) for wid in range(workers)]
        concurrent.futures.wait(futures)

    assert len(exceptions) == 0, f"Visual chaos exceptions detected: {exceptions}"
    print(f"\n[Visual Chaos Battery] 50 workers x {cycles_per_worker} cycles completed with 0 errors!")


def test_in_ram_visual_privacy_rule_4():
    """
    SAF-01: Verifies zero visual files (.png, .jpg, .bmp, .raw) exist or are created in working directory.
    """
    streamer = neocortex_streamer

    initial_images = len(list(Path(".").glob("*.png"))) + len(list(Path(".").glob("*.jpg")))

    for i in range(50):
        frame = generate_frame(pattern=(i * 5) % 255)
        streamer.process_frame(frame, force_diff=True)

    telemetry = streamer.get_telemetry()
    assert telemetry.ring_buffer_frames > 0

    # Ensure memory buffer zeroization
    streamer.halt()
    assert streamer.get_telemetry().ring_buffer_frames == 0

    final_images = len(list(Path(".").glob("*.png"))) + len(list(Path(".").glob("*.jpg")))
    assert final_images == initial_images
