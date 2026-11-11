"""Master Safety Audit, Chaos Concurrency Battery & Release Suite (Milestone 32 Phase 5).

Validates:
- Comprehensive audit of all 15 Milestone 32 tools in ToolRegistry (SAF-01.1).
- 100-cycle Universal Synchronous Guardian Kill Switch SLA benchmark (< 25.0ms SLA, target < 1.0ms) (SAF-02.1).
- Cross-pillar 50-worker chaos concurrency stress test across workflows, macros, and tool foundry (SAF-02.2).
- Universal Rule 8 Anti-Checkout defense across all subsystems.
- Universal Rule 11 Credential Scrubbing across all variable stores and inputs.
- Rule 7 non-destructive compensatory rollback verification.
"""

from concurrent.futures import ThreadPoolExecutor
import os
import shutil
import tempfile
import time
import pytest

from services.backend.safety.guardian import guardian
from services.backend.safety.registry import registry
from services.backend.orchestration.workflow_engine import (
    workflow_engine,
    WorkflowStep,
    StepActionType,
    WorkflowStatus,
    Rule8ViolationError as WFRule8Error,
)
from services.backend.orchestration.macro_engine import (
    macro_engine,
    RecordedActionType,
    Rule8ViolationError as MacroRule8Error,
)
from services.backend.evolution.tool_foundry import (
    tool_foundry,
    ToolFoundryStatus,
    Rule8ViolationError as FoundryRule8Error,
)
import services.backend.tools.workflow_tools
import services.backend.tools.macro_tools
import services.backend.tools.tool_foundry_tools


@pytest.fixture(autouse=True)
def reset_subsystems():
    guardian.resume()
    workflow_engine.reset_halt()
    macro_engine.reset_halt()
    tool_foundry.reset_halt()
    yield
    guardian.resume()
    workflow_engine.reset_halt()
    macro_engine.reset_halt()
    tool_foundry.reset_halt()


def test_tool_registry_audit_milestone_32():
    """SAF-01.1: Verify all 15 new tools introduced in Milestone 32 are registered and audited."""
    expected_tools = {
        # Phase 1: Workflow Engine (4 tools)
        "create_cross_app_workflow": 1,
        "execute_workflow_step": 1,
        "get_workflow_execution_status": 0,
        "abort_and_rollback_workflow": 1,
        # Phase 2: Macro Engine (5 tools)
        "compile_natural_language_macro": 1,
        "start_macro_demonstration_recording": 1,
        "stop_macro_demonstration_recording": 1,
        "execute_saved_macro": 1,
        "list_saved_macros": 0,
        # Phase 3: Tool Foundry (6 tools)
        "synthesize_python_micro_tool": 1,
        "validate_tool_ast_security": 0,
        "test_micro_tool_in_sandbox": 1,
        "hot_load_synthetic_micro_tool": 1,
        "unload_synthetic_micro_tool": 1,
        "list_synthetic_micro_tools": 0,
    }

    assert len(expected_tools) == 15, "Expected exactly 15 tools across Milestone 32"

    for tool_name, expected_tier in expected_tools.items():
        tool_def = registry.get(tool_name)
        assert tool_def is not None, f"Tool '{tool_name}' missing from ToolRegistry"
        assert tool_def.tier == expected_tier, f"Tool '{tool_name}' tier {tool_def.tier} != expected {expected_tier}"
        assert tool_def.args_schema is not None, f"Tool '{tool_name}' missing args_schema"
        assert callable(tool_def.preview_fn), f"Tool '{tool_name}' preview_fn must be callable"

        # Verify preview function produces non-empty output
        dummy_args = {}
        preview_text = tool_def.preview_fn(dummy_args)
        assert isinstance(preview_text, str)
        assert len(preview_text) > 0


def test_universal_guardian_kill_switch_100_cycle_sla():
    """SAF-02.1: 100-cycle Universal Synchronous Guardian Kill Switch SLA benchmark (< 25.0ms)."""
    latencies_ms = []

    for _ in range(100):
        t0 = time.perf_counter()
        guardian.trigger("Emergency stop operator trigger")
        workflow_engine.halt()
        macro_engine.halt()
        tool_foundry.halt()
        dt_ms = (time.perf_counter() - t0) * 1000.0
        latencies_ms.append(dt_ms)

        assert dt_ms < 25.0, f"Guardian SLA breached: {dt_ms}ms >= 25.0ms"

        # Verify all engines reject execution
        with pytest.raises(RuntimeError):
            workflow_engine.check_safety()
        with pytest.raises(RuntimeError):
            macro_engine.check_safety()
        with pytest.raises(RuntimeError):
            tool_foundry.check_safety()

        guardian.resume()
        workflow_engine.reset_halt()
        macro_engine.reset_halt()
        tool_foundry.reset_halt()

    avg_latency = sum(latencies_ms) / len(latencies_ms)
    max_latency = max(latencies_ms)

    assert avg_latency < 1.0, f"Average halt latency {avg_latency:.4f}ms exceeds 1.0ms"
    assert max_latency < 25.0, f"Max halt latency {max_latency:.4f}ms exceeds 25.0ms SLA"


