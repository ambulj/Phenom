"""
Phenom Multi-Dimensional Cognitive Feature Extractors (MIR-01)
Pipelines for extracting personal style traits across:
1. GitStyleExtractor: Commits & Code Review tone/architecture.
2. ObsidianThoughtExtractor: Markdown structure, wikilinks, tags, callouts, and daily notes.
3. EmailPersonaExtractor: Salutations, sign-offs, formality, brevity, and bullet usage.
4. WorkHabitsExtractor: Diurnal activity distribution, peak focus, break cadence, quiet windows.
All inputs are sanitized in-memory using the credential scrubber prior to extraction (Rule 11).
"""

import re
from datetime import datetime, timezone
from collections import Counter
from typing import List, Dict, Tuple, Any, Optional, Union
import statistics

from services.backend.schemas.cognitive_mirror import (
    GitStyleProfile,
    ObsidianThoughtProfile,
    CommunicationPersonaProfile,
    WorkHabitsProfile,
)
from services.backend.personality.scrubber import scrub_personal_secrets


# Common imperative base verbs in software engineering
IMPERATIVE_VERBS = {
    "add", "fix", "update", "refactor", "remove", "implement", "create", "delete",
    "handle", "ensure", "prevent", "support", "wire", "enforce", "clean", "optimize",
    "standardize", "bump", "allow", "integrate", "setup", "set", "use", "upgrade",
    "migrate", "document", "improve", "extract", "simplify", "align", "enable", "disable",
    "resolve", "revert", "format", "test", "release", "patch", "sanitize", "secure"
}

CONVENTIONAL_COMMIT_REGEX = re.compile(
    r"^(?P<prefix>feat|fix|docs|style|refactor|perf|test|build|ci|chore|revert)(?:\((?P<scope>[^)]+)\))?(?P<breaking>!)?:\s*(?P<subject>.+)$",
    re.IGNORECASE
)

COMMON_ARCHITECTURAL_KEYWORDS = [
    "type safety", "modularity", "immutability", "fail-fast", "single source of truth",
    "separation of concerns", "defensive programming", "idempotent", "dependency injection",
    "thread safe", "caching", "decoupling", "resilience", "zero-copy", "atomic"
]


class GitStyleExtractor:
    """Extracts git commit conventions, casing, length, and code review tone."""

    @staticmethod
    def extract_from_commits(commits: List[Union[str, Dict[str, Any]]]) -> GitStyleProfile:
        if not commits:
            return GitStyleProfile()

        raw_messages: List[str] = []
        for c in commits:
            if isinstance(c, str):
                raw_messages.append(scrub_personal_secrets(c))
            elif isinstance(c, dict):
                msg = c.get("message") or c.get("subject") or c.get("summary") or ""
                raw_messages.append(scrub_personal_secrets(str(msg)))

        raw_messages = [m.strip() for m in raw_messages if m.strip()]
        if not raw_messages:
            return GitStyleProfile()

        conventional_count = 0
        prefix_counter: Counter = Counter()
        subject_lengths: List[int] = []
        imperative_count = 0
        lowercase_count = 0

        for msg in raw_messages:
            first_line = msg.splitlines()[0].strip()
            match = CONVENTIONAL_COMMIT_REGEX.match(first_line)
            if match:
                conventional_count += 1
                prefix = match.group("prefix").lower()
                prefix_counter[prefix] += 1
                subject = match.group("subject").strip()
            else:
                subject = first_line

            if subject:
                subject_lengths.append(len(subject))
                if subject[0].islower():
                    lowercase_count += 1

                first_word = re.split(r"\s+", subject)[0].lower()
                if first_word in IMPERATIVE_VERBS:
                    imperative_count += 1

        total = len(raw_messages)
        conv_ratio = round(conventional_count / total, 3)
        prefix_distribution = {
            k: round(v / conventional_count, 3)
            for k, v in prefix_counter.items()
        } if conventional_count > 0 else {}

        avg_len = int(round(sum(subject_lengths) / len(subject_lengths))) if subject_lengths else 50
        imperative_ratio = round(imperative_count / total, 3)
        lowercase_ratio = round(lowercase_count / total, 3)

        return GitStyleProfile(
            conventional_commits_ratio=conv_ratio,
            primary_prefixes=prefix_distribution,
            avg_subject_length=avg_len,
            imperative_mood_ratio=imperative_ratio,
            lowercase_subject_ratio=lowercase_ratio,
            review_tone="direct",
            architectural_preferences=[],
        )

    @staticmethod
    def extract_from_reviews(reviews: List[str]) -> Tuple[str, List[str]]:
        """
        Analyzes code review comments for tone and architectural preferences.
        Returns (tone, architectural_keywords).
        """
        if not reviews:
            return "direct", []

        sanitized_reviews = [scrub_personal_secrets(r) for r in reviews if r.strip()]
        if not sanitized_reviews:
            return "direct", []

        question_markers = 0
        encouraging_markers = 0
        direct_markers = 0

        encouraging_terms = ["great", "nice", "looks good", "lgth", "clean", "love this", "well done", "awesome"]
        inquisitive_terms = ["could we", "what if", "should this", "can we", "would it be", "why not", "how about"]

        detected_arch = set()

        for rev in sanitized_reviews:
            lower_rev = rev.lower()
            if "?" in rev or any(q in lower_rev for q in inquisitive_terms):
                question_markers += 1
            if any(term in lower_rev for term in encouraging_terms):
                encouraging_markers += 1
            if any(term in lower_rev for term in ["must", "change this", "needs to", "drop", "please avoid", "refactor"]):
                direct_markers += 1

            for arch in COMMON_ARCHITECTURAL_KEYWORDS:
                if arch in lower_rev:
                    detected_arch.add(arch)

        total_reviews = len(sanitized_reviews)
        if question_markers >= encouraging_markers and question_markers > direct_markers:
            tone = "inquisitive"
        elif encouraging_markers > question_markers and encouraging_markers >= direct_markers:
            tone = "encouraging"
        else:
            tone = "direct"

        return tone, sorted(list(detected_arch))


