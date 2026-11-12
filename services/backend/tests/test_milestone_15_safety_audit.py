import pytest
from services.backend.safety.guardian import guardian
from services.backend.safety.registry import registry
import services.backend.tools.voice_action_tools
import services.backend.tools.cognitive_twin_tools
import services.backend.tools.subsystem_governance_tools
import services.backend.tools.multi_agent_mesh_tools


MILESTONE_15_TOOLS = [
    # Phase 1: Voice-to-Action Kernel
    ("voice_kernel_get_status", 0),
    ("voice_kernel_configure", 1),
    ("voice_kernel_simulate_chunk", 1),
    ("voice_kernel_abort_intent", 1),
    # Phase 2: Cognitive Twin & Life-Graph
    ("cognitive_twin_get_status", 0),
    ("cognitive_twin_query_graph", 0),
    ("cognitive_twin_ingest_episode", 1),
    ("cognitive_twin_prune_graph", 1),
    # Phase 3: Subsystem Governance & Self-Healing
    ("subsystem_get_health", 0),
    ("subsystem_trigger_remediation", 1),
    ("subsystem_reset_circuit_breaker", 1),
    ("subsystem_configure_thresholds", 1),
    # Phase 4: Multi-Agent Mesh Protocol
    ("mesh_get_status", 0),
    ("mesh_discover_peers", 0),
    ("mesh_delegate_task", 1),
    ("mesh_disconnect_peer", 1),
]


def test_milestone_15_all_16_tools_registered_and_tiered():
    assert len(MILESTONE_15_TOOLS) == 16

    for tool_name, expected_tier in MILESTONE_15_TOOLS:
        tool_def = registry.get(tool_name)
        assert tool_def is not None, f"Tool '{tool_name}' must be registered in ToolRegistry"
        assert tool_def.tier == expected_tier, f"Tool '{tool_name}' tier mismatch (expected {expected_tier}, got {tool_def.tier})"
        assert tool_def.preview_fn is not None, f"Tool '{tool_name}' missing preview function"
        assert tool_def.args_schema is not None, f"Tool '{tool_name}' missing args schema"


def test_milestone_15_all_tier_0_queries_execute():
    if guardian.is_halted:
        guardian.resume()

    for tool_name, tier in MILESTONE_15_TOOLS:
        if tier == 0:
            tool_def = registry.get(tool_name)
            res = tool_def.handler_fn()
            assert res is not None, f"Tier 0 tool '{tool_name}' returned None"


def test_milestone_15_guardian_lockdown_fails_closed():
    try:
        guardian.trigger("Milestone 15 Universal Lockdown Audit")
        assert guardian.is_halted

        # Phase 1: Voice Kernel
        with pytest.raises(PermissionError):
            registry.get("voice_kernel_get_status").handler_fn()
        with pytest.raises(PermissionError):
            registry.get("voice_kernel_configure").handler_fn(vad_threshold=0.5)
        with pytest.raises(PermissionError):
            registry.get("voice_kernel_simulate_chunk").handler_fn(rms_energy=0.3, speech_prob=0.8)
        with pytest.raises(PermissionError):
            registry.get("voice_kernel_abort_intent").handler_fn(action_id="act-1")

        # Phase 2: Cognitive Twin
        with pytest.raises(PermissionError):
            registry.get("cognitive_twin_get_status").handler_fn()
        with pytest.raises(PermissionError):
            registry.get("cognitive_twin_query_graph").handler_fn()
        with pytest.raises(PermissionError):
            registry.get("cognitive_twin_ingest_episode").handler_fn(activity_label="test")
        with pytest.raises(PermissionError):
            registry.get("cognitive_twin_prune_graph").handler_fn()

        # Phase 3: Subsystem Governance
        with pytest.raises(PermissionError):
            registry.get("subsystem_get_health").handler_fn()
        with pytest.raises(PermissionError):
            registry.get("subsystem_trigger_remediation").handler_fn(subsystem_name="voice_action", action_type="flush_stale_buffers")
        with pytest.raises(PermissionError):
            registry.get("subsystem_reset_circuit_breaker").handler_fn(subsystem_name="voice_action")
        with pytest.raises(PermissionError):
            registry.get("subsystem_configure_thresholds").handler_fn()

        # Phase 4: Multi-Agent Mesh
        with pytest.raises(PermissionError):
            registry.get("mesh_get_status").handler_fn()
        with pytest.raises(PermissionError):
            registry.get("mesh_discover_peers").handler_fn()
        with pytest.raises(PermissionError):
            registry.get("mesh_delegate_task").handler_fn(target_node_id="peer-1", capability_required="gpu_compute")
        with pytest.raises(PermissionError):
            registry.get("mesh_disconnect_peer").handler_fn(node_id="peer-1")
    finally:
        guardian.resume()
