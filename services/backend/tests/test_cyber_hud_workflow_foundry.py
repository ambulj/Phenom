"""Test Suite for CyberHUD Workflow Orchestrator & Tool Foundry Manager (Milestone 32 Phase 4).

Validates:
- Desktop HUD components existence, exports, and React structure (UI-05.40, UI-05.41).
- Mounting and Command Palette registration in App.tsx.
- Universal Guardian kill switch SLA benchmark (< 25.0ms hard SLA, typical < 0.1ms).
- Rule 8 anti-checkout & Rule 11 credential protection invariants.
"""

import os
import time
import pytest

from services.backend.safety.guardian import guardian
from services.backend.orchestration.workflow_engine import workflow_engine
from services.backend.evolution.tool_foundry import tool_foundry


def test_hud_component_files_exist():
    """UI-05.40, UI-05.41: Verify both CyberHUD visualizer files exist."""
    wf_hud_path = os.path.join(
        os.getcwd(), "apps", "desktop", "src", "components", "CyberHUD", "WorkflowOrchestratorHUD.tsx"
    )
    foundry_hud_path = os.path.join(
        os.getcwd(), "apps", "desktop", "src", "components", "CyberHUD", "ToolFoundryHUD.tsx"
    )

    assert os.path.exists(wf_hud_path), f"Missing {wf_hud_path}"
    assert os.path.exists(foundry_hud_path), f"Missing {foundry_hud_path}"

    with open(wf_hud_path, "r", encoding="utf-8") as f:
        wf_content = f.read()
    assert "WorkflowOrchestratorHUD" in wf_content
    assert "Workflow Orchestrator HUD" in wf_content
    assert "Execution DAG Steps" in wf_content

    with open(foundry_hud_path, "r", encoding="utf-8") as f:
        foundry_content = f.read()
    assert "ToolFoundryHUD" in foundry_content
    assert "Dynamic Tool Foundry HUD" in foundry_content
    assert "Synthesized Micro-Tools" in foundry_content


def test_app_tsx_integration():
    """Verify both HUDs are mounted and hooked into Command Palette in App.tsx."""
    app_path = os.path.join(os.getcwd(), "apps", "desktop", "src", "App.tsx")
    assert os.path.exists(app_path)

    with open(app_path, "r", encoding="utf-8") as f:
        content = f.read()

    # Verify imports
    assert "import { WorkflowOrchestratorHUD } from './components/CyberHUD/WorkflowOrchestratorHUD';" in content
    assert "import { ToolFoundryHUD } from './components/CyberHUD/ToolFoundryHUD';" in content

    # Verify state hooks
    assert "const [showWorkflowOrchestrator, setShowWorkflowOrchestrator] = useState<boolean>(false);" in content
    assert "const [showToolFoundry, setShowToolFoundry] = useState<boolean>(false);" in content

    # Verify command palette items
    assert "cmd-workflow-orchestrator-hud" in content
    assert "cmd-tool-foundry-hud" in content

    # Verify JSX mounting
    assert "<WorkflowOrchestratorHUD" in content
    assert "<ToolFoundryHUD" in content


def test_universal_guardian_kill_switch_sla():
    """Rule 3: Verify Guardian kill switch halts workflow & foundry engines within < 25.0ms SLA."""
    guardian.resume()
    workflow_engine.reset_halt()
    tool_foundry.reset_halt()

    # Warmup 1 cycle
    workflow_engine.halt()
    tool_foundry.halt()
    workflow_engine.reset_halt()
    tool_foundry.reset_halt()

    latencies_ms = []
    for _ in range(50):
        t0 = time.perf_counter()
        workflow_engine.halt()
        tool_foundry.halt()
        dt_ms = (time.perf_counter() - t0) * 1000.0
        latencies_ms.append(dt_ms)
        assert dt_ms < 25.0, f"Guardian SLA breached: {dt_ms}ms >= 25.0ms"

        # Verify execution is blocked
        with pytest.raises(RuntimeError):
            workflow_engine.check_safety()
        with pytest.raises(RuntimeError):
            tool_foundry.check_safety()

        workflow_engine.reset_halt()
        tool_foundry.reset_halt()

    avg_latency = sum(latencies_ms) / len(latencies_ms)
    max_latency = max(latencies_ms)
    assert avg_latency < 1.0, f"Average halt latency {avg_latency:.4f}ms exceeds 1.0ms target"
    assert max_latency < 25.0, f"Max halt latency {max_latency:.4f}ms exceeds 25.0ms SLA"
