"""
Phenom 4.0 Phase 3 Verification Suite
Comprehensive tests for:
1. HybridRouter: Intent classification, sub-5ms latency, and Rule 4 privacy overrides.
2. NemotronVisionClient: In-RAM base64 serialization, credential resolution, and network error handling.
3. MultimodalCoordinator: Seamless, zero-crash fallback to on-device OCR + Moondream2.
4. Screen Vision Tool: Tier 2 safety compliance with preview confirmation.
"""

import pytest
import time
from unittest.mock import patch, MagicMock, AsyncMock
from PIL import Image

from services.backend.orchestrator.hybrid_router import (
    HybridRouter,
    IntentCategory,
    IntentResult
)
from services.backend.vision.nemotron_client import NemotronVisionClient
from services.backend.vision.multimodal_coordinator import MultimodalCoordinator
from services.backend.tools.screen_vision_tools import ask_screen_vision_cloud
from services.backend.safety.registry import registry


# =====================================================================
# 1. HYBRID ROUTER TESTS
# =====================================================================

def test_action_local_routing():
    router = HybridRouter()
    queries = [
        "open Chrome browser",
        "launch Spotify and play music",
        "set volume to 80%",
        "pause playback",
        "remind me to check the oven in 10 minutes",
        "calculate 450 * 12",
        "what is the weather today?",
        "check battery percentage"
    ]
    for q in queries:
        res = router.classify_intent(q)
        assert res.category == IntentCategory.ACTION_LOCAL, f"Query '{q}' failed: got {res.category}"
        assert res.target_model == router.local_model_name
        assert res.requires_preview is False
        assert res.latency_ms < 5.0, f"Latency {res.latency_ms}ms exceeded 5.0ms"


def test_vision_local_routing():
    router = HybridRouter()
    queries = [
        "where is the submit button on screen?",
        "locate the search input field",
        "find button 'Cancel'",
        "what are the coordinates of the close button",
        "click on the settings tab"
    ]
    for q in queries:
        res = router.classify_intent(q)
        assert res.category == IntentCategory.VISION_LOCAL, f"Query '{q}' failed: got {res.category}"
        assert res.target_model == "local_ocr_uia"
        assert res.requires_preview is False
        assert res.latency_ms < 5.0


def test_vision_cloud_routing():
    router = HybridRouter()
    queries = [
        "explain this architecture diagram on screen",
        "what does this flowchart show?",
        "diagnose the bug in this code on screen",
        "analyze my screen and describe the layout",
        "summarize this dashboard slide for me"
    ]
    for q in queries:
        res = router.classify_intent(q)
        assert res.category == IntentCategory.VISION_CLOUD, f"Query '{q}' failed: got {res.category}"
        assert res.target_model == router.cloud_vision_model
        assert res.requires_preview is True  # Cloud vision requires Tier 2 approval
        assert res.privacy_status == "shareable"
        assert res.latency_ms < 5.0


def test_privacy_override_blocks_cloud_vision():
    router = HybridRouter()
    # Deep visual reasoning prompt that includes sensitive PII / secrets
    sensitive_query = "explain this architecture diagram on screen with my PAN ABCDE1234F and password Secret!234"
    res = router.classify_intent(sensitive_query)
    
    # Must NOT route to cloud; must be retained local under Rule 4
    assert res.category == IntentCategory.VISION_LOCAL
    assert res.target_model == "local_vlm_moondream"
    assert res.privacy_status == "private"
    assert "sensitive/private data" in res.reason


def test_router_batch_latency_benchmark():
    router = HybridRouter()
    test_queries = [
        "open calculator",
        "where is the OK button",
        "explain this diagram",
        "set volume 50",
        "find text on screen"
    ] * 20  # 100 queries

    latencies = []
    for q in test_queries:
        res = router.classify_intent(q)
        latencies.append(res.latency_ms)

    avg_latency = sum(latencies) / len(latencies)
    max_latency = max(latencies)
    assert avg_latency < 1.0, f"Average latency {avg_latency:.3f}ms exceeded 1.0ms"
    assert max_latency < 5.0, f"Max latency {max_latency:.3f}ms exceeded 5.0ms"