def test_cross_pillar_chaos_concurrency_battery():
    """SAF-02.2: 50 concurrent worker threads stress-testing all Milestone 32 pillars."""
    num_workers = 50
    results = []

    def chaos_worker(worker_id: int):
        try:
            pillar = worker_id % 3
            if pillar == 0:
                # Workflow DAG execution
                step = WorkflowStep(
                    id=f"step_{worker_id}",
                    name=f"Worker {worker_id} Task",
                    action_type=StepActionType.SHELL_COMMAND,
                    payload={"command": f"echo 'WORKER_{worker_id}'"},
                )
                dag = workflow_engine.create_workflow(
                    name=f"Workflow_{worker_id}",
                    description="Concurrent chaos test",
                    steps=[step],
                )
                report = workflow_engine.execute_workflow(dag.id)
                return ("WORKFLOW", report.status == WorkflowStatus.COMPLETED)

            elif pillar == 1:
                # Natural language macro compilation
                macro_def = macro_engine.compile_natural_language_macro(
                    intent=f"Worker {worker_id} check git and append to obsidian",
                    macro_name=f"Macro_{worker_id}",
                )
                return ("MACRO", len(macro_def.dag_template["steps"]) > 0)

            else:
                # Python micro-tool AST validation and sandbox
                code = f"""
def worker_{worker_id}_calc(x: int) -> int:
    return x * 2 + {worker_id}
"""
                ast_rep = tool_foundry.validate_ast_security(code)
                return ("FOUNDRY", ast_rep.is_safe)
        except Exception as ex:
            return ("ERROR", str(ex))

    t0 = time.perf_counter()
    with ThreadPoolExecutor(max_workers=num_workers) as executor:
        futures = [executor.submit(chaos_worker, i) for i in range(num_workers)]
        for f in futures:
            results.append(f.result())
    elapsed = time.perf_counter() - t0

    assert elapsed < 5.0, f"Chaos concurrency test took {elapsed:.2f}s (exceeds 5.0s ceiling)"
    errors = [r for r in results if r[0] == "ERROR" or r[1] is not True]
    assert len(errors) == 0, f"Chaos concurrency test had failures: {errors}"


def test_rule_8_anti_checkout_universal_matrix():
    """Rule 8: Verify universal anti-checkout protection across all Milestone 32 engines."""
    # 1. Workflow Engine
    with pytest.raises(WFRule8Error):
        workflow_engine.create_workflow(
            name="Checkout Cart Now",
            description="Process credit card billing",
            steps=[],
        )

    # 2. Macro Engine
    with pytest.raises(MacroRule8Error):
        macro_engine.compile_natural_language_macro(
            intent="Open amazon and click pay now with credit card",
        )

    # 3. Tool Foundry
    with pytest.raises(FoundryRule8Error):
        tool_foundry.synthesize_tool(
            name="purchase_gateway",
            description="Execute payment and buy now",
            parameters={"amount": "float"},
            logic_body="    return {'paid': True}",
            test_assertions=[],
        )


def test_rule_11_credential_protection_universal_matrix():
    """Rule 11: Verify universal credential scrubbing across all variable stores and inputs."""
    # 1. Workflow Engine
    wf_scrubbed = workflow_engine.scrub_dict({
        "safe_param": "hello",
        "api_key": "sk-proj-supersecret9981",
        "password": "UltraSecretPassword123",
    })
    assert wf_scrubbed["api_key"] == "[REDACTED]"
    assert wf_scrubbed["password"] == "[REDACTED]"
    assert wf_scrubbed["safe_param"] == "hello"

    # 2. Macro Engine
    macro_scrubbed, count = macro_engine.scrub_credentials("token: 'bearer-xyz-1234567890'")
    assert "[REDACTED]" in macro_scrubbed
    assert count > 0

    # 3. Tool Foundry
    foundry_scrubbed = tool_foundry.scrub_dict({
        "auth_token": "secret-auth-998877",
        "nested": {"secret": "top-secret-val"},
    })
    assert foundry_scrubbed["auth_token"] == "[REDACTED]"
    assert foundry_scrubbed["nested"]["secret"] == "[REDACTED]"


def test_cross_pillar_rule_7_compensatory_rollback():
    """Rule 7: Verify non-destructive compensatory rollback restores files safely."""
    tmp_dir = tempfile.mkdtemp(prefix="phenom_rollback_test_")
    test_file = os.path.join(tmp_dir, "config.json")
    try:
        with open(test_file, "w", encoding="utf-8") as f:
            f.write("ORIGINAL_BACKUP_CONTENT")

        step1 = WorkflowStep(
            id="mutate_step",
            name="Modify Config",
            action_type=StepActionType.FILE_OPERATION,
            payload={"operation": "WRITE", "path": test_file, "content": "MUTATED_CONTENT"},
            rollback_payload={
                "action_type": "FILE_RESTORE",
                "path": test_file,
                "original_content": "ORIGINAL_BACKUP_CONTENT",
            },
        )
        step2 = WorkflowStep(
            id="broken_step",
            name="Crash Step",
            action_type=StepActionType.SHELL_COMMAND,
            payload={"command": "python -c \"import sys; sys.exit(1)\""},
            dependencies=["mutate_step"],
        )

        dag = workflow_engine.create_workflow(
            name="Rollback Test DAG",
            description="Tests safe rollback",
            steps=[step1, step2],
        )

        report = workflow_engine.execute_workflow(dag.id, auto_rollback_on_failure=True)
        assert report.status == WorkflowStatus.ROLLED_BACK

        # Check content restored
        with open(test_file, "r", encoding="utf-8") as f:
            restored = f.read()
        assert restored == "ORIGINAL_BACKUP_CONTENT"

    finally:
        shutil.rmtree(tmp_dir, ignore_errors=True)
