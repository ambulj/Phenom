"""
Tests for Phenom Vault Git Integration & Dynamic Git Safety Tiers
"""

import os
import shutil
import tempfile
import pytest
from services.backend.memory.vault import (
    ObsidianVaultManager,
    get_configured_vault_path,
    check_and_migrate_legacy_vault,
    find_repo_root,
    vault_manager
)
from services.backend.safety.registry import registry
from services.backend.safety.engine import safety_engine
from services.backend.tools.git_tools import git_command_tier, GitCommandArgs

def test_vault_path_resolution_and_fixed_location():
    """Proves vault path is resolved to absolute directory and never relative to cwd."""
    vault_path = get_configured_vault_path()
    assert os.path.isabs(vault_path)
    assert not vault_path.endswith(os.path.join(os.getcwd(), "vault")) or "Documents" in vault_path
    assert "Documents" in vault_path or "Phenom" in vault_path

def test_vault_path_consistent_across_cwd(monkeypatch):
    """Proves that changing cwd does not change the resolved vault path."""
    original_cwd = os.getcwd()
    tmp1 = tempfile.mkdtemp()
    tmp2 = tempfile.mkdtemp()
    try:
        os.chdir(tmp1)
        path1 = get_configured_vault_path()

        os.chdir(tmp2)
        path2 = get_configured_vault_path()

        assert path1 == path2
        assert os.path.isabs(path1)
    finally:
        os.chdir(original_cwd)
        shutil.rmtree(tmp1, ignore_errors=True)
        shutil.rmtree(tmp2, ignore_errors=True)

def test_vault_git_initialization():
    """Proves vault manager initializes a git repository inside the vault path."""
    tmp_vault = tempfile.mkdtemp()
    try:
        manager = ObsidianVaultManager(vault_path=tmp_vault)
        assert os.path.exists(os.path.join(tmp_vault, ".git"))
        # Test note creation and git commit
        note_path = manager.write_note("Test Note", "Testing git sync")
        assert os.path.exists(note_path)
        sync_res = manager.sync_vault_git("Test commit")
        assert sync_res["status"] == "success"
        assert sync_res["committed"] is True
    finally:
        shutil.rmtree(tmp_vault, ignore_errors=True)

def test_vault_refuses_code_repo_collision():
    """Proves vault manager refuses to configure remote URL pointing to Phenom code repo."""
    tmp_vault = tempfile.mkdtemp()
    try:
        manager = ObsidianVaultManager(vault_path=tmp_vault)
        
        # Test with URL
        with pytest.raises(ValueError, match="Phenom code repository"):
            manager.set_remote_url("https://github.com/ambulj/Phenom.git")

        with pytest.raises(ValueError, match="Phenom code repository"):
            manager.set_remote_url("git@github.com:ambulj/Phenom.git")

        # Test with local code repo path
        code_root = find_repo_root()
        with pytest.raises(ValueError, match="Phenom code repository"):
            manager.set_remote_url(code_root)
    finally:
        shutil.rmtree(tmp_vault, ignore_errors=True)

def test_git_tier_resolution():
    """
    Proves:
    - Vault repository git operations are Tier 0 (auto-approved).
    - Code repository git operations are Tier 2 (require confirmation).
    - External arbitrary repositories are Tier 2.
    """
    vault_path = get_configured_vault_path()
    code_path = find_repo_root()

    # Vault path -> Tier 0
    tier_vault = registry.get_tier("git_command", {"repo_path": vault_path, "command": "status"})
    assert tier_vault == 0

    # Subfolder of vault -> Tier 0
    tier_vault_sub = registry.get_tier("git_command", {"repo_path": os.path.join(vault_path, "Notes"), "command": "status"})
    assert tier_vault_sub == 0

    # Code repo -> Tier 2
    tier_code = registry.get_tier("git_command", {"repo_path": code_path, "command": "status"})
    assert tier_code == 2

    # Arbitrary other folder -> Tier 2
    tier_other = registry.get_tier("git_command", {"repo_path": "C:\\Windows", "command": "status"})
    assert tier_other == 2

    # Empty / missing path -> Tier 2
    tier_none = registry.get_tier("git_command", {})
    assert tier_none == 2

