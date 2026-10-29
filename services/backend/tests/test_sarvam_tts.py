"""
Unit Tests for Sarvam AI Cloud Hindi TTS & Privacy Guard
"""

import base64
import os
import pytest
from unittest.mock import patch, MagicMock

from services.backend.voice.cloud_tts import SarvamTTSClient

@pytest.fixture
def sarvam_client():
    client = SarvamTTSClient(api_key="mock-sarvam-key")
    return client

def test_hindi_hinglish_detection(sarvam_client):
    # Devanagari Hindi
    assert sarvam_client.is_hindi_or_hinglish("नमस्ते, आप कैसे हैं?") is True
    assert sarvam_client.is_hindi_or_hinglish("धन्यवाद") is True

    # Romanized Hinglish
    assert sarvam_client.is_hindi_or_hinglish("sab theek hai, batao kya karna hai") is True
    assert sarvam_client.is_hindi_or_hinglish("bilkul zaroor") is True
    assert sarvam_client.is_hindi_or_hinglish("aaj ka mausam kaisa hai") is True

    # Standard English
    assert sarvam_client.is_hindi_or_hinglish("Open visual studio code and run the build") is False
    assert sarvam_client.is_hindi_or_hinglish("The system memory usage is 45 percent") is False

def test_privacy_preflight_blocks_sarvam(sarvam_client):
    """Proves that private Hindi text is NEVER sent to Sarvam cloud API."""
    private_text_1 = "Mera Aadhaar card 2345 6789 0123 hai, ise update karo"
    private_text_2 = "Mere bank account se 50000 debit hue hain"
    private_text_3 = "Email draft karo alex@example.com ko"

    # Must return None without attempting network request
    with patch("httpx.Client.post") as mock_post:
        res1 = sarvam_client.synthesize(private_text_1)
        res2 = sarvam_client.synthesize(private_text_2)
        res3 = sarvam_client.synthesize(private_text_3)

        assert res1 is None
        assert res2 is None
        assert res3 is None
        mock_post.assert_not_called()

def test_missing_api_key_falls_back():
    client = SarvamTTSClient(api_key=None)
    with patch.dict(os.environ, {}, clear=True):
        with patch("services.backend.voice.cloud_tts.get_credential", return_value=None):
            result = client.synthesize("sab theek hai, batao kya karna hai")
            assert result is None

def test_mock_successful_sarvam_synthesis(sarvam_client):
    fake_wav_bytes = b"RIFF....WAVEfmt ....data...."
    b64_audio = base64.b64encode(fake_wav_bytes).decode("utf-8")

    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {"audios": [b64_audio]}

    with patch("httpx.Client.post", return_value=mock_resp) as mock_post:
        result = sarvam_client.synthesize("sab theek hai, batao kya karna hai", is_shareable=True, speaker="chirag_hi_social")
        assert result == fake_wav_bytes
        mock_post.assert_called_once()
        # Verify request parameters
        call_kwargs = mock_post.call_args[1]
        assert call_kwargs["json"]["target_language_code"] == "hi-IN"
        assert call_kwargs["json"]["model"] == "bulbul:v2"
        assert call_kwargs["json"]["speaker"] == "chirag_hi_social"

def test_mock_sarvam_speaker_alias_resolution(sarvam_client):
    fake_wav_bytes = b"RIFF....WAVEfmt ....data...."
    b64_audio = base64.b64encode(fake_wav_bytes).decode("utf-8")

    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {"audios": [b64_audio]}

    with patch("httpx.Client.post", return_value=mock_resp) as mock_post:
        # Pass legacy alias 'arvind' -> must resolve to 'chirag_hi_social'
        result = sarvam_client.synthesize("sab theek hai, batao kya karna hai", is_shareable=True, speaker="arvind")
        assert result == fake_wav_bytes
        call_kwargs = mock_post.call_args[1]
        assert call_kwargs["json"]["speaker"] == "chirag_hi_social"

def test_mock_sarvam_429_quota_fallback(sarvam_client):
    mock_resp = MagicMock()
    mock_resp.status_code = 429
    mock_resp.text = "Quota limit reached"

    with patch("httpx.Client.post", return_value=mock_resp):
        sarvam_client.reset_quota_alert()
        result = sarvam_client.synthesize("sab theek hai, batao kya karna hai", is_shareable=True)
        assert result is None
        assert sarvam_client._quota_alert_fired is True

        # Second call also falls back gracefully without duplicate alerts
        result2 = sarvam_client.synthesize("sab theek hai, batao kya karna hai", is_shareable=True)
        assert result2 is None

def test_tts_engine_hindi_routing():
    from services.backend.voice.tts import tts_engine
    with patch("services.backend.voice.cloud_tts.sarvam_tts.is_hindi_or_hinglish", return_value=True):
        with patch("services.backend.voice.cloud_tts.sarvam_tts.synthesize", return_value=b"fake-wav") as mock_synth:
            with patch.object(tts_engine, "_speak_wav_bytes", return_value=True) as mock_speak_wav:
                tts_engine.speak("kya haal hai")
                import time
                time.sleep(0.1)
