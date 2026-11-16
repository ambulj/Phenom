"""Comprehensive Unit Test Suite for Real-Time Full-Duplex Voice Engine & Barge-In Soft-Mute.

Phase 48-03: VOICE-01, VOICE-02, VOICE-03.
Tests sub-300ms duplex audio streaming, sub-100ms instant soft-mute, non-destructive swarm execution,
emergency phrase Guardian kill switch (< 25ms SLA), contextual steering injection, and ToolRegistry tools.
"""

import time
import pytest
import numpy as np
from typing import Dict, Any

from services.backend.schemas.swarm_auction import AgentRole
from services.backend.schemas.voice_duplex import (
    BargeInEvent,
    BargeInType,
    DuplexAudioMetrics,
    DuplexStreamState,
    SwarmGuidanceInjection,
)
from services.backend.voice.barge_in_handler import BargeInSoftMuteHandler
from services.backend.voice.full_duplex_stream import FullDuplexStreamManager
from services.backend.voice.swarm_voice_bridge import SwarmVoiceBridge
from services.backend.swarm.scheduler import SwarmScheduler
import services.backend.tools.duplex_voice_tools
from services.backend.safety.registry import registry


# ============================================================================
# 1. Duplex Voice Schemas Validation
# ============================================================================

def test_duplex_voice_schemas():
    """Verify enum states, metrics defaults, and serialization."""
    event = BargeInEvent(
        event_id="evt_001",
        latency_ms=12.5,
        tts_attenuated=True,
        transcript="Hold on",
        barge_in_type=BargeInType.STEERING_GUIDANCE,
        swarm_continued=True,
    )
    dumped = event.model_dump()
    assert dumped["latency_ms"] == 12.5
    assert dumped["barge_in_type"] == "steering_guidance"
    assert dumped["swarm_continued"] is True

    metrics = DuplexAudioMetrics(
        roundtrip_latency_ms=45.2,
        vad_probability=0.85,
        tts_playing=True,
        user_speaking=True,
        soft_muted=False,
    )
    assert metrics.roundtrip_latency_ms == 45.2
    assert metrics.vad_probability == 0.85


# ============================================================================
# 2. Barge-In Soft-Mute Handler & Latency (VOICE-02)
# ============================================================================

def test_barge_in_soft_mute_latency_and_gain():
    """Verify audio output gain is attenuated to 0 in < 100ms SLA."""
    handler = BargeInSoftMuteHandler()
    handler.is_tts_playing = True
    handler.output_gain = 1.0

    # Warm-up call
    handler.trigger_soft_mute()

    # Measured call
    t_start = time.perf_counter()
    event = handler.trigger_soft_mute("Please check the tests")
    elapsed_ms = (time.perf_counter() - t_start) * 1000.0

    assert handler.output_gain == 0.0
    assert handler.is_tts_playing is False
    assert event.tts_attenuated is True
    # Hard SLA: Must be < 100.0 ms
    assert elapsed_ms < 100.0, f"Soft-mute took {elapsed_ms:.2f}ms, exceeding 100ms SLA"


def test_barge_in_swarm_continuity_vs_emergency_kill():
    """Verify swarm execution is preserved on conversational speech, halted only on emergency kill phrases."""
    guardian_triggered = False

    def mock_guardian_halt():
        nonlocal guardian_triggered
        guardian_triggered = True

    handler = BargeInSoftMuteHandler(guardian_halt_fn=mock_guardian_halt)

    # 1. Normal conversational steering -> Swarm continued, Guardian NOT triggered
    event_steer = handler.trigger_soft_mute("Focus on the authentication module first")
    assert event_steer.swarm_continued is True
    assert event_steer.barge_in_type == BargeInType.STEERING_GUIDANCE
    assert guardian_triggered is False

    # 2. Correction phrase -> Swarm continued, Guardian NOT triggered
    event_corr = handler.trigger_soft_mute("Don't touch that file")
    assert event_corr.swarm_continued is True
    assert event_corr.barge_in_type == BargeInType.CORRECTION
    assert guardian_triggered is False

    # 3. Emergency kill phrase -> Guardian TRIGGERED in < 25ms SLA, Swarm NOT continued
    t_kill_start = time.perf_counter()
    event_kill = handler.trigger_soft_mute("Phenom stop immediately")
    kill_elapsed_ms = (time.perf_counter() - t_kill_start) * 1000.0

    assert event_kill.swarm_continued is False
    assert event_kill.barge_in_type == BargeInType.EMERGENCY_HALT
    assert guardian_triggered is True
    assert kill_elapsed_ms < 25.0, f"Emergency kill took {kill_elapsed_ms:.2f}ms, exceeding 25ms SLA"


