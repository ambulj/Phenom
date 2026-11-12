"""
Integration Tests for Cognitive Mirror & Personalized Synthetic Twin (MIR-01, SAF-01)
Verifies multi-dimensional learning, confidence score progression, synthetic twin generation,
and zero cloud exfiltration.
"""

import os
import socket
import pytest
from unittest.mock import patch

from services.backend.schemas.cognitive_mirror import (
    MirrorDimension,
    SynthesisTaskType,
    GitStyleProfile,
    CognitiveProfile,
)
from services.backend.personality.cognitive_mirror import CognitiveMirrorEngine


@pytest.fixture
def clean_engine(tmp_path):
    db_file = str(tmp_path / "test_cognitive_mirror.db")
    engine = CognitiveMirrorEngine(db_path=db_file, encryption_key="test_mirror_secret_key_1234567890")
    return engine


def test_incremental_learning_and_confidence_progression(clean_engine):
    """Verifies confidence score increases as sample count grows."""
    engine = clean_engine

    # Initial state
    stats = engine.get_stats(MirrorDimension.GIT_STYLE)
    assert stats["confidence"] == 0.0
    assert stats["sample_count"] == 0

    # Learn 5 commits
    commits_batch_1 = [
        "feat(auth): add sqlcipher integration",
        "fix(core): resolve null pointer exception",
        "refactor(db): streamline query caching",
        "docs(api): document cognitive mirror contracts",
        "chore(deps): bump pydantic version",
    ]
    res1 = engine.learn_from_git(commits_override=commits_batch_1)
    assert res1["status"] == "success"
    assert res1["samples_learned"] == 5
    assert 0.2 <= res1["confidence"] <= 0.3

    # Learn 20 commits
    commits_batch_2 = [f"feat(module): add feature component {i}" for i in range(20)]
    res2 = engine.learn_from_git(commits_override=commits_batch_2)
    assert res2["samples_learned"] == 20
    assert res2["confidence"] == 1.0  # Cap reached at 20+ samples


def test_multi_source_learning(clean_engine):
    """Verifies learning across git, obsidian, emails, and work habits simultaneously."""
    engine = clean_engine

    mock_commits = [
        "feat(ui): update particle cloud colors",
        "fix(audio): resolve buffer underrun",
    ]
    mock_notes = [
        """# 2026-11-03 Project State
## Notes & Journal
- Reviewed [[Cognitive Mirror]] and [[Synthetic Twin]]
> [!NOTE]
> High confidence achieved.
"""
    ]
    mock_emails = [
        """Hi Team,

Let's make sure we benchmark the Guardian SLA under 25ms.

- Run pytest
- Measure halt latency

Best,
Phenom
"""
    ]
    mock_habits = [1730620800 + (i * 900) for i in range(10)]

    engine.learn_from_git(commits_override=mock_commits)
    engine.learn_from_obsidian(notes_override=mock_notes)
    engine.learn_from_email_drafts(drafts=mock_emails)
    engine.learn_from_work_habits(timestamps=mock_habits)

    profile = engine.get_profile()
    assert isinstance(profile, CognitiveProfile)
    assert profile.git_style.conventional_commits_ratio == 1.0
    assert "NOTE" in profile.obsidian_cadence.preferred_callouts
    assert profile.communication_persona.preferred_salutations[0] == "Hi"
    assert len(profile.work_habits.peak_hours) > 0


def test_synthetic_twin_commit_generation(clean_engine):
    """Verifies synthetic commit message conforms to learned conventional commits style."""
    engine = clean_engine
    commits = [
        "feat(auth): implement token generator",
        "fix(core): handle edge case",
        "feat(mirror): add synthetic twin generator",
    ]
    engine.learn_from_git(commits_override=commits)

    res = engine.synthesize_text(
        task=SynthesisTaskType.COMMIT_MESSAGE,
        context_prompt="implemented token refresh flow",
        metadata={"scope": "auth"},
    )
    assert res.task == SynthesisTaskType.COMMIT_MESSAGE
    # Conventional commit format: prefix(scope): subject
    assert "feat(auth): implement token refresh flow" in res.synthesized_text or "fix(auth): implement token refresh flow" in res.synthesized_text
    assert "conventional_commits" in res.applied_style_traits
    assert "imperative_mood" in res.applied_style_traits


def test_synthetic_twin_code_comment(clean_engine):
    """Verifies code review comment reflects learned review tone."""
    engine = clean_engine
    reviews = [
        "Could we check type safety here? What if the input is None?",
        "Should this be immutable to prevent concurrency issues?",
    ]
    engine.learn_from_git(commits_override=["feat: init"], reviews_override=reviews)

    res = engine.synthesize_text(
        task=SynthesisTaskType.CODE_COMMENT,
        context_prompt="Potential null dereference in query handler",
        metadata={"code_context": "user_id = req.user.id"},
    )
    assert "inquisitive" in str(res.applied_style_traits)
    assert "?" in res.synthesized_text


def test_synthetic_twin_email_and_note(clean_engine):
    """Verifies email draft and obsidian note generation."""
    engine = clean_engine
    drafts = [
        "Hi John,\nLet's make sure we wrap up testing.\n\nBest,\nDev",
    ]
    engine.learn_from_email_drafts(drafts=drafts)
    email_res = engine.synthesize_text(
        task=SynthesisTaskType.EMAIL_DRAFT,
        context_prompt="We have completed Phase 3 tests.",
        metadata={"recipient": "Sarah"},
    )
    assert "Hi Sarah," in email_res.synthesized_text
    assert "Best," in email_res.synthesized_text

    note_res = engine.synthesize_text(
        task=SynthesisTaskType.OBSIDIAN_NOTE,
        context_prompt="Verified SQLCipher encryption and Guardian SLA.",
        metadata={"topic": "Milestone 10 Phase 3"},
    )
    assert "Milestone 10 Phase 3" in note_res.synthesized_text
    assert "> [!NOTE]" in note_res.synthesized_text


def test_zero_cloud_exfiltration(clean_engine):
    """Verifies synthesis and extraction do not open any outbound socket connections."""
    engine = clean_engine

    original_connect = socket.socket.connect

    def forbidden_connect(self, *args, **kwargs):
        raise AssertionError("Zero cloud exfiltration violation: outbound socket connection attempted!")

    with patch.object(socket.socket, "connect", forbidden_connect):
        # Run learning and synthesis - must not touch any network
        engine.learn_from_git(commits_override=["feat(test): local commit"])
        res = engine.synthesize_text(
            task=SynthesisTaskType.COMMIT_MESSAGE,
            context_prompt="testing offline guarantee",
        )
        assert res.synthesized_text
