"""Test Suite for Cross-Application Workflow Orchestration (Milestone 32 Phase 1).

Validates:
- Multi-step cross-application workflow DAG creation and topological execution (FLOW-01.1).
- State verification checkpoints (pre-check, post-check, exit code, text match, file existence) (FLOW-01.2).
- Dynamic variable piping via {{step_id.output}} and shared variable store (CHAIN-02.1).
- Non-destructive compensatory step rollback on failure (CHAIN-02.2).
- Rule 8 Anti-Checkout defense rejecting payment/billing directives with Rule8ViolationError.
- Rule 11 Credential scrubbing masking secrets to [REDACTED].
- Universal Guardian kill switch SLA benchmark (< 25.0ms hard SLA, typical < 0.1ms).
- Tool registry integration and schema previews for all 4 tools.
"""

import os
import shutil
import tempfile
import time
import pytest

from services.backend.safety.guardian import guardian
from services.backend.safety.registry import registry
from services.backend.orchestration.workflow_engine import (
    WorkflowEngine,
    WorkflowStep,
    StepActionType,
    StepStatus,
    WorkflowStatus,
    StepVerification,
    VerificationType,
    Rule8ViolationError,
)
import services.backend.tools.workflow_tools  # Ensure tools are registered


@pytest.fixture
def test_engine():
    engine = WorkflowEngine()
    guardian.resume()
    engine.reset_halt()
    yield engine
    guardian.resume()
    engine.reset_halt()


@pytest.fixture
def temp_workspace():
    tmp_dir = tempfile.mkdtemp(prefix="phenom_wf_test_")
    yield tmp_dir
    shutil.rmtree(tmp_dir, ignore_errors=True)


def test_create_cross_app_workflow(test_engine):
    """FLOW-01.1: Verify creation and staging of a cross-app workflow DAG."""
    step1 = WorkflowStep(
        id="step_terminal",
        name="Check Local Repo Status",
        action_type=StepActionType.SHELL_COMMAND,
        target_app="terminal",
        payload={"command": "python -c \"print('REPO_OK')\""},
    )
    step2 = WorkflowStep(
        id="step_obsidian",
        name="Log Daily Note",
        action_type=StepActionType.OBSIDIAN_NOTE,
        target_app="obsidian",
        payload={"title": "Daily_Audit", "content": "Repository status verified."},
        dependencies=["step_terminal"],
    )

    dag = test_engine.create_workflow(
        name="Morning Repo Audit",
        description="Check repo status and append to Obsidian",
        steps=[step1, step2],
        initial_variables={"env": "local_dev"},
    )

    assert dag.id.startswith("wf-")
    assert dag.name == "Morning Repo Audit"
    assert dag.status == WorkflowStatus.CREATED
    assert len(dag.steps) == 2
    assert dag.variables["env"] == "local_dev"
    assert "step_terminal" in dag.steps
    assert "step_obsidian" in dag.steps


def test_chained_workflow_step_execution_and_variable_piping(test_engine, temp_workspace):
    """CHAIN-02.1: Verify step-by-step execution and context variable piping."""
    out_file = os.path.join(temp_workspace, "pipeline_result.txt")

    step1 = WorkflowStep(
        id="compute_token",
        name="Compute Session Hash",
        action_type=StepActionType.SHELL_COMMAND,
        payload={"command": "python -c \"print('SESSION_HASH_9981')\""},
    )
    step2 = WorkflowStep(
        id="write_session_file",
        name="Write Result to Disk",
        action_type=StepActionType.FILE_OPERATION,
        payload={
            "operation": "WRITE",
            "path": out_file,
            "content": "Result: {{compute_token.output.stdout}}",
        },
        dependencies=["compute_token"],
    )

    dag = test_engine.create_workflow(
        name="Chained Data Pipeline",
        description="Compute hash and write to file with variable interpolation",
        steps=[step1, step2],
    )

    report = test_engine.execute_workflow(dag.id)

    assert report.status == WorkflowStatus.COMPLETED
    assert report.completed_steps == 2
    assert report.failed_steps == 0
    assert os.path.exists(out_file)

    with open(out_file, "r", encoding="utf-8") as f:
        content = f.read()
    assert "SESSION_HASH_9981" in content


