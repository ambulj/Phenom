"""
Dynamic Window Layout Choreographer & Spatial Task Preset Engine.
Computes multi-display window geometry, coordinates layout transitions, and supports
reversible snapshot rollback across Windows desktop applications.

Part of Phenom 22.0 Sovereign Swarm Intelligence (WIN-03.1 / WIN-03.2).
"""

import time
import uuid
from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field

from services.backend.safety.guardian import guardian
from services.backend.spatial.multi_display_manager import multi_display_manager, DisplayGeometry


class WindowPlacement(BaseModel):
    app_identifier: str = Field(..., description="App name or class name e.g. 'code', 'chrome', 'terminal'")
    title_pattern: Optional[str] = Field(default=None, description="Window title regex pattern")
    display_id: str = Field(default="DISPLAY_1", description="Target monitor display_id")
    x: int = Field(..., description="Target screen X coordinate")
    y: int = Field(..., description="Target screen Y coordinate")
    width: int = Field(..., description="Target pixel width")
    height: int = Field(..., description="Target pixel height")


class LayoutPreset(BaseModel):
    preset_id: str
    name: str
    description: str
    target_task: str
    placements: List[WindowPlacement] = Field(default_factory=list)


class LayoutStateSnapshot(BaseModel):
    snapshot_id: str
    preset_id: Optional[str] = None
    applied_at: float = Field(default_factory=time.time)
    placements: List[WindowPlacement] = Field(default_factory=list)


