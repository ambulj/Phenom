"""
Safety-Wrapped Multimodal Context Fusion Tools.
Registers tools with ToolRegistry for 4-channel context fusion, deictic on-screen
reference resolution, and visual-semantic grounding (Phase 21-01 FUS-01.1 / FUS-01.2).
"""

from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field

from services.backend.safety.registry import registry
from services.backend.fusion.multimodal_fuser import multimodal_fuser
from services.backend.fusion.deictic_resolver import deictic_resolver


# ==========================================
# 1. Fuse Multimodal Context (Tier 0)
# ==========================================

class FuseMultimodalContextArgs(BaseModel):
    query: str = Field(..., description="Spoken or typed intent to correlate.")
    active_app: Optional[str] = Field(default=None, description="Foreground application executable or name.")
    window_title: Optional[str] = Field(default=None, description="Foreground window title.")
    screen_text: Optional[str] = Field(default=None, description="Visible OCR or UIA on-screen text snippets.")
    active_file: Optional[str] = Field(default=None, description="Currently active source file.")
    cursor_line: Optional[int] = Field(default=None, description="Current cursor line number in file.")

def fuse_multimodal_context_preview(args: Dict[str, Any]) -> str:
    query = args.get("query", "")
    app = args.get("active_app", "focused app")
    return f"Correlate multimodal context streams (voice + {app} + AST symbols) for query '{query}'."

@registry.register(
    name="fuse_multimodal_context",
    tier=0,
    description="Fuses voice intent, active window, on-screen text, and AST symbols into an enriched context prompt.",
    args_schema=FuseMultimodalContextArgs,
    preview_fn=fuse_multimodal_context_preview,
    can_remember_per_folder=False
)
def handle_fuse_multimodal_context(
    query: str,
    active_app: Optional[str] = None,
    window_title: Optional[str] = None,
    screen_text: Optional[str] = None,
    active_file: Optional[str] = None,
    cursor_line: Optional[int] = None
) -> Dict[str, Any]:
    fused = multimodal_fuser.fuse_context(
        query=query,
        active_app=active_app,
        window_title=window_title,
        screen_text=screen_text,
        active_file=active_file,
        cursor_line=cursor_line,
    )
    return fused.model_dump()


# ==========================================
# 2. Resolve Screen Deictic Reference (Tier 0)
# ==========================================

class ResolveScreenDeicticReferenceArgs(BaseModel):
    query: str = Field(..., description="Query containing deictic reference e.g. 'this function', 'that error'.")
    screen_text: Optional[str] = Field(default=None, description="Visible OCR / code text on screen.")
    active_file: Optional[str] = Field(default=None, description="Active source file path.")
    cursor_line: Optional[int] = Field(default=None, description="Line number of editor cursor.")

def resolve_screen_deictic_reference_preview(args: Dict[str, Any]) -> str:
    query = args.get("query", "")
    return f"Resolve deictic reference in '{query}' to concrete AST codebase symbol."

@registry.register(
    name="resolve_screen_deictic_reference",
    tier=0,
    description="Resolves conversational references ('this function', 'this class') to concrete AST symbols.",
    args_schema=ResolveScreenDeicticReferenceArgs,
    preview_fn=resolve_screen_deictic_reference_preview,
    can_remember_per_folder=False
)
def handle_resolve_screen_deictic_reference(
    query: str,
    screen_text: Optional[str] = None,
    active_file: Optional[str] = None,
    cursor_line: Optional[int] = None
) -> Dict[str, Any]:
    resolution = deictic_resolver.resolve(
        query=query,
        screen_text=screen_text,
        active_file=active_file,
        cursor_line=cursor_line,
    )
    return resolution.model_dump()


# ==========================================
# 3. Get Active Fusion State (Tier 0)
# ==========================================

class GetActiveFusionStateArgs(BaseModel):
    pass

def get_active_fusion_state_preview(args: Dict[str, Any]) -> str:
    return "Retrieve real-time multimodal fusion status and connected stream telemetry."

@registry.register(
    name="get_active_fusion_state",
    tier=0,
    description="Returns telemetry metrics for active multimodal context fusion channels.",
    args_schema=GetActiveFusionStateArgs,
    preview_fn=get_active_fusion_state_preview,
    can_remember_per_folder=False
)
def handle_get_active_fusion_state() -> Dict[str, Any]:
    return {
        "status": "active",
        "channels": ["voice_stt", "screen_ocr", "active_window_uia", "ast_symbols"],
        "latency_target_ms": 15.0,
        "deictic_resolution_enabled": True,
    }