def test_checkpoint_verification_success_and_failure(test_engine, temp_workspace):
    """FLOW-01.2: Verify state verification checkpoints (pre-check and post-check)."""
    valid_file = os.path.join(temp_workspace, "existing.txt")
    with open(valid_file, "w", encoding="utf-8") as f:
        f.write("VALID_PAYLOAD")

    # 1. Step with passing pre-check and post-check
    step_pass = WorkflowStep(
        id="verified_step",
        name="Verified File Check",
        action_type=StepActionType.SHELL_COMMAND,
        payload={"command": "python -c \"print('VERIFY_PASS')\""},
        pre_check=StepVerification(
            verification_type=VerificationType.FILE_EXISTS,
            target=valid_file,
        ),
        post_check=StepVerification(
            verification_type=VerificationType.TEXT_CONTAINS,
            target="VERIFY_PASS",
        ),
    )

    dag = test_engine.create_workflow(
        name="Verified Workflow",
        description="Step with valid checkpoints",
        steps=[step_pass],
    )

    report = test_engine.execute_workflow(dag.id)
    assert report.status == WorkflowStatus.COMPLETED
    assert report.completed_steps == 1

    # 2. Step with failing post-check
    step_fail = WorkflowStep(
        id="failing_post_check_step",
        name="Failing Step",
        action_type=StepActionType.SHELL_COMMAND,
        payload={"command": "python -c \"print('ACTUAL_OUTPUT')\""},
        post_check=StepVerification(
            verification_type=VerificationType.TEXT_CONTAINS,
            target="EXPECTED_NON_EXISTENT_STRING",
        ),
    )

    dag_fail = test_engine.create_workflow(
        name="Failing Checkpoint Workflow",
        description="Step with failing post-check",
        steps=[step_fail],
    )

    report_fail = test_engine.execute_workflow(dag_fail.id, auto_rollback_on_failure=False)
    assert report_fail.status == WorkflowStatus.FAILED
    assert report_fail.failed_steps == 1
    assert "Post-check failed" in dag_fail.steps["failing_post_check_step"].error


def test_compensatory_rollback_execution(test_engine, temp_workspace):
    """CHAIN-02.2: Verify compensatory rollback restores previous state on step failure."""
    file_to_mutate = os.path.join(temp_workspace, "mutable_config.json")
    with open(file_to_mutate, "w", encoding="utf-8") as f:
        f.write("ORIGINAL_CONTENT")

    step1 = WorkflowStep(
        id="mutate_config",
        name="Mutate Config File",
        action_type=StepActionType.FILE_OPERATION,
        payload={"operation": "WRITE", "path": file_to_mutate, "content": "NEW_MUTATED_CONTENT"},
        rollback_payload={
            "action_type": "FILE_RESTORE",
            "path": file_to_mutate,
            "original_content": "ORIGINAL_CONTENT",
        },
    )

    step2 = WorkflowStep(
        id="failing_step",
        name="Failing Dependent Step",
        action_type=StepActionType.SHELL_COMMAND,
        payload={"command": "python -c \"import sys; sys.exit(42)\""},
        post_check=StepVerification(
            verification_type=VerificationType.EXIT_CODE_ZERO,
            target="returncode",
        ),
        dependencies=["mutate_config"],
    )

    dag = test_engine.create_workflow(
        name="Rollback Workflow",
        description="Workflow with auto-rollback on downstream failure",
        steps=[step1, step2],
    )

    report = test_engine.execute_workflow(dag.id, auto_rollback_on_failure=True)

    assert report.status == WorkflowStatus.ROLLED_BACK
    assert dag.steps["mutate_config"].status == StepStatus.ROLLED_BACK

    # Verify content was restored by compensatory rollback
    with open(file_to_mutate, "r", encoding="utf-8") as f:
        restored_content = f.read()
    assert restored_content == "ORIGINAL_CONTENT"


