"""
Tests for Multi-Dimensional Cognitive Feature Extractors (MIR-01, Rule 11)
Verifies feature extraction for Git commits/reviews, Obsidian notes,
Email drafts, and Work habits timestamps, including secret scrubbing.
"""

import time
import pytest
from datetime import datetime, timezone

from services.backend.personality.extractors import (
    GitStyleExtractor,
    ObsidianThoughtExtractor,
    EmailPersonaExtractor,
    WorkHabitsExtractor,
)


def test_git_style_extractor_commits():
    """Verifies parsing of conventional vs freeform commits and imperative mood."""
    commits = [
        "feat(auth): add SQLCipher encryption key retrieval",
        "fix(safety): handle guardian halt race condition",
        "refactor(memory): optimize vector store lookups",
        "docs: update API documentation",
        "feat: implement cognitive mirror engine",
        "WIP added some stuff sk-1234567890abcdef1234567890",
        "fixed broken build",
    ]

    profile = GitStyleExtractor.extract_from_commits(commits)
    assert profile.conventional_commits_ratio > 0.6
    assert "feat" in profile.primary_prefixes
    assert "fix" in profile.primary_prefixes
    assert profile.imperative_mood_ratio > 0.5
    assert profile.avg_subject_length > 10
    # Credential in 6th commit must not leak into any representation
    assert "sk-" not in str(profile.model_dump())


def test_git_style_extractor_reviews():
    """Verifies tone classification and architectural keyword extraction."""
    reviews = [
        "Could we ensure type safety here? What if the input is None?",
        "Nice implementation! Looks clean and modular.",
        "Must avoid mutable defaults to ensure immutability and thread safe execution.",
    ]

    tone, arch_terms = GitStyleExtractor.extract_from_reviews(reviews)
    assert tone in ["inquisitive", "direct", "encouraging"]
    assert "type safety" in arch_terms
    assert "immutability" in arch_terms
    assert "thread safe" in arch_terms


def test_obsidian_thought_extractor():
    """Verifies markdown parsing: headings, wikilinks, tags, and callouts."""
    notes = [
        """# 2026-11-03 Daily Note
## Notes & Journal
Working on [[Cognitive Mirror]] and [[SQLCipher]] integration.
- Built database manager
- Added #security and #encryption tags

> [!NOTE]
> Ensure Guardian SLA is sub-25ms.

> [!TIP]
> Keep secrets in Windows Credential Manager.
""",
        """## Architecture Spec
### Components
* Integrated with [[FastAPI]]
* #performance review
> [!NOTE]
> Redact all in memory.
"""
    ]

    profile = ObsidianThoughtExtractor.extract_from_notes(notes)
    assert profile.avg_heading_depth >= 1.5
    assert profile.wikilink_density_per_500_words > 0.0
    assert profile.tag_density_per_500_words > 0.0
    assert "NOTE" in profile.preferred_callouts
    assert any("Notes & Journal" in sec or "Architecture Spec" in sec for sec in profile.daily_note_sections)


def test_email_persona_extractor():
    """Verifies email drafts extraction: formality, brevity, salutations, and phrases."""
    drafts = [
        """Hi Alex,

Let's make sure we test the Guardian kill switch thoroughly.

- Run unit tests
- Benchmark latency

Sounds good?

Best,
Phenom
""",
        """Dear Dr. Smith,

Furthermore, we cannot proceed with cloud exfiltration per our conversation. Please find attached the report.

Sincerely,
Phenom
"""
    ]

    profile = EmailPersonaExtractor.extract_from_drafts(drafts)
    assert any(s in ["Hi", "Dear"] for s in profile.preferred_salutations)
    assert any(s in ["Best,", "Best", "Sincerely,", "Sincerely"] for s in profile.preferred_signoffs)
    assert 0.0 <= profile.formality_score <= 1.0
    assert profile.bullet_point_preference > 0.0
    assert any("sounds good" in p or "let's make sure" in p for p in profile.characteristic_phrases)


def test_work_habits_extractor():
    """Verifies 24-hour diurnal binning, peak hours, and break cadence."""
    # Create synthetic timestamps centered around 10am, 11am, 2pm (14:00), 3pm (15:00)
    base_date = datetime(2026, 11, 3, 0, 0, 0, tzinfo=timezone.utc)
    base_ts = base_date.timestamp()

    timestamps = []
    # Morning burst: 10:00 to 11:30 (with 15 min gaps)
    for minute in range(0, 90, 15):
        timestamps.append(base_ts + (10 * 3600) + (minute * 60))

    # Afternoon burst: 14:00 to 15:30 (with 20 min gaps)
    for minute in range(0, 90, 20):
        timestamps.append(base_ts + (14 * 3600) + (minute * 60))

    profile = WorkHabitsExtractor.extract_from_timestamps(timestamps)
    assert len(profile.hourly_distribution) == 24
    assert len(profile.peak_hours) > 0
    assert 10 <= profile.break_cadence_minutes <= 30
    assert len(profile.quiet_time_windows) > 0


def test_extractor_secret_sanitization():
    """Verifies secrets never enter extracted profiles."""
    commits = [
        "feat(auth): configure Bearer ya29.1234567890abcdef1234567890 in C:\\Users\\Dev\\secrets.json",
    ]
    profile = GitStyleExtractor.extract_from_commits(commits)
    serialized = str(profile.model_dump())
    assert "ya29." not in serialized
    assert "C:\\Users\\Dev" not in serialized
