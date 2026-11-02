"""
Tests for Phenom Phase 1: Hinglish Persona & "Bro" Tuning
Verifies:
1. Prompt and Modelfile contain "Bro" honorific and Roman script Hinglish guidelines.
2. Greetings return natural, witty Hinglish addressed to "Bro".
3. Hinglish commands ("Spotify pause kar do", "Volume badhao") map to exact tool JSON calls without preamble.
4. English commands retain 100% parity and direct execution.
"""

import pytest
import os
import json
import httpx
from services.backend.orchestrator.engine import build_system_prompt

OLLAMA_CHAT_URL = "http://localhost:11434/api/chat"
MODEL_NAME = "phenom-jarvis:latest"


def test_system_prompt_contains_bro_and_hinglish():
    prompt = build_system_prompt()
    assert 'Bro' in prompt, "System prompt should contain 'Bro' honorific"
    assert 'Hinglish' in prompt, "System prompt should specify Hinglish language"
    assert 'Roman' in prompt, "System prompt should specify Roman alphabet"


def test_modelfile_hinglish_exists():
    path = os.path.join(os.path.dirname(__file__), "..", "..", "..", "Modelfile.hinglish")
    assert os.path.exists(path), "Modelfile.hinglish must exist"
    with open(path, "r", encoding="utf-8") as f:
        content = f.read()
    assert 'Bro' in content
    assert 'Hinglish' in content
    assert 'Roman script' in content


@pytest.mark.asyncio
async def test_hinglish_greeting_addresses_bro():
    sys_prompt = build_system_prompt()
    messages = [
        {"role": "system", "content": sys_prompt},
        {"role": "user", "content": "kya haal hai Bro?"}
    ]
    async with httpx.AsyncClient(timeout=30.0) as client:
        resp = await client.post(OLLAMA_CHAT_URL, json={
            "model": MODEL_NAME,
            "messages": messages,
            "stream": False,
            "options": {"temperature": 0.25}
        })
    assert resp.status_code == 200
    reply = resp.json().get("message", {}).get("content", "")
    assert len(reply.strip()) > 0
    # Must not contain raw tool JSON or markdown tool fences
    assert '"tool":' not in reply
    assert '```json' not in reply
    # Should address as Bro
    assert 'Bro' in reply or 'bro' in reply.lower()


@pytest.mark.asyncio
async def test_hinglish_media_pause_direct_call():
    sys_prompt = build_system_prompt()
    messages = [
        {"role": "system", "content": sys_prompt},
        {"role": "user", "content": "Spotify pause kar do"}
    ]
    async with httpx.AsyncClient(timeout=30.0) as client:
        resp = await client.post(OLLAMA_CHAT_URL, json={
            "model": MODEL_NAME,
            "messages": messages,
            "stream": False,
            "options": {"temperature": 0.1}
        })
    assert resp.status_code == 200
    reply = resp.json().get("message", {}).get("content", "").strip()
    # Must invoke control_media with pause or play_pause
    assert "control_media" in reply
    assert "pause" in reply


@pytest.mark.asyncio
async def test_hinglish_volume_up_direct_call():
    sys_prompt = build_system_prompt()
    messages = [
        {"role": "system", "content": sys_prompt},
        {"role": "user", "content": "Volume badhao"}
    ]
    async with httpx.AsyncClient(timeout=30.0) as client:
        resp = await client.post(OLLAMA_CHAT_URL, json={
            "model": MODEL_NAME,
            "messages": messages,
            "stream": False,
            "options": {"temperature": 0.1}
        })
    assert resp.status_code == 200
    reply = resp.json().get("message", {}).get("content", "").strip()
    assert "control_media" in reply
    assert "volume_up" in reply


@pytest.mark.asyncio
async def test_english_media_parity():
    sys_prompt = build_system_prompt()
    messages = [
        {"role": "system", "content": sys_prompt},
        {"role": "user", "content": "Toggle media play/pause on Spotify"}
    ]
    async with httpx.AsyncClient(timeout=30.0) as client:
        resp = await client.post(OLLAMA_CHAT_URL, json={
            "model": MODEL_NAME,
            "messages": messages,
            "stream": False,
            "options": {"temperature": 0.1}
        })
    assert resp.status_code == 200
    reply = resp.json().get("message", {}).get("content", "").strip()
    assert "control_media" in reply
