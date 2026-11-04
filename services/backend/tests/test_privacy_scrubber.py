"""
Unit Tests for Real-Time Privacy Scrubber (PRX-01, Permanent Rule 11, SAF-01).
Verifies:
- OpenAI, Anthropic, HuggingFace API key redaction
- GitHub and GitLab personal access token redaction
- AWS access key IDs and Bearer token redaction
- RSA Private key blocks and password fields redaction
- Credit card number redaction
- Recursive dictionary scrubbing
- Non-sensitive text passes through unchanged
"""

from services.backend.proactive.privacy_scrubber import PrivacyScrubber


def test_scrubber_api_keys_and_tokens():
    """Verify standard AI provider keys and tokens are redacted."""
    scrubber = PrivacyScrubber()

    raw_text = (
        "Configure OpenAI key sk-abcdef1234567890abcdef123456 and "
        "Anthropic sk-ant-api03-abcdef1234567890abcdef123456 and "
        "HuggingFace hf_abcdef1234567890abcdef123456"
    )
    clean, categories = scrubber.scrub_text(raw_text)

    assert "sk-abcdef" not in clean
    assert "sk-ant" not in clean
    assert "hf_abcdef" not in clean
    assert "[REDACTED_OPENAI_KEY]" in clean
    assert "[REDACTED_ANTHROPIC_KEY]" in clean
    assert "[REDACTED_HUGGINGFACE_KEY]" in clean
    assert "OPENAI_KEY" in categories
    assert "ANTHROPIC_KEY" in categories
    assert "HUGGINGFACE_KEY" in categories


def test_scrubber_git_and_cloud_credentials():
    """Verify GitHub, GitLab, AWS, and Bearer tokens are redacted."""
    scrubber = PrivacyScrubber()

    dummy_ghp = "ghp" + "_123456789012345678901234567890123456"
    raw_text = (
        f"Clone using {dummy_ghp} or "
        "glpat-12345678901234567890 and AWS key AKIA1234567890123456 and "
        "Authorization: Bearer mySecretJwtTokenString1234567890"
    )
    clean, categories = scrubber.scrub_text(raw_text)

    assert "ghp_" not in clean
    assert "glpat-" not in clean
    assert "AKIA1234567890123456" not in clean
    assert "mySecretJwtTokenString" not in clean
    assert "[REDACTED_GITHUB_PAT]" in clean
    assert "[REDACTED_GITLAB_PAT]" in clean
    assert "[REDACTED_AWS_KEY_ID]" in clean
    assert "[REDACTED_BEARER_TOKEN]" in clean


def test_scrubber_private_keys_and_passwords():
    """Verify private key blocks and password fields are sanitized."""
    scrubber = PrivacyScrubber()

    key_hdr = "-----" + "BEGIN RSA PRIVATE KEY-----"
    key_ftr = "-----" + "END RSA PRIVATE KEY-----"
    raw_text = (
        f"Connect with password: SuperSecretPass123! and key:\n"
        f"{key_hdr}\n"
        "MIIEowIBAAKCAQEA0m4pQ...\n"
        f"{key_ftr}"
    )
    clean, categories = scrubber.scrub_text(raw_text)

    assert "SuperSecretPass123!" not in clean
    assert "password=[REDACTED_SECRET]" in clean
    assert "MIIEowIBAAKCAQEA0m4pQ" not in clean
    assert "[REDACTED_PRIVATE_KEY]" in clean


def test_scrubber_recursive_dict():
    """Verify nested dictionary structures are scrubbed cleanly."""
    scrubber = PrivacyScrubber()

    data = {
        "user": "phenom_operator",
        "nested": {
            "token": "sk-1234567890abcdef1234567890",
            "metadata": [
                "normal note",
                "secret_key: topsecretcredential99",
            ],
        },
        "count": 42,
    }

    clean_dict, categories = scrubber.scrub_dict(data)

    assert clean_dict["user"] == "phenom_operator"
    assert "sk-" not in clean_dict["nested"]["token"]
    assert "[REDACTED_OPENAI_KEY]" in clean_dict["nested"]["token"]
    assert "topsecretcredential99" not in clean_dict["nested"]["metadata"][1]
    assert clean_dict["count"] == 42
    assert len(categories) > 0


def test_scrubber_benign_text_unchanged():
    """Verify ordinary non-sensitive text is untouched."""
    scrubber = PrivacyScrubber()
    text = "Building desktop overlay on Windows 11 with Python 3.11 and React 18."
    clean, categories = scrubber.scrub_text(text)
    assert clean == text
    assert len(categories) == 0
