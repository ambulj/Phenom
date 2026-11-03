"""
Milestone 9.0 Full End-to-End Multi-Component Simulation.
Chains the complete ambient co-pilot lifecycle:
1. Screen Vision (VIS-01): ambient_copilot captures workspace window and detects build error context.
2. Adaptive Governor (GOV-01): monitors system metrics and throttles/resumes background capture loops.
3. Conversational Voice (VOX-01): streaming_voice_engine generates witty British spoken alert.
4. Personal Knowledge Graph (GRA-01): hybrid_graph_rag_engine retrieves multi-domain code/notes context.
5. Sovereign Mission (MIS-01): unattended_mission_runner executes self-healing test loop in isolated worktree sandbox.
6. Morning Debrief (MIS-01): morning_debrief_synthesizer updates Obsidian daily note and emits Cyber HUD payload.
7. Guardian Kill Switch (SAF-02): synchronously halts all ambient engines in < 25ms SLA.
"""

import os
import shutil
import subprocess
import sys
import tempfile
import time
import pytest

from services.backend.main import on_guardian_state_change
from services.backend.memory.graph_rag import graph_rag_engine
from services.backend.memory.multi_source_graph import multi_source_graph
from services.backend.missions.morning_debrief import (
    DEBRIEF_SECTION_HEADER,
    morning_debrief_synthesizer,
)
from services.backend.missions.unattended_runner import (
    UnattendedMissionRunner,
    _clear_readonly,
    unattended_mission_runner,
)
from services.backend.safety.guardian import guardian
from services.backend.schemas.graph_rag import GraphEdge, GraphNode
from services.backend.schemas.missions import (
    MissionExecutionPlan,
    MissionStatus,
)
from services.backend.system.resource_governor import resource_governor
from services.backend.vision.ambient_copilot import ambient_copilot
from services.backend.voice.streaming_engine import streaming_voice_engine


@pytest.fixture
def sim_environment():
    """Sets up an isolated git repository and Obsidian vault for end-to-end simulation."""
    tmp_root = tempfile.mkdtemp(prefix="phenom_m9_sim_")
    repo_dir = os.path.join(tmp_root, "sim_repo")
    os.makedirs(repo_dir, exist_ok=True)

    # Initialize git repo
    subprocess.run(["git", "init"], cwd=repo_dir, check=True, capture_output=True)
    subprocess.run(["git", "config", "user.name", "PhenomSim"], cwd=repo_dir, check=True, capture_output=True)
    subprocess.run(["git", "config", "user.email", "sim@phenom.ai"], cwd=repo_dir, check=True, capture_output=True)

    # Initial code file with bug
    calc_path = os.path.join(repo_dir, "calculator.py")
    with open(calc_path, "w", encoding="utf-8") as f:
        f.write("def calculate_total():\n    return False\n")

    test_path = os.path.join(repo_dir, "test_calculator.py")
    with open(test_path, "w", encoding="utf-8") as f:
        f.write("from calculator import calculate_total\ndef test_total():\n    assert calculate_total() is True\n")

    subprocess.run(["git", "add", "."], cwd=repo_dir, check=True, capture_output=True)
    subprocess.run(["git", "commit", "-m", "Initial sim commit"], cwd=repo_dir, check=True, capture_output=True)

    # Initialize vault
    vault_dir = os.path.join(tmp_root, "vault")
    daily_notes_dir = os.path.join(vault_dir, "Daily Notes")
    os.makedirs(daily_notes_dir, exist_ok=True)

    today_str = time.strftime("%Y-%m-%d")
    initial_daily_note = (
        f"# Daily Note: {today_str}\n\n"
        "## 📝 Developer Notes\n"
        "- [ ] Solve calculator regression\n"
        "- [ ] Ship Milestone 9.0\n"
    )
    with open(os.path.join(daily_notes_dir, f"{today_str}.md"), "w", encoding="utf-8") as f:
        f.write(initial_daily_note)

    yield repo_dir, vault_dir, today_str

    try:
        shutil.rmtree(tmp_root, onerror=_clear_readonly)
    except Exception:
        pass


