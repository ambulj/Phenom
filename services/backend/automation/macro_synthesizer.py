"""
Autonomous Desktop Macro Synthesis Engine.
Records multi-app desktop interactions, keystrokes, and terminal executions,
synthesizing parameterized, idempotent YAML workflow recipes with self-healing targets.

Part of Phenom 21.0 Sovereign Omnimodal Intelligence (MAC-02.1 / AUT-02.1).
"""

import os
import re
import time
import yaml
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple
from pydantic import BaseModel, Field

from services.backend.safety.guardian import guardian
from services.backend.automation.gui_controller import Rule8ViolationError


class MacroStep(BaseModel):
    step_id: int = Field(..., description="1-based step execution index")
    action: str = Field(..., description="Action type: click, type, hotkey, wait, bash_exec, assert_screen")
    target_type: Optional[str] = Field(default=None, description="Selector type: uia_id, ocr_text, class_name, coordinate")
    target_value: Optional[str] = Field(default=None, description="Selector value or expression, supports ${param}")
    text_input: Optional[str] = Field(default=None, description="Text to type, supports ${param}")
    key_sequence: Optional[str] = Field(default=None, description="Keyboard shortcut combination e.g. 'ctrl+s'")
    command: Optional[str] = Field(default=None, description="CLI command string for bash_exec steps")
    coordinates: Optional[Tuple[int, int]] = Field(default=None, description="Fallback screen coordinates (x, y)")
    timeout_ms: int = Field(default=5000, description="Step timeout in milliseconds")
    description: str = Field(default="", description="Human-readable explanation of step")
    heal_strategy: str = Field(default="ocr_fallback", description="Strategy when target drifts: ocr_fallback, uia_fuzzy, relative_coord")


class ParameterSpec(BaseModel):
    name: str = Field(..., description="Parameter placeholder name e.g. 'file_name'")
    default_value: Any = Field(default="", description="Default value if not provided")
    description: str = Field(default="", description="Description of the parameter")
    required: bool = Field(default=False, description="Whether parameter must be supplied")


class WorkflowRecipe(BaseModel):
    recipe_id: str = Field(..., description="Unique slug identifier for the workflow")
    name: str = Field(..., description="Human-readable recipe title")
    description: str = Field(default="", description="Workflow purpose and instructions")
    parameters: Dict[str, ParameterSpec] = Field(default_factory=dict, description="Configurable workflow parameters")
    steps: List[MacroStep] = Field(default_factory=list, description="Ordered sequence of macro steps")
    created_at: str = Field(default_factory=lambda: datetime.utcnow().isoformat(), description="ISO timestamp")
    tags: List[str] = Field(default_factory=list, description="Categorization tags")
    safety_tier: int = Field(default=1, description="Safety confirmation tier (1 or 2)")


