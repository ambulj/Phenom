"""
Telepresence Package Exports.
"""

from services.backend.telepresence.av_pipeline import StreamingAVPipeline
from services.backend.telepresence.perception_manager import AmbientPerceptionManager

# Global singleton instance
streaming_av_pipeline = StreamingAVPipeline()

__all__ = [
    "StreamingAVPipeline",
    "AmbientPerceptionManager",
    "streaming_av_pipeline",
]
