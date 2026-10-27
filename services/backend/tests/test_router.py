"""
Unit tests for Phenom Model Router & Privacy Classifier
Tests:
1. Private by default stays local
2. Sensitive keywords stay local
3. Path keywords stay local
4. Shareable short input stays local
5. Long shareable input triggers cloud approval
6. Denial of cloud approval falls back to local
7. Approval routes to Nemotron
8. Manual override functionality
"""

import pytest
from services.backend.router.privacy import PrivacyClassifier
from services.backend.router.router import ModelRouter

@pytest.fixture
def classifier():
    return PrivacyClassifier()

@pytest.fixture
def router():
    return ModelRouter(ollama_model="llama3:latest", cloud_model="nvidia/llama-3.1-nemotron-70b-instruct")

def test_privacy_defaults(classifier):
    label, reason = classifier.classify("Hello Phenom, how is the weather?")
    assert label == "private" # Default policy

def test_privacy_sensitive_keywords(classifier):
    label, reason = classifier.classify("Here is my api_key: nvapi-12345")
    assert label == "private"
    assert "api_key" in reason

def test_privacy_paths(classifier):
    label, reason = classifier.classify("Summarize this file", file_paths=["C:/Users/User/Documents/report.pdf"])
    assert label == "private"
    assert "documents" in reason.lower()

def test_shareable_folder_override(classifier):
    classifier.add_shareable_folder("C:/PublicData")
    label, reason = classifier.classify("Read this public document", file_paths=["C:/PublicData/public_notes.txt"], manual_override="shareable")
    assert label == "shareable"

@pytest.mark.asyncio
async def test_router_private_stays_local(router):
    model, btype, meta = await router.route_request("Check my private tax records")
    assert btype == "local"
    assert model == "llama3:latest"
    assert meta["privacy_label"] == "private"

@pytest.mark.asyncio
async def test_router_short_shareable_stays_local(router):
    model, btype, meta = await router.route_request(
        "Summarize quantum computing principles in one sentence",
        manual_privacy_override="shareable"
    )
    assert btype == "local"
    assert model == "llama3:latest"

@pytest.mark.asyncio
async def test_router_long_shareable_escalation(router):
    long_text = "word " * 3500 # 3,500 words
    
    # 1. Approval denied -> Fallback to local
    async def mock_deny(req_id, preview, tokens):
        return False
    router.set_cloud_approval_handler(mock_deny)
    model, btype, meta = await router.route_request(long_text, manual_privacy_override="shareable")
    assert btype == "local"
    assert "Falling back to local 8B" in meta["routing_reason"]

    # 2. Approval granted -> Routes to Cloud Nemotron
    async def mock_approve(req_id, preview, tokens):
        return True
    router.set_cloud_approval_handler(mock_approve)
    model, btype, meta = await router.route_request(long_text, manual_privacy_override="shareable")
    assert btype == "cloud"
    assert model == "nvidia/llama-3.1-nemotron-70b-instruct"
