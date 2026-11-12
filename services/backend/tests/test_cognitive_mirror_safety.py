"""
Safety and Governance Tests for Cognitive Mirror Tools (SAF-01)
Verifies ToolRegistry tier assignment, schema validation, and preview functions.
"""

import pytest
from pydantic import ValidationError
from services.backend.safety.registry import registry
import services.backend.tools.mirror_tools  # Ensures registration
from services.backend.schemas.cognitive_mirror import (
    MirrorDimension,
    SynthesisTaskType,
    MirrorGetProfileStatsArgs,
    MirrorLearnFromSourcesArgs,
    MirrorSynthesizeTextArgs,
    MirrorResetProfileArgs,
)
from services.backend.tools.mirror_tools import (
    mirror_get_profile_stats,
    mirror_synthesize_text,
    mirror_learn_from_sources,
    mirror_reset_profile,
)


def test_tool_registry_tiers():
    """Asserts correct risk tier classifications for all 4 mirror tools."""
    assert registry.get("mirror_get_profile_stats") is not None
    assert registry.get_tier("mirror_get_profile_stats") == 0

    assert registry.get("mirror_synthesize_text") is not None
    assert registry.get_tier("mirror_synthesize_text") == 0

    assert registry.get("mirror_learn_from_sources") is not None
    assert registry.get_tier("mirror_learn_from_sources") == 1

    assert registry.get("mirror_reset_profile") is not None
    assert registry.get_tier("mirror_reset_profile") == 1


def test_preview_functions():
    """Verifies human-readable preview strings for tool execution."""
    stats_tool = registry.get("mirror_get_profile_stats")
    assert stats_tool is not None
    stats_preview = stats_tool.generate_preview({"dimension": "git_style"})
    assert "git_style" in stats_preview
    assert "(Read-Only)" in stats_preview

    synth_tool = registry.get("mirror_synthesize_text")
    assert synth_tool is not None
    synth_preview = synth_tool.generate_preview({"task": "commit_message", "context_prompt": "add auth"})
    assert "commit_message" in synth_preview

    learn_tool = registry.get("mirror_learn_from_sources")
    assert learn_tool is not None
    learn_preview = learn_tool.generate_preview({"sources": ["git", "obsidian"], "max_items": 50})
    assert "git, obsidian" in learn_preview
    assert "max 50" in learn_preview

    reset_tool = registry.get("mirror_reset_profile")
    assert reset_tool is not None
    reset_preview = reset_tool.generate_preview({"dimensions": ["git_style"]})
    assert "git_style" in reset_preview


def test_schema_validations():
    """Verifies Pydantic validation rejects malformed tool inputs."""
    # Invalid dimension
    with pytest.raises(ValidationError):
        MirrorGetProfileStatsArgs(dimension="invalid_dim")  # type: ignore

    # Invalid synthesis task
    with pytest.raises(ValidationError):
        MirrorSynthesizeTextArgs(task="hack_computer", context_prompt="run")  # type: ignore


@pytest.mark.asyncio
async def test_tool_execution_flow():
    """Verifies end-to-end async execution of mirror tools via wrapper handlers."""
    # 1. Get initial stats
    stats_res = await mirror_get_profile_stats(MirrorGetProfileStatsArgs())
    assert stats_res["status"] == "success"
    assert "stats" in stats_res

    # 2. Synthesize text
    synth_res = await mirror_synthesize_text(
        MirrorSynthesizeTextArgs(
            task=SynthesisTaskType.COMMIT_MESSAGE,
            context_prompt="update documentation and safety guidelines",
        )
    )
    assert synth_res["status"] == "success"
    assert synth_res["synthesized_text"]

    # 3. Reset profile
    reset_res = await mirror_reset_profile(
        MirrorResetProfileArgs(dimensions=[MirrorDimension.GIT_STYLE])
    )
    assert reset_res["status"] == "success"