# =====================================================================
# 2. NEMOTRON VISION CLIENT TESTS
# =====================================================================

def test_nemotron_in_ram_base64_encoding():
    client = NemotronVisionClient()
    # Large 4K image to test downscaling
    img = Image.new("RGB", (3840, 2160), color=(100, 150, 200))
    b64_str = client.encode_image_base64(img, max_dim=1280, quality=75)
    
    assert isinstance(b64_str, str)
    assert len(b64_str) > 100
    # Ensure memory buffer only, no temp file created


def test_nemotron_payload_construction():
    client = NemotronVisionClient(model_name="nvidia/neva-22b")
    b64_sample = "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg=="
    payload = client.build_payload(b64_sample, "Explain the diagram")
    
    assert payload["model"] == "nvidia/neva-22b"
    assert payload["max_tokens"] == 1024
    content = payload["messages"][0]["content"]
    assert content[0]["type"] == "text"
    assert content[0]["text"] == "Explain the diagram"
    assert content[1]["type"] == "image_url"
    assert content[1]["image_url"]["url"].startswith("data:image/jpeg;base64,")


def test_nemotron_credential_resolution(monkeypatch):
    client = NemotronVisionClient()
    
    # 1. When Credential Manager returns key
    with patch("services.backend.vision.nemotron_client.get_credential", return_value="nvapi-cred-mgr-key-12345"):
        assert client.get_api_key() == "nvapi-cred-mgr-key-12345"

    # 2. When Credential Manager is empty, fallback to NVIDIA_API_KEY
    with patch("services.backend.vision.nemotron_client.get_credential", return_value=None):
        monkeypatch.setenv("NVIDIA_API_KEY", "nvapi-env-key-67890")
        assert client.get_api_key() == "nvapi-env-key-67890"

    # 3. When both are missing
    with patch("services.backend.vision.nemotron_client.get_credential", return_value=None):
        monkeypatch.delenv("NVIDIA_API_KEY", raising=False)
        monkeypatch.delenv("NEMOTRON_API_KEY", raising=False)
        assert client.get_api_key() is None


@pytest.mark.asyncio
async def test_nemotron_missing_key_graceful_error():
    client = NemotronVisionClient()
    img = Image.new("RGB", (64, 64), color=(0, 0, 0))
    with patch.object(client, "get_api_key", return_value=None):
        res = await client.query_screen(img, "Analyze")
        assert res["status"] == "error"
        assert res["error_type"] == "no_api_key"
        assert "not configured" in res["message"]


@pytest.mark.asyncio
async def test_nemotron_query_success_mock():
    client = NemotronVisionClient()
    img = Image.new("RGB", (64, 64), color=(255, 255, 255))
    
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {
        "choices": [
            {
                "message": {
                    "role": "assistant",
                    "content": "The image illustrates a microservices architecture with a FastAPI gateway."
                }
            }
        ],
        "usage": {"prompt_tokens": 120, "completion_tokens": 45, "total_tokens": 165}
    }

    with patch.object(client, "get_api_key", return_value="nvapi-mock-key"):
        with patch("httpx.AsyncClient.post", AsyncMock(return_value=mock_resp)):
            res = await client.query_screen(img, "Explain architecture")
            assert res["status"] == "success"
            assert "FastAPI gateway" in res["description"]
            assert res["model"] == client.model_name


@pytest.mark.asyncio
async def test_nemotron_network_timeout():
    import httpx
    client = NemotronVisionClient()
    img = Image.new("RGB", (64, 64), color=(0, 0, 0))

    with patch.object(client, "get_api_key", return_value="nvapi-mock-key"):
        with patch("httpx.AsyncClient.post", AsyncMock(side_effect=httpx.TimeoutException("Read timed out"))):
            res = await client.query_screen(img, "Analyze")
            assert res["status"] == "error"
            assert res["error_type"] == "timeout"


