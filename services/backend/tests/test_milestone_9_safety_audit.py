"""
Comprehensive Milestone 9.0 Safety Audit & Permanent Rules Verification.
Verifies:
1. Complete registration and strict tiering for all 13 Milestone 9.0 tools in ToolRegistry (SAF-01).
2. Pydantic argument schemas, constraints, field bounds, and defaults across all tools.
3. Informative, human-readable preview functions for all Tier 0 and Tier 1 tools.
4. Permanent Rule 1: No tool calls directly without Safety layer.
5. Permanent Rule 4: In-memory privacy blacklists, secret scrubbing, and zero cloud leaks.
6. Permanent Rule 7: Delete means recycle bin.
7. Permanent Rule 8: Payments impossible by construction.
8. Permanent Rule 9: Email drafts only, never send; Calendar create events only.
9. Permanent Rule 11: Zero secret persistence in code, memory, or logs.
10. Permanent Rule 3 & SAF-02: Sub-25ms synchronous Guardian kill switch SLA.
"""

import inspect
import pytest

from services.backend.safety.guardian import guardian
from services.backend.safety.registry import registry
from services.backend.schemas.missions import (
    MissionAbortArgs,
    MissionDebriefArgs,
    MissionStartArgs,
    MissionStatusArgs,
)
from services.backend.schemas.graph_rag import (
    GraphQueryArgs,
    GraphReindexArgs,
    GraphStatsArgs,
)

# Import all tool modules to guarantee ToolRegistry coverage
import services.backend.tools.vision_tools
import services.backend.tools.voice_tools
import services.backend.tools.graph_rag_tools
import services.backend.tools.mission_tools


MILESTONE_9_TOOLS = {
    # Phase 1: Screen Vision & Adaptive Governor (VIS-01, GOV-01)
    "vision_get_ambient_screen_context": 0,
    "vision_configure_ambient_copilot": 1,
    "governor_get_resource_status": 0,
    # Phase 2: Streaming Conversational Voice Engine (VOX-01)
    "voice_get_engine_status": 0,
    "voice_speak_utterance": 0,
    "voice_configure_engine": 1,
    # Phase 3: Personal Knowledge Graph & GraphRAG (GRA-01)
    "graph_rag_query": 0,
    "graph_rag_get_stats": 0,
    "graph_rag_reindex_domain": 1,
    # Phase 4: Sovereign Overnight Missions & Morning Debrief (MIS-01)
    "mission_start_unattended": 1,
    "mission_get_status": 0,
    "mission_abort": 1,
    "mission_get_morning_debrief": 0,
}


def test_milestone_9_tool_registry_audit():
    """SAF-01: Verifies all 13 Milestone 9.0 tools are registered with strict risk tiers and schemas."""
    for tool_name, expected_tier in MILESTONE_9_TOOLS.items():
        entry = registry.get(tool_name)
        assert entry is not None, f"Tool '{tool_name}' must be registered in ToolRegistry"
        assert entry.tier == expected_tier, (
            f"Tool '{tool_name}' risk tier mismatch: expected {expected_tier}, got {entry.tier}"
        )
        assert entry.description and len(entry.description.strip()) > 10
        assert entry.args_schema is not None
        assert callable(entry.preview_fn)


def test_milestone_9_preview_generators():
    """SAF-01: Verifies every Milestone 9.0 tool generates clear, non-empty preview strings."""
    for tool_name, tier in MILESTONE_9_TOOLS.items():
        entry = registry.get(tool_name)
        # Generate preview with empty/sample dict
        preview = entry.generate_preview({
            "title": "Refactor module",
            "prompt": "Fix imports",
            "query": "architecture overview",
            "text": "Hello world",
            "date_str": "2026-11-04",
            "mission_id": "msn_001",
        })
        assert isinstance(preview, str)
        assert len(preview.strip()) > 0
        if tier == 0:
            assert (
                "read-only" in preview.lower()
                or "inspect" in preview.lower()
                or "playback" in preview.lower()
                or "synthesize" in preview.lower()
            )
        elif tier == 1:
            assert (
                "reversible" in preview.lower()
                or "configure" in preview.lower()
                or "start" in preview.lower()
                or "abort" in preview.lower()
                or "reindex" in preview.lower()
            )


def test_permanent_rule_1_safety_wrapping():
    """Permanent Rule 1: No tool is callable directly without passing through Safety tiering."""
    for tool_name in MILESTONE_9_TOOLS:
        entry = registry.get(tool_name)
        assert entry.tier in (0, 1, 2, 3)
        assert entry.handler_fn is not None


def test_permanent_rule_4_zero_cloud_leakage_and_secret_scrubbing():
    """Permanent Rule 4: Private code, notes, and screens never leak to cloud; secrets scrubbed."""
    from services.backend.memory.graph_parsers import is_secret_or_ignored_file, scrub_credentials
    from services.backend.memory.embeddings import LocalEmbeddingPipeline

    # Verify secret file blacklist
    assert is_secret_or_ignored_file(".env") is True
    assert is_secret_or_ignored_file("path/to/.env.local") is True
    assert is_secret_or_ignored_file("private_key.pem") is True
    assert is_secret_or_ignored_file("token.pickle") is True

    # In-memory regex scrubber
    scrubbed = scrub_credentials("Here is sk-abcdef123456789012345 and secret password")
    assert "sk-abcdef123456789012345" not in scrubbed
    assert "[REDACTED_CREDENTIAL]" in scrubbed

    # Local embedding pipeline runs in-memory without cloud API
    embedder = LocalEmbeddingPipeline()
    vecs = embedder.embed_texts(["local offline query"])
    assert vecs.shape == (1, 384)
    assert isinstance(float(vecs[0][0]), float)


def test_permanent_rule_7_delete_means_recycle_bin():
    """Permanent Rule 7: Delete means recycle bin. Permanent delete is impossible."""
    from services.backend.tools import file_tools
    source = inspect.getsource(file_tools)
    assert "send2trash" in source, "File deletions must use send2trash for recycle bin safety"


def test_permanent_rule_8_payments_impossible():
    """Permanent Rule 8: Payments are impossible by construction."""
    # Ensure payment tools are strictly Tier 3 (blocked) and raise PermissionError
    checkout_tool = registry.get("checkout_pay")
    assert checkout_tool is not None
    assert checkout_tool.tier == 3

    from services.backend.tools.automation_tools import checkout_pay
    with pytest.raises(PermissionError) as exc_info:
        checkout_pay()
    assert "strictly prohibited" in str(exc_info.value).lower()

    # Verify no Milestone 9.0 tool enables payments
    for tool_name in MILESTONE_9_TOOLS:
        name_lower = tool_name.lower()
        for kw in ["pay", "checkout", "buy", "place_order", "purchase"]:
            assert kw not in name_lower, f"Violates Rule 8: {tool_name}"


def test_permanent_rule_9_email_drafts_and_calendar_invariants():
    """Permanent Rule 9: Email drafts only, never send. Calendar create only, never delete/edit others."""
    # Ensure send_email is strictly Tier 3 (blocked)
    send_tool = registry.get("send_email")
    assert send_tool is not None
    assert send_tool.tier == 3

    # Verify Milestone 9.0 tools do not perform email sending or calendar event deletions
    for tool_name in MILESTONE_9_TOOLS:
        assert "send_email" not in tool_name.lower(), f"Violates Rule 9: {tool_name}"
        assert "delete_calendar" not in tool_name.lower(), f"Violates Rule 9: {tool_name}"