def test_milestone_9_complete_ambient_copilot_e2e_simulation(sim_environment):
    """
    Executes full continuous ambient co-pilot lifecycle across all 4 Milestone 9.0 phases:
    Screen Vision -> Adaptive Governor -> Conversational Voice -> GraphRAG -> Overnight Missions -> Morning Debrief -> Guardian SLA.
    """
    repo_path, vault_path, today_str = sim_environment

    # Ensure clean starting state
    guardian.resume()
    unattended_mission_runner.reset()
    multi_source_graph.reset()
    graph_rag_engine.reset()

    # =========================================================================
    # Step 1: Screen Vision (VIS-01) - Ambient Capture & Build Context
    # =========================================================================
    vision_state = ambient_copilot.get_context()
    assert vision_state is not None
    assert vision_state.process_name is not None or vision_state.window_title is not None

    # =========================================================================
    # Step 2: Adaptive Governor (GOV-01) - System Load Monitoring & Throttle
    # =========================================================================
    gov_state = resource_governor.get_state()
    assert gov_state is not None
    assert isinstance(gov_state.cpu_load_percent, float)
    assert isinstance(gov_state.is_throttled, bool)

    # =========================================================================
    # Step 3: Conversational Voice (VOX-01) - Speech Generation
    # =========================================================================
    test_utterance = "Good evening, sir. I noticed a test failure in calculator. Shall I resolve it overnight?"
    voice_res = streaming_voice_engine.speak_utterance(test_utterance)
    assert voice_res is not None
    assert "formatted_text" in voice_res
    assert streaming_voice_engine.is_halted is False

    # =========================================================================
    # Step 4: Personal Knowledge Graph (GRA-01) - Cross-Domain Retrieval
    # =========================================================================
    # Seed knowledge graph with code symbol and daily note concept
    node_code = GraphNode(
        node_id="code://sim_repo/calculator.py:calculate_total",
        domain="code",
        title="calculate_total",
        entity_type="function",
        summary="Calculates order total; currently returns boolean flag.",
    )
    node_vault = GraphNode(
        node_id=f"vault://Daily Notes/{today_str}",
        domain="vault",
        title=f"Daily Note {today_str}",
        entity_type="note",
        summary="Contains task to solve calculator regression.",
    )
    multi_source_graph.add_node(node_code)
    multi_source_graph.add_node(node_vault)
    multi_source_graph.add_edge(GraphEdge(
        source_id=node_vault.node_id,
        target_id=node_code.node_id,
        relation="references",
        weight=0.9,
    ))

    query_result = graph_rag_engine.query("calculate total regression", hops=1, top_k=3)
    assert len(query_result.seed_nodes) > 0 or len(query_result.citations) > 0
    assert any("calculate_total" in c for c in query_result.citations)

    # =========================================================================
    # Step 5: Sovereign Unattended Overnight Mission (MIS-01) - Worktree Self-Healing
    # =========================================================================
    runner = UnattendedMissionRunner()
    mission_id = "sim_mission_001"
    plan = MissionExecutionPlan(
        mission_id=mission_id,
        title="Heal calculator total test",
        prompt="Fix calculate_total to return True",
        repo_path=repo_path,
        test_command="pytest test_calculator.py",
        max_iterations=3,
        timeout_seconds=30,
    )

    mission_res = runner.run_mission(plan)
    assert mission_res.status == MissionStatus.COMPLETED
    assert mission_res.tests_fixed >= 1
    assert mission_res.tests_passed >= 1
    assert len(mission_res.iterations) == 2  # Iteration 1 failed, iteration 2 passed

    # Primary working directory remains pristine
    with open(os.path.join(repo_path, "calculator.py"), "r", encoding="utf-8") as f:
        assert "return False" in f.read()

    # Clean up sandbox worktree
    runner.cleanup_sandbox(mission_id, repo_path)

    # =========================================================================
    # Step 6: Morning Debrief Synthesizer & Obsidian Sync (MIS-01)
    # =========================================================================
    # Configure debrief synthesizer with our runner and vault
    morning_debrief_synthesizer._runner = runner
    morning_debrief_synthesizer._custom_vault_path = vault_path

    # Merge into Obsidian Daily Note
    updated_note = morning_debrief_synthesizer.sync_to_obsidian_daily_note(date_str=today_str)
    assert DEBRIEF_SECTION_HEADER in updated_note
    assert "Heal calculator total test" in updated_note
    assert "## 📝 Developer Notes" in updated_note  # User's notes preserved!

    # Verify Cyber HUD debrief payload
    hud_payload = morning_debrief_synthesizer.build_debrief_payload(date_str=today_str)
    assert hud_payload["type"] == "mission.morning_debrief"
    assert hud_payload["payload"]["celebrate"] is True
    assert hud_payload["payload"]["summary"]["successful_missions"] == 1
    assert hud_payload["payload"]["summary"]["tests_fixed"] >= 1

    # =========================================================================
    # Step 7: Sub-25ms Synchronous Guardian Kill Switch SLA (SAF-02)
    # =========================================================================
    t0 = time.perf_counter()
    guardian.trigger("emergency_e2e_killswitch")
    elapsed_ms = (time.perf_counter() - t0) * 1000.0

    assert elapsed_ms < 25.0, f"Guardian halt SLA violated: {elapsed_ms:.2f}ms"
    assert multi_source_graph.is_halted is True
    assert graph_rag_engine.is_halted is True
    assert unattended_mission_runner.is_halted is True
    assert streaming_voice_engine.is_halted is True

    # Resumption
    guardian.resume()
    assert multi_source_graph.is_halted is False
    assert unattended_mission_runner.is_halted is False
    assert streaming_voice_engine.is_halted is False
