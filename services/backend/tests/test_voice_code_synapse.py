"""
Tests for Cross-Modal Conversational Workspace Synapse & Real-Time Code-Voice Co-Editing.
Part of Phenom 23.0 Sovereign Neural Evolution (SYN-01, VOX-06, SAF-01, SAF-02).
"""

import time
import pytest
from typing import Dict, Any

from services.backend.synapse.voice_code_synapse import (
    VoiceCodeSynapse,
    ASTMutationRequest,
    ASTMutationResult,
    voice_code_synapse,
)
from services.backend.synapse.acoustic_earcon_manager import (
    AcousticEarconManager,
    acoustic_earcon_manager,
)
from services.backend.safety.guardian import guardian
from services.backend.safety.registry import registry
from services.backend.automation.gui_controller import Rule8ViolationError
import services.backend.tools.voice_code_synapse_tools as synapse_tools


@pytest.fixture(autouse=True)
def reset_guardian():
    guardian.resume()
    yield
    guardian.resume()


def test_spoken_ast_rename_param_mutation():
    """Verify spoken rename_param modifies parameter and generates clean unified diff."""
    synapse = VoiceCodeSynapse()
    src = "def fetch_api(timeout_ms):\n    return timeout_ms * 2\n"

    res = synapse.apply_spoken_mutation(
        file_path="services/api.py",
        target_symbol="fetch_api",
        mutation_type="rename_param",
        parameters={"old_param": "timeout_ms", "new_param": "timeout_seconds"},
        source_code=src,
    )

    assert res.status == "applied"
    assert "timeout_seconds" in res.modified_source
    assert "timeout_ms" not in res.modified_source
    assert "-def fetch_api(timeout_ms):" in res.unified_diff
    assert "+def fetch_api(timeout_seconds):" in res.unified_diff
    assert res.acoustic_cue == "ast_success"


def test_spoken_ast_add_type_hint_mutation():
    """Verify adding type hint annotates symbol and preserves valid AST."""
    synapse = VoiceCodeSynapse()
    src = "def process_data(val):\n    return val\n"

    res = synapse.apply_spoken_mutation(
        file_path="services/core.py",
        target_symbol="process_data",
        mutation_type="add_type_hint",
        parameters={"param": "val", "type_hint": "int"},
        source_code=src,
    )

    assert res.status == "applied"
    assert "val: int" in res.modified_source
    assert "+def process_data(val: int):" in res.unified_diff


def test_spoken_ast_wrap_try_except_mutation():
    """Verify wrap_try_except encloses body safely."""
    synapse = VoiceCodeSynapse()
    src = "def risky_task():\n    return 100 / 0\n"

    res = synapse.apply_spoken_mutation(
        file_path="services/calc.py",
        target_symbol="risky_task",
        mutation_type="wrap_try_except",
        parameters={},
        source_code=src,
    )

    assert res.status == "applied"
    assert "try:" in res.modified_source
    assert "except Exception as e:" in res.modified_source


def test_ast_syntax_error_detection_and_earcon():
    """Verify syntax error in mutation is detected and triggers syntax_error earcon."""
    synapse = VoiceCodeSynapse()
    src = "def broken():\n    return 'valid'\n"

    # Invalid Python syntax injection
    res = synapse.apply_spoken_mutation(
        file_path="services/err.py",
        target_symbol="broken",
        mutation_type="replace_return",
        parameters={"new_return": "def illegal_syntax((("},
        source_code=src,
    )

    assert res.status == "error"
    assert "AST Syntax Parse Failure" in res.error
    assert res.acoustic_cue == "syntax_error"


def test_transaction_rollback_rule_7():
    """Verify Rule 7: rolling back an AST mutation restores previous buffer content."""
    synapse = VoiceCodeSynapse()
    src = "def state_v1():\n    return 1\n"
    synapse.set_buffer_content("services/state.py", src)

    res = synapse.apply_spoken_mutation(
        file_path="services/state.py",
        target_symbol="state_v1",
        mutation_type="replace_return",
        parameters={"new_return": "2"},
    )
    assert res.status == "applied"
    assert synapse.get_buffer_content("services/state.py") != src

    # Rollback transaction
    rolled_back = synapse.rollback_transaction(res.transaction_id)
    assert rolled_back is True
    assert synapse.get_buffer_content("services/state.py") == src


def test_in_memory_procedural_acoustic_earcons():
    """Verify Rule 4: PCM earcons are generated in RAM with zero disk file creation."""
    earcon = AcousticEarconManager()

    for cue in ["ast_success", "syntax_error", "test_passed", "guardian_halt"]:
        pcm = earcon.generate_earcon_pcm(cue)
        assert isinstance(pcm, bytes)
        assert len(pcm) > 0
        assert len(pcm) % 2 == 0  # 16-bit aligned


def test_rule_8_anti_checkout_enforcement():
    """Rule 8: Attempting to mutate payment or checkout logic must raise Rule8ViolationError."""
    synapse = VoiceCodeSynapse()
    with pytest.raises(Rule8ViolationError):
        synapse.apply_spoken_mutation(
            file_path="services/pay.py",
            target_symbol="execute_checkout_payment",
            mutation_type="replace_return",
            parameters={"new_return": "True"},
        )


def test_guardian_kill_switch_sla_halt():
    """Guardian trigger must synchronously interrupt AST code mutation in < 25.0ms SLA."""
    guardian.trigger()
    t0 = time.perf_counter()
    with pytest.raises(PermissionError, match="Guardian kill switch"):
        voice_code_synapse.apply_spoken_mutation(
            file_path="services/test.py",
            target_symbol="test_fn",
            mutation_type="replace_return",
            parameters={},
        )
    latency_ms = (time.perf_counter() - t0) * 1000.0

    assert latency_ms < 25.0, f"Guardian SLA exceeded: {latency_ms:.4f}ms >= 25.0ms"


def test_tool_registry_and_previews():
    """Verify tool registration and preview generator functions in ToolRegistry."""
    tool_names = [
        "apply_voice_code_mutation",
        "play_acoustic_earcon",
        "get_synapse_buffer_state",
    ]
    for name in tool_names:
        tool = registry.get(name)
        assert tool is not None, f"Tool {name} is not registered in ToolRegistry"
        assert callable(tool.handler_fn)

    # Preview generators
    preview_mutation = registry.get("apply_voice_code_mutation").generate_preview({
        "file_path": "main.py",
        "target_symbol": "init",
        "mutation_type": "rename_param",
    })
    assert "Apply spoken AST mutation" in preview_mutation

    preview_earcon = registry.get("play_acoustic_earcon").generate_preview({"cue_type": "ast_success"})
    assert "ast_success" in preview_earcon