class ObsidianThoughtExtractor:
    """Extracts note structure, wikilinks, tags, callout preferences, and daily sections."""

    RE_HEADING = re.compile(r"^(#{1,6})\s+(.+)$", re.MULTILINE)
    RE_WIKILINK = re.compile(r"\[\[([^\]|#]+)(?:#[^\]|]+)?(?:\|[^\]]+)?\]\]")
    RE_TAG = re.compile(r"(?<!\S)#([A-Za-z0-9_\-\/]+)(?!\S)")
    RE_CALLOUT = re.compile(r"^>\s*\[!([A-Za-z_-]+)\]", re.MULTILINE)
    RE_BULLET_DASH = re.compile(r"^\s*-\s+", re.MULTILINE)
    RE_BULLET_ASTERISK = re.compile(r"^\s*\*\s+", re.MULTILINE)

    @classmethod
    def extract_from_notes(cls, notes: List[str]) -> ObsidianThoughtProfile:
        if not notes:
            return ObsidianThoughtProfile()

        sanitized_notes = [scrub_personal_secrets(n) for n in notes if n.strip()]
        if not sanitized_notes:
            return ObsidianThoughtProfile()

        heading_depths: List[int] = []
        dash_bullets = 0
        asterisk_bullets = 0
        total_words = 0
        total_wikilinks = 0
        total_tags = 0
        total_callouts = 0
        callout_counter: Counter = Counter()
        section_counter: Counter = Counter()

        for note in sanitized_notes:
            # Word count
            words = len(re.findall(r"\w+", note))
            total_words += max(words, 1)

            # Headings
            headings = cls.RE_HEADING.findall(note)
            for hashes, title in headings:
                depth = len(hashes)
                heading_depths.append(depth)
                if depth == 2:
                    clean_title = title.strip()
                    section_counter[clean_title] += 1

            # Bullets
            dash_bullets += len(cls.RE_BULLET_DASH.findall(note))
            asterisk_bullets += len(cls.RE_BULLET_ASTERISK.findall(note))

            # Wikilinks
            links = cls.RE_WIKILINK.findall(note)
            total_wikilinks += len(links)

            # Tags (filter out markdown headings captured by #)
            tags = cls.RE_TAG.findall(note)
            # Remove digits-only or headings
            clean_tags = [t for t in tags if not t.isdigit() and not t.startswith("#")]
            total_tags += len(clean_tags)

            # Callouts
            callouts = cls.RE_CALLOUT.findall(note)
            total_callouts += len(callouts)
            for c in callouts:
                callout_counter[c.upper()] += 1

        avg_depth = round(sum(heading_depths) / len(heading_depths), 2) if heading_depths else 2.0
        preferred_bullet = "-" if dash_bullets >= asterisk_bullets else "*"

        words_500_blocks = max(total_words / 500.0, 1.0)
        wikilink_density = round(total_wikilinks / words_500_blocks, 2)
        tag_density = round(total_tags / words_500_blocks, 2)
        callout_freq = round(total_callouts / words_500_blocks, 2)

        preferred_callouts = [name for name, _ in callout_counter.most_common(3)]
        top_sections = [name for name, count in section_counter.most_common(5) if count >= 1]

        return ObsidianThoughtProfile(
            avg_heading_depth=avg_depth,
            preferred_bullet_marker=preferred_bullet,
            wikilink_density_per_500_words=wikilink_density,
            tag_density_per_500_words=tag_density,
            callout_frequency=callout_freq,
            preferred_callouts=preferred_callouts,
            daily_note_sections=top_sections,
        )


