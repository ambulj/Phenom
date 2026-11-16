"""
Comprehensive Unit Test Battery for Phase 47-04:
Self-Reflective Healing Loop, Circuit Breakers & Universal Guardian Kill Switch.
Verifies requirements: HEAL-01, HEAL-02, HEAL-03, HEAL-04.
"""

import time
import pytest

from services.backend.orchestrator.reflection_engine import (
    ReflectionEngine,
    ReflectionDiagnosis,
    ErrorCategory,
    RetryStrategy,
    reflection_engine
)
from services.backend.orchestrator.circuit_breaker import (
    MissionCircuitBreaker,
    CircuitBreakerTrippedError,
    CircuitBreakerState,
    mission_circuit_breaker
)
from services.backend.safety.universal_guardian import (
    UniversalGuardianCoordinator,
    HaltRecord,
    universal_guardian
)


@pytest.fixture(autouse=True)
def reset_guardian_state():
    """Ensure Guardian kill switch is reset before and after each test."""
    universal_guardian.resume()
    yield
    universal_guardian.resume()


# ============================================================================
# 1. Error Traceback & State Reflection Engine (HEAL-01)
# ============================================================================

def test_reflection_syntax_error_diagnosis():
    """Verifies that Python syntax errors are parsed and diagnosed as PATCH_CODE."""
    engine = ReflectionEngine()
    tb_text = """
    Traceback (most recent call last):
      File "services/backend/main.py", line 42, in <module>
        def broken_fn(a, b
    SyntaxError: invalid syntax
    """
    diag = engine.diagnose_failure(tb_text)
    assert diag.error_category == ErrorCategory.SYNTAX
    assert diag.retry_strategy == RetryStrategy.PATCH_CODE
    assert diag.line_number == 42
    assert "main.py" in str(diag.failing_file)
    assert diag.confidence >= 0.90


def test_reflection_import_error_diagnosis():
    """Verifies that missing module dependencies are diagnosed as INSTALL_DEPENDENCY."""
    engine = ReflectionEngine()
    tb_text = """
    Traceback (most recent call last):
      File "services/backend/coding/test_runner.py", line 12, in <module>
        import nonexistent_package_xyz
    ModuleNotFoundError: No module named 'nonexistent_package_xyz'
    """
    diag = engine.diagnose_failure(tb_text)
    assert diag.error_category == ErrorCategory.IMPORT_MISSING
    assert diag.retry_strategy == RetryStrategy.INSTALL_DEPENDENCY
    assert "nonexistent_package_xyz" in diag.root_cause


def test_reflection_file_not_found_diagnosis():
    """Verifies that missing file paths are diagnosed as CREATE_FILE."""
    engine = ReflectionEngine()
    tb_text = """
    Traceback (most recent call last):
      File "services/backend/research/obsidian_synthesizer.py", line 88, in synthesize
        with open('vault/Research/missing_note.md', 'r') as f:
    FileNotFoundError: [Errno 2] No such file or directory: 'vault/Research/missing_note.md'
    """
    diag = engine.diagnose_failure(tb_text)
    assert diag.error_category == ErrorCategory.FILE_NOT_FOUND
    assert diag.retry_strategy == RetryStrategy.CREATE_FILE
    assert "missing_note.md" in diag.root_cause


def test_reflection_dom_selector_diagnosis():
    """Verifies that missing UI selectors are diagnosed as ALTERNATIVE_SELECTOR."""
    engine = ReflectionEngine()
    dom_err = "Playwright TimeoutError: Timeout 15000ms exceeded waiting for locator('#submit-checkout-btn')"
    diag = engine.diagnose_failure(dom_err)
    assert diag.error_category == ErrorCategory.SELECTOR_MISSING
    assert diag.retry_strategy == RetryStrategy.ALTERNATIVE_SELECTOR
    assert "#submit-checkout-btn" in diag.root_cause


# ============================================================================
# 2. Autonomous Retry Counter & Circuit Breakers (HEAL-02, HEAL-03)
# ============================================================================

def test_circuit_breaker_retry_cap_escalation():
    """
    Verifies that step retries are strictly capped at 5 attempts (HEAL-02),
    and the 6th attempt raises CircuitBreakerTrippedError.
    """
    breaker = MissionCircuitBreaker(max_retries_per_step=5)
    m_id = "mission_retry_test"
    breaker.start_mission(m_id)

    # Attempts 1 through 5 succeed
    for i in range(1, 6):
        cnt = breaker.record_retry(m_id, node_id="step_code_patch")
        assert cnt == i

    # 6th attempt breaches the 5-retry limit and must trip
    with pytest.raises(CircuitBreakerTrippedError) as exc_info:
        breaker.record_retry(m_id, node_id="step_code_patch")

    assert "exceeded max retry cap of 5 attempts" in str(exc_info.value)
    assert breaker.get_state(m_id).is_tripped is True


def test_circuit_breaker_step_count_limit():
    """
    Verifies that mission step execution is strictly capped at 25 steps (HEAL-03).
    """
    breaker = MissionCircuitBreaker(max_steps=25)
    m_id = "mission_step_cap_test"
    breaker.start_mission(m_id)

    # Execute 25 valid steps
    for step_num in range(1, 26):
        cnt = breaker.record_step(m_id, node_id=f"node_{step_num}")
        assert cnt == step_num

    # 26th step breaches the 25-step cap
    with pytest.raises(CircuitBreakerTrippedError) as exc_info:
        breaker.record_step(m_id, node_id="node_26")

    assert "maximum execution limit of 25 total steps" in str(exc_info.value)
    assert breaker.get_state(m_id).is_tripped is True


def test_circuit_breaker_duration_timeout():
    """
    Verifies that mission duration is capped at 15 minutes / 900s (HEAL-03).
    """
    breaker = MissionCircuitBreaker(max_duration_seconds=900.0)
    m_id = "mission_timeout_test"
    state = breaker.start_mission(m_id)

    # Artificially age the mission start time past 900 seconds
    state.started_at = time.time() - 950.0

    with pytest.raises(CircuitBreakerTrippedError) as exc_info:
        breaker.check_health(m_id)

    assert "hard time cap of 900.0s" in str(exc_info.value)
    assert breaker.get_state(m_id).is_tripped is True


# ============================================================================
# 3. Universal Guardian Kill Switch SLA (< 25ms) (HEAL-04)
# ============================================================================

def test_universal_guardian_kill_switch_sla():
    """
    Verifies that Universal Guardian halts all operations in < 25.0ms SLA (HEAL-04).
    """
    record = universal_guardian.trigger_kill(source="hotkey", reason="Physical Ctrl+Alt+P override")

    assert record.source == "hotkey"
    assert universal_guardian.is_halted is True
    assert record.latency_ms < 25.0, f"Guardian halt latency was {record.latency_ms:.2f}ms (exceeded 25ms SLA)"

    # Resume clears halted state
    universal_guardian.resume()
    assert universal_guardian.is_halted is False


def test_universal_guardian_voice_triggers():
    """Verifies that voice emergency cues trigger kill switch detection."""
    guardian_coord = UniversalGuardianCoordinator()

    assert guardian_coord.check_voice_trigger("Phenom stop what you are doing") is True
    assert guardian_coord.check_voice_trigger("Emergency halt immediately") is True
    assert guardian_coord.check_voice_trigger("kill switch") is True
    assert guardian_coord.check_voice_trigger("Phenom write me a poem") is False