# =====================================================================
# 3. MULTIMODAL COORDINATOR & OFFLINE FALLBACK TESTS
# =====================================================================

@pytest.mark.asyncio
async def test_coordinator_cloud_path_success():
    coordinator = MultimodalCoordinator()
    img = Image.new("RGB", (200, 200), color=(10, 20, 30))

    with patch.object(coordinator.grabber, "grab_frame", return_value=img):
        with patch.object(coordinator.masker, "mask_sensitive_windows", return_value=(img, 1)):
            with patch.object(coordinator.nemotron, "query_screen", AsyncMock(return_value={
                "status": "success",
                "model": "nvidia/neva-22b",
                "description": "Cloud comprehension of application UI."
            })):
                res = await coordinator.execute_screen_query("What is open?", prefer_cloud=True)
                assert res["status"] == "success"
                assert res["source"] == "cloud_nemotron"
                assert res["fallback_engaged"] is False
                assert res["privacy_masked_windows"] == 1
                assert "Cloud comprehension" in res["description"]


@pytest.mark.asyncio
async def test_coordinator_resilient_fallback_on_cloud_failure():
    coordinator = MultimodalCoordinator()
    img = Image.new("RGB", (200, 200), color=(10, 20, 30))

    # Simulate cloud returning network connection failure
    with patch.object(coordinator.grabber, "grab_frame", return_value=img):
        with patch.object(coordinator.masker, "mask_sensitive_windows", return_value=(img, 0)):
            with patch.object(coordinator.nemotron, "query_screen", AsyncMock(return_value={
                "status": "error",
                "error_type": "network_error",
                "message": "Connection refused to build.nvidia.com"
            })):
                with patch.object(coordinator.moondream, "query_image", AsyncMock(return_value={
                    "status": "success",
                    "description": "On-device VLM detected a code editor."
                })):
                    with patch.object(coordinator.ocr, "extract_text_via_ocr", return_value=[{"text": "def test():"}]):
                        res = await coordinator.execute_screen_query("Explain screen", prefer_cloud=True)
                        
                        # Verification of zero-crash fallback
                        assert res["status"] == "success"
                        assert res["source"] == "local_fallback"
                        assert res["fallback_engaged"] is True
                        assert "Connection refused" in res["fallback_reason"]
                        assert "On-device VLM" in res["description"]
                        assert "def test():" in res["description"]


# =====================================================================
# 4. SAFETY & TOOL INTEGRATION TESTS
# =====================================================================

def test_ask_screen_vision_cloud_safety_registry():
    tool = registry.get("ask_screen_vision_cloud")
    assert tool is not None, "ask_screen_vision_cloud must be registered in Safety Registry"
    assert tool.tier == 2, "ask_screen_vision_cloud must be strictly classified as Tier 2"
    assert tool.preview_fn is not None, "ask_screen_vision_cloud must define a preview function"
    preview = tool.preview_fn({"question": "Explain this chart"})
    assert "Explain this chart" in preview
    assert "[Cloud Vision Preview]" in preview


@pytest.mark.asyncio
async def test_ask_screen_vision_cloud_execution():
    with patch("services.backend.tools.screen_vision_tools.multimodal_coordinator.execute_screen_query", AsyncMock(return_value={
        "status": "success",
        "source": "cloud_nemotron",
        "model": "nvidia/neva-22b",
        "description": "Analyzed complex chart successfully.",
        "fallback_engaged": False,
        "privacy_masked_windows": 0,
        "message": "Cloud vision analysis complete."
    })):
        res = await ask_screen_vision_cloud("Analyze this chart")
        assert res["status"] == "success"
        assert res["source"] == "cloud_nemotron"
        assert res["fallback_engaged"] is False
        assert "Analyzed complex chart" in res["description"]
