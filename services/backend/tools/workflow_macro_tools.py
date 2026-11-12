"""
Safety-Wrapped Workflow Macro Tools.
Exposes autonomous desktop macro recording, recipe synthesis, self-healing execution,
and execution diff previews to the Safety ToolRegistry (Phase 21-02 MAC-02 / AUT-02).
"""

from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field

from services.backend.safety.registry import registry
from services.backend.automation.macro_synthesizer import macro_synthesizer, MacroStep
from services.backend.automation.workflow_engine import workflow_engine


# ==========================================
# 1. Record Macro Step (Tier 0)
# ==========================================

class RecordMacroStepArgs(BaseModel):
    action: str = Field(..., description="Action type: click, type, hotkey, wait, bash_exec, assert_screen")
    target_type: Optional[str] = Field(default=None, description="Selector type: uia_id, ocr_text, class_name, coordinate")
    target_value: Optional[str] = Field(default=None, description="Selector value or expression, supports ${param}")
    text_input: Optional[str] = Field(default=None, description="Text to type, supports ${param}")
    key_sequence: Optional[str] = Field(default=None, description="Keyboard shortcut combination e.g. 'ctrl+s'")
    command: Optional[str] = Field(default=None, description="CLI command string for bash_exec")
    timeout_ms: int = Field(default=5000, description="Step timeout in milliseconds")
    description: str = Field(default="", description="Human-readable step description")
    session_id: str = Field(default="default", description="Macro recording session id")

def record_macro_step_preview(args: Dict[str, Any]) -> str:
    action = args.get("action", "action")
    tgt = args.get("target_value") or args.get("command") or args.get("text_input") or "screen"
    return f"Record macro step: {action} on {tgt} into session buffer."

@registry.register(
    name="record_macro_step",
    tier=0,
    description="Records a desktop action or keystroke into the active macro recording session.",
    args_schema=RecordMacroStepArgs,
    preview_fn=record_macro_step_preview,
    can_remember_per_folder=False
)
def handle_record_macro_step(
    action: str,
    target_type: Optional[str] = None,
    target_value: Optional[str] = None,
    text_input: Optional[str] = None,
    key_sequence: Optional[str] = None,
    command: Optional[str] = None,
    timeout_ms: int = 5000,
    description: str = "",
    session_id: str = "default"
) -> Dict[str, Any]:
    step = macro_synthesizer.record_step({
        "action": action,
        "target_type": target_type,
        "target_value": target_value,
        "text_input": text_input,
        "key_sequence": key_sequence,
        "command": command,
        "timeout_ms": timeout_ms,
        "description": description,
    }, session_id=session_id)
    return step.model_dump()


# ==========================================
# 2. Synthesize Workflow Recipe (Tier 1)
# ==========================================

class SynthesizeWorkflowRecipeArgs(BaseModel):
    name: str = Field(..., description="Workflow recipe title")
    description: str = Field(default="", description="Workflow explanation")
    session_id: Optional[str] = Field(default=None, description="Session ID to compile from. If empty, uses provided steps.")
    steps: Optional[List[Dict[str, Any]]] = Field(default=None, description="Explicit list of step dictionaries if not using session.")
    parameters: Optional[Dict[str, Any]] = Field(default=None, description="Configurable parameter defaults")
    tags: Optional[List[str]] = Field(default=None, description="Categorization tags")

def synthesize_workflow_recipe_preview(args: Dict[str, Any]) -> str:
    name = args.get("name", "New Recipe")
    return f"Synthesize and save parameterized YAML workflow recipe '{name}'."

