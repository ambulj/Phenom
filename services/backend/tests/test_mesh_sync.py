"""
Unit tests for Real-Time Local Mesh Synchronization
Verifies companion approval cards, HMAC signatures, Tier 3 prohibition,
non-blocking telemetry broadcasting, and GraphRAG LWW delta merging.
"""

import time
import pytest
from services.backend.schemas.mesh import (
    CompanionApprovalDecision,
    MeshDeviceRole,
    PairedDeviceProfile
)
from services.backend.mesh.approval_cards import CompanionApprovalManager
from services.backend.mesh.graph_sync import MeshGraphSynchronizer
from services.backend.mesh.p2p_mesh_engine import P2PMeshEngine
from services.backend.mesh.telemetry_streamer import MeshTelemetryBroadcaster
from services.backend.safety.confirmations import ConfirmationEngine


def test_approval_cards_tier3_rejection(tmp_path):
    engine = P2PMeshEngine(
        node_id="desktop-host",
        registry_path=str(tmp_path / "devices.json")
    )
    conf_engine = ConfirmationEngine()
    mgr = CompanionApprovalManager(engine=engine, conf_engine=conf_engine)

    # Build a Tier 3 confirmation
    tier3_req = conf_engine.build_confirmation(
        request_id="req-tier3-test",
        tier=3,
        tool_name="permanent_destroy",
        action_verb="Delete",
        item_count=1,
        target_summary="System Directory"
    )

    # Dispatching Tier 3 to companion must be strictly blocked
    with pytest.raises(ValueError, match="strictly prohibited"):
        mgr.dispatch_approval_card(tier3_req)


def test_approval_card_push_and_signature_resolution(tmp_path):
    engine = P2PMeshEngine(
        node_id="desktop-host",
        registry_path=str(tmp_path / "devices.json")
    )
    conf_engine = ConfirmationEngine()
    mgr = CompanionApprovalManager(engine=engine, conf_engine=conf_engine)

    # Register mock paired companion device with dynamic secret
    mock_secret = "secret_" + "companion_key_test_123"
    profile = PairedDeviceProfile(
        node_id="phone-node",
        device_name="Companion Phone",
        device_role=MeshDeviceRole.COMPANION_MOBILE,
        shared_secret_hash=mock_secret,
        paired_at=time.time(),
        last_seen_at=time.time()
    )
    engine.device_registry.register_device(profile)

    # Build Tier 1 confirmation
    conf = conf_engine.build_confirmation(
        request_id="req-tier1-edit",
        tier=1,
        tool_name="write_file",
        action_verb="Write",
        item_count=1,
        target_summary="notes.md"
    )

    # Dispatch card
    card = mgr.dispatch_approval_card(conf, diff_preview="+ new content")
    assert card.request_id == "req-tier1-edit"
    assert card.tier == 1

    # Valid companion decision
    now = time.time()
    sig = mgr.compute_decision_signature(
        request_id="req-tier1-edit",
        decision="approved",
        node_id="phone-node",
        decided_at=now,
        secret=mock_secret
    )

    decision = CompanionApprovalDecision(
        request_id="req-tier1-edit",
        decision="approved",
        node_id="phone-node",
        decided_at=now,
        signature=sig
    )

    result = mgr.handle_companion_decision(decision)
    assert result is True

    # Bad signature rejection
    tampered_decision = CompanionApprovalDecision(
        request_id="req-tier1-edit",
        decision="approved",
        node_id="phone-node",
        decided_at=now,
        signature="invalid_tampered_signature"
    )
    with pytest.raises(ValueError, match="No pending confirmation"):
        mgr.handle_companion_decision(tampered_decision)


def test_telemetry_streamer_non_blocking(tmp_path):
    engine = P2PMeshEngine(
        node_id="desktop-host",
        registry_path=str(tmp_path / "devices.json")
    )
    streamer = MeshTelemetryBroadcaster(engine=engine, queue_size=10)

    # Stream swarm debate
    ok1 = streamer.broadcast_swarm_debate(
        debate_id="deb-001",
        round_num=1,
        specialist_role="SecuritySpecialist",
        critique="Code adheres to AEAD spec.",
        consensus_score=0.98
    )
    assert ok1 is True

    # Stream mission progress
    ok2 = streamer.broadcast_mission_progress(
        mission_id="mis-001",
        phase="WAVE_1",
        progress_pct=25.0,
        log_line="Completed encryption module."
    )
    assert ok2 is True

    streamer.stop()


def test_graphrag_delta_sync_lww():
    sync_desktop = MeshGraphSynchronizer(node_id="desktop-host")
    sync_mobile = MeshGraphSynchronizer(node_id="mobile-host")

    # Desktop writes node at t=100
    sync_desktop.record_node(
        uri="vault://meeting-notes.md",
        title="Architecture Discussion",
        content="Initial draft.",
        timestamp=100.0
    )

    # Mobile writes same node at t=150 (newer edit)
    sync_mobile.record_node(
        uri="vault://meeting-notes.md",
        title="Architecture Discussion",
        content="Updated with mobile bullet points.",
        timestamp=150.0
    )

    # Sync from mobile to desktop
    delta = sync_mobile.generate_outbound_deltas(since_timestamp=0.0)
    res = sync_desktop.apply_inbound_deltas(delta)

    assert res["nodes_updated"] == 1
    assert res["nodes_skipped"] == 0

    node = sync_desktop.get_node("vault://meeting-notes.md")
    assert node is not None
    assert "mobile bullet points" in node["content"]

    # Now attempt sync with older delta (t=80)
    stale_delta = sync_mobile.generate_outbound_deltas(since_timestamp=0.0)
    for n in stale_delta.node_deltas:
        n["updated_at"] = 80.0
        n["content"] = "Ancient text"

    res_stale = sync_desktop.apply_inbound_deltas(stale_delta)
    assert res_stale["nodes_updated"] == 0
    assert res_stale["nodes_skipped"] == 1

    # Text must NOT be overwritten by older edit
    node_after = sync_desktop.get_node("vault://meeting-notes.md")
    assert node_after is not None
    assert "mobile bullet points" in node_after["content"]