class EmailPersonaExtractor:
    """Extracts email salutations, signoffs, formality, brevity, and formatting preferences."""

    RE_SALUTATION = re.compile(
        r"^(Hi\s+[A-Za-z]+|Hey\s+[A-Za-z]+|Hello\s+[A-Za-z]+|Dear\s+[A-Za-z]+|Good\s+(?:morning|afternoon|evening)|Hi|Hey|Hello|Dear)[,\s]",
        re.MULTILINE | re.IGNORECASE
    )
    RE_SIGNOFF = re.compile(
        r"(?i)\n\s*(Best regards|Warm regards|Kind regards|Best|Thanks|Cheers|Warmly|Regards|Sincerely|Thank you),?\s*$",
        re.MULTILINE
    )

    FORMAL_MARKERS = [
        "dear", "sincerely", "regards", "respectfully", "furthermore", "please find attached",
        "would you kindly", "in regards to", "per our conversation", "do not", "cannot", "will not"
    ]
    INFORMAL_MARKERS = [
        "hey", "cheers", "yep", "nope", "gonna", "wanna", "cool", "super", "!", ":)", ";)", "awesome",
        "don't", "can't", "won't", "let's"
    ]

    CHARACTERISTIC_PHRASES = [
        "let's make sure", "sounds good", "heads up", "looping in", "quick question",
        "touch base", "circle back", "at your earliest convenience", "per my previous note",
        "looking forward", "let me know if", "thanks in advance", "follow up"
    ]

    @classmethod
    def extract_from_drafts(cls, drafts: List[str]) -> CommunicationPersonaProfile:
        if not drafts:
            return CommunicationPersonaProfile()

        sanitized_drafts = [scrub_personal_secrets(d) for d in drafts if d.strip()]
        if not sanitized_drafts:
            return CommunicationPersonaProfile()

        salutation_counter: Counter = Counter()
        signoff_counter: Counter = Counter()
        phrase_counter: Counter = Counter()

        total_words_list: List[int] = []
        total_lines = 0
        bullet_lines = 0

        formality_scores: List[float] = []

        for draft in sanitized_drafts:
            lower_draft = draft.lower()

            # Salutations
            sal_match = cls.RE_SALUTATION.search(draft)
            if sal_match:
                # Normalize salutation prefix (e.g. "Hi", "Hey", "Hello", "Dear")
                raw_sal = sal_match.group(1).strip()
                normalized_sal = raw_sal.split()[0].capitalize()
                salutation_counter[normalized_sal] += 1

            # Signoffs
            sign_match = cls.RE_SIGNOFF.search(draft)
            if sign_match:
                raw_sign = sign_match.group(1).strip()
                signoff_counter[raw_sign.capitalize()] += 1

            # Word count and lines
            words = len(re.findall(r"\w+", draft))
            total_words_list.append(words)

            lines = [l.strip() for l in draft.splitlines() if l.strip()]
            for line in lines:
                total_lines += 1
                if line.startswith(("-", "*", "•")) or re.match(r"^\d+\.\s+", line):
                    bullet_lines += 1

            # Formality scoring
            formal_count = sum(1 for m in cls.FORMAL_MARKERS if m in lower_draft)
            informal_count = sum(1 for m in cls.INFORMAL_MARKERS if m in lower_draft)
            total_markers = formal_count + informal_count
            if total_markers > 0:
                draft_formality = formal_count / total_markers
            else:
                draft_formality = 0.5
            formality_scores.append(draft_formality)

            # Characteristic phrases
            for phrase in cls.CHARACTERISTIC_PHRASES:
                if phrase in lower_draft:
                    phrase_counter[phrase] += 1

        top_salutations = [s for s, _ in salutation_counter.most_common(3)]
        top_signoffs = [s for s, _ in signoff_counter.most_common(3)]

        avg_formality = round(statistics.mean(formality_scores), 2) if formality_scores else 0.5
        avg_words = statistics.mean(total_words_list) if total_words_list else 100

        # Brevity: <= 30 words is 1.0, >= 200 words is 0.0
        brevity = max(0.0, min(1.0, 1.0 - (avg_words - 30) / 170.0))
        brevity = round(brevity, 2)

        bullet_pref = round(bullet_lines / total_lines, 2) if total_lines > 0 else 0.0
        characteristic_phrases = [p for p, _ in phrase_counter.most_common(4)]

        return CommunicationPersonaProfile(
            preferred_salutations=top_salutations or ["Hi"],
            preferred_signoffs=top_signoffs or ["Best,"],
            formality_score=avg_formality,
            brevity_score=brevity,
            bullet_point_preference=bullet_pref,
            characteristic_phrases=characteristic_phrases,
        )


