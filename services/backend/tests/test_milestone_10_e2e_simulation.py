"""
Milestone 10.0 Comprehensive Multi-Component E2E Integration Suite (MSH-01, SWM-01, GUI-01, MIR-01, SAF-02)
Chains all 4 milestone components into a sovereign local multi-agent workflow:
1. Specialist Swarm Debate (SWM-01)
2. Isolated Hidden Virtual Desktop Automation (GUI-01)
3. Cognitive Mirror Personalized Text Synthesis (MIR-01)
4. Encrypted Local P2P Mesh & Remote Voice Stream (MSH-01)
5. Universal Guardian Universal Kill Switch Halt (SAF-02)
"""

import os
import time
import pytest

from services.backend.schemas.mesh import (
    CompanionApprovalDecision,
    MeshDeviceRole,
    PairedDeviceProfile
)
from services.backend.schemas.cognitive_mirror import (
    MirrorDimension,
    SynthesisTaskType
)
from services.backend.schemas.swarm_debate import SwarmProposal
from services.backend.swarm.specialist_orchestrator import SpecialistSwarmOrchestrator
from services.backend.automation.virtual_desktop_backend import MockVirtualDesktopBackend
from services.backend.automation.virtual_desktop_manager import VirtualDesktopManager
from services.backend.personality.cognitive_mirror import CognitiveMirrorEngine
from services.backend.mesh.approval_cards import CompanionApprovalManager
from services.backend.mesh.crypto import MeshCryptoEngine
from services.backend.mesh.discovery import MeshDiscoveryEngine
from services.backend.mesh.graph_sync import MeshGraphSynchronizer
from services.backend.mesh.p2p_mesh_engine import P2PMeshEngine
from services.backend.mesh.remote_voice import MeshRemoteVoiceStreamer
from services.backend.safety.confirmations import ConfirmationEngine
from services.backend.safety.guardian import guardian


