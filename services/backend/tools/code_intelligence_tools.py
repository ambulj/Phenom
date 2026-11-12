"""
Safety-Wrapped Code Intelligence Tools (Phase 20-01 DEV-01.1 / DEV-01.2 / DEV-01.3).
Registers tools with ToolRegistry for AST parsing, semantic symbol discovery, and multi-file refactoring.
"""

from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field

from services.backend.safety.registry import registry
from services.backend.coding.workspace_indexer import workspace_indexer
from services.backend.coding.refactor_engine import refactor_engine


# ==========================================
# 1. Index Workspace Symbols (Tier 0)
# ==========================================

class IndexWorkspaceSymbolsArgs(BaseModel):
    max_files: Optional[int] = Field(default=1000, description="Maximum number of code files to scan.")

def index_workspace_symbols_preview(args: Dict[str, Any]) -> str:
    limit = args.get("max_files", 1000)
    return f"Scan workspace AST and index symbols across up to {limit} files."

@registry.register(
    name="index_workspace_symbols",
    tier=0,
    description="Parses workspace AST and builds an in-memory symbol table and dependency call graph.",
    args_schema=IndexWorkspaceSymbolsArgs,
    preview_fn=index_workspace_symbols_preview,
    can_remember_per_folder=False
)
def handle_index_workspace_symbols(max_files: int = 1000) -> Dict[str, Any]:
    return workspace_indexer.index_workspace(max_files=max_files)


# ==========================================
# 2. Lookup Symbol Definition (Tier 0)
# ==========================================

class LookupSymbolDefinitionArgs(BaseModel):
    symbol_name: str = Field(description="Name of the function, class, or type to locate.")

def lookup_symbol_definition_preview(args: Dict[str, Any]) -> str:
    name = args.get("symbol_name", "")
    return f"Look up definition, file path, signature, and docstring for symbol '{name}'."

@registry.register(
    name="lookup_symbol_definition",
    tier=0,
    description="Locates exact symbol definitions, signatures, line numbers, and docstrings.",
    args_schema=LookupSymbolDefinitionArgs,
    preview_fn=lookup_symbol_definition_preview,
    can_remember_per_folder=False
)
def handle_lookup_symbol_definition(symbol_name: str) -> Dict[str, Any]:
    definitions = workspace_indexer.lookup_symbol(symbol_name)
    return {
        "symbol": symbol_name,
        "count": len(definitions),
        "definitions": definitions
    }


# ==========================================
# 3. Find Symbol References (Tier 0)
# ==========================================

class FindSymbolReferencesArgs(BaseModel):
    symbol_name: str = Field(description="Name of the symbol whose call sites and callers to discover.")

def find_symbol_references_preview(args: Dict[str, Any]) -> str:
    name = args.get("symbol_name", "")
    return f"Discover all call sites and incoming references to symbol '{name}' across the codebase."

@registry.register(
    name="find_symbol_references",
    tier=0,
    description="Traces the dependency call graph to discover all callers and references to a symbol.",
    args_schema=FindSymbolReferencesArgs,
    preview_fn=find_symbol_references_preview,
    can_remember_per_folder=False
)
def handle_find_symbol_references(symbol_name: str) -> Dict[str, Any]:
    return workspace_indexer.find_references(symbol_name)


# ==========================================
# 4. Preview Code Refactor (Tier 0)
# ==========================================

class PreviewCodeRefactorArgs(BaseModel):
    old_symbol: str = Field(description="Existing identifier or symbol name.")
    new_symbol: str = Field(description="Replacement identifier or symbol name.")
    target_files: Optional[List[str]] = Field(default=None, description="Optional subset of files to inspect.")

def preview_code_refactor_preview(args: Dict[str, Any]) -> str:
    old = args.get("old_symbol", "")
    new = args.get("new_symbol", "")
    return f"Generate unified diff preview for renaming '{old}' -> '{new}' without writing to disk."

@registry.register(
    name="preview_code_refactor",
    tier=0,
    description="Generates syntax-highlighted unified diffs for a proposed multi-file symbol refactor.",
    args_schema=PreviewCodeRefactorArgs,
    preview_fn=preview_code_refactor_preview,
    can_remember_per_folder=False
)
def handle_preview_code_refactor(
    old_symbol: str,
    new_symbol: str,
    target_files: Optional[List[str]] = None
) -> Dict[str, Any]:
    return refactor_engine.preview_symbol_rename(old_symbol, new_symbol, target_files)


# ==========================================
# 5. Apply Code Refactor (Tier 1)
# ==========================================

class ApplyCodeRefactorArgs(BaseModel):
    file_updates: Dict[str, str] = Field(description="Mapping of file path to new full content.")

def apply_code_refactor_preview(args: Dict[str, Any]) -> str:
    updates = args.get("file_updates", {})
    paths = list(updates.keys())
    preview_paths = ", ".join(paths[:3]) + (f" and {len(paths)-3} more" if len(paths) > 3 else "")
    return f"Apply atomic multi-file refactor to {len(paths)} files: {preview_paths}."

@registry.register(
    name="apply_code_refactor",
    tier=1,
    description="Atomically applies reviewed multi-file code modifications with automatic rollback on error.",
    args_schema=ApplyCodeRefactorArgs,
    preview_fn=apply_code_refactor_preview,
    can_remember_per_folder=False
)
def handle_apply_code_refactor(file_updates: Dict[str, str]) -> Dict[str, Any]:
    return refactor_engine.apply_refactor(file_updates)