@registry.register(
    name="synthesize_workflow_recipe",
    tier=1,
    description="Compiles recorded or supplied desktop interaction steps into a parameterized YAML workflow recipe.",
    args_schema=SynthesizeWorkflowRecipeArgs,
    preview_fn=synthesize_workflow_recipe_preview,
    can_remember_per_folder=False
)
def handle_synthesize_workflow_recipe(
    name: str,
    description: str = "",
    session_id: Optional[str] = None,
    steps: Optional[List[Dict[str, Any]]] = None,
    parameters: Optional[Dict[str, Any]] = None,
    tags: Optional[List[str]] = None
) -> Dict[str, Any]:
    macro_steps: List[MacroStep] = []
    if session_id:
        macro_steps = macro_synthesizer.stop_recording(session_id)
    elif steps:
        macro_steps = [MacroStep(**s) for s in steps]

    recipe = macro_synthesizer.synthesize_recipe(
        name=name,
        description=description,
        steps=macro_steps,
        parameters=parameters,
        tags=tags,
    )
    saved_path = macro_synthesizer.save_recipe(recipe)
    yaml_preview = macro_synthesizer.to_yaml(recipe)

    return {
        "recipe_id": recipe.recipe_id,
        "name": recipe.name,
        "file_path": saved_path,
        "steps_count": len(recipe.steps),
        "parameters": list(recipe.parameters.keys()),
        "yaml_preview": yaml_preview,
    }


# ==========================================
# 3. Preview Workflow Execution (Tier 0)
# ==========================================

class PreviewWorkflowExecutionArgs(BaseModel):
    recipe_id: str = Field(..., description="Recipe ID or filename e.g. 'export_daily_report'")
    parameters: Optional[Dict[str, Any]] = Field(default=None, description="Parameter bindings")

def preview_workflow_execution_preview(args: Dict[str, Any]) -> str:
    r_id = args.get("recipe_id", "recipe")
    return f"Simulate execution diff and predict self-healing retargeting for workflow '{r_id}'."

@registry.register(
    name="preview_workflow_execution",
    tier=0,
    description="Simulates workflow execution, resolving parameters and testing element locators without changing desktop state.",
    args_schema=PreviewWorkflowExecutionArgs,
    preview_fn=preview_workflow_execution_preview,
    can_remember_per_folder=False
)
def handle_preview_workflow_execution(
    recipe_id: str,
    parameters: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    recipe = macro_synthesizer.load_recipe(recipe_id)
    result = workflow_engine.preview_execution(recipe, params=parameters)
    return result.model_dump()


# ==========================================
# 4. Execute Workflow Recipe (Tier 1)
# ==========================================

class ExecuteWorkflowRecipeArgs(BaseModel):
    recipe_id: str = Field(..., description="Recipe ID to execute")
    parameters: Optional[Dict[str, Any]] = Field(default=None, description="Parameter values to bind")
    dry_run: bool = Field(default=False, description="Whether to simulate actions without dispatching mouse clicks")

def execute_workflow_recipe_preview(args: Dict[str, Any]) -> str:
    r_id = args.get("recipe_id", "recipe")
    dry = " (dry run)" if args.get("dry_run") else ""
    return f"Execute automated workflow recipe '{r_id}'{dry} with self-healing element retargeting."

@registry.register(
    name="execute_workflow_recipe",
    tier=1,
    description="Executes a validated desktop workflow recipe step-by-step with live self-healing retargeting.",
    args_schema=ExecuteWorkflowRecipeArgs,
    preview_fn=execute_workflow_recipe_preview,
    can_remember_per_folder=False
)
async def handle_execute_workflow_recipe(
    recipe_id: str,
    parameters: Optional[Dict[str, Any]] = None,
    dry_run: bool = False
) -> Dict[str, Any]:
    recipe = macro_synthesizer.load_recipe(recipe_id)
    result = await workflow_engine.execute_recipe(recipe, params=parameters, dry_run=dry_run)
    return result.model_dump()


# ==========================================
# 5. List Workflow Recipes (Tier 0)
# ==========================================

class ListWorkflowRecipesArgs(BaseModel):
    pass

def list_workflow_recipes_preview(args: Dict[str, Any]) -> str:
    return "List all synthesized and stored desktop workflow recipes."

@registry.register(
    name="list_workflow_recipes",
    tier=0,
    description="Lists all saved desktop workflow recipes with their step counts, safety tiers, and parameter names.",
    args_schema=ListWorkflowRecipesArgs,
    preview_fn=list_workflow_recipes_preview,
    can_remember_per_folder=False
)
def handle_list_workflow_recipes() -> List[Dict[str, Any]]:
    return macro_synthesizer.list_recipes()
