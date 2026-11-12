"""
Phenom Phase 2 Verification Suite: Obsidian Second Brain & Note Crystallization
Tests automated session crystallization, Obsidian YAML/wikilink formatting,
strict vault path sandboxing, 1-click reversible rollback, and Tier 1 Safety Registry tools.
"""

import os
import shutil
import tempfile
import pytest
from datetime import datetime, timezone

from services.backend.memory.vault import (
    ObsidianVaultManager,
    resolve_and_sandbox_vault_path,
    VaultSandboxViolation,
    find_repo_root
)
from services.backend.memory.crystallizer import (
    SessionCrystallizer,
    CrystallizedItem,
    NoteType,
    sanitize_filename
)
from services.backend.safety.registry import registry
from services.backend.tools.memory_tools import (
    crystallize_session_notes,
    rollback_vault_note
)


@pytest.fixture
def temp_vault():
    """Creates an isolated temporary Obsidian vault for safe testing."""
    temp_dir = tempfile.mkdtemp(prefix="phenom-test-vault-")
    manager = ObsidianVaultManager(vault_path=temp_dir)
    crystallizer = SessionCrystallizer(vault_inst=manager)
    yield manager, crystallizer, temp_dir
    shutil.rmtree(temp_dir, ignore_errors=True)


# =====================================================================
# 1. EXTRACTION & FORMATTING TESTS
# =====================================================================

def test_extract_decisions():
    crystallizer = SessionCrystallizer()
    text = """
    We discussed architectural patterns for the hybrid model.
    Decision: Use local RTX 8B for fast intent classification and cloud Nemotron for complex vision.
    The rationale was keeping latency under 5ms for local actions.
    """
    items = crystallizer.extract_from_text(text, session_id="test-session-1")
    assert len(items) == 1
    decision = items[0]
    assert decision.note_type == NoteType.DECISION
    assert "local RTX 8B" in decision.title
    assert "decision" in decision.tags
    assert "[[Decisions Index]]" in decision.wikilinks


def test_extract_tasks_with_priority():
    crystallizer = SessionCrystallizer()
    text = """
    Action items for today:
    - [ ] Deploy new particle orb shaders [high]
    - [ ] Run benchmark on wake word engine
    * [ ] Update documentation [low]
    """
    items = crystallizer.extract_from_text(text, session_id="test-session-2")
    assert len(items) == 3

    assert items[0].note_type == NoteType.TASK
    assert items[0].metadata.get("priority") == "high"
    assert "priority-high" in items[0].tags

    assert items[1].note_type == NoteType.TASK
    assert items[1].metadata.get("priority") == "normal"

    assert items[2].note_type == NoteType.TASK
    assert items[2].metadata.get("priority") == "low"


def test_extract_research_and_code_snippets():
    crystallizer = SessionCrystallizer()
    text = """
    Research: Three.js InstancedMesh with 15k particles maintains 60fps on RTX GPUs.
    Memory usage remained below 220MB throughout tests.
    """
    items = crystallizer.extract_from_text(text, session_id="test-session-3")
    assert len(items) == 1
    res = items[0]
    assert res.note_type == NoteType.RESEARCH
    assert "Three.js InstancedMesh" in res.title
    assert "research" in res.tags


def test_extract_empty_and_casual_banter():
    crystallizer = SessionCrystallizer()
    assert crystallizer.extract_from_text("") == []
    assert crystallizer.extract_from_text("   \n\t  ") == []
    assert crystallizer.extract_from_text("Hello Phenom! How are you today? I am doing great.") == []


def test_obsidian_formatting_yaml_frontmatter():
    crystallizer = SessionCrystallizer()
    item = CrystallizedItem(
        note_type=NoteType.DECISION,
        title="Decision - Implement Hybrid Router",
        summary="Classify queries in < 5ms",
        content="Details about the hybrid router...",
        tags=["decision", "architecture"],
        wikilinks=["[[Decisions Index]]", "[[Phase 3 Plan]]"]
    )
    formatted = crystallizer.format_obsidian_note(item)

    # Must start with YAML frontmatter
    assert formatted.startswith("---\n")
    assert "title: \"Decision - Implement Hybrid Router\"" in formatted
    assert "type: decision" in formatted
    assert "- decision" in formatted
    assert "- architecture" in formatted
    assert "status: active" in formatted
    assert "> [!NOTE] Summary" in formatted
    assert "- [[Decisions Index]]" in formatted
    assert "- [[Phase 3 Plan]]" in formatted


# =====================================================================
# 2. CRYSTALLIZATION EXECUTION & DAILY LOG TESTS
# =====================================================================

def test_session_crystallization_in_vault(temp_vault):
    manager, crystallizer, temp_dir = temp_vault

    items = [
        CrystallizedItem(
            note_type=NoteType.DECISION,
            title="Decision - Strict Sandboxing",
            summary="Sandboxing note writes to vault",
            content="Always verify os.path.commonpath",
            tags=["decision", "safety"]
        ),
        CrystallizedItem(
            note_type=NoteType.TASK,
            title="Task - Verify Rollback",
            summary="Test 1-click undo",
            content="- [ ] Verify rollback restores prior state",
            tags=["task"]
        )
    ]

    result = crystallizer.crystallize_session(items, session_id="session-42", update_daily_log=True)
    assert result.items_extracted == 2
    assert len(result.notes_written) == 2
    assert result.daily_log_updated is True
    assert len(result.undo_tokens) >= 2

    # Check files exist on disk
    for path in result.notes_written:
        assert os.path.exists(path)
        with open(path, "r", encoding="utf-8") as f:
            content = f.read()
            assert "---" in content
            assert "status: active" in content

    # Check Daily Log was updated
    today = datetime.now().strftime("%Y-%m-%d")
    daily_file = os.path.join(temp_dir, "Daily Logs", f"{today}.md")
    assert os.path.exists(daily_file)
    with open(daily_file, "r", encoding="utf-8") as f:
        daily_text = f.read()
        assert "Session Crystallization (session-42)" in daily_text
        assert "[[Decision - Strict Sandboxing]]" in daily_text


