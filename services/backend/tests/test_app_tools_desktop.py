import pytest
import subprocess
from unittest.mock import patch, MagicMock
from services.backend.tools.app_tools import (
    resolve_application_path,
    open_app,
    close_app,
    _launch_on_default_desktop,
)

def test_resolve_application_path_url():
    assert resolve_application_path("https://youtube.com") == "https://youtube.com"
    assert resolve_application_path("http://localhost:8000") == "http://localhost:8000"

def test_resolve_application_path_known():
    resolved_brave = resolve_application_path("brave")
    assert "brave" in resolved_brave.lower()

    resolved_notepad = resolve_application_path("notepad")
    assert "notepad" in resolved_notepad.lower()

def test_open_app_url_invokes_desktop_launch():
    with patch("services.backend.tools.app_tools._launch_on_default_desktop", return_value=12345) as mock_launch:
        res = open_app("https://www.youtube.com/results?search_query=baarishein")
        assert res["launched"] is True
        assert res["launcher_pid"] == 12345
        mock_launch.assert_called_once()
        call_args = mock_launch.call_args[0][0]
        assert "cmd.exe /c start" in call_args
        assert "https://www.youtube.com/results?search_query=baarishein" in call_args

def test_open_app_browser_applies_chromium_flags():
    with patch("services.backend.tools.app_tools._launch_on_default_desktop", return_value=54321) as mock_launch:
        res = open_app("brave")
        assert res["launched"] is True
        assert res["launcher_pid"] == 54321
        mock_launch.assert_called_once()
        call_args = mock_launch.call_args[0][0]
        assert "--new-window" in call_args
        assert "--disable-gpu" in call_args
        assert "--disable-extensions" in call_args

def test_open_app_generic_executable():
    with patch("services.backend.tools.app_tools._launch_on_default_desktop", return_value=99999) as mock_launch:
        res = open_app("notepad")
        assert res["launched"] is True
        assert res["launcher_pid"] == 99999
        mock_launch.assert_called_once()


def test_run_wsl_command_mocked():
    from services.backend.tools.app_tools import run_wsl_command
    with patch("subprocess.run") as mock_run:
        mock_proc = MagicMock()
        mock_proc.returncode = 0
        mock_proc.stdout = "Linux kali 6.18.58-microsoft-standard-WSL2 x86_64\n"
        mock_proc.stderr = ""
        mock_run.return_value = mock_proc

        result = run_wsl_command("uname -a", distro="kali-linux")
        assert result["success"] is True
        assert result["returncode"] == 0
        assert "kali" in result["stdout"]
        mock_run.assert_called_once()
        cmd_called = mock_run.call_args[0][0]
        assert cmd_called == ["wsl", "-d", "kali-linux", "bash", "-c", "uname -a"]


def test_run_wsl_command_timeout():
    from services.backend.tools.app_tools import run_wsl_command
    with patch("subprocess.run", side_effect=subprocess.TimeoutExpired(cmd="sleep 10", timeout=2)):
        result = run_wsl_command("sleep 10", timeout_seconds=2)
        assert result["success"] is False
        assert result["returncode"] == -1
        assert "timed out after 2 seconds" in result["stderr"]
