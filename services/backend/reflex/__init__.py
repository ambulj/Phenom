"""Reflex package for Neural Perception & Active Desktop Reflexes (Milestone 51)."""

from services.backend.reflex.visual_sentinel import VisualReflexSentinel
from services.backend.reflex.notification_sentinel import NotificationReflexSentinel
from services.backend.reflex.jarvis_commentator import JarvisCommentator
from services.backend.reflex.reflex_engine import ReflexEngine, ReflexReaction, SuggestedAction

visual_sentinel = VisualReflexSentinel()
notification_sentinel = NotificationReflexSentinel()
jarvis_commentator = JarvisCommentator()
reflex_engine = ReflexEngine(commentator=jarvis_commentator)

__all__ = [
    "VisualReflexSentinel",
    "NotificationReflexSentinel",
    "JarvisCommentator",
    "ReflexEngine",
    "ReflexReaction",
    "SuggestedAction",
    "visual_sentinel",
    "notification_sentinel",
    "jarvis_commentator",
    "reflex_engine",
]
