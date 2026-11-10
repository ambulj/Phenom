import pytest
import time
import asyncio
from services.backend.remote.interactive_approvals import (
    InteractiveApprovalManager,
    ApprovalTicket,
    interactive_approval_manager
)
from services.backend.remote.telegram_mesh import (
    TelegramMeshManager,
    telegram_mesh,
    RemoteVoiceRAGResult,
    TelegramMeshStatus
)
from services.backend.safety.guardian import guardian
from services.backend.safety.registry import registry
import services.backend.tools.telegram_mesh_tools  # Ensure tools are registered


@pytest.mark.asyncio
async def test_remote_voice_note_hybrid_rag_synthesis():
    """Test remote voice note queries are transcribed in RAM and answered with citations."""
    mesh = TelegramMeshManager()
    voice_buffer = b"\x1f\x8b\x08" + b"\x00" * 2048  # Simulated in-memory PCM voice packet

    res = await mesh.handle_remote_voice_note(
        voice_bytes=voice_buffer,
        simulated_transcript="What are the safety governance tiers in Phenom?"
    )

    assert isinstance(res, RemoteVoiceRAGResult)
    assert "safety" in res.query.lower() or "phenom" in res.query.lower()
    assert isinstance(res.answer, str)
    assert len(res.answer) > 0
    assert res.duration_ms >= 0.0


@pytest.mark.asyncio
async def test_interactive_approval_ticket_lifecycle():
    """Test creating an approval ticket, formatting inline buttons, and callback resolution."""
    mgr = InteractiveApprovalManager()
    ticket = mgr.create_ticket(
        action_name="git_atomic_refactor",
        tier=1,
        preview_text="Rename function calculate_subtotal to calculate_order_subtotal",
        tool_args={"old_name": "calculate_subtotal", "new_name": "calculate_order_subtotal"}
    )

    assert ticket.ticket_id.startswith("appr_")
    assert ticket.status == "pending"

    # Verify inline keyboard format
    keyboard = mgr.format_inline_keyboard(ticket)
    assert "inline_keyboard" in keyboard
    buttons = keyboard["inline_keyboard"][0]
    assert buttons[0]["text"] == "Approve ✅"
    assert buttons[0]["callback_data"] == f"approve:{ticket.ticket_id}"
    assert buttons[1]["text"] == "Reject ❌"

    # Simulate callback query resolution
    ok = mgr.resolve_ticket(ticket.ticket_id, "approved", resolved_by="telegram_user_99")
    assert ok is True
    assert ticket.status == "approved"
    assert ticket.resolved_by == "telegram_user_99"


@pytest.mark.asyncio
async def test_approval_ticket_expiration_handling():
    """Test tickets automatically expire and unblock awaiting futures."""
    mgr = InteractiveApprovalManager()
    ticket = mgr.create_ticket(
        action_name="delete_scratch_file",
        tier=1,
        preview_text="Delete temporary log",
        timeout_sec=0.1
    )

    # Wait for expiration
    decision = await mgr.wait_for_decision(ticket.ticket_id, timeout_sec=0.2)
    assert decision == "expired"
    assert ticket.status == "expired"


@pytest.mark.asyncio
async def test_remote_emergency_halt_guardian_sla():
    """Test remote /halt command immediately triggers Guardian kill switch in < 25.0ms SLA."""
    mesh = TelegramMeshManager()
    guardian.resume()
    assert guardian.is_halted is False

    try:
        t0 = time.perf_counter()
        res = mesh.handle_command("/halt")
        elapsed_ms = (time.perf_counter() - t0) * 1000

        assert elapsed_ms < 25.0, f"Remote /halt took {elapsed_ms:.2f}ms, exceeding 25.0ms SLA"
        assert guardian.is_halted is True
        assert res["status"] == "emergency_halt_triggered"
        assert res["guardian_halted"] is True
    finally:
        guardian.resume()


@pytest.mark.asyncio
async def test_telegram_command_routing_and_status():
    """Test standard command routing: /status, /rag, /vault, and unknown commands."""
    mesh = TelegramMeshManager()

    status_res = mesh.handle_command("/status")
    assert status_res["status"] == "ok"
    assert "Phenom Status" in status_res["response"]

    rag_res = mesh.handle_command("/rag architecture")
    assert rag_res["command"] == "/rag"
    assert "results_count" in rag_res

    unknown_res = mesh.handle_command("/foobar")
    assert unknown_res["status"] == "unknown_command"


@pytest.mark.asyncio
async def test_telegram_mesh_tools_registration_and_previews():
    """Test all Phase 3 tools are registered in Safety Registry with proper tiers and previews."""
    tool_names = [
        "dispatch_telegram_approval_request",
        "handle_telegram_callback_decision",
        "execute_remote_voice_rag",
        "get_telegram_mesh_status"
    ]

    for name in tool_names:
        entry = registry.get(name)
        assert entry is not None, f"Tool {name} missing from registry"

        if name == "dispatch_telegram_approval_request":
            assert entry.tier == 1
        else:
            assert entry.tier == 0

        preview = entry.preview_fn({
            "action_name": "run_tests",
            "tier": 1,
            "callback_data": "approve:appr_123",
            "query": "explain RAG"
        })
        assert isinstance(preview, str)
        assert len(preview) > 5
