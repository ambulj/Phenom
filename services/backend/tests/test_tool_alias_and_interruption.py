"""
Tests for Tool Alias Normalization and Interruption Fast-Paths
Verifies:
1. Orchestrator alias resolution (brave, youtube, chrome, spotify -> open_app)
2. Fast silence interception ("shut up", "stop", "chup", "shaant")
3. Voice coordinator silence trigger
"""

import pytest
import re
from services.backend.orchestrator.engine import orchestrator
from services.backend.tools.app_tools import resolve_application_path, open_app
from services.backend.voice.voice_coordinator import voice_coordinator

def test_tool_alias_resolution_apps():
    # Test browser / app alias
    tool, args = orchestrator._resolve_tool_alias("brave", {})
    assert tool == "open_app"
    assert args["app_name"] == "brave"

    tool, args = orchestrator._resolve_tool_alias("chrome", {})
    assert tool == "open_app"
    assert args["app_name"] == "chrome"

    tool, args = orchestrator._resolve_tool_alias("spotify", {})
    assert tool == "open_app"
    assert args["app_name"] == "spotify"

    tool, args = orchestrator._resolve_tool_alias("launch_app", {"name": "notepad"})
    assert tool == "open_app"
    assert args["app_name"] == "notepad"

def test_tool_alias_resolution_youtube():
    # Test YouTube with song query
    tool, args = orchestrator._resolve_tool_alias("youtube", {"play": "Baarishein"})
    assert tool == "open_app"
    assert "https://www.youtube.com/results?search_query=Baarishein" in args["app_name"]

    # Test generic YouTube
    tool, args = orchestrator._resolve_tool_alias("youtube", {"song": "<song_name>"})
    assert tool == "open_app"
    assert args["app_name"] == "https://www.youtube.com"

def test_resolve_application_path_registry_and_urls():
    brave_path = resolve_application_path("brave")
    assert "brave.exe" in brave_path.lower()

    chrome_path = resolve_application_path("chrome")
    assert "chrome.exe" in chrome_path.lower()

    url = "https://www.youtube.com/results?search_query=Baarishein"
    assert resolve_application_path(url) == url

@pytest.mark.asyncio
async def test_fast_silence_interception():
    # Test conversational turn silence
    events = []
    async for ev in orchestrator.run_conversation_turn("shut up"):
        events.append(ev)
    
    assert any(ev.get("type") == "chat.token" and "Sab shaant" in ev.get("payload", {}).get("token", "") for ev in events)
    assert any(ev.get("type") == "state.change" and ev.get("payload", {}).get("state") == "idle" for ev in events)

@pytest.mark.asyncio
async def test_voice_coordinator_silence():
    res = await voice_coordinator.process_transcript("chup ho ja")
    assert res.get("status") == "silence_triggered"
    assert res.get("interrupted") is True
