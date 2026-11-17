"""Reflex package for Neural Perception & Active Desktop Reflexes (Milestone 51)."""

from services.backend.reflex.visual_sentinel import VisualReflexSentinel
from services.backend.reflex.notification_sentinel import NotificationReflexSentinel

visual_sentinel = VisualReflexSentinel()
notification_sentinel = NotificationReflexSentinel()

__all__ = ["VisualReflexSentinel", "NotificationReflexSentinel", "visual_sentinel", "notification_sentinel"]
