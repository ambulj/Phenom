import pytest
import time
import asyncio
import tempfile
import os
from services.backend.automation.macro_synthesizer import (
    MacroSynthesizer,
    WorkflowRecipe,
    MacroStep,
    macro_synthesizer
)
from services.backend.automation.workflow_engine import (
    WorkflowEngine,
    workflow_engine,
    SelfHealEvent
)
from services.backend.safety.guardian import guardian
from services.backend.safety.registry import registry
from services.backend.automation.gui_controller import Rule8ViolationError
import services.backend.tools.workflow_macro_tools  # Ensure tools are registered


@pytest.mark.asyncio
async def test_macro_recording_and_parameterized_synthesis():
    """Test recording desktop steps, extracting ${param} placeholders, and YAML synthesis."""
    with tempfile.TemporaryDirectory() as tmp_dir:
        synth = MacroSynthesizer(recipe_dir=tmp_dir)
        synth.start_recording(session_id="test_session")

        synth.record_step({
            "action": "click",
            "target_type": "ocr_text",
            "target_value": "File Explorer",
            "description": "Open Explorer"
        }, session_id="test_session")

        synth.record_step({
            "action": "type",
            "target_value": "SearchInput",
            "text_input": "project_${project_name}_report.docx",
            "description": "Search for project report"
        }, session_id="test_session")

        synth.record_step({
            "action": "bash_exec",
            "command": "python generate_summary.py --target=${output_dir}",
            "description": "Run summary script"
        }, session_id="test_session")

        steps = synth.stop_recording(session_id="test_session")
        assert len(steps) == 3

        recipe = synth.synthesize_recipe(
            name="Search and Summarize Project",
            description="Searches for report and runs summary script",
            steps=steps
        )

        assert recipe.name == "Search and Summarize Project"
        assert "project_name" in recipe.parameters
        assert "output_dir" in recipe.parameters
        assert recipe.safety_tier == 2  # Raised to Tier 2 due to bash_exec

        yaml_str = synth.to_yaml(recipe)
        assert "project_${project_name}_report.docx" in yaml_str
        assert "recipe_id: search_and_summarize_project" in yaml_str

        # Roundtrip parse
        reparsed = synth.from_yaml(yaml_str)
        assert reparsed.recipe_id == recipe.recipe_id
        assert len(reparsed.steps) == 3


@pytest.mark.asyncio
async def test_recipe_file_persistence_and_loading():
    """Test saving and loading recipes from filesystem."""
    with tempfile.TemporaryDirectory() as tmp_dir:
        synth = MacroSynthesizer(recipe_dir=tmp_dir)
        step = MacroStep(
            step_id=1,
            action="hotkey",
            key_sequence="ctrl+shift+p",
            description="Open command palette"
        )
        recipe = synth.synthesize_recipe(
            name="Quick Palette",
            steps=[step]
        )

        saved_path = synth.save_recipe(recipe)
        assert os.path.exists(saved_path)

        loaded = synth.load_recipe(recipe.recipe_id)
        assert loaded.name == "Quick Palette"
        assert loaded.steps[0].key_sequence == "ctrl+shift+p"

        recipes_list = synth.list_recipes()
        assert len(recipes_list) == 1
        assert recipes_list[0]["recipe_id"] == "quick_palette"


@pytest.mark.asyncio
async def test_self_healing_element_retargeting():
    """Test workflow engine heals drifted selectors using on-screen OCR text matching."""
    engine = WorkflowEngine()
    step1 = MacroStep(
        step_id=1,
        action="click",
        target_type="uia_id",
        target_value="ExportButton_V1",
        heal_strategy="ocr_fallback",
        description="Click export button"
    )
    recipe = WorkflowRecipe(
        recipe_id="export_workflow",
        name="Export Workflow",
        steps=[step1]
    )

    # Mock screen elements where ExportButton_V1 ID is missing, but OCR text 'Export' exists at shifted location
    mock_screen = [
        {"id": "HeaderTitle", "text": "Report Studio", "bbox": [0, 0, 200, 30]},
        {"id": "ExportButton_V2_Shifted", "text": "Export", "bbox": [450, 800, 530, 830]}
    ]

    res = await engine.execute_recipe(
        recipe=recipe,
        mock_screen_elements=mock_screen,
        dry_run=True
    )

    assert res.status == "success"
    assert res.completed_steps == 1
    assert res.healed_steps_count == 1
    heal_event = res.heal_log[0]
    assert heal_event.step_id == 1
    assert "Export" in heal_event.healed_target
    assert heal_event.confidence >= 0.8