class MacroSynthesizer:
    """
    Records and compiles live desktop interaction streams into parameterized YAML workflow recipes.
    """

    PARAM_RE = re.compile(r"\$\{([A-Za-z_][A-Za-z0-9_]*)\}")
    RULE_8_PAYMENT_RE = re.compile(
        r"\b(?:checkout|place\s+order|pay\s+now|buy\s+now|complete\s+purchase|complete\s+payment|payment|credit\s+card|cvv|password)\b",
        re.IGNORECASE
    )

    def __init__(self, recipe_dir: Optional[str] = None):
        self.recipe_dir = recipe_dir or os.path.join(os.path.dirname(__file__), "recipes")
        os.makedirs(self.recipe_dir, exist_ok=True)
        self._active_sessions: Dict[str, List[MacroStep]] = {}

    def start_recording(self, session_id: str = "default") -> None:
        """Starts a new macro recording session."""
        if guardian.is_halted:
            raise PermissionError("Guardian kill switch is active. Macro recording blocked.")
        self._active_sessions[session_id] = []

    def record_step(self, step_data: Dict[str, Any], session_id: str = "default") -> MacroStep:
        """
        Appends a raw interaction step to the recording session.
        Validates against Rule 8 anti-checkout invariants.
        """
        if guardian.is_halted:
            raise PermissionError("Guardian kill switch is active. Macro recording blocked.")

        # Rule 8 Invariant check
        raw_repr = str(step_data)
        if self.RULE_8_PAYMENT_RE.search(raw_repr):
            raise Rule8ViolationError(
                f"Rule 8 Violation: Cannot record action targeting payment/checkout control: {raw_repr}"
            )

        session = self._active_sessions.setdefault(session_id, [])
        step_id = len(session) + 1

        step = MacroStep(
            step_id=step_id,
            action=step_data.get("action", "click"),
            target_type=step_data.get("target_type"),
            target_value=step_data.get("target_value"),
            text_input=step_data.get("text_input"),
            key_sequence=step_data.get("key_sequence"),
            command=step_data.get("command"),
            coordinates=step_data.get("coordinates"),
            timeout_ms=step_data.get("timeout_ms", 5000),
            description=step_data.get("description", f"Step {step_id}"),
            heal_strategy=step_data.get("heal_strategy", "ocr_fallback"),
        )
        session.append(step)
        return step

    def stop_recording(self, session_id: str = "default") -> List[MacroStep]:
        """Stops recording and returns the recorded steps."""
        return self._active_sessions.pop(session_id, [])

    def synthesize_recipe(
        self,
        name: str,
        description: str = "",
        steps: Optional[List[MacroStep]] = None,
        parameters: Optional[Dict[str, Any]] = None,
        recipe_id: Optional[str] = None,
        tags: Optional[List[str]] = None,
    ) -> WorkflowRecipe:
        """
        Compiles macro steps into a structured WorkflowRecipe, detecting and binding parameter placeholders.
        """
        if guardian.is_halted:
            raise PermissionError("Guardian kill switch is active. Recipe synthesis blocked.")

        effective_steps = steps or []
        slug = recipe_id or re.sub(r"[^a-z0-9_]+", "_", name.lower().strip()).strip("_")

        # Discover parameter placeholders
        discovered_params: Dict[str, ParameterSpec] = {}
        if parameters:
            for p_name, p_val in parameters.items():
                if isinstance(p_val, dict):
                    discovered_params[p_name] = ParameterSpec(**p_val)
                elif isinstance(p_val, ParameterSpec):
                    discovered_params[p_name] = p_val
                else:
                    discovered_params[p_name] = ParameterSpec(
                        name=p_name, default_value=p_val, description=f"Parameter {p_name}"
                    )

        for step in effective_steps:
            for field_val in (step.target_value, step.text_input, step.command):
                if field_val:
                    for match in self.PARAM_RE.findall(field_val):
                        if match not in discovered_params:
                            discovered_params[match] = ParameterSpec(
                                name=match,
                                default_value="",
                                description=f"Extracted parameter {match}",
                                required=True,
                            )

        # Assess safety tier: min Tier 1, Tier 2 if bash_exec exists
        safety_tier = 1
        if any(s.action == "bash_exec" for s in effective_steps):
            safety_tier = 2

        recipe = WorkflowRecipe(
            recipe_id=slug,
            name=name,
            description=description,
            parameters=discovered_params,
            steps=effective_steps,
            tags=tags or ["macro", "synthesized"],
            safety_tier=safety_tier,
        )
        return recipe

    def to_yaml(self, recipe: WorkflowRecipe) -> str:
        """Converts WorkflowRecipe to clean, readable YAML."""
        data = recipe.model_dump()
        return yaml.dump(data, sort_keys=False, default_flow_style=False)

    def from_yaml(self, yaml_content: str) -> WorkflowRecipe:
        """Parses a YAML string into a WorkflowRecipe."""
        data = yaml.safe_load(yaml_content)
        if not isinstance(data, dict):
            raise ValueError("Invalid YAML recipe format: expected mapping.")
        return WorkflowRecipe(**data)

    def save_recipe(self, recipe: WorkflowRecipe) -> str:
        """Saves recipe YAML to recipe_dir."""
        file_path = os.path.join(self.recipe_dir, f"{recipe.recipe_id}.yaml")
        yaml_str = self.to_yaml(recipe)
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(yaml_str)
        return file_path

    def load_recipe(self, recipe_id: str) -> WorkflowRecipe:
        """Loads a recipe by recipe_id or relative filename."""
        clean_id = recipe_id.replace(".yaml", "")
        file_path = os.path.join(self.recipe_dir, f"{clean_id}.yaml")
        if not os.path.isfile(file_path):
            raise FileNotFoundError(f"Workflow recipe '{recipe_id}' not found at {file_path}")
        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()
        return self.from_yaml(content)

    def list_recipes(self) -> List[Dict[str, Any]]:
        """Lists all stored recipes in recipe_dir."""
        results = []
        if not os.path.exists(self.recipe_dir):
            return results
        for f in os.listdir(self.recipe_dir):
            if f.endswith(".yaml"):
                try:
                    p = os.path.join(self.recipe_dir, f)
                    with open(p, "r", encoding="utf-8") as fp:
                        r = self.from_yaml(fp.read())
                        results.append({
                            "recipe_id": r.recipe_id,
                            "name": r.name,
                            "description": r.description,
                            "steps_count": len(r.steps),
                            "safety_tier": r.safety_tier,
                            "parameters": list(r.parameters.keys()),
                        })
                except Exception:
                    continue
        return results


# Global singleton
macro_synthesizer = MacroSynthesizer()
