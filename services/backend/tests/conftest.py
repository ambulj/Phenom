"""
Pytest configuration and custom marker hooks for Phenom backend tests.
Handles automatic skipping for Windows-only and audio-hardware dependent tests.
"""

import sys
import pytest

def has_working_audio() -> bool:
    try:
        import sounddevice as sd
        devices = sd.query_devices()
        return len(devices) > 0
    except Exception:
        return False

AUDIO_AVAILABLE = has_working_audio()
IS_WINDOWS = sys.platform == "win32"

def pytest_configure(config):
    config.addinivalue_line(
        "markers", "windows_only: Mark test as requiring Windows OS (APIs, registry, win32cred, uiautomation)"
    )
    config.addinivalue_line(
        "markers", "needs_audio: Mark test as requiring PortAudio and working audio hardware"
    )
    config.addinivalue_line(
        "markers", "slow: Mark test as slow-running (heavy models, long timeouts)"
    )
    config.addinivalue_line(
        "markers", "needs_gpu: Mark test as requiring NVIDIA GPU / CUDA"
    )

def pytest_collection_modifyitems(config, items):
    skip_windows = pytest.mark.skip(reason="Test requires Windows OS (sys.platform == 'win32')")
    skip_audio = pytest.mark.skip(reason="Test requires PortAudio and active audio hardware")

    for item in items:
        if "windows_only" in item.keywords and not IS_WINDOWS:
            item.add_marker(skip_windows)
        if "needs_audio" in item.keywords and not AUDIO_AVAILABLE:
            item.add_marker(skip_audio)
