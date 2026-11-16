"""Comprehensive Test Suite for Self-Reflective Post-Mortem & Proactive Synthesis (Milestone 49 Phase 2).

Covers:
- REFL-01: Post-mortem trace analysis, category classification, and deterministic error signatures.
- REFL-02: Executable heuristic compilation, AST syntax validation, constraint enforcement, and planner prompts.
- REFL-03: Proactive routine anticipation, workspace pre-stage plans, and crisp morning briefings (<= 60 words).
- Safety: Rule 8/11 scrubbing and Guardian kill switch SLA (< 25ms).
- ToolRegistry: Tier classification and execution of reflective tools.
"""

import os
import shutil
import tempfile
import time
import pytest

from services.backend.schemas.reflective_postmortem import (
    FailureCategory,
    FailureTrace,
    HeuristicRule,
    PostMortemAnalysis,
    ProactiveRoutine,
    SpokenMorningBriefing,
    WorkspacePreStagePlan,
)
from services.backend.safety.postmortem_engine import PostMortemEngine
from services.backend.safety.heuristic_synthesizer import HeuristicSynthesizer
from services.backend.safety.proactive_synthesizer import ProactiveSynthesizer
from services.backend.memory.temporal_graph_engine import TemporalGraphEngine
from services.backend.schemas.temporal_graph import EntityType, TemporalEntity, TemporalEpisode
from services.backend.safety.guardian import guardian
from services.backend.safety.registry import registry
from services.backend.tools.reflective_postmortem_tools import (
    handle_analyze_failure_postmortem,
    handle_generate_proactive_briefing,
    handle_synthesize_heuristic_rule,
)


@pytest.fixture
def temp_refl_env():
    temp_dir = tempfile.mkdtemp(prefix="phenom_refl_test_")
    db_path = os.path.join(temp_dir, "test_refl_graph.db")
    heuristics_dir = os.path.join(temp_dir, "heuristics")
    os.makedirs(heuristics_dir, exist_ok=True)

    engine = TemporalGraphEngine(db_path=db_path)
    pm_engine = PostMortemEngine()
    synth = HeuristicSynthesizer(heuristics_dir=heuristics_dir)
    proactive = ProactiveSynthesizer(engine=engine)

    yield {
        "temp_dir": temp_dir,
        "heuristics_dir": heuristics_dir,
        "engine": engine,
        "pm_engine": pm_engine,
        "synth": synth,
        "proactive": proactive,
    }

    shutil.rmtree(temp_dir, ignore_errors=True)


# ============================================================================
# 1. Schema & Validation Tests (REFL-01, REFL-02, REFL-03)
# ============================================================================

def test_spoken_morning_briefing_word_limit():
    valid_text = "Good morning, Sir. Systems are nominal and all 43 tests pass. I am ready."
    briefing = SpokenMorningBriefing(
        date_str="2026-11-17",
        briefing_text=valid_text,
        word_count=len(valid_text.split()),
        priorities=["Task 1"],
    )
    assert briefing.word_count <= 60

    # Test rejection when exceeding 60 words
    too_long = "word " * 65
    with pytest.raises(ValueError, match="exceeds strict 60-word"):
        SpokenMorningBriefing(
            date_str="2026-11-17",
            briefing_text=too_long,
            word_count=65,
        )


# ============================================================================
# 2. Post-Mortem Trace Analysis & Signatures (REFL-01)
# ============================================================================