# ============================================================================
# 3. Full-Duplex Stream Manager & VAD Processing (VOICE-01)
# ============================================================================

def test_full_duplex_stream_manager():
    """Verify roundtrip latency < 300ms and state machine transitions."""
    manager = FullDuplexStreamManager()
    assert manager.state == DuplexStreamState.LISTENING

    # 1. Silence chunk (ambient noise rms ~50)
    silence = np.ones(512, dtype=np.int16) * 50
    st_silence = manager.process_input_frame(silence)
    assert st_silence == DuplexStreamState.LISTENING

    # 2. Loud vocal chunk (rms ~1500)
    speech = np.ones(512, dtype=np.int16) * 1500
    st1 = manager.process_input_frame(speech)
    st2 = manager.process_input_frame(speech)  # 2nd chunk triggers speech onset
    assert st2 == DuplexStreamState.USER_SPEAKING

    # Roundtrip SLA check (< 300ms)
    metrics = manager.get_metrics()
    assert metrics.roundtrip_latency_ms < 300.0
    assert metrics.user_speaking is True

    # 3. Test agent speaking + barge-in -> transitions to SOFT_MUTED
    manager.set_agent_speaking(True)
    assert manager.state == DuplexStreamState.AGENT_SPEAKING

    # Interruption frames
    manager.process_input_frame(speech)
    st_barge = manager.process_input_frame(speech)
    assert st_barge == DuplexStreamState.SOFT_MUTED
    assert manager.get_metrics().soft_muted is True


# ============================================================================
# 4. Contextual Swarm Voice Bridge (VOICE-03)
# ============================================================================

def test_swarm_voice_bridge_steering_injection():
    """Verify speech steering guidance is injected into active SwarmScheduler tasks."""
    scheduler = SwarmScheduler()
    bridge = SwarmVoiceBridge(default_scheduler=scheduler)

    # Enqueue tasks in scheduler
    task1 = scheduler.enqueue_task("n_code", "run_workspace_tests", {"mode": "fast"}, AgentRole.CODER)
    task2 = scheduler.enqueue_task("n_audit", "check_mission_preconditions", {}, AgentRole.SECURITY_AUDITOR)

    # Inject vocal guidance mid-flight
    injection = bridge.inject_guidance(
        transcript="Make sure you prioritize the security preconditions check first",
        scheduler=scheduler,
    )

    assert injection.barge_in_type == BargeInType.STEERING_GUIDANCE
    assert injection.applied is True

    # Verify task arguments updated with operator guidance
    queue = scheduler.get_queue_status()
    assert len(queue) == 2
    assert queue[0].arguments["_operator_guidance"] == "Make sure you prioritize the security preconditions check first"
    assert queue[0].arguments["_guidance_priority"] == 8

    # Verify task is NOT aborted or halted (Swarm continuity preserved!)
    assert queue[0].status == task1.status  # Still SCHEDULED!


# ============================================================================
# 5. Tool Registry Integration & Execution
# ============================================================================

def test_duplex_voice_tools_registry():
    """Verify tool registration, tier numbers, preview generation, and execution."""
    tool_cfg = registry.get("configure_duplex_streaming")
    tool_inj = registry.get("inject_voice_guidance")
    tool_met = registry.get("get_duplex_voice_metrics")

    assert tool_cfg is not None
    assert tool_cfg.tier == 0  # Tier 0 read-only
    assert tool_inj is not None
    assert tool_inj.tier == 1  # Tier 1 queue steering
    assert tool_met is not None
    assert tool_met.tier == 0  # Tier 0 telemetry

    # Execute configure_duplex_streaming
    res_cfg = tool_cfg.handler_fn(vad_threshold=0.35, buffer_seconds=4.0)
    assert res_cfg["status"] == "configured"
    assert res_cfg["vad_threshold"] == 0.35
    assert res_cfg["buffer_seconds"] == 4.0

    # Execute get_duplex_voice_metrics
    res_met = tool_met.handler_fn()
    assert "roundtrip_latency_ms" in res_met
    assert "vad_probability" in res_met

    # Execute inject_voice_guidance
    res_inj = tool_inj.handler_fn(transcript="Focus on bug fixes")
    assert res_inj["guidance_text"] == "Focus on bug fixes"
    assert res_inj["barge_in_type"] == "steering_guidance"
