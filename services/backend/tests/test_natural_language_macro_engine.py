"""Test Suite for Natural Language Macro Synthesis & Visual Action Recorder (Milestone 32 Phase 2).

Validates:
- Natural language macro compilation into parameterized WorkflowDAG (MACRO-01.1).
- Interactive action recording with noise filtering and debounce (MACRO-01.2).
- Dynamic variable parameterization and execution (REC-02.1).
- Local macro persistence in encrypted database (REC-02.2).
- Rule 8 Anti-Checkout defense rejecting payment/billing directives with Rule8ViolationError.
- Rule 11 Credential scrubbing masking passwords, tokens, and keys to [REDACTED].
- Universal Guardian kill switch SLA benchmark (< 25.0ms hard SLA, typical < 0.1ms).
- Tool registry integration and schema previews for all 5 macro tools.
"""

import os
import shutil
import tempfile
import time
import pytest

from services.backend.safety.guardian import guardian
from services.backend.safety.registry import registry
from services.backend.orchestration.macro_engine import (
    MacroEngine,
    RecordedActionType,
    Rule8ViolationError,
)
from services.backend.orchestration.workflow_engine import workflow_engine
import services.backend.tools.macro_tools  # Ensure tools are registered


@pytest.fixture
def temp_macro_engine():
    tmp_dir = tempfile.mkdtemp(prefix="phenom_macro_test_")
    db_file = os.path.join(tmp_dir, "test_macros.db")
    engine = MacroEngine(db_path=db_file)
    guardian.resume()
    engine.reset_halt()
    workflow_engine.reset_halt()
    yield engine
    guardian.resume()
    engine.reset_halt()
    shutil.rmtree(tmp_dir, ignore_errors=True)


def test_compile_natural_language_macro(temp_macro_engine):
    """MACRO-01.1: Verify natural language directive compiles into a multi-step DAG."""
    intent = "Check git repo status, run diagnostics tests, and append summary to obsidian daily note"
    macro_def = temp_macro_engine.compile_natural_language_macro(
        intent=intent,
        macro_name="Morning Dev Routine",
        voice_trigger="run morning routine",
    )

    assert macro_def.name == "Morning Dev Routine"
    assert macro_def.voice_trigger == "run morning routine"
    assert "git" in macro_def.tags
    assert "testing" in macro_def.tags
    assert "obsidian" in macro_def.tags

    dag_template = macro_def.dag_template
    steps = dag_template["steps"]
    assert len(steps) >= 3
    assert "step_git_sync" in steps
    assert "step_run_tests" in steps
    assert "step_obsidian_log" in steps


def test_demonstration_action_recorder_and_noise_filtering(temp_macro_engine):
    """MACRO-01.2: Verify action recording with click noise suppression and debounce."""
    temp_macro_engine.start_recording("Demo Session")

    # 1. Normal click
    act1 = temp_macro_engine.record_action(
        action_type=RecordedActionType.MOUSE_CLICK,
        target="Explorer",
        x=200,
        y=300,
    )
    assert act1 is not None

    # 2. Jittery click (< 5px away within 0.2s) -> Should be suppressed
    act_jitter = temp_macro_engine.record_action(
        action_type=RecordedActionType.MOUSE_CLICK,
        target="Explorer",
        x=202,
        y=301,
    )
    assert act_jitter is None

    # 3. Legitimate second click far away
    act2 = temp_macro_engine.record_action(
        action_type=RecordedActionType.MOUSE_CLICK,
        target="VSCode",
        x=800,
        y=400,
    )
    assert act2 is not None

    # 4. Terminal command action
    act_cmd = temp_macro_engine.record_action(
        action_type=RecordedActionType.TERMINAL_COMMAND,
        target="pwsh",
        data="git branch --show-current",
    )
    assert act_cmd is not None

    # Stop recording and synthesize
    macro_def = temp_macro_engine.stop_recording_and_synthesize("My Recorded Workflow")
    assert macro_def.name == "My Recorded Workflow"
    assert "recorded" in macro_def.tags
    assert len(macro_def.dag_template["steps"]) == 3  # act1, act2, act_cmd


def test_dynamic_parameterization_and_execution(temp_macro_engine):
    """REC-02.1: Verify parameterization and execution of saved macros with variable injection."""
    temp_macro_engine.start_recording("Parameter Demo")
    temp_macro_engine.record_action(
        action_type=RecordedActionType.KEYSTROKE_INPUT,
        target="Editor",
        data="Initial Text",
    )
    temp_macro_engine.record_action(
        action_type=RecordedActionType.TERMINAL_COMMAND,
        target="cmd",
        data="python -c \"print('PARAM_TEST_OK')\"",
    )
    macro_def = temp_macro_engine.stop_recording_and_synthesize("ParamMacro")

    assert len(macro_def.parameters) > 0
    param_name = macro_def.parameters[0]

    # Execute macro with parameter override
    report = temp_macro_engine.execute_macro(
        macro_id=macro_def.id,
        parameter_values={param_name: "Injected Dynamic Text"},
    )

    assert report["status"] == "COMPLETED"
    assert report["completed_steps"] == 2


