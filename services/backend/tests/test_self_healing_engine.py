"""Unit and Safety Integration Tests for Autonomous Neuro-Symbolic Self-Healing Kernel.

Validates traceback parsing, fault classification, deterministic AST patch synthesis,
unified diff generation, reversible transaction rollback, Rule 8 anti-checkout defense,
and Guardian kill switch SLA.
Phase 24-01 (HEAL-01, SYM-02, SAF-01, SAF-02).
"""

import time
import pytest
from pathlib import Path
import tempfile
import shutil

from services.backend.healing.diagnostic_engine import (
    DiagnosticEngine,
    Rule8ViolationError as DiagRule8Error,
)
from services.backend.healing.patch_synthesizer import (
    PatchSynthesizer,
    Rule8ViolationError as PatchRule8Error,
)
from services.backend.safety.guardian import guardian
from services.backend.safety.registry import registry
import services.backend.tools.self_healing_tools  # Ensure tools are loaded


@pytest.fixture(autouse=True)
def reset_guardian():
    guardian.resume()
    yield
    guardian.resume()


def test_traceback_fault_diagnosis_accuracy():
    """Verify diagnostic engine parses frames and accurately classifies faults."""
    engine = DiagnosticEngine()

    tb_none = """Traceback (most recent call last):
  File "services/backend/api.py", line 42, in get_user_data
    return user.profile
AttributeError: 'NoneType' object has no attribute 'profile'"""

    rep1 = engine.diagnose_traceback(tb_none)
    assert rep1.error_type == "AttributeError"
    assert rep1.fault_category == "NULL_OR_NONE_DEREFERENCE"
    assert rep1.line_number == 42
    assert rep1.function_name == "get_user_data"
    assert rep1.confidence_score >= 0.90

    tb_key = """Traceback (most recent call last):
  File "services/backend/cache.py", line 18, in lookup_cache
    val = config["api_timeout"]
KeyError: 'api_timeout'"""

    rep2 = engine.diagnose_traceback(tb_key)
    assert rep2.error_type == "KeyError"
    assert rep2.fault_category == "MISSING_DICTIONARY_KEY"
    assert rep2.line_number == 18

    tb_zero = """Traceback (most recent call last):
  File "services/backend/metrics.py", line 29, in calculate_average
    return total_score / count
ZeroDivisionError: division by zero"""

    rep3 = engine.diagnose_traceback(tb_zero)
    assert rep3.error_type == "ZeroDivisionError"
    assert rep3.fault_category == "DIVISION_BY_ZERO"

    tb_import = """Traceback (most recent call last):
  File "main.py", line 4, in <module>
    import scipy
ModuleNotFoundError: No module named 'scipy'"""

    rep4 = engine.diagnose_traceback(tb_import)
    assert rep4.fault_category == "MISSING_IMPORT"


def test_symbolic_patch_synthesis_and_unified_diff():
    """Verify deterministic AST patch synthesis and unified diff output."""
    engine = DiagnosticEngine()
    synth = PatchSynthesizer()

    source = (
        "def lookup_cache(config):\n"
        "    val = config['api_timeout']\n"
        "    return val\n"
    )
    tb = """Traceback (most recent call last):
  File "services/backend/cache.py", line 2, in lookup_cache
    val = config['api_timeout']
KeyError: 'api_timeout'"""

    rep = engine.diagnose_traceback(tb, source_code=source)
    patch_res = synth.synthesize_patch(rep, source_code=source, dry_run=True)

    assert patch_res.fault_category == "MISSING_DICTIONARY_KEY"
    assert "config.get('api_timeout', None)" in patch_res.patched_line
    assert "---" in patch_res.unified_diff
    assert "+++" in patch_res.unified_diff
    assert patch_res.dry_run is True


def test_patch_application_and_transaction_rollback_rule_7():
    """Verify reversible patch application and snapshot rollback (Rule 7 non-destructibility)."""
    engine = DiagnosticEngine()
    synth = PatchSynthesizer()

    temp_dir = tempfile.mkdtemp()
    test_file = Path(temp_dir) / "metrics.py"
    original_code = (
        "def compute_rate(total, elapsed):\n"
        "    return total / elapsed\n"
    )
    test_file.write_text(original_code, encoding="utf-8")

    tb = f"""Traceback (most recent call last):
  File "{test_file.as_posix()}", line 2, in compute_rate
    return total / elapsed
ZeroDivisionError: division by zero"""

    rep = engine.diagnose_traceback(tb, source_code=original_code)
    patch_res = synth.synthesize_patch(rep, source_code=original_code, dry_run=True)

    # 1. Apply patch
    apply_res = synth.apply_patch(patch_res.patch_id)
    assert apply_res["status"] == "applied"
    modified_code = test_file.read_text(encoding="utf-8")
    assert "elapsed != 0" in modified_code

    # 2. Rollback patch (Rule 7)
    rollback_res = synth.rollback_patch(patch_res.patch_id)
    assert rollback_res["status"] == "rolled_back"
    restored_code = test_file.read_text(encoding="utf-8")
    assert restored_code == original_code

    shutil.rmtree(temp_dir, ignore_errors=True)


def test_rule_8_anti_checkout_enforcement():
    """Verify Rule 8 payment / checkout rejection across diagnosis and patch synthesis."""
    engine = DiagnosticEngine()
    synth = PatchSynthesizer()

    with pytest.raises(DiagRule8Error, match="Rule 8 violation"):
        engine.diagnose_traceback("Exception in process_checkout_payment_flow")

    with pytest.raises(PatchRule8Error, match="Rule 8 violation"):
        rep = engine.diagnose_traceback("KeyError: 'item_id'")
        synth.synthesize_patch(rep, source_code="def buy_now_checkout(): pass")


def test_guardian_kill_switch_sla_halt():
    """Verify Guardian kill switch halts diagnosis and synthesis in < 25.0ms SLA."""
    guardian.trigger("Emergency test halt")
    assert guardian.is_halted

    engine = DiagnosticEngine()
    synth = PatchSynthesizer()

    t0 = time.perf_counter()
    with pytest.raises(PermissionError, match="Guardian kill switch is TRIPPED"):
        engine.diagnose_traceback("KeyError: 'test'")
    t1 = time.perf_counter()
    latency_ms = (t1 - t0) * 1000.0
    assert latency_ms < 25.0, f"Halt latency {latency_ms:.4f}ms exceeded 25.0ms SLA"

    guardian.resume()


def test_tool_registry_and_previews():
    """Verify tool registration, tier classifications, and preview generations."""
    diag_tool = registry.get("diagnose_runtime_failure")
    assert diag_tool is not None
    assert diag_tool.tier == 0
    preview_diag = diag_tool.generate_preview({"traceback_text": "KeyError: 'id'"})
    assert "KeyError" in preview_diag

    synth_tool = registry.get("synthesize_healing_patch")
    assert synth_tool is not None
    assert synth_tool.tier == 0
    preview_synth = synth_tool.generate_preview({"traceback_text": "KeyError", "source_code": "a=1"})
    assert "candidate" in preview_synth

    apply_tool = registry.get("apply_healing_patch")
    assert apply_tool is not None
    assert apply_tool.tier == 1
    preview_apply = apply_tool.generate_preview({"patch_id": "patch_12345"})
    assert "patch_12345" in preview_apply
