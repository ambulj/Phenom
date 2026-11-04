"""
Tests for Deep Windows UIAutomation (UIA) & Self-Healing Workflows (RPA-01).
Verifies tree crawling, background pattern invocation, fuzzy self-healing resolution,
and verification checkpoints.
"""

import pytest
from services.backend.automation.deep_uia_engine import DeepUIAutomationEngine
from services.backend.schemas.deep_uia import (
    UIElementType,
    UIPatternType,
    UIWorkflowStep,
)


def test_uia_tree_traversal_and_indexing():
    engine = DeepUIAutomationEngine()
    tree = engine.get_tree()

    assert tree.name == "Notepad - Working Document"
    assert tree.control_type == UIElementType.WINDOW
    assert len(tree.children) == 3

    # Verify indexed elements
    btn_save = engine._elements_by_id.get("elem-btn-save-01")
    assert btn_save is not None
    assert btn_save.name == "Save"
    assert UIPatternType.INVOKE in btn_save.supported_patterns


def test_uia_exact_and_fuzzy_element_finding():
    engine = DeepUIAutomationEngine()

    # Exact match on name
    res_exact = engine.find_element(name_query="Save")
    assert res_exact is not None
    elem, is_healed = res_exact
    assert elem.name == "Save"
    assert is_healed is False

    # Exact match on automation_id
    res_id = engine.find_element(name_query="", automation_id="txtDocTitle")
    assert res_id is not None
    elem_id, is_healed = res_id
    assert elem_id.name == "Document Title"
    assert is_healed is False

    # Fuzzy match on shifted or typo query: "Sav Document" -> matches "Save" or "Document Title"
    res_fuzzy = engine.find_element(
        name_query="Savv",
        control_type=UIElementType.BUTTON,
        fuzzy_threshold=0.60,
    )
    assert res_fuzzy is not None
    elem_f, is_healed = res_fuzzy
    assert elem_f.name == "Save"
    assert is_healed is True


def test_uia_non_intrusive_invocation_and_set_value():
    engine = DeepUIAutomationEngine()

    # Invoke button
    inv_res = engine.invoke_element("elem-btn-save-01", non_intrusive=True)
    assert inv_res["status"] == "success"
    assert inv_res["non_intrusive"] is True

    # Set value on text field
    val_res = engine.set_value("elem-edit-title-02", "Annual Report 2026.docx", non_intrusive=True)
    assert val_res["status"] == "success"
    assert val_res["new_value"] == "Annual Report 2026.docx"

    # Verify state updated in element
    elem = engine._elements_by_id["elem-edit-title-02"]
    assert elem.value == "Annual Report 2026.docx"


def test_uia_self_healing_workflow_execution():
    engine = DeepUIAutomationEngine()

    steps = [
        # Step 1: Set title using exact name query
        UIWorkflowStep(
            step_id="step-1",
            action_type="SET_VALUE",
            target_query="Document Title",
            value_payload="Project Phenom Whitepaper",
            verification_expected="Project Phenom Whitepaper",
        ),
        # Step 2: Click save using fuzzy query "Sav" (self-heals to "Save")
        UIWorkflowStep(
            step_id="step-2",
            action_type="CLICK",
            target_query="Sav",
            control_type=UIElementType.BUTTON,
        ),
    ]

    result = engine.execute_workflow(steps=steps, auto_heal=True)
    assert result.is_success is True
    assert result.total_steps == 2
    assert result.successful_steps == 2
    assert result.healed_steps == 1  # Step 2 was healed
    assert steps[1].healing_applied is True
    assert steps[0].status == "VERIFIED"
    assert steps[1].status == "VERIFIED"


def test_uia_workflow_aborts_on_guardian_halt():
    engine = DeepUIAutomationEngine()
    engine.halt()

    steps = [
        UIWorkflowStep(
            step_id="step-1",
            action_type="CLICK",
            target_query="Save",
        )
    ]

    with pytest.raises(PermissionError, match="Guardian kill switch is active"):
        engine.execute_workflow(steps=steps)


def test_rule_8_payment_invocation_blocked():
    """Verify that Rule 8 forbids automated payment or purchase execution."""
    engine = DeepUIAutomationEngine()
    # Add a mock checkout button
    from services.backend.schemas.deep_uia import UIElementNode
    pay_btn = UIElementNode(
        element_id="elem-btn-checkout-99",
        name="Complete Purchase",
        automation_id="btnPayNow",
        control_type=UIElementType.BUTTON,
        supported_patterns=[UIPatternType.INVOKE],
    )
    engine._elements_by_id[pay_btn.element_id] = pay_btn

    with pytest.raises(PermissionError, match="Rule 8 Violation"):
        engine.invoke_element(pay_btn.element_id)


def test_rule_8_11_password_typing_blocked():
    """Verify that Rule 8/11 forbids typing passwords into UIA inputs."""
    engine = DeepUIAutomationEngine()
    from services.backend.schemas.deep_uia import UIElementNode
    pw_field = UIElementNode(
        element_id="elem-edit-pw-99",
        name="User Password",
        automation_id="txtPasswordInput",
        control_type=UIElementType.EDIT,
        supported_patterns=[UIPatternType.VALUE],
        is_password=True,
    )
    engine._elements_by_id[pw_field.element_id] = pw_field

    with pytest.raises(PermissionError, match="Rule 8/11 Violation"):
        engine.set_value(pw_field.element_id, "my-secret-password-123")

