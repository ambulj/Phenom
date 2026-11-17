"""Reflex package for Neural Perception & Active Desktop Reflexes (Milestone 51)."""

from services.backend.reflex.visual_sentinel import VisualReflexSentinel
from services.backend.reflex.notification_sentinel import NotificationReflexSentinel
from services.backend.reflex.jarvis_commentator import JarvisCommentator
from services.backend.reflex.reflex_engine import ReflexEngine, ReflexReaction, SuggestedAction
from services.backend.reflex.clipboard_classifier import ClipboardClassifier, ClipboardContentType, ClassifiedClipboardPayload
from services.backend.reflex.clipboard_sentinel import ClipboardSentinel, ClipboardItem
from services.backend.safety.clipboard_privacy_filter import ClipboardPrivacyFilter, SanitizedClipboardResult

visual_sentinel = VisualReflexSentinel()
notification_sentinel = NotificationReflexSentinel()
jarvis_commentator = JarvisCommentator()
reflex_engine = ReflexEngine(commentator=jarvis_commentator)
clipboard_sentinel = ClipboardSentinel()

__all__ = [
    "VisualReflexSentinel",
    "NotificationReflexSentinel",
    "JarvisCommentator",
    "ReflexEngine",
    "ReflexReaction",
    "SuggestedAction",
    "ClipboardClassifier",
    "ClipboardContentType",
    "ClassifiedClipboardPayload",
    "ClipboardSentinel",
    "ClipboardItem",
    "ClipboardPrivacyFilter",
    "SanitizedClipboardResult",
    "visual_sentinel",
    "notification_sentinel",
    "jarvis_commentator",
    "reflex_engine",
    "clipboard_sentinel",
]
