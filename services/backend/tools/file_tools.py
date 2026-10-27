"""
Phenom File Tools
Strictly registered in the Safety Layer with risk tiers, argument schemas,
human-readable previews, and undo capabilities where applicable.
"""

import os
import shutil
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field
import send2trash
from services.backend.safety.registry import registry

# ==========================================
# Tier 0 (Read-Only) File Tools
# ==========================================

class ListFilesArgs(BaseModel):
    path: str = Field(description="Directory path to list")

@registry.register(
    name="list_files",
    tier=0,
    description="List files and subdirectories in a folder",
    args_schema=ListFilesArgs,
    preview_fn=lambda a: f"List contents of folder: {a.get('path')}"
)
def list_files(path: str) -> List[Dict[str, Any]]:
    norm_path = os.path.abspath(path)
    if not os.path.exists(norm_path):
        raise FileNotFoundError(f"Directory not found: {path}")
    if not os.path.isdir(norm_path):
        raise NotADirectoryError(f"Path is not a directory: {path}")

    entries = []
    for item in os.listdir(norm_path):
        full_item = os.path.join(norm_path, item)
        is_dir = os.path.isdir(full_item)
        size = 0 if is_dir else os.path.getsize(full_item)
        entries.append({
            "name": item,
            "path": full_item,
            "is_directory": is_dir,
            "size_bytes": size
        })
    return entries

class ReadFileArgs(BaseModel):
    path: str = Field(description="File path to read")
    max_bytes: int = Field(default=50000, description="Maximum bytes to read")

@registry.register(
    name="read_file",
    tier=0,
    description="Read textual contents of a file",
    args_schema=ReadFileArgs,
    preview_fn=lambda a: f"Read contents of file: {a.get('path')}"
)
def read_file(path: str, max_bytes: int = 50000) -> str:
    norm_path = os.path.abspath(path)
    if not os.path.exists(norm_path):
        raise FileNotFoundError(f"File not found: {path}")
    if not os.path.isfile(norm_path):
        raise IsADirectoryError(f"Path is a directory, not a file: {path}")

    with open(norm_path, "r", encoding="utf-8", errors="replace") as f:
        return f.read(max_bytes)

class SearchFilesByNameArgs(BaseModel):
    directory: str = Field(description="Directory to search in")
    query: str = Field(description="File name substring to search for")
    max_results: int = Field(default=50, description="Maximum results to return")

@registry.register(
    name="search_files_by_name",
    tier=0,
    description="Search for files by name substring within a directory",
    args_schema=SearchFilesByNameArgs,
    preview_fn=lambda a: f"Search in '{a.get('directory')}' for files matching '{a.get('query')}'"
)
def search_files_by_name(directory: str, query: str, max_results: int = 50) -> List[str]:
    norm_dir = os.path.abspath(directory)
    if not os.path.exists(norm_dir):
        raise FileNotFoundError(f"Directory not found: {directory}")

    matches = []
    lower_query = query.lower()
    for root, dirs, files in os.walk(norm_dir):
        for f in files:
            if lower_query in f.lower():
                matches.append(os.path.join(root, f))
                if len(matches) >= max_results:
                    return matches
    return matches

# ==========================================
# Tier 1 (Reversible Change) File Tools
# ==========================================

class CreateFileArgs(BaseModel):
    path: str = Field(description="File path to create")
    content: str = Field(default="", description="Text content to write into the file")

@registry.register(
    name="create_file",
    tier=1,
    description="Create or overwrite a file with specific content",
    args_schema=CreateFileArgs,
    preview_fn=lambda a: f"Create file at '{a.get('path')}' ({len(a.get('content', ''))} characters)",
    can_remember_per_folder=True,
    undo_fn=lambda a, res: send2trash.send2trash(a["path"]) if os.path.exists(a["path"]) else None
)
def create_file(path: str, content: str = "") -> Dict[str, Any]:
    norm_path = os.path.abspath(path)
    os.makedirs(os.path.dirname(norm_path), exist_ok=True)
    with open(norm_path, "w", encoding="utf-8") as f:
        f.write(content)
    return {"path": norm_path, "bytes_written": len(content.encode("utf-8"))}

