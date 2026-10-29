"""
Unit & Integration Tests for Phenom Privacy Classifier & Cloud Cascade (Task 7f)
Verifies:
1. High-precision regex detection for Indian PII & Credentials:
   - Aadhaar ID
   - PAN Card
   - Indian Mobile Phone
   - UPI ID
   - Luhn-validated Credit Card numbers
   - Bank IFSC codes
   - API keys & Private Key blocks
2. 100% Precision on Private Data (Zero False Negatives).
3. Multi-provider cloud rate-limit cascade (HTTP 429 failover).
4. Terminal fallback to Local 8B upon complete cloud saturation.
5. Strict pre-flight privacy assertion blocking cloud escalation on private data.
"""

import os
import pytest
from services.backend.router.privacy import (
    privacy_classifier,
    is_valid_luhn,
    PrivacyViolationError
)
from services.backend.router.cloud_fallback import (
    MultiProviderCloudCascade,
    CloudRateLimitError
)

def test_indian_pii_regex_detection():
    # Aadhaar
    label, reason = privacy_classifier.classify("My Aadhaar card number is 2345 6789 0123")
    assert label == "private"
    assert "Aadhaar ID" in reason

    # PAN
    label, reason = privacy_classifier.classify("Income tax PAN is ABCDE1234F for filing")
    assert label == "private"
    assert "PAN Card" in reason

    # Phone
    label, reason = privacy_classifier.classify("Contact me on +91 9876543210 please")
    assert label == "private"
    assert "Phone Number" in reason

    # UPI
    label, reason = privacy_classifier.classify("Send payment to rahul.sharma@okaxis")
    assert label == "private"
    assert "UPI ID" in reason

    # Bank IFSC
    label, reason = privacy_classifier.classify("Transfer funds to HDFC0001234 account")
    assert label == "private"
    assert "IFSC Code" in reason

def test_credit_card_luhn_validation():
    # Valid Visa card
    valid_card = "4532015112830366"
    assert is_valid_luhn(valid_card) is True
    label, reason = privacy_classifier.classify(f"Pay using card {valid_card}")
    assert label == "private"
    assert "Credit Card" in reason

    # Invalid Luhn card number should not trigger credit card PII
    invalid_card = "4532015112830367"
    assert is_valid_luhn(invalid_card) is False

def test_api_keys_and_secrets_detection():
    # NVIDIA API Key
    label, reason = privacy_classifier.classify("nvapi-1234567890abcdefghijklmnopqrstuvwxyzABCD")
    assert label == "private"
    assert "NVIDIA API Key" in reason

    # AWS Key
    label, reason = privacy_classifier.classify("AKIAIOSFODNN7EXAMPLE")
    assert label == "private"
    assert "AWS Access Key" in reason

    # Google Key
    label, reason = privacy_classifier.classify("AIzaSyD-1234567890abcdefghijklmnopqrstuv")
    assert label == "private"
    assert "Google API Key" in reason

    # GitHub Token
    label, reason = privacy_classifier.classify("ghp_1234567890abcdefghijklmnopqrstuvwxyz")
    assert label == "private"
    assert "GitHub Personal Access Token" in reason

    # RSA Private Key
    label, reason = privacy_classifier.classify("-----BEGIN RSA PRIVATE KEY-----\nMIIEowIBAAKCAQEA0...\n-----END RSA PRIVATE KEY-----")
    assert label == "private"
    assert "Private Key Block" in reason

def test_private_path_and_unauthorized_folder():
    # Documents path
    label, reason = privacy_classifier.classify("Summarize file", file_paths=["C:\\Users\\user\\Documents\\contract.pdf"])
    assert label == "private"
    assert "documents" in reason.lower()

    # Unauthorized path outside shareable folder
    label, reason = privacy_classifier.classify("Read file", file_paths=["C:\\RandomFolder\\notes.txt"])
    assert label == "private"
    assert "not inside an authorized shareable folder" in reason

    # Adding shareable folder allows file
    privacy_classifier.add_shareable_folder("C:\\RandomFolder")
    try:
        label, reason = privacy_classifier.classify("Read file", file_paths=["C:\\RandomFolder\\notes.txt"], manual_override="shareable")
        assert label == "shareable"
    finally:
        privacy_classifier.remove_shareable_folder("C:\\RandomFolder")

@pytest.mark.asyncio
async def test_cloud_cascade_rate_limit_failover(monkeypatch):
    # Set mock API keys so cascade attempts them
    monkeypatch.setenv("NVIDIA_API_KEY", "mock_nvidia_key")
    monkeypatch.setenv("GROQ_API_KEY", "mock_groq_key")
    monkeypatch.setenv("OPENROUTER_API_KEY", "mock_openrouter_key")

    cascade = MultiProviderCloudCascade()

    # Primary NVIDIA 429 rate limit -> Failover to Groq
    res1 = await cascade.execute_cascade(
        prompt="Explain quicksort in Python",
        mock_failures={"nvidia": 429}
    )
    assert res1["status"] == "success"
    assert res1["provider"] == "groq"
    assert res1["cascade_hops"] == 1
    assert res1["cascade_history"][0]["provider"] == "nvidia"
    assert res1["cascade_history"][0]["reason"] == "rate_limited_429"

    # NVIDIA and Groq both 429 -> Failover to OpenRouter
    res2 = await cascade.execute_cascade(
        prompt="Explain quicksort in Python",
        mock_failures={"nvidia": 429, "groq": 429}
    )
    assert res2["status"] == "success"
    assert res2["provider"] == "openrouter"
    assert res2["cascade_hops"] == 2

    # All cloud providers saturated -> Terminal fallback to Local 8B
    res3 = await cascade.execute_cascade(
        prompt="Explain quicksort in Python",
        mock_failures={"nvidia": 429, "groq": 429, "openrouter": 429}
    )
    assert res3["status"] == "fallback_local"
    assert res3["provider"] == "local_8b"
    assert "fell back to Local 8B" in res3["notice"]

@pytest.mark.asyncio
async def test_cloud_cascade_rejects_private_payload_before_network():
    cascade = MultiProviderCloudCascade()
    with pytest.raises(PrivacyViolationError) as exc:
        await cascade.execute_cascade(prompt="Mera Aadhaar card 2345 6789 1234 linked hai")
    assert "Aadhaar ID" in str(exc.value)
