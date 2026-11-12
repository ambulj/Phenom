"""
Safety-Wrapped Voice-Code Synapse & Real-Time Co-Editing Tools.
Registers tools with ToolRegistry for spoken AST code mutations, dry-run diffs,
and procedural in-memory acoustic earcons (Phase 23-03 SYN-01 / VOX-06).
"""

from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field

from services.backend.safety.registry import registry
from services.backend.synapse.voice_code_synapse import voice_code_synapse
from services.backend.synapse.acoustic_earcon_manager import acoustic_earcon_manager


# ==========================================
# 1. Apply Voice Code Mutation (Tier 1)
# ==========================================

class ApplyVoiceCodeMutationArgs(BaseModel):
    file_path: str = Field(..., description="Target source code filepath")
    target_symbol: str = Field(..., description="Function or class name to mutate")
    mutation_type: str = Field(..., description="rename_param, add_type_hint, replace_return, wrap_try_except")
    parameters: Dict[str, Any] = Field(default_factory=dict, description="Mutation parameters")
    dry_run: Optional[bool] = Field(default=False, description="Whether to preview diff without applying changes")

def apply_voice_code_mutation_preview(args: Dict[str, Any]) -> str:
    fp = args.get("file_path", "file.py")
    sym = args.get("target_symbol", "symbol")
    mtype = args.get("mutation_type", "mutation")
    dr = " (dry-run preview)" if args.get("dry_run") else ""
    return f"Apply spoken AST mutation '{mtype}' to '{sym}' in '{fp}'{dr}."

@registry.register(
    name="apply_voice_code_mutation",
    tier=1,
    description="Transforms spoken programming directives into atomic AST buffer modifications with unified diffs.",
    args_schema=ApplyVoiceCodeMutationArgs,
    preview_fn=apply_voice_code_mutation_preview,
    can_remember_per_folder=False
)
def handle_apply_voice_code_mutation(
    file_path: str,
    target_symbol: str,
    mutation_type: str,
    parameters: Optional[Dict[str, Any]] = None,
    dry_run: bool = False,
) -> Dict[str, Any]:
    res = voice_code_synapse.apply_spoken_mutation(
        file_path=file_path,
        target_symbol=target_symbol,
        mutation_type=mutation_type,
        parameters=parameters or {},
        dry_run=dry_run,
    )
    return res.model_dump()


# ==========================================
# 2. Play Acoustic Earcon (Tier 0)
# ==========================================

class PlayAcousticEarconArgs(BaseModel):
    cue_type: str = Field(..., description="Earcon type: 'ast_success', 'syntax_error', 'test_passed', 'guardian_halt'")

def play_acoustic_earcon_preview(args: Dict[str, Any]) -> str:
    cue = args.get("cue_type", "cue")
    return f"Synthesize in-memory procedural acoustic earcon '{cue}'."

@registry.register(
    name="play_acoustic_earcon",
    tier=0,
    description="Generates a non-verbal procedural acoustic cue in RAM to signal AST syntax or test outcomes.",
    args_schema=PlayAcousticEarconArgs,
    preview_fn=play_acoustic_earcon_preview,
    can_remember_per_folder=False
)
def handle_play_acoustic_earcon(cue_type: str) -> Dict[str, Any]:
    pcm = acoustic_earcon_manager.generate_earcon_pcm(cue_type)
    return {
        "cue_type": cue_type,
        "pcm_bytes_length": len(pcm),
        "status": "synthesized_in_ram",
    }


# ==========================================
# 3. Get Synapse Buffer State (Tier 0)
# ==========================================

class GetSynapseBufferStateArgs(BaseModel):
    file_path: str = Field(..., description="File path to check active buffer content")

def get_synapse_buffer_state_preview(args: Dict[str, Any]) -> str:
    fp = args.get("file_path", "file.py")
    return f"Inspect live AST co-editor buffer content for '{fp}'."

@registry.register(
    name="get_synapse_buffer_state",
    tier=0,
    description="Returns the active in-memory code buffer and transaction history for a source file.",
    args_schema=GetSynapseBufferStateArgs,
    preview_fn=get_synapse_buffer_state_preview,
    can_remember_per_folder=False
)
def handle_get_synapse_buffer_state(file_path: str) -> Dict[str, Any]:
    content = voice_code_synapse.get_buffer_content(file_path)
    return {
        "file_path": file_path,
        "has_content": content is not None,
        "content_length": len(content) if content else 0,
        "active_transactions": len(voice_code_synapse._history),
    }


# Programmatic aliases
apply_voice_code_mutation = handle_apply_voice_code_mutation
play_acoustic_earcon = handle_play_acoustic_earcon
get_synapse_buffer_state = handle_get_synapse_buffer_state
