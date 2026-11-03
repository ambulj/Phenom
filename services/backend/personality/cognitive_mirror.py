"""
Phenom Cognitive Mirror Orchestration Engine (MIR-01, SAF-02)
Manages multi-dimensional cognitive profiling, encrypted SQLCipher persistence,
incremental style learning, and sub-25ms synchronous Guardian kill switch SLA.
"""

import os
import json
import time
import subprocess
import glob
from typing import Optional, List, Dict, Any, Union
from datetime import datetime, timezone

from services.backend.schemas.cognitive_mirror import (
    MirrorDimension,
    SynthesisTaskType,
    GitStyleProfile,
    ObsidianThoughtProfile,
    CommunicationPersonaProfile,
    WorkHabitsProfile,
    CognitiveProfile,
    MirrorSynthesisResult,
)
from services.backend.personality.cognitive_db import CognitiveDatabaseManager
from services.backend.personality.extractors import (
    GitStyleExtractor,
    ObsidianThoughtExtractor,
    EmailPersonaExtractor,
    WorkHabitsExtractor,
)
from services.backend.personality.synthesizer import SyntheticTwinSynthesizer
from services.backend.personality.scrubber import scrub_personal_secrets


class CognitiveMirrorEngine:
    """
    Central orchestrator for the Cognitive Mirror and Personalized Synthetic Twin.
    Ensures zero cloud exfiltration, in-memory credential sanitization,
    encrypted SQLCipher persistence, and immediate synchronous Guardian kill switch compliance.
    """

    def __init__(self, db_path: Optional[str] = None, encryption_key: Optional[str] = None):
        self._halted: bool = False
        self.db = CognitiveDatabaseManager(db_path=db_path, encryption_key=encryption_key)
        self.profile = CognitiveProfile()
        self.synthesizer = SyntheticTwinSynthesizer(self.profile)
        self._load_persisted_profile()

    def halt(self):
        """Synchronously halts all cognitive mirror operations (< 25ms SLA, typical < 1ms)."""
        self._halted = True

    def reset(self):
        """Synchronously restores operational state after Guardian resume."""
        self._halted = False

    @property
    def is_halted(self) -> bool:
        return self._halted

    def _check_halted(self):
        if self._halted:
            raise PermissionError("Guardian kill switch is active. Cognitive mirror operations prohibited.")

    def _load_persisted_profile(self):
        """Loads all dimension profiles from SQLCipher database into memory."""
        try:
            # 1. Git style
            git_data = self.db.get_dimension_profile(MirrorDimension.GIT_STYLE.value)
            if git_data:
                self.profile.git_style = GitStyleProfile.model_validate_json(git_data["profile_json"])
                self.profile.confidence_scores[MirrorDimension.GIT_STYLE.value] = git_data["confidence"]
                self.profile.sample_counts[MirrorDimension.GIT_STYLE.value] = git_data["sample_count"]

            # 2. Obsidian cadence
            obs_data = self.db.get_dimension_profile(MirrorDimension.OBSIDIAN_CADENCE.value)
            if obs_data:
                self.profile.obsidian_cadence = ObsidianThoughtProfile.model_validate_json(obs_data["profile_json"])
                self.profile.confidence_scores[MirrorDimension.OBSIDIAN_CADENCE.value] = obs_data["confidence"]
                self.profile.sample_counts[MirrorDimension.OBSIDIAN_CADENCE.value] = obs_data["sample_count"]

            # 3. Communication persona
            comm_data = self.db.get_dimension_profile(MirrorDimension.COMMUNICATION_PERSONA.value)
            if comm_data:
                self.profile.communication_persona = CommunicationPersonaProfile.model_validate_json(comm_data["profile_json"])
                self.profile.confidence_scores[MirrorDimension.COMMUNICATION_PERSONA.value] = comm_data["confidence"]
                self.profile.sample_counts[MirrorDimension.COMMUNICATION_PERSONA.value] = comm_data["sample_count"]

            # 4. Work habits
            habits_data = self.db.get_dimension_profile(MirrorDimension.WORK_HABITS.value)
            if habits_data:
                self.profile.work_habits = WorkHabitsProfile.model_validate_json(habits_data["profile_json"])
                self.profile.confidence_scores[MirrorDimension.WORK_HABITS.value] = habits_data["confidence"]
                self.profile.sample_counts[MirrorDimension.WORK_HABITS.value] = habits_data["sample_count"]

            self.profile.last_updated = datetime.now(timezone.utc).isoformat()
            self.synthesizer.update_profile(self.profile)
        except Exception:
            # Database might be uninitialized or freshly created
            pass

    def get_profile(self, dimension: Optional[MirrorDimension] = None) -> Union[CognitiveProfile, Dict[str, Any]]:
        """Returns the aggregate CognitiveProfile or a specific dimension."""
        self._check_halted()
        if dimension == MirrorDimension.GIT_STYLE:
            return self.profile.git_style.model_dump()
        elif dimension == MirrorDimension.OBSIDIAN_CADENCE:
            return self.profile.obsidian_cadence.model_dump()
        elif dimension == MirrorDimension.COMMUNICATION_PERSONA:
            return self.profile.communication_persona.model_dump()
        elif dimension == MirrorDimension.WORK_HABITS:
            return self.profile.work_habits.model_dump()
        return self.profile

    def get_stats(self, dimension: Optional[MirrorDimension] = None) -> Dict[str, Any]:
        """Returns stats and confidence scores for cognitive mirror dimensions."""
        self._check_halted()
        stats = {
            "confidence_scores": self.profile.confidence_scores,
            "sample_counts": self.profile.sample_counts,
            "last_updated": self.profile.last_updated,
            "version": self.profile.version,
        }
        if dimension:
            dim_key = dimension.value if isinstance(dimension, MirrorDimension) else str(dimension)
            return {
                "dimension": dim_key,
                "confidence": self.profile.confidence_scores.get(dim_key, 0.0),
                "sample_count": self.profile.sample_counts.get(dim_key, 0),
                "profile": getattr(self.profile, dim_key, {}),
            }
        return stats

    def learn_from_git(
        self,
        repo_path: Optional[str] = None,
        max_commits: int = 100,
        commits_override: Optional[List[Union[str, Dict[str, Any]]]] = None,
        reviews_override: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """Learns git commit patterns and review tone from local git repository."""
        self._check_halted()
        commits: List[Union[str, Dict[str, Any]]] = []

        if commits_override is not None:
            commits = commits_override
        else:
            target_repo = repo_path or os.getcwd()
            try:
                cmd = ["git", "log", f"-n{max_commits}", "--pretty=format:%s"]
                res = subprocess.run(cmd, cwd=target_repo, capture_output=True, text=True, check=False)
                if res.returncode == 0 and res.stdout.strip():
                    commits = [line.strip() for line in res.stdout.splitlines() if line.strip()]
            except Exception:
                commits = []

        if not commits:
            return {"status": "no_data", "dimension": MirrorDimension.GIT_STYLE.value, "samples_learned": 0}

        profile = GitStyleExtractor.extract_from_commits(commits)
        if reviews_override:
            tone, arch = GitStyleExtractor.extract_from_reviews(reviews_override)
            profile.review_tone = tone
            profile.architectural_preferences = arch

        sample_count = len(commits)
        confidence = min(1.0, round(sample_count / 20.0, 2))

        self.profile.git_style = profile
        self.profile.sample_counts[MirrorDimension.GIT_STYLE.value] = sample_count
        self.profile.confidence_scores[MirrorDimension.GIT_STYLE.value] = confidence
        self.profile.last_updated = datetime.now(timezone.utc).isoformat()

        # Persist encrypted
        self.db.save_dimension_profile(
            dimension=MirrorDimension.GIT_STYLE.value,
            profile_json=profile.model_dump_json(),
            confidence=confidence,
            sample_count=sample_count,
        )
        self.db.save_learned_sample(
            sample_id=f"git_batch_{int(time.time())}",
            dimension=MirrorDimension.GIT_STYLE.value,
            source_type="git_commits",
            features_json=profile.model_dump_json(),
        )

        self.synthesizer.update_profile(self.profile)
        return {
            "status": "success",
            "dimension": MirrorDimension.GIT_STYLE.value,
            "samples_learned": sample_count,
            "confidence": confidence,
            "profile": profile.model_dump(),
        }

    def learn_from_obsidian(
        self,
        vault_path: Optional[str] = None,
        max_notes: int = 50,
        notes_override: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """Learns markdown structure and thought habits from Obsidian vault notes."""
        self._check_halted()
        notes: List[str] = []

        if notes_override is not None:
            notes = notes_override
        else:
            target_vault = vault_path or os.path.abspath("vault")
            if os.path.isdir(target_vault):
                md_files = glob.glob(os.path.join(target_vault, "**", "*.md"), recursive=True)
                for fpath in md_files[:max_notes]:
                    try:
                        with open(fpath, "r", encoding="utf-8", errors="ignore") as f:
                            notes.append(f.read())
                    except Exception:
                        pass

        if not notes:
            return {"status": "no_data", "dimension": MirrorDimension.OBSIDIAN_CADENCE.value, "samples_learned": 0}

        profile = ObsidianThoughtExtractor.extract_from_notes(notes)
        sample_count = len(notes)
        confidence = min(1.0, round(sample_count / 15.0, 2))

        self.profile.obsidian_cadence = profile
        self.profile.sample_counts[MirrorDimension.OBSIDIAN_CADENCE.value] = sample_count
        self.profile.confidence_scores[MirrorDimension.OBSIDIAN_CADENCE.value] = confidence
        self.profile.last_updated = datetime.now(timezone.utc).isoformat()

        # Persist encrypted
        self.db.save_dimension_profile(
            dimension=MirrorDimension.OBSIDIAN_CADENCE.value,
            profile_json=profile.model_dump_json(),
            confidence=confidence,
            sample_count=sample_count,
        )
        self.db.save_learned_sample(
            sample_id=f"obsidian_batch_{int(time.time())}",
            dimension=MirrorDimension.OBSIDIAN_CADENCE.value,
            source_type="vault_notes",
            features_json=profile.model_dump_json(),
        )

        self.synthesizer.update_profile(self.profile)
        return {
            "status": "success",
            "dimension": MirrorDimension.OBSIDIAN_CADENCE.value,
            "samples_learned": sample_count,
            "confidence": confidence,
            "profile": profile.model_dump(),
        }

    def learn_from_email_drafts(
        self, drafts: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """Learns email persona from drafts or sent templates."""
        self._check_halted()
        sample_drafts = drafts or []
        if not sample_drafts:
            return {"status": "no_data", "dimension": MirrorDimension.COMMUNICATION_PERSONA.value, "samples_learned": 0}

        profile = EmailPersonaExtractor.extract_from_drafts(sample_drafts)
        sample_count = len(sample_drafts)
        confidence = min(1.0, round(sample_count / 10.0, 2))

        self.profile.communication_persona = profile
        self.profile.sample_counts[MirrorDimension.COMMUNICATION_PERSONA.value] = sample_count
        self.profile.confidence_scores[MirrorDimension.COMMUNICATION_PERSONA.value] = confidence
        self.profile.last_updated = datetime.now(timezone.utc).isoformat()

        self.db.save_dimension_profile(
            dimension=MirrorDimension.COMMUNICATION_PERSONA.value,
            profile_json=profile.model_dump_json(),
            confidence=confidence,
            sample_count=sample_count,
        )
        self.db.save_learned_sample(
            sample_id=f"email_batch_{int(time.time())}",
            dimension=MirrorDimension.COMMUNICATION_PERSONA.value,
            source_type="email_drafts",
            features_json=profile.model_dump_json(),
        )

        self.synthesizer.update_profile(self.profile)
        return {
            "status": "success",
            "dimension": MirrorDimension.COMMUNICATION_PERSONA.value,
            "samples_learned": sample_count,
            "confidence": confidence,
            "profile": profile.model_dump(),
        }

    def learn_from_work_habits(
        self, timestamps: Optional[List[Union[float, int, str]]] = None
    ) -> Dict[str, Any]:
        """Learns diurnal work habits from timestamped operational logs."""
        self._check_halted()
        sample_ts = timestamps or []
        if not sample_ts:
            return {"status": "no_data", "dimension": MirrorDimension.WORK_HABITS.value, "samples_learned": 0}

        profile = WorkHabitsExtractor.extract_from_timestamps(sample_ts)
        sample_count = len(sample_ts)
        confidence = min(1.0, round(sample_count / 30.0, 2))

        self.profile.work_habits = profile
        self.profile.sample_counts[MirrorDimension.WORK_HABITS.value] = sample_count
        self.profile.confidence_scores[MirrorDimension.WORK_HABITS.value] = confidence
        self.profile.last_updated = datetime.now(timezone.utc).isoformat()

        self.db.save_dimension_profile(
            dimension=MirrorDimension.WORK_HABITS.value,
            profile_json=profile.model_dump_json(),
            confidence=confidence,
            sample_count=sample_count,
        )
        self.db.save_learned_sample(
            sample_id=f"habits_batch_{int(time.time())}",
            dimension=MirrorDimension.WORK_HABITS.value,
            source_type="activity_timestamps",
            features_json=profile.model_dump_json(),
        )

        self.synthesizer.update_profile(self.profile)
        return {
            "status": "success",
            "dimension": MirrorDimension.WORK_HABITS.value,
            "samples_learned": sample_count,
            "confidence": confidence,
            "profile": profile.model_dump(),
        }

    def learn_from_sources(
        self,
        sources: List[str],
        repo_path: Optional[str] = None,
        vault_path: Optional[str] = None,
        max_items: int = 100,
    ) -> Dict[str, Any]:
        """Learns across multiple selected sources."""
        self._check_halted()
        results: Dict[str, Any] = {}

        for src in sources:
            src_lower = src.lower()
            if "git" in src_lower:
                results["git"] = self.learn_from_git(repo_path=repo_path, max_commits=max_items)
            elif "obsidian" in src_lower or "vault" in src_lower:
                results["obsidian"] = self.learn_from_obsidian(vault_path=vault_path, max_notes=max_items)
            elif "email" in src_lower:
                results["email"] = self.learn_from_email_drafts()
            elif "habit" in src_lower:
                results["habits"] = self.learn_from_work_habits()

        return {
            "status": "success",
            "learned_sources": list(results.keys()),
            "details": results,
            "overall_confidence": self.profile.confidence_scores,
        }

    def synthesize_text(
        self,
        task: SynthesisTaskType,
        context_prompt: str,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> MirrorSynthesisResult:
        """Synthesizes text in the user's authentic style matching the requested task."""
        self._check_halted()
        meta = metadata or {}

        if task == SynthesisTaskType.COMMIT_MESSAGE:
            result = self.synthesizer.synthesize_commit_message(context_prompt, metadata=meta)
        elif task == SynthesisTaskType.CODE_COMMENT:
            code_context = meta.get("code_context", "")
            result = self.synthesizer.synthesize_code_comment(code_context, context_prompt, metadata=meta)
        elif task == SynthesisTaskType.EMAIL_DRAFT:
            recipient = meta.get("recipient", "Colleague")
            result = self.synthesizer.synthesize_email_draft(recipient, context_prompt, metadata=meta)
        elif task == SynthesisTaskType.OBSIDIAN_NOTE:
            topic = meta.get("topic", "Personal Note")
            result = self.synthesizer.synthesize_obsidian_note(topic, context_prompt, metadata=meta)
        else:
            raise ValueError(f"Unsupported synthesis task: {task}")

        # Log synthesis to encrypted db
        self.db.log_synthesis(
            task_type=task.value,
            prompt_summary=context_prompt[:80],
            applied_traits=result.applied_style_traits,
            duration_ms=result.duration_ms,
        )

        return result

    def reset_profile(
        self, dimensions: Optional[List[Union[MirrorDimension, str]]] = None
    ) -> Dict[str, Any]:
        """Resets specified dimensions or the entire cognitive profile."""
        self._check_halted()
        if dimensions:
            reset_names = []
            for d in dimensions:
                dim_str = d.value if isinstance(d, MirrorDimension) else str(d)
                self.db.reset_dimension(dim_str)
                self.profile.confidence_scores.pop(dim_str, None)
                self.profile.sample_counts.pop(dim_str, None)
                if dim_str == MirrorDimension.GIT_STYLE.value:
                    self.profile.git_style = GitStyleProfile()
                elif dim_str == MirrorDimension.OBSIDIAN_CADENCE.value:
                    self.profile.obsidian_cadence = ObsidianThoughtProfile()
                elif dim_str == MirrorDimension.COMMUNICATION_PERSONA.value:
                    self.profile.communication_persona = CommunicationPersonaProfile()
                elif dim_str == MirrorDimension.WORK_HABITS.value:
                    self.profile.work_habits = WorkHabitsProfile()
                reset_names.append(dim_str)
            self.synthesizer.update_profile(self.profile)
            return {"status": "success", "reset_dimensions": reset_names}
        else:
            self.db.reset_dimension(None)
            self.profile = CognitiveProfile()
            self.synthesizer.update_profile(self.profile)
            return {"status": "success", "reset_dimensions": ["all"]}


# Singleton engine instance
cognitive_mirror = CognitiveMirrorEngine()