# =====================================================================
# 3. STRICT SANDBOXING & PATH TRAVERSAL DEFENSE TESTS
# =====================================================================

def test_sandboxing_valid_subpaths(temp_vault):
    manager, crystallizer, temp_dir = temp_vault

    # Normal relative paths inside vault
    p1 = resolve_and_sandbox_vault_path("Notes/Test.md", temp_dir)
    assert p1.startswith(os.path.realpath(temp_dir))

    p2 = resolve_and_sandbox_vault_path("Daily Logs/2026-11-02.md", temp_dir)
    assert p2.startswith(os.path.realpath(temp_dir))


def test_sandboxing_rejects_empty():
    with pytest.raises(VaultSandboxViolation):
        resolve_and_sandbox_vault_path("")

    with pytest.raises(VaultSandboxViolation):
        resolve_and_sandbox_vault_path("   ")


def test_sandboxing_blocks_parent_directory_traversal(temp_vault):
    manager, crystallizer, temp_dir = temp_vault

    # Traversal escaping vault root
    with pytest.raises(VaultSandboxViolation):
        resolve_and_sandbox_vault_path("../escaped.md", temp_dir)

    with pytest.raises(VaultSandboxViolation):
        resolve_and_sandbox_vault_path("Notes/../../escaped.md", temp_dir)

    with pytest.raises(VaultSandboxViolation):
        resolve_and_sandbox_vault_path("Notes/../../../Windows/System32/evil.dll", temp_dir)


def test_sandboxing_blocks_repo_collision(temp_vault):
    manager, crystallizer, temp_dir = temp_vault
    repo_root = find_repo_root()

    # Attempting to target file inside the code repository
    code_file = os.path.join(repo_root, "services", "backend", "main.py")
    with pytest.raises(VaultSandboxViolation):
        resolve_and_sandbox_vault_path(code_file, temp_dir)


# =====================================================================
# 4. 1-CLICK REVERSIBLE ROLLBACK TESTS
# =====================================================================

def test_1click_rollback_created_note(temp_vault):
    manager, crystallizer, temp_dir = temp_vault

    items = [
        CrystallizedItem(
            note_type=NoteType.RESEARCH,
            title="Research - Temporary Spike",
            summary="Throwaway spike note",
            content="Testing deletion on rollback",
            tags=["spike"]
        )
    ]
    result = crystallizer.crystallize_session(items, session_id="rollback-test", update_daily_log=False)
    created_note = result.notes_written[0]
    undo_token = result.undo_tokens[0]

    assert os.path.exists(created_note)

    # Execute 1-click rollback
    rollback_res = crystallizer.rollback_vault_mutation(undo_token)
    assert rollback_res["status"] == "deleted"
    assert not os.path.exists(created_note)

    # Calling rollback again with same token must fail
    with pytest.raises(ValueError):
        crystallizer.rollback_vault_mutation(undo_token)


def test_1click_rollback_updated_note(temp_vault):
    manager, crystallizer, temp_dir = temp_vault

    # Create pre-existing note
    note_rel = os.path.join("Notes", "Decisions", "Decision - Preexisting.md")
    note_path = resolve_and_sandbox_vault_path(note_rel, temp_dir)
    os.makedirs(os.path.dirname(note_path), exist_ok=True)
    original_content = "# Original Title\n\nOriginal preserved text."
    with open(note_path, "w", encoding="utf-8") as f:
        f.write(original_content)

    # Overwrite via crystallizer
    updated_item = [
        CrystallizedItem(
            note_type=NoteType.DECISION,
            title="Decision - Preexisting",
            summary="New summary",
            content="New overwritten content",
            tags=["decision"]
        )
    ]
    result = crystallizer.crystallize_session(updated_item, session_id="update-test", update_daily_log=False)
    undo_token = result.undo_tokens[0]

    # Verify overwritten
    with open(note_path, "r", encoding="utf-8") as f:
        assert "New overwritten content" in f.read()

    # Revert via 1-click rollback
    rollback_res = crystallizer.rollback_vault_mutation(undo_token)
    assert rollback_res["status"] == "restored"

    # Verify original content is restored
    with open(note_path, "r", encoding="utf-8") as f:
        restored = f.read()
        assert restored == original_content


# =====================================================================
# 5. SAFETY REGISTRY & TOOL REGISTRATION TESTS
# =====================================================================

def test_crystallize_tools_registered_in_safety_registry():
    c_tool = registry.get("crystallize_session_notes")
    assert c_tool is not None
    assert c_tool.tier == 1
    assert c_tool.preview_fn is not None

    r_tool = registry.get("rollback_vault_note")
    assert r_tool is not None
    assert r_tool.tier == 1
    assert r_tool.preview_fn is not None

    # Test preview functions
    preview_c = c_tool.preview_fn({"session_text": "Decision: use sqlite", "session_id": "test-123"})
    assert "test-123" in preview_c
    assert "Crystallize session insights" in preview_c

    preview_r = r_tool.preview_fn({"undo_token": "undo-vault-abc"})
    assert "undo-vault-abc" in preview_r
    assert "Rollback" in preview_r
