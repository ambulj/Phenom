"""
Unit Tests for NEURAL-NEOCORTEX Window Classifier, Local OCR & Privacy Masker
Milestone 44.0: Project NEURAL-NEOCORTEX (Phase 2)
"""

import pytest

from services.backend.safety.registry import registry
from services.backend.vision.privacy_masker import privacy_masker
from services.backend.vision.screen_classifier import screen_classifier, WindowCategory
from services.backend.tools.neocortex_tools import (
    handle_query_neocortex_visual_state,
    handle_set_neocortex_capture_mode,
    handle_audit_screen_privacy_mask,
)


def test_pii_and_credential_redaction_accuracy():
    """Verifies that API keys, AWS tokens, JWTs, cards, and passwords are automatically redacted (Rule 11)."""
    masker = privacy_masker

    mock_sk = "sk-" + "abcdef1234567890abcdef1234567890"
    mock_aws = "AKIA" + "IOSFODNN7EXAMPLE"
    mock_gh = "ghp_" + "123456789012345678901234567890123456"

    samples = [
        (f"export OPENAI_API_KEY={mock_sk}", "[REDACTED_API_KEY]"),
        (f"AWS_ACCESS_KEY_ID={mock_aws}", "[REDACTED_AWS_KEY]"),
        (f"git clone https://{mock_gh}@github.com", "[REDACTED_GH_TOKEN]"),
        ("Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxMjM0NTY3ODkwIn0.dozG6p1e5xY", "Bearer [REDACTED_JWT]"),
        ("Card Number: 4532-1234-5678-9010 on billing file", "[REDACTED_CREDIT_CARD]"),
        ("database_connection_url password=MySuperSecretRootPass123 port=5432", "password=[REDACTED_SECRET]"),
    ]

    for raw, expected_token in samples:
        masked, count = masker.mask_pii_text(raw)
        assert expected_token in masked, f"Failed to redact token in: '{raw}'. Got: '{masked}'"
        assert count >= 1


def test_sensitive_window_blinding_policy():
    """Verifies that password vaults and banking trigger blinding, while cyber tools are allowed."""
    masker = privacy_masker

    # Sensitive windows that MUST be blinded
    sensitive_windows = [
        ("KeePassXC - Passwords.kdbx", "keepassxc.exe"),
        ("Bitwarden - My Vault", "bitwarden.exe"),
        ("1Password - Personal", "1password.exe"),
        ("Chase Bank - Personal Accounts", "chrome.exe"),
        ("New Tab - InPrivate", "msedge.exe"),
        ("Private Browsing - Mozilla Firefox", "firefox.exe"),
    ]

    for title, proc in sensitive_windows:
        assert masker.is_sensitive_window(title, proc) is True, f"Failed to blind sensitive window: {title} ({proc})"

    # Red-Team developer tools that must NEVER be blinded
    allowed_windows = [
        ("kali@kali: ~", "wsl.exe"),
        ("Administrator: Windows PowerShell", "powershell.exe"),
        ("Command Prompt - nmap -sV 127.0.0.1", "cmd.exe"),
        ("Ghidra - CodeBrowser: kernel32.dll", "ghidra.exe"),
        ("Wireshark - Capturing on Wi-Fi", "wireshark.exe"),
    ]

    for title, proc in allowed_windows:
        assert masker.is_sensitive_window(title, proc) is False, f"Erroneously blinded red-team tool: {title} ({proc})"


def test_window_classification_categories():
    """Verifies semantic category assignment for active foreground windows."""
    classifier = screen_classifier

    wsl_res = classifier.classify_window("kali@kali: /home/kali", "wsl.exe")
    assert wsl_res.category == WindowCategory.RED_TEAM_TERMINAL
    assert wsl_res.is_terminal is True

    ghidra_res = classifier.classify_window("Ghidra: elf_binary", "ghidra.exe")
    assert ghidra_res.category == WindowCategory.REVERSE_ENGINEERING

    code_res = classifier.classify_window("neocortex.py - Phenom - Visual Studio Code", "code.exe")
    assert code_res.category == WindowCategory.CODE_EDITOR

    vault_res = classifier.classify_window("KeePassXC", "keepassxc.exe")
    assert vault_res.category == WindowCategory.SENSITIVE_VAULT
    assert vault_res.is_sensitive is True


def test_ocr_extraction_with_automatic_pii_masking():
    """Verifies that extracted OCR bounding boxes carry coordinates, text, and redaction flags."""
    classifier = screen_classifier

    mock_token = "sk-" + "live12345678901234567890123456"
    raw_lines = [
        "[*] Discovered open port: 22/tcp (OpenSSH 8.9p1)",
        f"[*] Authenticating with API token: {mock_token}",
        "[+] Successfully spawned root shell on target 127.0.0.1",
    ]

    boxes = classifier.extract_ocr_blocks(raw_lines, base_x=100, base_y=100, line_height=25)
    assert len(boxes) == 3

    # First box: nominal port text
    assert "OpenSSH" in boxes[0].text
    assert boxes[0].is_redacted is False
    assert boxes[0].y == 100

    # Second box: must have redacted API key
    assert "[REDACTED_API_KEY]" in boxes[1].text
    assert boxes[1].is_redacted is True
    assert boxes[1].y == 125

    # Third box: root shell
    assert "root shell" in boxes[2].text
    assert boxes[2].is_redacted is False
    assert boxes[2].y == 150


def test_neocortex_tools_registration_and_execution():
    """Verifies ToolRegistry integration for neocortex tools."""
    assert registry.get_tier("query_neocortex_visual_state") == 0
    assert registry.get_tier("set_neocortex_capture_mode") == 1
    assert registry.get_tier("audit_screen_privacy_mask") == 0

    # Test query state
    state = handle_query_neocortex_visual_state()
    assert "telemetry" in state
    assert "classification" in state

    # Test set mode
    mode_res = handle_set_neocortex_capture_mode(capture_mode="CONTINUOUS", target_fps=8.0)
    assert mode_res["status"] == "success"
    assert mode_res["capture_mode"] == "CONTINUOUS"
    assert mode_res["target_fps"] == 8.0

    # Test audit privacy mask tool
    mock_test_token = "sk-" + "test999999999999999999999999"
    audit_res = handle_audit_screen_privacy_mask(
        text_sample=f"Token: {mock_test_token}",
        window_title="KeePassXC Master",
        process_name="keepassxc.exe",
    )
    assert audit_res["is_redacted"] is True
    assert "[REDACTED_API_KEY]" in audit_res["masked_text"]
    assert audit_res["is_sensitive"] is True
