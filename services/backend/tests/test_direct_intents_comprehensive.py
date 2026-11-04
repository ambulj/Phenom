import pytest
import urllib.parse
from services.backend.orchestrator.engine import orchestrator
from services.backend.tools.app_tools import open_app, resolve_application_path

def test_yt_music_intents():
    # Test "play music from yt"
    res1 = orchestrator._detect_direct_intent("play music from yt")
    assert res1 is not None
    tool, args, msg = res1
    assert tool == "open_app"
    assert "youtube.com/results?search_query=" in args["app_name"]
    assert "trending" in args["app_name"].lower() or "hits" in args["app_name"].lower()

    # Test "play baarishein on yt"
    res2 = orchestrator._detect_direct_intent("play baarishein on yt")
    assert res2 is not None
    tool, args, msg = res2
    assert "baarishein" in args["app_name"].lower()

    # Test "play baarishein on youtube"
    res3 = orchestrator._detect_direct_intent("play baarishein on youtube")
    assert res3 is not None
    assert "baarishein" in res3[1]["app_name"].lower()

    # Test "open yt" and "open youtube"
    res4 = orchestrator._detect_direct_intent("open yt")
    assert res4 is not None
    assert res4[1]["app_name"] == "https://www.youtube.com"

    res5 = orchestrator._detect_direct_intent("open youtube")
    assert res5 is not None
    assert res5[1]["app_name"] == "https://www.youtube.com"

def test_website_intents():
    # Test "open google.com"
    res1 = orchestrator._detect_direct_intent("open google.com")
    assert res1 is not None
    assert res1[1]["app_name"] == "https://google.com"

    # Test "open website amazon"
    res2 = orchestrator._detect_direct_intent("open website amazon")
    assert res2 is not None
    assert "amazon.com" in res2[1]["app_name"]

    # Test "open github.com"
    res3 = orchestrator._detect_direct_intent("open github.com")
    assert res3 is not None
    assert res3[1]["app_name"] == "https://github.com"

def test_app_intents():
    # Test "open brave"
    res1 = orchestrator._detect_direct_intent("open brave")
    assert res1 is not None
    assert res1[1]["app_name"] == "brave"

    # Test "open notepad"
    res2 = orchestrator._detect_direct_intent("open notepad")
    assert res2 is not None
    assert res2[1]["app_name"] == "notepad"
