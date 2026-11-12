"""Unit tests for Milestone 13 Phase 2: Volumetric Spatial 3D Canvas & Vision Gestures (VOL-01)."""

import pytest
from services.backend.schemas.volumetric import (
    Vector3D,
    VolumetricNode,
    GestureType,
    VisionGesturePayload,
    ProjectionGeometry,
)
from services.backend.volumetric.gesture_tracker import VisionGestureTracker
from services.backend.volumetric.canvas_manager import VolumetricCanvasManager


def test_gesture_tracker_ingest_and_notify():
    tracker = VisionGestureTracker()
    received_gestures = []

    tracker.register_listener(lambda g: received_gestures.append(g))

    payload = tracker.ingest_gesture(
        gesture_type=GestureType.POINT,
        confidence=0.95,
        hand_position=Vector3D(x=0.2, y=0.1, z=1.4),
    )

    assert payload.gesture_type == GestureType.POINT
    assert payload.confidence == 0.95
    assert len(received_gestures) == 1
    assert received_gestures[0].gesture_id == payload.gesture_id
    assert tracker.get_last_gesture() is not None
    assert tracker.get_last_gesture().gesture_type == GestureType.POINT


def test_gesture_tracker_classify_landmarks():
    tracker = VisionGestureTracker()

    # Pinch classification: thumb tip near index tip (dist < 0.05m)
    thumb = Vector3D(x=0.1, y=0.2, z=1.0)
    index_near = Vector3D(x=0.12, y=0.22, z=1.0)
    g_pinch = tracker.classify_from_landmarks(thumb_tip=thumb, index_tip=index_near)
    assert g_pinch.gesture_type == GestureType.PINCH

    # Point classification: thumb far from index (dist >= 0.05m)
    index_far = Vector3D(x=0.3, y=0.4, z=1.0)
    g_point = tracker.classify_from_landmarks(thumb_tip=thumb, index_tip=index_far)
    assert g_point.gesture_type == GestureType.POINT


def test_volumetric_canvas_node_lifecycle_and_projections():
    tracker = VisionGestureTracker()
    manager = VolumetricCanvasManager(gesture_tracker=tracker)

    # Spawn nodes
    node1 = manager.spawn_node(
        label="Terminal 3D",
        x=0.5,
        y=0.2,
        z=1.5,
        color_hex="#00f0ff",
        depth_layer=1,
        is_pinned=True,
    )
    assert node1.label == "Terminal 3D"
    assert node1.is_pinned is True

    node2 = manager.spawn_node(
        label="Telemetry Card",
        x=-0.5,
        y=-0.2,
        z=1.8,
        color_hex="#ffb800",
        depth_layer=2,
        is_pinned=False,
    )
    assert node2.label == "Telemetry Card"
    assert node2.is_pinned is False

    state = manager.get_state()
    assert state.is_active is True
    assert state.total_nodes == 2

    # Switch projections
    p_spherical = manager.set_projection_mode("spherical")
    assert p_spherical == ProjectionGeometry.SPHERICAL
    assert manager.get_state().projection_mode == ProjectionGeometry.SPHERICAL

    p_planar = manager.set_projection_mode("planar")
    assert p_planar == ProjectionGeometry.PLANAR

    # Raycast selection
    hit = manager.select_node_by_raycast(Vector3D(x=0.52, y=0.21, z=1.48))
    assert hit is not None
    assert hit.node_id == node1.node_id
    assert manager.get_state().selected_node_id == node1.node_id

    # Gesture Palm Dismiss: Should clear unpinned node2, keep pinned node1
    tracker.ingest_gesture(
        gesture_type=GestureType.PALM_DISMISS,
        confidence=0.99,
        hand_position=Vector3D(x=0.0, y=0.0, z=1.0),
    )

    state_after_dismiss = manager.get_state()
    assert state_after_dismiss.total_nodes == 1
    assert state_after_dismiss.nodes[0].node_id == node1.node_id

    # Clear canvas
    cleared = manager.clear_canvas()
    assert cleared == 1
    assert manager.get_state().total_nodes == 0
    assert manager.get_state().is_active is False
