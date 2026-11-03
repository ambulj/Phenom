"""
Sensory Fabric & P2P Media Drop Safety Tools (SAF-01)
Registers Tier 0 and Tier 1 tools in the Safety ToolRegistry for:
- Companion camera in-RAM frame inspection & local VLM/OCR analysis (Tier 0)
- AirDrop-style encrypted P2P file & document drops (Tier 1)
- P2P media drop transfer history queries (Tier 0)
"""

from typing import Dict, Any
from services.backend.safety.registry import registry
from services.backend.schemas.sensory import (
    CameraGetFrameArgs,
    CameraAnalyzeArgs,
    MediaDropSendFileArgs,
    MediaDropGetHistoryArgs,
    MediaDropDestination,
)
from services.backend.sensors.companion_camera import companion_camera_streamer
from services.backend.mesh.media_drop import media_drop_manager


# ==========================================
# Tier 0 Tools (Read-Only)
# ==========================================

@registry.register(
    name="camera_get_companion_frame",
    tier=0,
    description="Inspects the latest in-RAM camera frame and telemetry from a paired companion device (Read-Only)",
    args_schema=CameraGetFrameArgs,
    preview_fn=lambda a: (
        f"Inspect latest in-RAM companion camera frame "
        f"(node_id={a.get('node_id') if isinstance(a, dict) else getattr(a, 'node_id', None)}) "
        f"(Read-Only)"
    ),
)
async def camera_get_companion_frame(args: CameraGetFrameArgs) -> Dict[str, Any]:
    frame = companion_camera_streamer.get_latest_frame(node_id=args.node_id)
    if not frame:
        return {
            "status": "no_frame",
            "message": "No companion camera frames available in memory buffer",
        }

    return {
        "status": "success",
        "frame_id": frame["frame_id"],
        "node_id": frame["node_id"],
        "timestamp": frame["timestamp"],
        "width": frame["width"],
        "height": frame["height"],
        "resolution": f"{frame['width']}x{frame['height']}",
        "battery_level": frame.get("battery_level"),
        "is_charging": frame.get("is_charging", False),
        "wifi_rssi": frame.get("wifi_rssi"),
        "thumbnail_base64": frame.get("thumbnail_base64"),
    }


@registry.register(
    name="camera_analyze_object_or_ocr",
    tier=0,
    description="Analyzes in-RAM companion camera frame using local VLM or OCR engine (Read-Only)",
    args_schema=CameraAnalyzeArgs,
    preview_fn=lambda a: (
        f"Analyze companion camera frame via local "
        f"{a.get('task_type', 'object') if isinstance(a, dict) else getattr(a, 'task_type', 'object')} engine "
        f"(Read-Only)"
    ),
)
async def camera_analyze_object_or_ocr(args: CameraAnalyzeArgs) -> Dict[str, Any]:
    result = await companion_camera_streamer.analyze_frame(
        task_type=args.task_type,
        prompt=args.prompt,
    )
    return {
        "status": "success",
        "result": result.model_dump(),
    }


@registry.register(
    name="media_drop_get_history",
    tier=0,
    description="Queries the history of recent P2P media and document drops (Read-Only)",
    args_schema=MediaDropGetHistoryArgs,
    preview_fn=lambda a: "Query P2P media drop transfer history (Read-Only)",
)
async def media_drop_get_history(args: MediaDropGetHistoryArgs) -> Dict[str, Any]:
    history = media_drop_manager.get_history(limit=args.limit)
    return {
        "status": "success",
        "count": len(history),
        "transfers": [t.model_dump() for t in history],
    }


# ==========================================
# Tier 1 Tools (Reversible Changes with Preview)
# ==========================================

@registry.register(
    name="media_drop_send_file",
    tier=1,
    description="Initiates an AirDrop-style encrypted P2P media drop to a paired companion device (Reversible change with preview)",
    args_schema=MediaDropSendFileArgs,
    preview_fn=lambda a: (
        f"Send file '{a.get('file_path') if isinstance(a, dict) else getattr(a, 'file_path', '')}' "
        f"to companion '{a.get('target_node_id') if isinstance(a, dict) else getattr(a, 'target_node_id', '')}' "
        f"(destination: {a.get('destination') if isinstance(a, dict) else getattr(a, 'destination', 'downloads')})"
    ),
)
async def media_drop_send_file(args: MediaDropSendFileArgs) -> Dict[str, Any]:
    manifest, transfer = media_drop_manager.create_send_manifest(
        file_path=args.file_path,
        source_node_id="host-desktop",
        target_node_id=args.target_node_id,
        destination=MediaDropDestination(args.destination),
    )
    return {
        "status": "initiated",
        "transfer": transfer.model_dump(),
        "manifest": manifest.model_dump(),
    }
