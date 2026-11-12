import pytest
from services.backend.safety.guardian import guardian
from services.backend.safety.registry import registry
import services.backend.tools.voice_action_tools as vat


def test_voice_action_tools_registered_in_registry():
    expected_tools = [
        ("voice_kernel_get_status", 0),
        ("voice_kernel_configure", 1),
        ("voice_kernel_simulate_chunk", 1),
        ("voice_kernel_abort_intent", 1),
    ]

    for tool_name, expected_tier in expected_tools:
        tool_def = registry.get(tool_name)
        assert tool_def is not None, f"Tool {tool_name} not registered in ToolRegistry"
        assert tool_def.tier == expected_tier, f"Tool {tool_name} tier mismatch"


def test_voice_action_tier_0_queries_execute():
    if guardian.is_halted:
        guardian.resume()

    res = vat.voice_kernel_get_status()
    assert "state" in res
    assert "noise_floor_rms" in res
    assert "vad_threshold" in res


def test_voice_action_tier_1_controls_with_preview():
    if guardian.is_halted:
        guardian.resume()

    # Configure tool
    tool_conf = registry.get("voice_kernel_configure")
    preview = tool_conf.preview_fn({"vad_threshold": 0.65, "noise_floor_rms": 0.08, "barge_in_sensitivity": 0.85})
    assert "0.65" in preview
    assert "0.08" in preview

    conf_res = vat.voice_kernel_configure(vad_threshold=0.65, noise_floor_rms=0.08)
    assert conf_res["vad_threshold"] == 0.65
    assert conf_res["noise_floor_rms"] == 0.08

    # Simulate chunk tool
    tool_sim = registry.get("voice_kernel_simulate_chunk")
    sim_preview = tool_sim.preview_fn({"rms_energy": 0.3, "speech_prob": 0.8, "transcript_text": "status check"})
    assert "status check" in sim_preview

    sim_res = vat.voice_kernel_simulate_chunk(rms_energy=0.3, speech_prob=0.8, transcript_text="status check")
    assert sim_res["state"] in ["dispatching", "listening", "idle"]


def test_voice_action_tools_fail_closed_under_guardian_halt():
    try:
        guardian.trigger("Emergency test halt")
        assert guardian.is_halted

        with pytest.raises(PermissionError):
            vat.voice_kernel_get_status()

        with pytest.raises(PermissionError):
            vat.voice_kernel_configure(vad_threshold=0.5)

        with pytest.raises(PermissionError):
            vat.voice_kernel_simulate_chunk(rms_energy=0.3, speech_prob=0.8)

        with pytest.raises(PermissionError):
            vat.voice_kernel_abort_intent(action_id="act-test")
    finally:
        guardian.resume()
