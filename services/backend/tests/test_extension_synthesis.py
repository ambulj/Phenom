"""
Tests for Self-Synthesizing Extension Fabric & AST Safety Auditor (EXT-01).
Verifies safe micro-tool compilation, rejection of prohibited modules/builtins/Rule 7/8,
hot-reloading, and clean ToolRegistry unloading.
"""

import pytest
from services.backend.extensions.ast_auditor import ASTSafetyAuditor
from services.backend.extensions.extension_manager import DynamicExtensionManager
from services.backend.safety.registry import registry
from services.backend.schemas.extensions import ExtensionStatus


def test_ast_auditor_allows_safe_code():
    auditor = ASTSafetyAuditor()
    safe_code = """
def calculate_growth(initial: float, rate: float, periods: int) -> float:
    return initial * ((1.0 + rate) ** periods)
"""
    is_safe, violations = auditor.audit_code(safe_code)
    assert is_safe is True
    assert len(violations) == 0


def test_ast_auditor_blocks_dangerous_builtins():
    auditor = ASTSafetyAuditor()
    dangerous_code = """
def exploit():
    return eval("1 + 1")
"""
    is_safe, violations = auditor.audit_code(dangerous_code)
    assert is_safe is False
    assert any("eval" in v for v in violations)


def test_ast_auditor_blocks_forbidden_modules():
    auditor = ASTSafetyAuditor()
    module_code = """
import subprocess
def run_command():
    subprocess.call(["dir"])
"""
    is_safe, violations = auditor.audit_code(module_code)
    assert is_safe is False
    assert any("subprocess" in v for v in violations)


def test_ast_auditor_blocks_rule_7_permanent_deletion():
    auditor = ASTSafetyAuditor()
    del_code = """
import os
def delete_file(path: str):
    os.remove(path)
"""
    is_safe, violations = auditor.audit_code(del_code)
    assert is_safe is False
    assert any("Rule 7" in v or "remove" in v for v in violations)


def test_ast_auditor_blocks_rule_8_payment_terms():
    auditor = ASTSafetyAuditor()
    pay_code = """
def process_order(total: float):
    pay_now(total)
"""
    is_safe, violations = auditor.audit_code(pay_code)
    assert is_safe is False
    assert any("Rule 8" in v or "pay_now" in v for v in violations)


def test_dynamic_extension_lifecycle_and_hot_registry():
    manager = DynamicExtensionManager()

    code = """
def dynamic_unit_converter(meters: float = 1.0) -> float:
    return meters * 3.28084
"""
    ext_id, meta = manager.synthesize_extension(
        name="dynamic_unit_converter",
        description="Converts meters to feet",
        python_code=code,
        risk_tier=0,
    )

    assert meta.status == ExtensionStatus.LOADED
    assert meta.ast_verified is True
    assert "dynamic_unit_converter" in registry._tools

    # Execute hot-loaded tool directly via registry
    tool = registry._tools["dynamic_unit_converter"]
    res = tool.handler_fn(meters=10.0)
    assert abs(res - 32.8084) < 1e-4

    # Hot-reload extension
    reloaded_meta = manager.hot_reload_extension(ext_id)
    assert reloaded_meta.status == ExtensionStatus.LOADED
    assert "dynamic_unit_converter" in registry._tools

    # Unload extension and verify clean unregistration
    unloaded = manager.unload_extension(ext_id)
    assert unloaded is True
    assert "dynamic_unit_converter" not in registry._tools
    assert manager._extensions[ext_id].status == ExtensionStatus.UNLOADED
