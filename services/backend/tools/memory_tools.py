"""
Phenom Long-Term Memory, RAG, and Vault Tools
Safety Layer registered tools:
- Tier 0: search_memory, search_photos, index_folder_documents, vault_read_note, summarize_long_document, organize_downloads_dry_run
- Tier 1: vault_write_note, vault_append_daily_log, organize_downloads_apply, undo_cleanup
- Tier 3: modify_photo, delete_photo (PERMANENTLY BLOCKED)
"""

from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field
from services.backend.safety.registry import registry
from services.backend.memory.vector_store import vector_store
from services.backend.memory.vault import vault_manager
from services.backend.memory.photo_indexer import photo_indexer
from services.backend.memory.cleanup_organizer import cleanup_organizer
from services.backend.memory.doc_reader import doc_reader
from services.backend.orchestrator.engine import orchestrator

# ==========================================
# Tier 0 Tools (Read-Only)
# ==========================================

class SearchMemoryArgs(BaseModel):
    query: str = Field(description="Search query to retrieve from documents, notes, and past conversations")
    folder_filter: Optional[str] = Field(default=None, description="Optional folder path to constrain search")

@registry.register(
    name="search_memory",
    tier=0,
    description="Searches indexed documents, notes, and past conversation memory with source citations",
    args_schema=SearchMemoryArgs,
    preview_fn=lambda a: f"Search memory & documents for: '{a.get('query')}'"
)
def search_memory(query: str, folder_filter: Optional[str] = None) -> Dict[str, Any]:
    doc_results = vector_store.search(query, top_k=5, folder_filter=folder_filter)
    conv_results = vector_store.search_conversations(query, limit=3)
    return {
        "query": query,
        "document_matches": doc_results,
        "conversation_matches": conv_results
    }

class SearchPhotosArgs(BaseModel):
    query: str = Field(description="Description, tags, or keywords to search photos by")

@registry.register(
    name="search_photos",
    tier=0,
    description="Searches indexed photos by natural language description, tags, or metadata without modifying them",
    args_schema=SearchPhotosArgs,
    preview_fn=lambda a: f"Search photos matching description: '{a.get('query')}'"
)
def search_photos(query: str) -> List[Dict[str, Any]]:
    return photo_indexer.search_photos(query)

class IndexFolderDocumentsArgs(BaseModel):
    folder_path: str = Field(description="Path to folder to index for semantic vector search")

@registry.register(
    name="index_folder_documents",
    tier=0,
    description="Scans and incrementally indexes documents in a folder into the encrypted vector store",
    args_schema=IndexFolderDocumentsArgs,
    preview_fn=lambda a: f"Index documents in: '{a.get('folder_path')}'"
)
def index_folder_documents(folder_path: str) -> Dict[str, Any]:
    return vector_store.index_folder(folder_path)

class VaultReadNoteArgs(BaseModel):
    title_or_path: str = Field(description="Note title or path inside vault/")

@registry.register(
    name="vault_read_note",
    tier=0,
    description="Reads a plain Markdown note from the Obsidian vault",
    args_schema=VaultReadNoteArgs,
    preview_fn=lambda a: f"Read Obsidian vault note: '{a.get('title_or_path')}'"
)
def vault_read_note(title_or_path: str) -> str:
    return vault_manager.read_note(title_or_path)

class SummarizeLongDocumentArgs(BaseModel):
    file_path: str = Field(description="Path to PDF, docx, pptx, or text document to summarize")

@registry.register(
    name="summarize_long_document",
    tier=0,
    description="Extracts text from long documents (PDF/Word/PowerPoint) and generates structured summary",
    args_schema=SummarizeLongDocumentArgs,
    preview_fn=lambda a: f"Summarize document: '{a.get('file_path')}'"
)
def summarize_long_document(file_path: str) -> Dict[str, Any]:
    text = doc_reader.read_document(file_path)
    chunks = doc_reader.chunk_text(text, chunk_size=500, overlap=50)
    summary_preview = f"Document '{file_path}' ({len(text)} characters, {len(chunks)} chunks). First section: {chunks[0][:300]}..." if chunks else "Empty document."
    return {
        "file_path": file_path,
        "total_chunks": len(chunks),
        "summary": summary_preview
    }

class OrganizeDownloadsDryRunArgs(BaseModel):
    downloads_path: str = Field(description="Path to Downloads directory to evaluate for cleanup")