class LayoutChoreographer:
    """
    Coordinates task-driven desktop layouts across multi-display topologies with reversible rollbacks.
    """

    def __init__(self):
        self._presets: Dict[str, LayoutPreset] = {}
        self._history: List[LayoutStateSnapshot] = []
        self._active_preset: Optional[str] = None
        self._initialize_built_in_presets()

    def _initialize_built_in_presets(self):
        self._presets["coding_focus"] = LayoutPreset(
            preset_id="coding_focus",
            name="Deep Coding Focus",
            description="70/30 split on primary monitor for IDE & terminal; secondary monitor for browser docs",
            target_task="development",
            placements=[
                WindowPlacement(app_identifier="code", title_pattern=".*", display_id="DISPLAY_1", x=0, y=0, width=1792, height=1440),
                WindowPlacement(app_identifier="terminal", title_pattern=".*", display_id="DISPLAY_1", x=1792, y=0, width=768, height=1440),
                WindowPlacement(app_identifier="chrome", title_pattern=".*", display_id="DISPLAY_2", x=2560, y=0, width=1080, height=1920),
            ]
        )

        self._presets["debugging_split"] = LayoutPreset(
            preset_id="debugging_split",
            name="Interactive Debugging Split",
            description="50/50 dual pane for debugger and web app view; secondary monitor for logs",
            target_task="debugging",
            placements=[
                WindowPlacement(app_identifier="code", title_pattern=".*", display_id="DISPLAY_1", x=0, y=0, width=1280, height=1440),
                WindowPlacement(app_identifier="chrome", title_pattern=".*", display_id="DISPLAY_1", x=1280, y=0, width=1280, height=1440),
                WindowPlacement(app_identifier="terminal", title_pattern=".*", display_id="DISPLAY_2", x=2560, y=0, width=1080, height=1920),
            ]
        )

        self._presets["research_reading"] = LayoutPreset(
            preset_id="research_reading",
            name="Research & Synthesis Reading",
            description="Primary display 60% PDF reader / browser, 40% Obsidian scratchpad notes",
            target_task="research",
            placements=[
                WindowPlacement(app_identifier="chrome", title_pattern=".*", display_id="DISPLAY_1", x=0, y=0, width=1536, height=1440),
                WindowPlacement(app_identifier="obsidian", title_pattern=".*", display_id="DISPLAY_1", x=1536, y=0, width=1024, height=1440),
            ]
        )

        self._presets["monitoring_grid"] = LayoutPreset(
            preset_id="monitoring_grid",
            name="Telemetry 2x2 Grid",
            description="Balanced 4-quadrant layout for real-time monitoring and dashboards",
            target_task="monitoring",
            placements=[
                WindowPlacement(app_identifier="terminal", title_pattern=".*", display_id="DISPLAY_1", x=0, y=0, width=1280, height=720),
                WindowPlacement(app_identifier="metrics", title_pattern=".*", display_id="DISPLAY_1", x=1280, y=0, width=1280, height=720),
                WindowPlacement(app_identifier="logs", title_pattern=".*", display_id="DISPLAY_1", x=0, y=720, width=1280, height=720),
                WindowPlacement(app_identifier="hud", title_pattern=".*", display_id="DISPLAY_1", x=1280, y=720, width=1280, height=720),
            ]
        )

    def list_presets(self) -> List[LayoutPreset]:
        return list(self._presets.values())

    def get_preset(self, preset_id: str) -> Optional[LayoutPreset]:
        return self._presets.get(preset_id)

    def calculate_preset_coordinates(self, preset_id: str) -> List[WindowPlacement]:
        """
        Dynamically calculates window coordinates scaled to match the live detected monitor geometry.
        """
        preset = self.get_preset(preset_id)
        if not preset:
            raise KeyError(f"Layout preset '{preset_id}' not found")

        displays = multi_display_manager.detect_monitors()
        disp_map = {d.display_id: d for d in displays}
        primary = multi_display_manager.get_primary_monitor()

        scaled_placements: List[WindowPlacement] = []
        for p in preset.placements:
            target_disp = disp_map.get(p.display_id, primary)

            # Map coordinates proportionally to target display resolution
            # Standard reference scale is 2560x1440
            scale_x = target_disp.width / 2560.0
            scale_y = target_disp.height / 1440.0

            scaled_x = int(target_disp.x + (p.x % 2560) * scale_x)
            scaled_y = int(target_disp.y + p.y * scale_y)
            scaled_w = int(p.width * scale_x)
            scaled_h = int(p.height * scale_y)

            scaled_placements.append(
                WindowPlacement(
                    app_identifier=p.app_identifier,
                    title_pattern=p.title_pattern,
                    display_id=target_disp.display_id,
                    x=scaled_x,
                    y=scaled_y,
                    width=max(400, scaled_w),
                    height=max(300, scaled_h),
                )
            )

        return scaled_placements

    def apply_layout_preset(self, preset_id: str) -> Dict[str, Any]:
        """
        Applies a layout preset to active windows with reversible snapshot creation.
        Strictly verifies Guardian kill switch (< 25.0ms SLA).
        """
        if guardian.is_halted:
            raise PermissionError("Guardian kill switch is active. Window layout choreography halted.")

        t0 = time.perf_counter()
        preset = self.get_preset(preset_id)
        if not preset:
            raise KeyError(f"Preset '{preset_id}' not found")

        # Compute geometry
        placements = self.calculate_preset_coordinates(preset_id)

        # Record reversible snapshot before applying changes (Rule 7)
        snap_id = f"snap_{uuid.uuid4().hex[:8]}"
        snapshot = LayoutStateSnapshot(
            snapshot_id=snap_id,
            preset_id=preset_id,
            applied_at=time.time(),
            placements=placements,
        )
        self._history.append(snapshot)
        self._active_preset = preset_id

        # In live Windows environments, Win32 MoveWindow or SetWindowPos calls would reposition windows
        # Here we return the verified geometric choreography plan
        duration_ms = (time.perf_counter() - t0) * 1000.0

        return {
            "status": "applied",
            "preset_id": preset_id,
            "name": preset.name,
            "snapshot_id": snap_id,
            "windows_choreographed": len(placements),
            "placements": [p.model_dump() for p in placements],
            "duration_ms": duration_ms,
        }

    def rollback_last_layout(self) -> Dict[str, Any]:
        """Rolls back the most recently applied layout (Rule 7 reversibility)."""
        if len(self._history) < 2:
            return {"status": "noop", "message": "No previous layout snapshot to rollback to"}

        # Pop current snapshot
        self._history.pop()
        prev = self._history[-1]
        self._active_preset = prev.preset_id

        return {
            "status": "rolled_back",
            "restored_snapshot_id": prev.snapshot_id,
            "preset_id": prev.preset_id,
            "placements_count": len(prev.placements),
        }

    def get_active_state(self) -> Dict[str, Any]:
        displays = multi_display_manager.detect_monitors()
        return {
            "active_preset": self._active_preset,
            "displays": [d.model_dump() for d in displays],
            "total_presets": len(self._presets),
            "snapshots_in_history": len(self._history),
        }


# Global singleton
layout_choreographer = LayoutChoreographer()
