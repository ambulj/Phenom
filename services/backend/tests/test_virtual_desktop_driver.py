"""
Unit tests for Virtual Desktop Driver: RAM capture and event injection.
"""

import pytest
from PIL import Image
from services.backend.automation.virtual_desktop_backend import MockVirtualDesktopBackend
from services.backend.automation.virtual_desktop_driver import (
    VirtualDesktopDriver,
    pack_client_coordinates,
    WM_LBUTTONDOWN,
    WM_LBUTTONUP,
    WM_MOUSEMOVE,
    WM_CHAR,
    WM_KEYDOWN,
    WM_KEYUP,
)
from services.backend.schemas.virtual_desktop import MouseButton


@pytest.fixture
def mock_backend():
    backend = MockVirtualDesktopBackend()
    backend.create_desktop("TestDesk")
    backend.launch_process("test_app.exe", None, "TestDesk")
    return backend


@pytest.fixture
def driver(mock_backend):
    return VirtualDesktopDriver(backend=mock_backend)


def test_pack_client_coordinates():
    # Test (100, 200): y << 16 | (x & 0xFFFF)
    lparam = pack_client_coordinates(100, 200)
    unpacked_x = lparam & 0xFFFF
    unpacked_y = (lparam >> 16) & 0xFFFF
    assert unpacked_x == 100
    assert unpacked_y == 200

    # Negative or large coordinates
    lparam2 = pack_client_coordinates(0, 0)
    assert lparam2 == 0


def test_capture_window_ram_zero_disk_io(driver, mock_backend):
    hwnd = list(mock_backend._windows.keys())[0]
    img = driver.capture_window_ram(hwnd)

    assert isinstance(img, Image.Image)
    assert img.size[0] > 0
    assert img.size[1] > 0
    assert img.mode in ("RGB", "RGBA")


def test_capture_window_base64(driver, mock_backend):
    hwnd = list(mock_backend._windows.keys())[0]
    b64_str = driver.capture_window_base64(hwnd)
    assert b64_str.startswith("data:image/jpeg;base64,")
    assert len(b64_str) > 100


def test_post_mouse_click_sequence(driver, mock_backend):
    hwnd = list(mock_backend._windows.keys())[0]
    mock_backend.injected_messages.clear()

    res = driver.post_mouse_click(hwnd, 250, 350, MouseButton.LEFT)
    assert res is True

    messages = mock_backend.injected_messages
    assert len(messages) == 3
    # 1. MOUSEMOVE
    assert messages[0][1] == WM_MOUSEMOVE
    # 2. LBUTTONDOWN
    assert messages[1][1] == WM_LBUTTONDOWN
    # 3. LBUTTONUP
    assert messages[2][1] == WM_LBUTTONUP

    expected_lparam = pack_client_coordinates(250, 350)
    assert messages[1][3] == expected_lparam
    assert messages[2][3] == expected_lparam


def test_post_mouse_drag_sequence(driver, mock_backend):
    hwnd = list(mock_backend._windows.keys())[0]
    mock_backend.injected_messages.clear()

    res = driver.post_mouse_drag(hwnd, 100, 100, 200, 200, steps=4)
    assert res is True

    messages = mock_backend.injected_messages
    # 1 initial move + 1 down + 3 intermediate moves + 1 final move + 1 up = 7 messages
    assert len(messages) >= 5
    assert messages[1][1] == WM_LBUTTONDOWN
    assert messages[-1][1] == WM_LBUTTONUP


def test_post_text_injection(driver, mock_backend):
    hwnd = list(mock_backend._windows.keys())[0]
    mock_backend.injected_messages.clear()

    res = driver.post_text(hwnd, "Phenom 10.0")
    assert res is True

    char_msgs = [m for m in mock_backend.injected_messages if m[1] == WM_CHAR]
    assert len(char_msgs) == len("Phenom 10.0")
    assert char_msgs[0][2] == ord("P")
    assert char_msgs[1][2] == ord("h")

    # Verify text reached mock window state
    assert mock_backend._windows[hwnd]["content_text"] == "Phenom 10.0"


def test_post_key_and_hotkey(driver, mock_backend):
    hwnd = list(mock_backend._windows.keys())[0]
    mock_backend.injected_messages.clear()

    res = driver.post_key(hwnd, "enter")
    assert res is True
    assert any(m[1] == WM_KEYDOWN and m[2] == 0x0D for m in mock_backend.injected_messages)
    assert any(m[1] == WM_KEYUP and m[2] == 0x0D for m in mock_backend.injected_messages)

    mock_backend.injected_messages.clear()
    hk_res = driver.post_hotkey(hwnd, "ctrl+s")
    assert hk_res is True
    # Ctrl down, S down, S up, Ctrl up
    assert len(mock_backend.injected_messages) == 4