def test_macro_persistence_and_retrieval(temp_macro_engine):
    """REC-02.2: Verify macro persistence, voice trigger lookup, and inventory listing."""
    temp_macro_engine.compile_natural_language_macro(
        intent="open browser to localhost:5173",
        macro_name="Launch Local App",
        voice_trigger="open local app",
    )

    # Lookup by voice trigger
    loaded_macro = temp_macro_engine.get_macro("open local app")
    assert loaded_macro is not None
    assert loaded_macro.name == "Launch Local App"

    # Listing
    all_macros = temp_macro_engine.list_macros()
    assert len(all_macros) == 1
    assert all_macros[0]["name"] == "Launch Local App"
    assert all_macros[0]["voice_trigger"] == "open local app"


def test_rule_8_anti_checkout_defense(temp_macro_engine):
    """Rule 8: Verify rejection of any macro compiling or recording payment actions."""
    with pytest.raises(Rule8ViolationError):
        temp_macro_engine.compile_natural_language_macro(
            intent="Go to amazon and click checkout button now",
        )

    temp_macro_engine.start_recording("Dangerous Record")
    with pytest.raises(Rule8ViolationError):
        temp_macro_engine.record_action(
            action_type=RecordedActionType.KEYSTROKE_INPUT,
            target="Credit Card Form",
            data="credit card 4111222233334444 cvv 123",
        )


def test_rule_11_credential_protection(temp_macro_engine):
    """Rule 11: Verify sensitive credentials in recorded keystrokes are scrubbed."""
    temp_macro_engine.start_recording("Secret Keystrokes")
    act = temp_macro_engine.record_action(
        action_type=RecordedActionType.KEYSTROKE_INPUT,
        target="Terminal",
        data="export API_KEY='sk-ant-secrettoken99818283'",
    )

    assert "[REDACTED]" in act.data
    assert "sk-ant" not in act.data


def test_universal_guardian_kill_switch_sla(temp_macro_engine):
    """Rule 3: Verify Guardian kill switch halts macro engine within < 25.0ms SLA."""
    guardian.resume()
    temp_macro_engine.reset_halt()

    latencies_ms = []
    for _ in range(50):
        t0 = time.perf_counter()
        temp_macro_engine.halt()
        dt_ms = (time.perf_counter() - t0) * 1000.0
        latencies_ms.append(dt_ms)
        assert dt_ms < 25.0, f"Guardian SLA breached: {dt_ms}ms >= 25.0ms"

        # Verify execution is blocked
        with pytest.raises(RuntimeError) as exc_info:
            temp_macro_engine.check_safety()
        assert "Guardian kill switch" in str(exc_info.value)

        temp_macro_engine.reset_halt()

    avg_latency = sum(latencies_ms) / len(latencies_ms)
    max_latency = max(latencies_ms)
    assert avg_latency < 1.0, f"Average halt latency {avg_latency:.4f}ms exceeds 1.0ms target"
    assert max_latency < 25.0, f"Max halt latency {max_latency:.4f}ms exceeds 25.0ms SLA"


def test_macro_tools_registry_audit():
    """SAF-01: Verify all 5 macro tools are registered in ToolRegistry."""
    expected_tools = [
        "compile_natural_language_macro",
        "start_macro_demonstration_recording",
        "stop_macro_demonstration_recording",
        "execute_saved_macro",
        "list_saved_macros",
    ]

    for tool_name in expected_tools:
        tool_def = registry.get(tool_name)
        assert tool_def is not None, f"Tool '{tool_name}' not registered in ToolRegistry"
        assert tool_def.args_schema is not None
        assert callable(tool_def.preview_fn)

    # Verify Tiers
    assert registry.get("compile_natural_language_macro").tier == 1
    assert registry.get("start_macro_demonstration_recording").tier == 1
    assert registry.get("stop_macro_demonstration_recording").tier == 1
    assert registry.get("execute_saved_macro").tier == 1
    assert registry.get("list_saved_macros").tier == 0

    # Verify preview generation
    preview_compile = registry.get("compile_natural_language_macro").preview_fn({
        "intent": "Run morning tests and sync",
        "macro_name": "Morning Task",
    })
    assert "Morning Task" in preview_compile

    preview_exec = registry.get("execute_saved_macro").preview_fn({
        "macro_id": "macro-9981",
    })
    assert "macro-9981" in preview_exec