class CreateFolderArgs(BaseModel):
    path: str = Field(description="Directory path to create")

@registry.register(
    name="create_folder",
    tier=1,
    description="Create a new directory",
    args_schema=CreateFolderArgs,
    preview_fn=lambda a: f"Create new folder at '{a.get('path')}'",
    can_remember_per_folder=True,
    undo_fn=lambda a, res: os.rmdir(a["path"]) if os.path.exists(a["path"]) and not os.listdir(a["path"]) else None
)
def create_folder(path: str) -> Dict[str, Any]:
    norm_path = os.path.abspath(path)
    os.makedirs(norm_path, exist_ok=True)
    return {"path": norm_path, "created": True}

class MoveFileArgs(BaseModel):
    src: str = Field(description="Source file or directory path")
    dest: str = Field(description="Destination path")

@registry.register(
    name="move_file",
    tier=1,
    description="Move a file or folder from source to destination",
    args_schema=MoveFileArgs,
    preview_fn=lambda a: f"Move '{a.get('src')}' to '{a.get('dest')}'",
    can_remember_per_folder=True,
    undo_fn=lambda a, res: shutil.move(a["dest"], a["src"])
)
def move_file(src: str, dest: str) -> Dict[str, Any]:
    norm_src = os.path.abspath(src)
    norm_dest = os.path.abspath(dest)
    if not os.path.exists(norm_src):
        raise FileNotFoundError(f"Source does not exist: {src}")
    os.makedirs(os.path.dirname(norm_dest), exist_ok=True)
    shutil.move(norm_src, norm_dest)
    return {"src": norm_src, "dest": norm_dest, "moved": True}

class CopyFileArgs(BaseModel):
    src: str = Field(description="Source file or directory path")
    dest: str = Field(description="Destination path")

@registry.register(
    name="copy_file",
    tier=1,
    description="Copy a file or directory to a new location",
    args_schema=CopyFileArgs,
    preview_fn=lambda a: f"Copy '{a.get('src')}' to '{a.get('dest')}'",
    can_remember_per_folder=True,
    undo_fn=lambda a, res: send2trash.send2trash(a["dest"]) if os.path.exists(a["dest"]) else None
)
def copy_file(src: str, dest: str) -> Dict[str, Any]:
    norm_src = os.path.abspath(src)
    norm_dest = os.path.abspath(dest)
    if not os.path.exists(norm_src):
        raise FileNotFoundError(f"Source does not exist: {src}")
    os.makedirs(os.path.dirname(norm_dest), exist_ok=True)
    if os.path.isdir(norm_src):
        shutil.copytree(norm_src, norm_dest)
    else:
        shutil.copy2(norm_src, norm_dest)
    return {"src": norm_src, "dest": norm_dest, "copied": True}

# ==========================================
# Tier 2 (Destructive) File Tools
# ==========================================

class RecycleDeleteArgs(BaseModel):
    path: str = Field(description="File or folder path to send to the Recycle Bin")

@registry.register(
    name="recycle_delete",
    tier=2,
    description="Move a file or folder safely to the Windows Recycle Bin (Never permanently delete)",
    args_schema=RecycleDeleteArgs,
    preview_fn=lambda a: f"SEND TO RECYCLE BIN: '{a.get('path')}' (Can be restored from Recycle Bin)",
    can_remember_per_folder=False # Never remembered per SAFETY.md
)
def recycle_delete(path: str) -> Dict[str, Any]:
    norm_path = os.path.abspath(path)
    if not os.path.exists(norm_path):
        raise FileNotFoundError(f"Path does not exist: {path}")
    # Enforces Permanent Rule 7: Delete means recycle bin. Never permanent delete.
    send2trash.send2trash(norm_path)
    return {"path": norm_path, "recycled": True}
