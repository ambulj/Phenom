"""
Phenom Cognitive Mirror Schemas and Protocol Models
Pydantic V2 models for modeling personal coding, journaling, communication,
and work habits styles, along with encrypted synthesis contracts (MIR-01, SAF-01).
"""

from enum import Enum
from typing import Dict, List, Optional, Tuple, Any
from datetime import datetime, timezone
from pydantic import BaseModel, Field


class MirrorDimension(str, Enum):
    GIT_STYLE = "git_style"
    OBSIDIAN_CADENCE = "obsidian_cadence"
    COMMUNICATION_PERSONA = "communication_persona"
    WORK_HABITS = "work_habits"


class SynthesisTaskType(str, Enum):
    COMMIT_MESSAGE = "commit_message"
    CODE_COMMENT = "code_comment"
    EMAIL_DRAFT = "email_draft"
    OBSIDIAN_NOTE = "obsidian_note"


class GitStyleProfile(BaseModel):
    conventional_commits_ratio: float = 0.0
    primary_prefixes: Dict[str, float] = Field(default_factory=dict)
    avg_subject_length: int = 50
    imperative_mood_ratio: float = 0.0
    lowercase_subject_ratio: float = 0.0
    review_tone: str = "direct"  # direct, inquisitive, encouraging
    architectural_preferences: List[str] = Field(default_factory=list)


class ObsidianThoughtProfile(BaseModel):
    avg_heading_depth: float = 2.0
    preferred_bullet_marker: str = "-"
    wikilink_density_per_500_words: float = 0.0
    tag_density_per_500_words: float = 0.0
    callout_frequency: float = 0.0
    preferred_callouts: List[str] = Field(default_factory=list)
    daily_note_sections: List[str] = Field(default_factory=list)


class CommunicationPersonaProfile(BaseModel):
    preferred_salutations: List[str] = Field(default_factory=list)
    preferred_signoffs: List[str] = Field(default_factory=list)
    formality_score: float = 0.5  # 0.0 colloquial to 1.0 formal
    brevity_score: float = 0.5    # 0.0 verbose to 1.0 ultra-terse
    bullet_point_preference: float = 0.0
    characteristic_phrases: List[str] = Field(default_factory=list)


class WorkHabitsProfile(BaseModel):
    peak_hours: List[int] = Field(default_factory=list)
    break_cadence_minutes: int = 60
    quiet_time_windows: List[Tuple[int, int]] = Field(default_factory=list)
    hourly_distribution: Dict[int, float] = Field(default_factory=dict)


class CognitiveProfile(BaseModel):
    git_style: GitStyleProfile = Field(default_factory=GitStyleProfile)
    obsidian_cadence: ObsidianThoughtProfile = Field(default_factory=ObsidianThoughtProfile)
    communication_persona: CommunicationPersonaProfile = Field(default_factory=CommunicationPersonaProfile)
    work_habits: WorkHabitsProfile = Field(default_factory=WorkHabitsProfile)
    confidence_scores: Dict[str, float] = Field(default_factory=dict)
    sample_counts: Dict[str, int] = Field(default_factory=dict)
    last_updated: str = ""
    version: int = 1


# Tool Argument Schemas

class MirrorGetProfileStatsArgs(BaseModel):
    dimension: Optional[MirrorDimension] = None


class MirrorLearnFromSourcesArgs(BaseModel):
    sources: List[str] = Field(default_factory=lambda: ["git", "obsidian", "email", "habits"])
    max_items: Optional[int] = 100
    repo_path: Optional[str] = None
    vault_path: Optional[str] = None


class MirrorSynthesizeTextArgs(BaseModel):
    task: SynthesisTaskType
    context_prompt: str
    metadata: Optional[Dict[str, Any]] = None


class MirrorResetProfileArgs(BaseModel):
    dimensions: Optional[List[MirrorDimension]] = None


# Synthesis and Learning Models

class MirrorSynthesisResult(BaseModel):
    task: SynthesisTaskType
    synthesized_text: str
    applied_style_traits: List[str] = Field(default_factory=list)
    confidence: float = 0.0
    duration_ms: float = 0.0


class SynthesisResponse(MirrorSynthesisResult):
    pass


class LearningSample(BaseModel):
    sample_id: str
    dimension: MirrorDimension
    source_type: str
    features: Dict[str, Any] = Field(default_factory=dict)
    timestamp: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


class SynthesisRequest(BaseModel):
    task: SynthesisTaskType
    context_prompt: str
    metadata: Dict[str, Any] = Field(default_factory=dict)