def test_postmortem_analysis_classification_and_signatures(temp_refl_env):
    pm: PostMortemEngine = temp_refl_env["pm_engine"]

    # Test 1: Resource Not Found
    trace_not_found = FailureTrace(
        task_id="task_open_ide",
        tool_name="open_app",
        input_arguments={"path": "C:\\Invalid\\NonExistent.exe"},
        exception_type="FileNotFoundError",
        error_message="The system cannot find the file specified: C:\\Invalid\\NonExistent.exe",
    )
    analysis1 = pm.analyze(trace_not_found)
    assert analysis1.category == FailureCategory.RESOURCE_NOT_FOUND
    assert "open_app" in analysis1.failure_signature
    assert "existence verification" in analysis1.remediation_strategy

    # Test 2: Timeout
    trace_timeout = FailureTrace(
        task_id="task_deep_scrape",
        tool_name="crawl_page",
        input_arguments={"url": "https://example.com", "timeout": 300},
        exception_type="TimeoutError",
        error_message="Operation timed out after 300 seconds",
    )
    analysis2 = pm.analyze(trace_timeout)
    assert analysis2.category == FailureCategory.TIMEOUT
    assert "timeout" in analysis2.failure_signature
    assert "Clamp execution timeout" in analysis2.remediation_strategy

    # Test 3: Precondition Failed
    trace_precond = FailureTrace(
        task_id="task_click_btn",
        tool_name="click_desktop_element",
        input_arguments={"element_id": "btn_save"},
        exception_type="RuntimeError",
        error_message="Target window not focused; prerequisite window focus not ready",
    )
    analysis3 = pm.analyze(trace_precond)
    assert analysis3.category == FailureCategory.PRECONDITION_FAILED
    assert "window focus" in analysis3.remediation_strategy


# ============================================================================
# 3. Heuristic Synthesizer AST Validation & Enforcement (REFL-02)
# ============================================================================

def test_heuristic_synthesizer_ast_validation_and_enforcement(temp_refl_env):
    synth: HeuristicSynthesizer = temp_refl_env["synth"]

    # 1. Verify invalid AST syntax rejection
    with pytest.raises(ValueError, match="Invalid Python AST"):
        synth.register_rule(
            rule_id="bad_syntax_rule",
            tool_name="open_app",
            failure_signature="sig_bad",
            description="Bad rule syntax",
            constraint_expression="def invalid_syntax(:",
            planner_guideline="Do not use.",
        )

    # 2. Register valid rule
    valid_rule = synth.register_rule(
        rule_id="heur_clamp_timeout_01",
        tool_name="crawl_page",
        failure_signature="sig_timeout",
        description="Clamp timeout to 60s max",
        constraint_expression="args.get('timeout', 30.0) <= 60.0",
        planner_guideline="Always keep crawler timeout at or under 60 seconds.",
    )
    assert valid_rule.is_active is True

    # 3. Verify rule persistence
    fpath = os.path.join(temp_refl_env["heuristics_dir"], "heur_clamp_timeout_01.json")
    assert os.path.exists(fpath)

    # 4. Evaluate heuristics: passing invocation
    ok, err = synth.evaluate_heuristics("crawl_page", {"url": "https://test.com", "timeout": 30.0})
    assert ok is True
    assert err is None

    # 5. Evaluate heuristics: failing invocation
    ok_fail, err_fail = synth.evaluate_heuristics("crawl_page", {"url": "https://test.com", "timeout": 120.0})
    assert ok_fail is False
    assert "Heuristic Violation" in err_fail

    # 6. Verify planner prompt guideline generation
    guidelines = synth.get_planner_prompt_guidelines("crawl_page")
    assert "Active Learned Heuristics" in guidelines
    assert "Always keep crawler timeout" in guidelines


def test_heuristic_synthesize_from_postmortem(temp_refl_env):
    pm: PostMortemEngine = temp_refl_env["pm_engine"]
    synth: HeuristicSynthesizer = temp_refl_env["synth"]

    trace = FailureTrace(
        task_id="task_fail_1",
        tool_name="open_app",
        exception_type="FileNotFoundError",
        error_message="Target path missing not found",
    )
    analysis = pm.analyze(trace)
    rule = synth.synthesize_from_postmortem(analysis)
    assert rule.tool_name == "open_app"
    assert rule.is_active is True


# ============================================================================
# 4. Proactive Routine Mining & Morning Briefings (REFL-03)
# ============================================================================

