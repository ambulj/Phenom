"""
Phenom Autonomous Workflow DAG Planner
Compiles high-level user intents into an ordered Directed Acyclic Graph (DAG) with:
- Per-step tool parameters & dependencies
- Strict safety risk tier assignments (Tier 0, 1, 2)
- Explicit runtime pre-conditions (window title, process, file presence)
- Divergence guards for automated pause & operator notification
"""

import os
import re
import time
from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field

from services.backend.safety.registry import registry


class StepPrecondition(BaseModel):
    """Runtime environmental checks required before executing a step."""
    expected_window_title: Optional[str] = None
    expected_process_name: Optional[str] = None
    file_must_exist: Optional[str] = None
    network_required: bool = False


class WorkflowStep(BaseModel):
    """An individual atomic task inside an autonomous workflow DAG."""
    step_id: str
    title: str
    tool_name: str
    args: Dict[str, Any] = Field(default_factory=dict)
    tier: int = 0
    depends_on: List[str] = Field(default_factory=list)
    precondition: Optional[StepPrecondition] = None
    status: str = "pending"  # pending, running, completed, failed, diverged, paused
    output: Optional[Any] = None
    error: Optional[str] = None
    divergence_reason: Optional[str] = None


class WorkflowDAG(BaseModel):
    """Complete multi-step execution graph."""
    dag_id: str
    goal: str
    steps: List[WorkflowStep]
    max_tier: int = 0
    estimated_duration_s: float = 5.0
    status: str = "created"  # created, approved, executing, completed, failed, aborted, diverged
    created_at: float = Field(default_factory=time.time)
    approved_at: Optional[float] = None
    completed_at: Optional[float] = None

    def get_step(self, step_id: str) -> Optional[WorkflowStep]:
        for s in self.steps:
            if s.step_id == step_id:
                return s
        return None

    def get_executable_steps(self) -> List[WorkflowStep]:
        """Returns steps whose dependencies have all completed successfully."""
        ready = []
        completed_ids = {s.step_id for s in self.steps if s.status == "completed"}
        for s in self.steps:
            if s.status == "pending":
                if all(dep in completed_ids for dep in s.depends_on):
                    ready.append(s)
        return ready


class WorkflowDAGPlanner:
    """Compiles natural language cross-app intents into executable DAGs."""

    def plan(self, goal: str, explicit_steps: Optional[List[Dict[str, Any]]] = None) -> WorkflowDAG:
        dag_id = f"dag_{os.urandom(4).hex()}"

        if explicit_steps:
            steps: List[WorkflowStep] = []
            for idx, raw in enumerate(explicit_steps):
                s_id = raw.get("step_id", f"step_{idx+1}")
                tool = raw.get("tool_name", "read_file")
                args = raw.get("args", {})
                
                # Derive tier from registry if available
                t_def = registry.get(tool)
                tier = raw.get("tier", t_def.tier if t_def else 0)
                
                pre_dict = raw.get("precondition")
                precond = StepPrecondition(**pre_dict) if pre_dict else None
                
                step = WorkflowStep(
                    step_id=s_id,
                    title=raw.get("title", f"Step {idx+1}: {tool}"),
                    tool_name=tool,
                    args=args,
                    tier=tier,
                    depends_on=raw.get("depends_on", [f"step_{idx}"] if idx > 0 else []),
                    precondition=precond,
                )
                steps.append(step)
        else:
            steps = self._decompose_intent(goal)

        max_tier = max([s.tier for s in steps]) if steps else 0
        est_duration = sum([2.0 if s.tier == 0 else 4.0 for s in steps])

        return WorkflowDAG(
            dag_id=dag_id,
            goal=goal,
            steps=steps,
            max_tier=max_tier,
            estimated_duration_s=est_duration,
        )

    def _decompose_intent(self, goal: str) -> List[WorkflowStep]:
        """Decomposes intent string into realistic cross-application steps."""
        steps: List[WorkflowStep] = []
        lower = goal.lower()

        # Step 1: Context or Application Setup
        if any(k in lower for k in ["code", "script", "repo", "git", "file"]):
            steps.append(WorkflowStep(
                step_id="step_1",
                title="Inspect Project Workspace Context",
                tool_name="list_files",
                args={"path": "."},
                tier=0,
                depends_on=[],
                precondition=StepPrecondition(file_must_exist=".")
            ))
        elif any(k in lower for k in ["browser", "web", "search", "lookup"]):
            steps.append(WorkflowStep(
                step_id="step_1",
                title="Query Web Information",
                tool_name="search_web",
                args={"query": goal},
                tier=0,
                depends_on=[],
                precondition=StepPrecondition(network_required=True)
            ))
        else:
            steps.append(WorkflowStep(
                step_id="step_1",
                title="Verify Environment Readiness",
                tool_name="get_sensory_proximity_telemetry",
                args={},
                tier=0,
                depends_on=[],
            ))

        # Step 2: Synthesis or Processing
        if any(k in lower for k in ["write", "create", "draft", "save", "note"]):
            steps.append(WorkflowStep(
                step_id="step_2",
                title="Draft Output Artifact in Scratch Enclave",
                tool_name="write_file",
                args={"path": "vault/Scratch/workflow_output.md", "content": f"# Output for: {goal}\n\nAutomated workflow generation."},
                tier=1,
                depends_on=["step_1"],
                precondition=StepPrecondition(file_must_exist="vault")
            ))
        elif any(k in lower for k in ["test", "execute", "run", "verify"]):
            steps.append(WorkflowStep(
                step_id="step_2",
                title="Execute Validation Command",
                tool_name="execute_shell_command",
                args={"command": "python -m pytest tests/ -k test_safety"},
                tier=2,
                depends_on=["step_1"],
            ))
        else:
            steps.append(WorkflowStep(
                step_id="step_2",
                title="Synthesize Results to Episodic Knowledge Matrix",
                tool_name="synthesize_heuristic_rule",
                args={"failure_signature": "goal_orchestration", "rule_body": f"Guidance for {goal}"},
                tier=1,
                depends_on=["step_1"],
            ))

        # Step 3: Verification & Handoff
        steps.append(WorkflowStep(
            step_id="step_3",
            title="Audit Workspace State & Prepare Handoff Briefing",
            tool_name="read_file",
            args={"path": "AGENTS.md"},
            tier=0,
            depends_on=["step_2"],
        ))

        return steps


dag_planner = WorkflowDAGPlanner()
