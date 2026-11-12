"""Unit and Safety Integration Tests for Predictive Task Anticipation & Ambient Pipelining.

Validates Markov state transitions, conditional probability calculation, cache prewarming,
Rule 8 anti-checkout enforcement, Rule 11 credential scrubbing, and Guardian kill switch SLA.
Phase 23-04 (PRED-01, AUT-04, SAF-01, SAF-02).
"""

import time
import pytest
from pathlib import Path
import tempfile
import shutil

from services.backend.proactive.task_anticipation_engine import (
    TaskAnticipationEngine,
    Rule8ViolationError as AnticipationRule8Error,
)
from services.backend.proactive.cache_prewarmer import (
    CachePrewarmer,
    Rule8ViolationError as PrewarmerRule8Error,
)
from services.backend.safety.guardian import guardian
from services.backend.safety.registry import registry
import services.backend.tools.predictive_task_tools  # Ensure tools are loaded


@pytest.fixture
def clean_engine():
    temp_dir = tempfile.mkdtemp()
    engine = TaskAnticipationEngine(persistence_dir=temp_dir)
    yield engine
    shutil.rmtree(temp_dir, ignore_errors=True)
    guardian.resume()


@pytest.fixture
def clean_prewarmer():
    prewarmer = CachePrewarmer()
    yield prewarmer
    guardian.resume()


def test_habit_transition_recording_and_probability(clean_engine):
    """Verify Markov transition counters and exact conditional probabilities."""
    # Record git_commit -> git_push (3 times), git_commit -> run_tests (1 time)
    res1 = clean_engine.record_transition("git_commit", "git_push")
    clean_engine.record_transition("git_commit", "git_push")
    res2 = clean_engine.record_transition("git_commit", "run_tests")
    res3 = clean_engine.record_transition("git_commit", "git_push")

    assert res3["transition_count"] == 3
    assert res3["total_source_occurrences"] == 4
    # P(git_push | git_commit) = 3 / 4 = 0.75
    assert res3["conditional_probability"] == 0.75

    predictions = clean_engine.predict_next_actions(current_action="git_commit", threshold=0.50)
    assert len(predictions) == 1
    assert predictions[0].target_action == "git_push"
    assert predictions[0].probability == 0.75
    assert predictions[0].confidence_level == "HIGH"


def test_marginal_prior_predictions_without_current_action(clean_engine):
    """Verify marginal probability calculations when no current action is specified."""
    clean_engine.record_transition("edit_code", "run_tests")
    clean_engine.record_transition("run_tests", "git_commit")

    predictions = clean_engine.predict_next_actions(current_action=None, threshold=0.20)
    assert len(predictions) > 0
    actions = [p.target_action for p in predictions]
    assert "run_tests" in actions or "git_commit" in actions


def test_action_card_soft_dismissal_rule_7(clean_engine):
    """Verify soft dismissal preserves underlying transition weights (Rule 7 non-destructibility)."""
    clean_engine.record_transition("open_repo", "git_status")
    clean_engine.record_transition("open_repo", "git_pull")

    preds_before = clean_engine.predict_next_actions("open_repo", threshold=0.30)
    assert len(preds_before) == 2

    dismiss_res = clean_engine.dismiss_action_card("ant_open_repo_git_status")
    assert dismiss_res["status"] == "dismissed"

    # git_status should no longer be recommended, but git_pull remains
    preds_after = clean_engine.predict_next_actions("open_repo", threshold=0.30)
    assert len(preds_after) == 1
    assert preds_after[0].target_action == "git_pull"

    # Verify transitions count remains intact
    assert clean_engine.transitions["open_repo"]["git_status"] == 1


def test_rule_11_credential_scrubbing(clean_engine):
    """Verify secrets and tokens are scrubbed from habit transition labels (Rule 11)."""
    clean_engine.record_transition("login ghp_123456789012345678901234", "git_fetch")
    assert "ghp_123456789012345678901234" not in clean_engine.transitions
    assert any("[SCRUBBED_GITHUB_TOKEN]" in k for k in clean_engine.transitions.keys())


def test_cache_prewarmer_operations(clean_prewarmer):
    """Verify cache pre-warming, hit metrics, and budget telemetry."""
    entry = clean_prewarmer.prewarm_target("services.backend.synapse", target_type="ast_symbols")
    assert entry.status == "WARM"
    assert entry.size_bytes > 0

    hit_entry = clean_prewarmer.access_target("services.backend.synapse")
    assert hit_entry is not None
    assert hit_entry.hit_count == 1

    status = clean_prewarmer.get_prewarm_status()
    assert status["total_entries"] == 1
    assert status["total_hits"] == 1
    assert status["total_size_bytes"] > 0

    clear_res = clean_prewarmer.clear_cache()
    assert clear_res["cleared_entries"] == 1
    assert clean_prewarmer.get_prewarm_status()["total_entries"] == 0


def test_rule_8_anti_checkout_enforcement(clean_engine, clean_prewarmer):
    """Verify strict Rule 8 rejection of payment/checkout directives across engine and prewarmer."""
    with pytest.raises(AnticipationRule8Error, match="Rule 8 violation"):
        clean_engine.record_transition("view_cart", "execute_checkout_payment")

    with pytest.raises(AnticipationRule8Error, match="Rule 8 violation"):
        clean_engine.predict_next_actions("buy_now_order")

    with pytest.raises(PrewarmerRule8Error, match="Rule 8 violation"):
        clean_prewarmer.prewarm_target("stripe_credit_card_checkout")


def test_guardian_kill_switch_sla_halt(clean_engine, clean_prewarmer):
    """Verify Guardian kill switch halts anticipation and pre-warming in < 25.0ms SLA."""
    guardian.trigger("Emergency test halt")
    assert guardian.is_halted

    t0 = time.perf_counter()
    with pytest.raises(PermissionError, match="Guardian kill switch is TRIPPED"):
        clean_engine.record_transition("edit_code", "run_tests")
    t1 = time.perf_counter()
    latency_ms = (t1 - t0) * 1000.0
    assert latency_ms < 25.0, f"Halt latency {latency_ms:.4f}ms exceeded 25.0ms SLA"

    t0 = time.perf_counter()
    with pytest.raises(PermissionError, match="Guardian kill switch is TRIPPED"):
        clean_prewarmer.prewarm_target("ast_parser")
    t1 = time.perf_counter()
    latency_ms = (t1 - t0) * 1000.0
    assert latency_ms < 25.0, f"Halt latency {latency_ms:.4f}ms exceeded 25.0ms SLA"

    guardian.resume()


def test_tool_registry_and_previews():
    """Verify tool registration, tier classifications, and preview generations."""
    pred_tool = registry.get("predict_next_actions")
    assert pred_tool is not None
    assert pred_tool.tier == 0
    preview_pred = pred_tool.generate_preview({"current_action": "git_commit", "threshold": 0.6})
    assert "git_commit" in preview_pred

    prewarm_tool = registry.get("prewarm_workflow_cache")
    assert prewarm_tool is not None
    assert prewarm_tool.tier == 0
    preview_prewarm = prewarm_tool.generate_preview({"target_name": "symbols_indexer", "target_type": "ast_symbols"})
    assert "symbols_indexer" in preview_prewarm

    dismiss_tool = registry.get("dismiss_action_card")
    assert dismiss_tool is not None
    assert dismiss_tool.tier == 0
    preview_dismiss = dismiss_tool.generate_preview({"action_id": "ant_card_42"})
    assert "ant_card_42" in preview_dismiss