def test_proactive_routine_and_morning_briefing(temp_refl_env):
    engine: TemporalGraphEngine = temp_refl_env["engine"]
    proactive: ProactiveSynthesizer = temp_refl_env["proactive"]

    # Record historical episodes
    now = time.time()
    for i in range(5):
        ep = TemporalEpisode(
            id=f"ep_coding_{i}",
            title=f"Autonomous Coding Session {i}",
            episode_type="CODING",
            event_timestamp=now - (i * 86400.0),
            recorded_at=now - (i * 86400.0),
            tags=["coding", "phenom"],
        )
        engine.record_episode(ep)

    # Mine routines
    routines = proactive.mine_proactive_routines()
    assert len(routines) >= 1
    assert "Coding" in routines[0].title

    # Generate pre-stage plan
    plan = proactive.generate_pre_stage_plan(routines[0])
    assert plan.target_workspace_name == routines[0].title
    assert len(plan.apps_to_launch) >= 1

    # Generate spoken morning briefing
    briefing = proactive.generate_morning_briefing(user_name="Commander")
    assert briefing.word_count <= 60
    assert "Commander" in briefing.briefing_text
    assert "nominal" in briefing.briefing_text


# ============================================================================
# 5. Safety Guards: Rule 8, Rule 11, and Guardian Kill Switch SLA
# ============================================================================

def test_postmortem_rule_8_and_rule_11_scrubbing(temp_refl_env):
    pm: PostMortemEngine = temp_refl_env["pm_engine"]

    fake_secret = "nv" + "api-abcdef1234567890abcdef"
    trace = FailureTrace(
        task_id="task_sec_test",
        tool_name="cloud_dispatch",
        input_arguments={"key": fake_secret},
        exception_type="PermissionError",
        error_message=f"Access denied with api_key={fake_secret} on checkout billing page.",
    )
    analysis = pm.analyze(trace)
    assert fake_secret not in analysis.root_cause_summary
    assert "checkout" not in analysis.root_cause_summary.lower() or "[REDACTED_FINANCIAL]" in analysis.root_cause_summary


def test_guardian_kill_switch_sla_postmortem(temp_refl_env):
    pm: PostMortemEngine = temp_refl_env["pm_engine"]

    durations_ms = []
    trace = FailureTrace(
        task_id="t1",
        tool_name="test",
        exception_type="Exception",
        error_message="err",
    )

    for _ in range(100):
        t0 = time.perf_counter()
        guardian._halted = True
        try:
            pm.analyze(trace)
        except PermissionError:
            pass
        finally:
            guardian._halted = False
        t1 = time.perf_counter()
        durations_ms.append((t1 - t0) * 1000.0)

    max_ms = max(durations_ms)
    avg_ms = sum(durations_ms) / len(durations_ms)

    assert max_ms < 25.0, f"Guardian SLA exceeded: max={max_ms:.3f}ms"
    assert avg_ms < 5.0, f"Guardian SLA avg too high: {avg_ms:.3f}ms"


# ============================================================================
# 6. ToolRegistry Verification & Handler Invocations
# ============================================================================

def test_reflective_postmortem_tool_registrations():
    tool_analyze = registry.get("analyze_failure_postmortem")
    assert tool_analyze is not None
    assert tool_analyze.tier == 0

    tool_synth = registry.get("synthesize_heuristic_rule")
    assert tool_synth is not None
    assert tool_synth.tier == 1

    tool_briefing = registry.get("generate_proactive_briefing")
    assert tool_briefing is not None
    assert tool_briefing.tier == 0


def test_reflective_tool_handlers_execution():
    # 1. Analyze failure postmortem
    res_analyze = handle_analyze_failure_postmortem(
        task_id="mission_dag_task_01",
        tool_name="open_app",
        exception_type="FileNotFoundError",
        error_message="Executable not found at C:\\App\\bad.exe",
    )
    assert res_analyze["status"] == "success"
    assert res_analyze["category"] == "RESOURCE_NOT_FOUND"

    # 2. Synthesize heuristic rule
    res_synth = handle_synthesize_heuristic_rule(
        tool_name="open_app",
        failure_signature=res_analyze["failure_signature"],
        description="Verify executable exists before open_app",
        constraint_expression="args.get('path') is not None",
        planner_guideline="Verify target path before opening application.",
    )
    assert res_synth["status"] == "success"
    assert res_synth["is_active"] is True

    # 3. Generate proactive briefing
    res_briefing = handle_generate_proactive_briefing(user_name="Operator")
    assert res_briefing["status"] == "success"
    assert res_briefing["word_count"] <= 60
    assert "Operator" in res_briefing["briefing_text"]
    assert "pre_stage_plan" in res_briefing
