"""
Tests for Phenom Commit Guard & Secret Scanner (scripts/scan_secrets.py)
Proves that every blocked path and secret pattern is caught and blocked.
"""

import pytest
from scripts.scan_secrets import check_file_path, check_content

@pytest.mark.parametrize("blocked_path", [
    "vault/Notes/MyNote.md",
    "vault/Daily Logs/2026-10-29.md",
    "Documents/Phenom/vault/note.md",
    "user_data/session.json",
    "services/backend/user_data/cookies.txt",
    "test.db",
    "memory.sqlite",
    "analytics.sqlite3",
    ".env",
    ".env.production",
    ".env.local",
    "services/backend/.env",
    "subfolder/secret.env",
    "crash_logs/crash_20261029.log",
    "services/backend/crash_logs/error.log"
])
def test_blocked_paths_rejected(blocked_path):
    """Proves that blocked paths and filenames are recognized and rejected."""
    violation = check_file_path(blocked_path)
    assert violation is not None, f"Expected {blocked_path} to be blocked, but check_file_path returned None"

@pytest.mark.parametrize("allowed_path", [
    "services/backend/main.py",
    "apps/desktop/src/App.tsx",
    "README.md",
    "config.toml",
    "services/backend/tests/test_router.py",
    "package.json"
])
def test_allowed_paths_accepted(allowed_path):
    """Proves that regular codebase paths pass inspection."""
    violation = check_file_path(allowed_path)
    assert violation is None, f"Expected {allowed_path} to pass, but got: {violation}"

def test_nvidia_key_detected():
    """Proves NVIDIA API key pattern (nvapi-...) is blocked."""
    dummy_key = "nvapi-" + "aB1cD2eF3gH4iJ5kL6mN7oP8qR9sT0"
    content = f"NVIDIA_KEY = '{dummy_key}'\n"
    violations = check_content(content, filename="test_code.py")
    assert len(violations) == 1
    assert violations[0]["pattern_name"] == "NVIDIA API Key"

def test_google_key_detected():
    """Proves Google API key pattern (AIza...) is blocked."""
    dummy_key = "AIza" + "SyD1234567890abcdefghijklmnopqrstuv"
    content = f"GOOGLE_API_KEY = '{dummy_key}'\n"
    violations = check_content(content, filename="test_code.py")
    assert len(violations) == 1
    assert violations[0]["pattern_name"] == "Google API Key"

def test_github_token_detected():
    """Proves GitHub Personal Access Token (ghp_...) is blocked."""
    dummy_token = "ghp_" + "1234567890abcdefghijklmnopqrstuvwxyz"
    content = f"GITHUB_TOKEN = '{dummy_token}'\n"
    violations = check_content(content, filename="test_code.py")
    assert len(violations) == 1
    assert violations[0]["pattern_name"] == "GitHub Personal Access Token"

def test_github_fine_grained_pat_detected():
    """Proves GitHub Fine-Grained Token (github_pat_...) is blocked."""
    dummy_pat = "github_pat_" + "11AAAAAAA01234567890abcdefghijklmnopqrstuvwxyz_0123456789abcdef"
    content = f"GITHUB_PAT = '{dummy_pat}'\n"
    violations = check_content(content, filename="test_code.py")
    assert len(violations) == 1
    assert violations[0]["pattern_name"] == "GitHub Fine-Grained Token"

def test_telegram_bot_token_detected():
    """Proves Telegram Bot Token ([0-9]{8,10}:...) is blocked."""
    dummy_bot_token = "1234567890" + ":" + "ABCdefGHIjklMNOpqrSTUvwxYZ123456789"
    content = f"TELEGRAM_BOT_TOKEN = '{dummy_bot_token}'\n"
    violations = check_content(content, filename="test_code.py")
    assert len(violations) == 1
    assert violations[0]["pattern_name"] == "Telegram Bot Token"

def test_private_key_header_detected():
    """Proves private key headers are blocked."""
    pk_rsa = "-----BEGIN " + "RSA PRIVATE KEY-----\nMIIEowIBAAKCAQEA0...\n-----END RSA PRIVATE KEY-----"
    pk_generic = "-----BEGIN " + "PRIVATE KEY-----\nMIIEvgIBADANBgkqhkiG9w0BAQEFAASCBKgw...\n-----END PRIVATE KEY-----"
    pk_openssh = "-----BEGIN " + "OPENSSH PRIVATE KEY-----\nb3BlbnNzaC1rZXktdjEAAAA...\n-----END OPENSSH PRIVATE KEY-----"

    for pk in [pk_rsa, pk_generic, pk_openssh]:
        violations = check_content(pk, filename="key.pem")
        assert len(violations) >= 1
        assert violations[0]["pattern_name"] == "Private Key Header"

def test_clean_content_passes():
    """Proves regular code without secrets passes without violations."""
    clean_code = """
def calculate_metrics(values):
    return sum(values) / len(values) if values else 0.0

class UserProfile:
    def __init__(self, username: str):
        self.username = username
"""
    violations = check_content(clean_code, filename="services/backend/math_utils.py")
    assert len(violations) == 0