def test_rule_8_anti_checkout_defense(test_engine):
    """Rule 8: Verify rejection of any workflow with payment or checkout directives."""
    with pytest.raises(Rule8ViolationError):
        test_engine.create_workflow(
            name="E-Commerce Checkout Workflow",
            description="Automate Amazon checkout and purchase",
            steps=[],
        )

    with pytest.raises(Rule8ViolationError):
        test_engine.create_workflow(
            name="Normal Workflow",
            description="Normal workflow",
            steps=[
                WorkflowStep(
                    id="step_pay",
                    name="Enter Credit Card Number",
                    action_type=StepActionType.SHELL_COMMAND,
                    payload={"command": "curl https://api.stripe.com/v1/charges"},
                )
            ],
        )


def test_rule_11_credential_protection(test_engine):
    """Rule 11: Verify sensitive credentials and tokens are scrubbed to [REDACTED]."""
    dag = test_engine.create_workflow(
        name="Secret Workflow",
        description="Safe processing",
        steps=[
            WorkflowStep(
                id="step_auth",
                name="Configure Bearer Token",
                action_type=StepActionType.CUSTOM_TOOL,
                payload={"api_key": "sk-proj-supersecret1234567890", "safe_param": "hello"},
            )
        ],
        initial_variables={"password": "UltraSecretPassword123", "region": "us-east-1"},
    )

    assert dag.variables["password"] == "[REDACTED]"
    assert dag.variables["region"] == "us-east-1"
    assert dag.steps["step_auth"].payload["api_key"] == "[REDACTED]"
    assert dag.steps["step_auth"].payload["safe_param"] == "hello"


def test_universal_guardian_kill_switch_sla(test_engine):
    """Rule 3: Verify Guardian kill switch halts workflow execution within < 25.0ms SLA."""
    guardian.resume()
    test_engine.reset_halt()

    latencies_ms = []
    for _ in range(50):
        t0 = time.perf_counter()
        test_engine.halt()
        dt_ms = (time.perf_counter() - t0) * 1000.0
        latencies_ms.append(dt_ms)
        assert dt_ms < 25.0, f"Guardian SLA breached: {dt_ms}ms >= 25.0ms"

        # Verify execution is blocked
        with pytest.raises(RuntimeError) as exc_info:
            test_engine.check_safety()
        assert "Guardian kill switch" in str(exc_info.value)

        test_engine.reset_halt()

    avg_latency = sum(latencies_ms) / len(latencies_ms)
    max_latency = max(latencies_ms)
    assert avg_latency < 1.0, f"Average halt latency {avg_latency:.4f}ms exceeds 1.0ms target"
    assert max_latency < 25.0, f"Max halt latency {max_latency:.4f}ms exceeds 25.0ms SLA"


def test_workflow_tools_registry_audit():
    """SAF-01: Verify all 4 workflow tools are registered in ToolRegistry."""
    expected_tools = [
        "create_cross_app_workflow",
        "execute_workflow_step",
        "get_workflow_execution_status",
        "abort_and_rollback_workflow",
    ]

    for tool_name in expected_tools:
        tool_def = registry.get(tool_name)
        assert tool_def is not None, f"Tool '{tool_name}' not registered in ToolRegistry"
        assert tool_def.args_schema is not None
        assert callable(tool_def.preview_fn)

    # Verify Tiers
    assert registry.get("create_cross_app_workflow").tier == 1
    assert registry.get("execute_workflow_step").tier == 1
    assert registry.get("get_workflow_execution_status").tier == 0
    assert registry.get("abort_and_rollback_workflow").tier == 1

    # Verify preview generation
    preview_create = registry.get("create_cross_app_workflow").preview_fn({
        "name": "Test Pipeline",
        "steps": [{"id": "s1"}],
    })
    assert "Test Pipeline" in preview_create

    preview_abort = registry.get("abort_and_rollback_workflow").preview_fn({
        "workflow_id": "wf-1234",
    })
    assert "wf-1234" in preview_abort