@registry.register(
    name="organize_downloads_dry_run",
    tier=0,
    description="Simulates Downloads folder organization and duplicate detection without modifying any files",
    args_schema=OrganizeDownloadsDryRunArgs,
    preview_fn=lambda a: f"Preview Downloads cleanup plan for: '{a.get('downloads_path')}'"
)
def organize_downloads_dry_run(downloads_path: str) -> Dict[str, Any]:
    return cleanup_organizer.generate_dry_run(downloads_path)

# ==========================================
# Tier 1 Tools (Reversible Changes)
# ==========================================

class VaultWriteNoteArgs(BaseModel):
    title: str = Field(description="Title of note")
    content: str = Field(description="Markdown content to write")
    subfolder: str = Field(default="Notes", description="Subfolder inside vault/")

@registry.register(
    name="vault_write_note",
    tier=1,
    description="Creates or updates a note in the Obsidian vault",
    args_schema=VaultWriteNoteArgs,
    preview_fn=lambda a: f"Write note '{a.get('title')}' in Obsidian vault ({a.get('subfolder', 'Notes')})",
    can_remember_per_folder=True
)
def vault_write_note(title: str, content: str, subfolder: str = "Notes") -> str:
    return vault_manager.write_note(title, content, subfolder)

class VaultAppendDailyLogArgs(BaseModel):
    entry: str = Field(description="Log text to append to today's daily log")

@registry.register(
    name="vault_append_daily_log",
    tier=1,
    description="Appends a timestamped log entry to today's Obsidian daily log",
    args_schema=VaultAppendDailyLogArgs,
    preview_fn=lambda a: f"Append entry to Obsidian daily log: '{a.get('entry')[:50]}...'",
    can_remember_per_folder=True
)
def vault_append_daily_log(entry: str) -> str:
    return vault_manager.append_daily_log(entry)

class OrganizeDownloadsApplyArgs(BaseModel):
    plan: Dict[str, Any] = Field(description="Dry run plan generated by organize_downloads_dry_run")

@registry.register(
    name="organize_downloads_apply",
    tier=1,
    description="Executes Downloads cleanup plan: categorizes files and moves duplicates to recycle bin",
    args_schema=OrganizeDownloadsApplyArgs,
    preview_fn=lambda a: f"Apply Downloads cleanup: {a.get('plan', {}).get('moves_count', 0)} moves, {a.get('plan', {}).get('duplicates_count', 0)} duplicate recycles",
    can_remember_per_folder=True
)
def organize_downloads_apply(plan: Dict[str, Any]) -> Dict[str, Any]:
    summary, undo_token = cleanup_organizer.apply_cleanup(plan)
    return summary

class UndoCleanupArgs(BaseModel):
    undo_token: str = Field(description="Undo token returned by organize_downloads_apply")

@registry.register(
    name="undo_cleanup",
    tier=1,
    description="Rolls back previous Downloads cleanup operations, restoring files to original paths",
    args_schema=UndoCleanupArgs,
    preview_fn=lambda a: f"Rollback cleanup operation: '{a.get('undo_token')}'"
)
def undo_cleanup(undo_token: str) -> Dict[str, Any]:
    return cleanup_organizer.undo_cleanup(undo_token)

# ==========================================
# Tier 3 Tools (Permanently Blocked on Photos)
# ==========================================

class ModifyPhotoArgs(BaseModel):
    photo_path: str = Field(description="Path of photo")

@registry.register(
    name="modify_photo",
    tier=3,
    description="Attempts to edit, rename, or move a photo. Permanently blocked.",
    args_schema=ModifyPhotoArgs,
    preview_fn=lambda a: f"ATTEMPT TO MODIFY PHOTO: '{a.get('photo_path')}'"
)
def modify_photo(photo_path: str):
    raise PermissionError("Photo modification is strictly prohibited by SAFETY.md Rule #6. Photos are indexed and searched only.")

class DeletePhotoArgs(BaseModel):
    photo_path: str = Field(description="Path of photo")

@registry.register(
    name="delete_photo",
    tier=3,
    description="Attempts to delete a photo. Permanently blocked.",
    args_schema=DeletePhotoArgs,
    preview_fn=lambda a: f"ATTEMPT TO DELETE PHOTO: '{a.get('photo_path')}'"
)
def delete_photo(photo_path: str):
    raise PermissionError("Photo deletion is strictly prohibited by SAFETY.md Rule #6. Photos are indexed and searched only.")