@pytest.mark.asyncio
async def test_milestone_10_full_e2e_lifecycle(tmp_path):
    # Ensure clean guardian state
    if guardian.is_halted:
        guardian.resume()

    # ----------------------------------------------------
    # Phase 1: Multi-Agent Specialist Swarm Debate (SWM-01)
    # ----------------------------------------------------
    swarm_orch = SpecialistSwarmOrchestrator()
    guardian.add_state_callback(lambda s: swarm_orch.halt() if s == "halted" else swarm_orch.reset())

    proposal = SwarmProposal(
        title="Refactor P2P Cryptographic Transport",
        description="Upgrading transport security to ChaCha20-Poly1305 with HKDF key derivation.",
        risk_tier=1,
        diff="def test(): pass"
    )
    debate = await swarm_orch.dispatch_debate(proposal, max_rounds=2)
    assert debate.debate_id is not None
    assert len(debate.turns) >= 1
    assert debate.final_score >= 0.0

    # ----------------------------------------------------
    # Phase 2: Isolated Virtual Desktop Automation (GUI-01)
    # ----------------------------------------------------
    mock_gui_backend = MockVirtualDesktopBackend()
    vdesk_mgr = VirtualDesktopManager(backend=mock_gui_backend)
    guardian.add_state_callback(lambda s: vdesk_mgr.halt() if s == "halted" else vdesk_mgr.reset())

    session = vdesk_mgr.create_desktop(session_id="Automated-P2P-Compiler")
    assert session.session_id == "Automated-P2P-Compiler"
    assert session.is_active is True

    # Launch app inside isolated virtual desktop
    pid, hwnd = vdesk_mgr.launch_isolated_app(session.session_id, "pytest.exe", ["tests/"])
    assert pid > 0

    # Enumerate windows inside isolated desktop without moving user cursor
    windows = vdesk_mgr.enum_windows(session.session_id)
    assert len(windows) >= 1
    assert windows[0].hwnd > 0

    # ----------------------------------------------------
    # Phase 3: Cognitive Mirror & Authentic Twin (MIR-01)
    # ----------------------------------------------------
    mirror_db = str(tmp_path / "cognitive_mirror_e2e.db")
    mirror = CognitiveMirrorEngine(db_path=mirror_db, encryption_key="e2e_test_secret_key_1234567890123")
    guardian.add_state_callback(lambda s: mirror.halt() if s == "halted" else mirror.reset())

    # Train mirror on user's authentic conventional commit style
    commits = [
        "feat(mesh): add chacha20 transport security",
        "fix(crypto): prevent sequence replay with sliding bitmask",
        "docs(mesh): document zero cloud sovereign invariant",
        "test(safety): assert sub-25ms killswitch sla",
    ]
    mirror.learn_from_git(commits_override=commits)
    stats = mirror.get_stats(MirrorDimension.GIT_STYLE)
    assert stats["sample_count"] == 4

    # Synthesize commit message in authentic style
    synth_result = mirror.synthesize_text(
        task=SynthesisTaskType.COMMIT_MESSAGE,
        context_prompt="Completed Wave 4 P2P mesh and safety verification suite."
    )
    assert synth_result.synthesized_text.startswith("feat") or synth_result.synthesized_text.startswith("chore") or "mesh" in synth_result.synthesized_text

    # ----------------------------------------------------
    # Phase 4: Encrypted Local P2P Mesh Synchronization (MSH-01)
    # ----------------------------------------------------
    mesh_db = str(tmp_path / "paired_devices_e2e.json")
    mesh_engine = P2PMeshEngine(
        node_id="desktop-primary-rig",
        device_name="Phenom Main Desktop",
        guardian=guardian,
        registry_path=mesh_db
    )
    mesh_engine.start()

    # Step A: Companion discovers host via UDP beacon
    beacon_engine = MeshDiscoveryEngine(
        node_id="companion-pixel-9",
        device_name="Pixel 9 Pro Companion",
        discovery_port=53549
    )

    # Step B: Ephemeral QR pairing
    qr_payload = mesh_engine.generate_pairing_qr(ttl_seconds=120)
    assert qr_payload.token is not None
    assert qr_payload.qr_matrix_svg is not None

    companion_profile = mesh_engine.verify_pairing(
        node_id="companion-pixel-9",
        device_name="Pixel 9 Pro Companion",
        device_role=MeshDeviceRole.COMPANION_MOBILE,
        token=qr_payload.token,
        client_ip="192.168.1.155"
    )
    assert companion_profile is not None
    assert companion_profile.node_id == "companion-pixel-9"

    # Step C: Register active encrypted session
    shared_key = os.urandom(32)
    mesh_engine.register_session("companion-pixel-9", MeshCryptoEngine(key=shared_key))

    # Step D: Companion Approval Card Push and Signed Resolution
    conf_engine = ConfirmationEngine()
    approval_mgr = CompanionApprovalManager(engine=mesh_engine, conf_engine=conf_engine)
    tier1_conf = conf_engine.build_confirmation(
        request_id="e2e-conf-001",
        tier=1,
        tool_name="mesh_sync_push",
        action_verb="Push",
        item_count=1,
        target_summary="GraphRAG deltas to companion"
    )
    card = approval_mgr.dispatch_approval_card(tier1_conf, diff_preview="+ 1 node synced")
    assert card.request_id == "e2e-conf-001"

    now = time.time()
    sig = approval_mgr.compute_decision_signature(
        request_id="e2e-conf-001",
        decision="approved",
        node_id="companion-pixel-9",
        decided_at=now,
        secret=companion_profile.shared_secret_hash
    )
    decision = CompanionApprovalDecision(
        request_id="e2e-conf-001",
        decision="approved",
        node_id="companion-pixel-9",
        decided_at=now,
        signature=sig
    )
    decision_ok = approval_mgr.handle_companion_decision(decision)
    assert decision_ok is True

    # Step E: Bi-directional GraphRAG note delta sync
    graph_sync = MeshGraphSynchronizer(node_id="desktop-primary-rig")
    graph_sync.record_node("vault://e2e-design.md", "P2P Architecture", "Decentralized mesh draft.")
    delta = graph_sync.generate_outbound_deltas(since_timestamp=0.0)
    assert len(delta.node_deltas) == 1

    # Step F: Remote Voice Summon with Sub-5ms Barge-In
    voice_streamer = MeshRemoteVoiceStreamer(engine=mesh_engine)
    tts_chunk = b"\x00\x01" * 512
    voice_streamer.stream_tts_chunk_to_companion("companion-pixel-9", tts_chunk)
    assert voice_streamer._is_tts_active is True
    # User speaks on companion -> triggers instant barge-in
    barge_latency_ms = voice_streamer.trigger_barge_in()
    assert barge_latency_ms < 5.0
    assert voice_streamer._is_tts_active is False

    # ----------------------------------------------------
    # Phase 5: Universal Guardian Universal Kill Switch Halt (SAF-02)
    # ----------------------------------------------------
    t_halt_start = time.perf_counter()
    guardian.trigger("e2e_universal_emergency_stop")
    elapsed_halt_ms = (time.perf_counter() - t_halt_start) * 1000

    print(f"\n[UNIVERSAL GUARDIAN HALT] Simultaneous multi-component halt elapsed: {elapsed_halt_ms:.4f} ms")
    assert elapsed_halt_ms < 25.0

    # Assert all components are simultaneously halted
    assert swarm_orch.is_halted is True
    assert len(vdesk_mgr.list_active_sessions()) == 0
    assert mirror.is_halted is True
    assert mesh_engine.is_halted is True

    # Assert operations across all components are blocked with PermissionError
    with pytest.raises(PermissionError):
        mesh_engine.generate_pairing_qr()

    with pytest.raises(PermissionError):
        vdesk_mgr.launch_isolated_app(session.session_id, "calc.exe")

    with pytest.raises(PermissionError):
        mirror.synthesize_text(SynthesisTaskType.COMMIT_MESSAGE, "Test prompt")

    # Clean shutdown
    mesh_engine.stop()
    beacon_engine.stop()
    guardian.resume()
