"""
Phenom Personalized Synthetic Twin Synthesizer (MIR-01)
Generates authentic text matching the user's learned personal style across:
1. Commit messages (conventional commit ratio, prefixes, imperative mood, casing, length).
2. Code review comments (inquisitive/direct/encouraging tone, architectural principles).
3. Email draft replies (salutations, sign-offs, formality, brevity, bullet formatting).
4. Obsidian notes (headings, bullet markers, callouts, wikilinks).
Operates strictly in-memory and on-device (Rule 4, zero cloud exfiltration).
"""

import time
import re
from typing import Dict, Any, Optional, List

from services.backend.schemas.cognitive_mirror import (
    CognitiveProfile,
    SynthesisTaskType,
    MirrorSynthesisResult,
)
from services.backend.personality.scrubber import scrub_personal_secrets


class SyntheticTwinSynthesizer:
    """Synthesizes text matching the user's learned cognitive style traits."""

    def __init__(self, profile: Optional[CognitiveProfile] = None):
        self.profile = profile or CognitiveProfile()

    def update_profile(self, profile: CognitiveProfile):
        self.profile = profile

    def synthesize_commit_message(
        self, diff_or_summary: str, metadata: Optional[Dict[str, Any]] = None
    ) -> MirrorSynthesisResult:
        start_time = time.perf_counter()
        meta = metadata or {}
        scope = meta.get("scope")
        clean_summary = scrub_personal_secrets(diff_or_summary).strip()

        git_style = self.profile.git_style
        applied_traits: List[str] = []

        # Determine prefix
        prefix = "feat"
        if git_style.primary_prefixes:
            # Pick most common prefix or infer from context
            lower_sum = clean_summary.lower()
            if "fix" in lower_sum or "bug" in lower_sum or "error" in lower_sum:
                prefix = "fix"
            elif "refactor" in lower_sum or "clean" in lower_sum:
                prefix = "refactor"
            elif "doc" in lower_sum or "comment" in lower_sum:
                prefix = "docs"
            elif "test" in lower_sum:
                prefix = "test"
            else:
                prefix = max(git_style.primary_prefixes.items(), key=lambda x: x[1])[0]
        applied_traits.append(f"prefix:{prefix}")

        # Format subject with imperative mood
        words = clean_summary.split()
        first_word = words[0] if words else "update"
        rest = " ".join(words[1:]) if len(words) > 1 else ""

        # Normalize to imperative if needed
        imperative_map = {
            "added": "add", "adding": "add", "adds": "add",
            "fixed": "fix", "fixing": "fix", "fixes": "fix",
            "updated": "update", "updating": "update", "updates": "update",
            "refactored": "refactor", "refactoring": "refactor",
            "implemented": "implement", "implementing": "implement",
            "removed": "remove", "removing": "remove",
            "handled": "handle", "handling": "handle",
        }
        clean_first = imperative_map.get(first_word.lower(), first_word)
        applied_traits.append("imperative_mood")

        # Casing preference
        if git_style.lowercase_subject_ratio > 0.5:
            clean_first = clean_first.lower()
            applied_traits.append("lowercase_casing")
        else:
            clean_first = clean_first.capitalize()
            applied_traits.append("capitalized_casing")

        subject = f"{clean_first} {rest}".strip() if rest else clean_first

        # Conventional commits format
        if git_style.conventional_commits_ratio >= 0.5:
            applied_traits.append("conventional_commits")
            if scope:
                text = f"{prefix}({scope}): {subject}"
            else:
                text = f"{prefix}: {subject}"
        else:
            applied_traits.append("freeform_commit")
            text = subject

        duration_ms = round((time.perf_counter() - start_time) * 1000.0, 3)
        confidence = self.profile.confidence_scores.get("git_style", 0.5)

        return MirrorSynthesisResult(
            task=SynthesisTaskType.COMMIT_MESSAGE,
            synthesized_text=text,
            applied_style_traits=applied_traits,
            confidence=confidence,
            duration_ms=duration_ms,
        )

    def synthesize_code_comment(
        self, code_context: str, issue_description: str, metadata: Optional[Dict[str, Any]] = None
    ) -> MirrorSynthesisResult:
        start_time = time.perf_counter()
        git_style = self.profile.git_style
        tone = git_style.review_tone
        clean_issue = scrub_personal_secrets(issue_description).strip()
        applied_traits: List[str] = [f"tone:{tone}"]

        arch_note = ""
        if git_style.architectural_preferences:
            top_arch = git_style.architectural_preferences[0]
            arch_note = f" to preserve {top_arch}"
            applied_traits.append(f"arch_principle:{top_arch}")

        if tone == "inquisitive":
            text = f"Could we consider updating this{arch_note}? {clean_issue}"
        elif tone == "encouraging":
            text = f"Looks great! One small suggestion{arch_note}: {clean_issue}"
        else:  # direct
            text = f"Change needed{arch_note}: {clean_issue}"

        duration_ms = round((time.perf_counter() - start_time) * 1000.0, 3)
        confidence = self.profile.confidence_scores.get("git_style", 0.5)

        return MirrorSynthesisResult(
            task=SynthesisTaskType.CODE_COMMENT,
            synthesized_text=text,
            applied_style_traits=applied_traits,
            confidence=confidence,
            duration_ms=duration_ms,
        )

    def synthesize_email_draft(
        self, recipient: str, context: str, metadata: Optional[Dict[str, Any]] = None
    ) -> MirrorSynthesisResult:
        start_time = time.perf_counter()
        meta = metadata or {}
        persona = self.profile.communication_persona
        clean_context = scrub_personal_secrets(context).strip()
        applied_traits: List[str] = []

        # Salutation
        salutation = persona.preferred_salutations[0] if persona.preferred_salutations else "Hi"
        applied_traits.append(f"salutation:{salutation}")

        # Sign-off
        signoff = persona.preferred_signoffs[0] if persona.preferred_signoffs else "Best,"
        if not signoff.endswith(","):
            signoff = f"{signoff},"
        applied_traits.append(f"signoff:{signoff}")

        # Characteristic phrase
        phrase = persona.characteristic_phrases[0] if persona.characteristic_phrases else ""
        if phrase:
            applied_traits.append(f"phrase:{phrase}")

        lines = [f"{salutation} {recipient.strip()},", ""]

        # Brevity / bullets
        if persona.bullet_point_preference > 0.3 or persona.brevity_score > 0.6:
            applied_traits.append("bullet_structure")
            if phrase:
                lines.append(f"{phrase.capitalize()}:")
            lines.append(f"- {clean_context}")
        else:
            applied_traits.append("prose_structure")
            if phrase:
                lines.append(f"{phrase.capitalize()}, {clean_context}")
            else:
                lines.append(clean_context)

        lines.extend(["", signoff, "Phenom"])
        text = "\n".join(lines)

        duration_ms = round((time.perf_counter() - start_time) * 1000.0, 3)
        confidence = self.profile.confidence_scores.get("communication_persona", 0.5)

        return MirrorSynthesisResult(
            task=SynthesisTaskType.EMAIL_DRAFT,
            synthesized_text=text,
            applied_style_traits=applied_traits,
            confidence=confidence,
            duration_ms=duration_ms,
        )

    def synthesize_obsidian_note(
        self, topic: str, content: str, metadata: Optional[Dict[str, Any]] = None
    ) -> MirrorSynthesisResult:
        start_time = time.perf_counter()
        obs = self.profile.obsidian_cadence
        clean_topic = scrub_personal_secrets(topic).strip()
        clean_content = scrub_personal_secrets(content).strip()
        applied_traits: List[str] = []

        # Heading depth
        depth = int(round(obs.avg_heading_depth)) if obs.avg_heading_depth >= 1.0 else 2
        hashes = "#" * depth
        applied_traits.append(f"heading_depth:{depth}")

        bullet = obs.preferred_bullet_marker or "-"
        applied_traits.append(f"bullet_marker:{bullet}")

        lines = [f"{hashes} {clean_topic}", ""]

        # Callout
        callout_type = obs.preferred_callouts[0] if obs.preferred_callouts else "NOTE"
        applied_traits.append(f"callout:{callout_type}")
        lines.append(f"> [!{callout_type}]")
        lines.append(f"> Key takeaway for [[{clean_topic}]]")
        lines.append("")

        # Content bullets
        for line in clean_content.splitlines():
            if line.strip():
                lines.append(f"{bullet} {line.strip()}")

        text = "\n".join(lines)
        duration_ms = round((time.perf_counter() - start_time) * 1000.0, 3)
        confidence = self.profile.confidence_scores.get("obsidian_cadence", 0.5)

        return MirrorSynthesisResult(
            task=SynthesisTaskType.OBSIDIAN_NOTE,
            synthesized_text=text,
            applied_style_traits=applied_traits,
            confidence=confidence,
            duration_ms=duration_ms,
        )