@pytest.mark.asyncio
async def test_preview_execution_diff_simulation():
    """Test preview execution simulates parameter interpolation and step results without execution."""
    engine = WorkflowEngine()
    step1 = MacroStep(
        step_id=1,
        action="type",
        target_value="SearchBox",
        text_input="query for ${search_topic}",
        description="Type search query"
    )
    recipe = WorkflowRecipe(
        recipe_id="search_recipe",
        name="Search Recipe",
        steps=[step1]
    )

    preview_res = engine.preview_execution(
        recipe=recipe,
        params={"search_topic": "quantum computing"}
    )

    assert preview_res.status == "preview"
    assert preview_res.completed_steps == 1
    assert "quantum computing" in preview_res.steps_results[0].output


@pytest.mark.asyncio
async def test_rule_8_anti_checkout_shield_in_workflow_engine():
    """Test that steps targeting checkout or payment strictly raise Rule8ViolationError."""
    engine = WorkflowEngine()
    step_checkout = MacroStep(
        step_id=1,
        action="click",
        target_value="Complete Checkout and Pay $99",
        description="Attempt payment"
    )
    recipe = WorkflowRecipe(
        recipe_id="dangerous_recipe",
        name="Dangerous Recipe",
        steps=[step_checkout]
    )

    with pytest.raises(Rule8ViolationError) as exc_info:
        await engine.execute_recipe(recipe=recipe)
    assert "Rule 8" in str(exc_info.value) or "checkout" in str(exc_info.value).lower()

    # Also test preview rejection
    with pytest.raises(Rule8ViolationError):
        engine.preview_execution(recipe=recipe)


@pytest.mark.asyncio
async def test_workflow_macro_tools_registration_and_previews():
    """Test all Phase 2 tools are registered in Safety Registry with proper previews."""
    tool_names = [
        "record_macro_step",
        "synthesize_workflow_recipe",
        "preview_workflow_execution",
        "execute_workflow_recipe",
        "list_workflow_recipes"
    ]

    for name in tool_names:
        entry = registry.get(name)
        assert entry is not None, f"Tool {name} missing from registry"

        if name in ("synthesize_workflow_recipe", "execute_workflow_recipe"):
            assert entry.tier >= 1
        else:
            assert entry.tier == 0

        preview = entry.preview_fn({
            "name": "Daily Sync",
            "action": "click",
            "target_value": "SyncButton",
            "recipe_id": "daily_sync"
        })
        assert isinstance(preview, str)
        assert len(preview) > 5


@pytest.mark.asyncio
async def test_universal_guardian_kill_switch_sla():
    """Test synchronous Guardian trigger halts workflow execution in < 25.0ms SLA."""
    guardian.trigger("Phase 2 test halt")
    try:
        engine = WorkflowEngine()
        step = MacroStep(step_id=1, action="wait", timeout_ms=5000)
        recipe = WorkflowRecipe(recipe_id="slow_recipe", name="Slow Recipe", steps=[step])

        start_time = time.perf_counter()
        with pytest.raises(PermissionError) as exc_info:
            await engine.execute_recipe(recipe=recipe)
        elapsed_ms = (time.perf_counter() - start_time) * 1000

        assert elapsed_ms < 25.0, f"Guardian halt took {elapsed_ms:.2f}ms, exceeding 25.0ms SLA"
        assert "halted" in str(exc_info.value).lower()
    finally:
        guardian.resume()