@pytest.mark.asyncio
async def test_safety_engine_enforces_git_tiers(monkeypatch):
    """
    Proves that safety engine auto-runs Tier 0 vault git commands without confirmation handler,
    but blocks or requests confirmation for Tier 2 code repo git commands.
    """
    tmp_vault = tempfile.mkdtemp()
    manager = ObsidianVaultManager(vault_path=tmp_vault)
    monkeypatch.setattr(vault_manager, "vault_path", tmp_vault)

    try:
        # 1. Vault repo: should succeed with auto-run (Tier 0)
        res = await safety_engine.execute_tool(
            tool_name="git_command",
            raw_args={"repo_path": tmp_vault, "command": "status"},
            source="desktop"
        )
        assert res["status"] == "success"

        # 2. Code repo without confirmation handler: must fail PermissionError (Tier 2 requires confirmation)
        code_path = find_repo_root()
        safety_engine.set_confirmation_handler(None)
        with pytest.raises(PermissionError, match="requires confirmation"):
            await safety_engine.execute_tool(
                tool_name="git_command",
                raw_args={"repo_path": code_path, "command": "status"},
                source="desktop"
            )

        # 3. Code repo with approved confirmation handler: succeeds
        async def dummy_approve(*args):
            return ("approved", False)

        safety_engine.set_confirmation_handler(dummy_approve)
        res_approved = await safety_engine.execute_tool(
            tool_name="git_command",
            raw_args={"repo_path": code_path, "command": "status"},
            source="desktop"
        )
        assert res_approved["status"] == "success"

        # 4. Code repo with denied confirmation handler: fails
        async def dummy_deny(*args):
            return ("denied", False)

        safety_engine.set_confirmation_handler(dummy_deny)
        with pytest.raises(PermissionError, match="denied by the user"):
            await safety_engine.execute_tool(
                tool_name="git_command",
                raw_args={"repo_path": code_path, "command": "status"},
                source="desktop"
            )
    finally:
        safety_engine.set_confirmation_handler(None)
        shutil.rmtree(tmp_vault, ignore_errors=True)

def test_vault_migration_verification():
    """Proves one-time migration copies files, verifies SHA-256 hashes, and preserves data."""
    old_dir = tempfile.mkdtemp()
    new_dir = tempfile.mkdtemp()

    try:
        # Create test notes in old_dir
        os.makedirs(os.path.join(old_dir, "Notes"), exist_ok=True)
        note_file = os.path.join(old_dir, "Notes", "TestNote.md")
        with open(note_file, "w", encoding="utf-8") as f:
            f.write("# Hello Vault Migration\nContent here.\n")

        # Migrate
        res = check_and_migrate_legacy_vault(old_path=old_dir, new_path=new_dir, remove_old=False)
        assert res["needed"] is True
        assert res["migrated"] == 1
        assert res["verified"] is True
        assert os.path.exists(os.path.join(new_dir, "Notes", "TestNote.md"))
        assert os.path.exists(note_file)  # Preserved since remove_old was False
    finally:
        shutil.rmtree(old_dir, ignore_errors=True)
        shutil.rmtree(new_dir, ignore_errors=True)

def test_token_sanitization():
    """Proves sensitive tokens are never printed or returned in plain text."""
    manager = ObsidianVaultManager()
    sensitive_token = "ghp_1234567890abcdef1234567890abcdef"
    raw_message = f"Error pushing to https://oauth2:{sensitive_token}@github.com/user/private-vault.git"
    sanitized = manager.sanitize_text(raw_message, token=sensitive_token)

    assert sensitive_token not in sanitized
    assert "[REDACTED" in sanitized
