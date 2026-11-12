"""
Unit Tests for Phase 4 Project Knowledge Crystallizer (RES-01, SAF-01)
"""

import os
import shutil
import pytest

from services.backend.coding.project_crystallizer import ProjectKnowledgeCrystallizer
from services.backend.safety.guardian import guardian
from services.backend.safety.registry import registry
import services.backend.tools.coding_tools


@pytest.fixture
def temp_vault(tmp_path):
    vault_dir = tmp_path / "vault"
    vault_dir.mkdir(parents=True, exist_ok=True)
    return str(vault_dir)


@pytest.fixture
def crystallizer(temp_vault):
    return ProjectKnowledgeCrystallizer(vault_path=temp_vault)


def test_note_scaffolding_and_wikilinks(crystallizer, temp_vault):
    """Test initial project note generation with bidirectional wikilinks (RES-01)."""
    res = crystallizer.crystallize_decision(
        project_name="NovaEngine",
        root_path="C:\\Projects\\NovaEngine",
        title="Adopt WebGPU Rendering",
        decision="Migrated from OpenGL to WebGPU for compute shader performance.",
        rationale="Enables local particle physics calculations without CPU bottlenecks.",
        stack_summary="Rust / WGSL"
    )

    assert res["status"] == "crystallized"
    note_path = res["note_path"]
    assert os.path.isfile(note_path)

    with open(note_path, "r", encoding="utf-8") as f:
        content = f.read()

    assert "# Project: NovaEngine" in content
    assert "Rust / WGSL" in content
    assert "[[Daily Notes/" in content
    assert "Adopt WebGPU Rendering" in content
    assert "Enables local particle physics" in content
    assert "## Notes & Journal" in content


def test_non_destructive_merging(crystallizer, temp_vault):
    """Test updating project note preserves handwritten user notes and appends fixes."""
    # 1. Initial creation
    res1 = crystallizer.crystallize_decision(
        project_name="NovaEngine",
        root_path="C:\\Projects\\NovaEngine",
        title="Initial Architecture",
        decision="Monorepo layout."
    )
    note_path = res1["note_path"]

    # 2. Simulate user writing custom journal notes into the file
    with open(note_path, "r", encoding="utf-8") as f:
        content = f.read()
    user_notes = "### Private Thoughts\nRemember to benchmark frame rates on low-end laptops!"
    content = content.replace("*(User notes and reflections here - preserved across automated updates)*\n", user_notes)
    with open(note_path, "w", encoding="utf-8") as f:
        f.write(content)

    # 3. Automated build fix crystallization
    res2 = crystallizer.crystallize_build_fix(
        project_name="NovaEngine",
        root_path="C:\\Projects\\NovaEngine",
        error_type="E0308",
        file_path="src/render.rs",
        patch_summary="Added missing lifetime annotation 'a to BufferRef"
    )
    assert res2["status"] == "crystallized"

    # 4. Verify user's handwritten notes are intact
    with open(note_path, "r", encoding="utf-8") as f:
        updated_content = f.read()

    assert user_notes in updated_content
    assert "src/render.rs" in updated_content
    assert "lifetime annotation" in updated_content
    assert "Initial Architecture" in updated_content


def test_reversible_rollback_token(crystallizer, temp_vault):
    """Test instantaneous note reversion using rollback_token."""
    # Step 1: Initial state
    res1 = crystallizer.crystallize_decision(
        project_name="NovaEngine",
        root_path="C:\\Projects\\NovaEngine",
        title="Original Setting",
        decision="Use default allocator."
    )
    note_path = res1["note_path"]
    with open(note_path, "r", encoding="utf-8") as f:
        original_text = f.read()

    # Step 2: Mutate with second decision
    res2 = crystallizer.crystallize_decision(
        project_name="NovaEngine",
        root_path="C:\\Projects\\NovaEngine",
        title="Experimental Change",
        decision="Switched to mimalloc."
    )
    token = res2["rollback_token"]

    # Step 3: Revert using rollback token
    reverted = crystallizer.rollback_note("NovaEngine", token)
    assert reverted is True

    with open(note_path, "r", encoding="utf-8") as f:
        restored_text = f.read()

    assert restored_text == original_text
    assert "Experimental Change" not in restored_text


def test_safety_tool_registration():
    """Verify crystallization tools in ToolRegistry adhere to risk tiers (SAF-01)."""
    crystallize_tool = registry.get("coding_crystallize_project_knowledge")
    assert crystallize_tool is not None
    assert int(crystallize_tool.tier) == 1

    rollback_tool = registry.get("coding_rollback_crystallized_note")
    assert rollback_tool is not None
    assert int(rollback_tool.tier) == 1

    query_tool = registry.get("coding_query_project_knowledge")
    assert query_tool is not None
    assert int(query_tool.tier) == 0


def test_guardian_halt(crystallizer):
    """Verify Guardian halt immediately blocks crystallization mutations (SAF-02)."""
    guardian.trigger("Test crystallizer halt")
    assert crystallizer.is_halted is True

    with pytest.raises(PermissionError, match="Guardian kill switch is active"):
        crystallizer.crystallize_decision(
            project_name="NovaEngine",
            root_path="C:\\Projects\\NovaEngine",
            title="Blocked Decision",
            decision="Will fail."
        )

    guardian.resume()
    assert crystallizer.is_halted is False
