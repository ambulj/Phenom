"""Natural Language Macro Synthesis & Action Recording Tools for Phenom (Milestone 32 Phase 2).

Registers 5 specialized tools in ToolRegistry:
1. compile_natural_language_macro (Tier 1)
2. start_macro_demonstration_recording (Tier 1)
3. stop_macro_demonstration_recording (Tier 1)
4. execute_saved_macro (Tier 1)
5. list_saved_macros (Tier 0)
"""

from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field

from services.backend.safety.registry import registry
from services.backend.orchestration.macro_engine import (
    macro_engine,
    RecordedActionType,
)


# ==========================================
# 1. Compile Natural Language Macro (Tier 1)
# ==========================================

class CompileNaturalLanguageMacroArgs(BaseModel):
    intent: str = Field(..., description="Conversational directive or voice command describing the macro.")
    macro_name: Optional[str] = Field(None, description="Optional name for the macro.")
    voice_trigger: Optional[str] = Field(None, description="Optional spoken trigger phrase (e.g. 'run morning sync').")


def preview_compile_natural_language_macro(args: Dict[str, Any]) -> str:
    intent = args.get("intent", "")
    name = args.get("macro_name", "Macro")
    return f"Compile natural language macro '{name}': \"{intent[:50]}...\""


@registry.register(
    name="compile_natural_language_macro",
    tier=1,
    description="Translates a natural language or voice directive into a structured, parameterized workflow macro DAG (Tier 1 staging).",
    args_schema=CompileNaturalLanguageMacroArgs,
    preview_fn=preview_compile_natural_language_macro,
    can_remember_per_folder=False,
)
def handle_compile_natural_language_macro(
    intent: str,
    macro_name: Optional[str] = None,
    voice_trigger: Optional[str] = None,
) -> Dict[str, Any]:
    macro_def = macro_engine.compile_natural_language_macro(
        intent=intent,
        macro_name=macro_name,
        voice_trigger=voice_trigger,
    )
    return macro_def.model_dump()


# ==========================================
# 2. Start Macro Demonstration Recording (Tier 1)
# ==========================================

class StartMacroRecordingArgs(BaseModel):
    recording_name: str = Field(..., description="Name for the demonstration recording session.")


def preview_start_macro_recording(args: Dict[str, Any]) -> str:
    name = args.get("recording_name", "Recording")
    return f"Start demonstration recording session for '{name}'"


@registry.register(
    name="start_macro_demonstration_recording",
    tier=1,
    description="Starts capturing GUI actions and keystrokes for demonstration macro compilation (Tier 1 staging).",
    args_schema=StartMacroRecordingArgs,
    preview_fn=preview_start_macro_recording,
    can_remember_per_folder=False,
)
def handle_start_macro_recording(recording_name: str) -> Dict[str, Any]:
    rec_id = macro_engine.start_recording(recording_name)
    return {"recording_id": rec_id, "name": recording_name, "status": "RECORDING"}


# ==========================================
# 3. Stop Macro Demonstration Recording (Tier 1)
# ==========================================

class StopMacroRecordingArgs(BaseModel):
    macro_name: str = Field(..., description="Name to assign to the synthesized macro.")
    voice_trigger: Optional[str] = Field(None, description="Optional spoken trigger phrase.")


def preview_stop_macro_recording(args: Dict[str, Any]) -> str:
    name = args.get("macro_name", "Macro")
    return f"Stop recording and synthesize demonstration macro '{name}'"


@registry.register(
    name="stop_macro_demonstration_recording",
    tier=1,
    description="Stops recording, suppresses noise, parameterizes variables, and saves macro DAG (Tier 1 compilation).",
    args_schema=StopMacroRecordingArgs,
    preview_fn=preview_stop_macro_recording,
    can_remember_per_folder=False,
)
def handle_stop_macro_recording(
    macro_name: str,
    voice_trigger: Optional[str] = None,
) -> Dict[str, Any]:
    macro_def = macro_engine.stop_recording_and_synthesize(
        macro_name=macro_name,
        voice_trigger=voice_trigger,
    )
    return macro_def.model_dump()


# ==========================================
# 4. Execute Saved Macro (Tier 1)
# ==========================================

class ExecuteSavedMacroArgs(BaseModel):
    macro_id: str = Field(..., description="ID, name, or voice trigger of the saved macro.")
    parameters: Optional[Dict[str, Any]] = Field(None, description="Optional runtime parameters or variable overrides.")


def preview_execute_saved_macro(args: Dict[str, Any]) -> str:
    m_id = args.get("macro_id", "")
    return f"Execute saved macro '{m_id}'"


@registry.register(
    name="execute_saved_macro",
    tier=1,
    description="Executes a previously saved natural language or recorded macro DAG (Tier 1 execution).",
    args_schema=ExecuteSavedMacroArgs,
    preview_fn=preview_execute_saved_macro,
    can_remember_per_folder=False,
)
def handle_execute_saved_macro(
    macro_id: str,
    parameters: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    result = macro_engine.execute_macro(macro_id=macro_id, parameter_values=parameters)
    return result


# ==========================================
# 5. List Saved Macros (Tier 0)
# ==========================================

class ListSavedMacrosArgs(BaseModel):
    pass


def preview_list_saved_macros(args: Dict[str, Any]) -> str:
    return "List all saved macros and trigger phrases"


@registry.register(
    name="list_saved_macros",
    tier=0,
    description="Returns read-only inventory of stored macros and their voice triggers (Tier 0 read-only).",
    args_schema=ListSavedMacrosArgs,
    preview_fn=preview_list_saved_macros,
    can_remember_per_folder=False,
)
def handle_list_saved_macros() -> List[Dict[str, Any]]:
    return macro_engine.list_macros()