class WorkHabitsExtractor:
    """Extracts 24-hour diurnal activity distributions, peak focus blocks, and break cadences."""

    @staticmethod
    def extract_from_timestamps(timestamps: List[Union[float, int, str]]) -> WorkHabitsProfile:
        if not timestamps:
            return WorkHabitsProfile()

        epoch_seconds: List[float] = []
        for ts in timestamps:
            if isinstance(ts, (int, float)):
                epoch_seconds.append(float(ts))
            elif isinstance(ts, str):
                try:
                    dt = datetime.fromisoformat(ts.replace("Z", "+00:00"))
                    epoch_seconds.append(dt.timestamp())
                except Exception:
                    try:
                        epoch_seconds.append(float(ts))
                    except Exception:
                        pass

        if not epoch_seconds:
            return WorkHabitsProfile()

        epoch_seconds.sort()

        hour_counter: Counter = Counter()
        for s in epoch_seconds:
            dt = datetime.fromtimestamp(s)
            hour_counter[dt.hour] += 1

        total_events = len(epoch_seconds)
        distribution = {h: round(hour_counter[h] / total_events, 4) for h in range(24)}

        # Peak hours: top 4 hours
        peak_hours = [h for h, _ in hour_counter.most_common(4)]

        # Quiet windows: longest run of consecutive hours with activity below 2%
        quiet_hours = [h for h in range(24) if distribution[h] < 0.02]
        quiet_windows: List[Tuple[int, int]] = []
        if quiet_hours:
            # Detect contiguous blocks (handling wrap-around if needed or simple ranges)
            start = quiet_hours[0]
            prev = quiet_hours[0]
            for h in quiet_hours[1:]:
                if h == prev + 1:
                    prev = h
                else:
                    quiet_windows.append((start, prev))
                    start = h
                    prev = h
            quiet_windows.append((start, prev))

        # Break cadence: median gap between consecutive timestamps within 10 mins to 4 hours
        gaps_minutes: List[float] = []
        for i in range(1, len(epoch_seconds)):
            diff_min = (epoch_seconds[i] - epoch_seconds[i - 1]) / 60.0
            if 10.0 <= diff_min <= 240.0:
                gaps_minutes.append(diff_min)

        break_cadence = int(round(statistics.median(gaps_minutes))) if gaps_minutes else 60

        return WorkHabitsProfile(
            peak_hours=sorted(peak_hours),
            break_cadence_minutes=break_cadence,
            quiet_time_windows=quiet_windows,
            hourly_distribution=distribution,
        )
