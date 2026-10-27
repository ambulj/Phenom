"""
Phenom Downloads Cleanup Organizer & Reversible Undo Manager
Features:
- Categorizes files by extension into: Documents, Images, Archives, Installers, Media, Code, Other.
- Subdivides into Year-Month subfolders based on file modification date.
- Identifies identical file duplicates via SHA-256 and marks them for Recycle Bin.
- Dry Run mode: previews planned file operations without altering any file.
- Reversible Undo: records an undo ledger allowing 100% reversible rollback of moves.
"""

import os
import shutil
import hashlib
import uuid
from datetime import datetime
from typing import List, Dict, Any, Optional
import send2trash

CATEGORY_MAP = {
    # Documents
    ".pdf": "Documents", ".docx": "Documents", ".doc": "Documents",
    ".txt": "Documents", ".pptx": "Documents", ".xlsx": "Documents", ".csv": "Documents",
    # Images
    ".png": "Images", ".jpg": "Images", ".jpeg": "Images",
    ".gif": "Images", ".svg": "Images", ".webp": "Images",
    # Archives
    ".zip": "Archives", ".rar": "Archives", ".7z": "Archives", ".tar": "Archives", ".gz": "Archives",
    # Installers
    ".exe": "Installers", ".msi": "Installers", ".iso": "Installers",
    # Media
    ".mp4": "Media", ".mp3": "Media", ".mkv": "Media", ".wav": "Media", ".mov": "Media",
    # Code
    ".py": "Code", ".js": "Code", ".ts": "Code", ".html": "Code", ".css": "Code", ".json": "Code"
}

class CleanupOrganizer:
    def __init__(self):
        self._undo_history: Dict[str, List[Dict[str, str]]] = {}

    def _hash_file(self, file_path: str) -> str:
        h = hashlib.sha256()
        with open(file_path, "rb") as f:
            while chunk := f.read(65536):
                h.update(chunk)
        return h.hexdigest()

    def generate_dry_run(self, target_folder: str) -> Dict[str, Any]:
        """
        Scans folder and produces a plan of moves and duplicate recycles.
        No filesystem changes occur during dry run.
        """
        abs_folder = os.path.abspath(target_folder)
        if not os.path.isdir(abs_folder):
            raise FileNotFoundError(f"Folder not found: {target_folder}")

        plan_steps = []
        seen_hashes: Dict[str, str] = {}
        files_to_scan = []

        # Only organize top-level files in target folder to avoid re-organizing existing category dirs
        for entry in os.scandir(abs_folder):
            if entry.is_file():
                files_to_scan.append(entry.path)

        for file_path in files_to_scan:
            filename = os.path.basename(file_path)
            ext = os.path.splitext(filename)[1].lower()
            category = CATEGORY_MAP.get(ext, "Other")

            mtime = os.path.getmtime(file_path)
            dt = datetime.fromtimestamp(mtime)
            ym_folder = dt.strftime("%Y-%m")

            file_hash = self._hash_file(file_path)

            if file_hash in seen_hashes:
                # Duplicate detected: plan to recycle
                original_file = seen_hashes[file_hash]
                plan_steps.append({
                    "action": "recycle_duplicate",
                    "source": file_path,
                    "filename": filename,
                    "duplicate_of": original_file,
                    "size_bytes": os.path.getsize(file_path)
                })
            else:
                seen_hashes[file_hash] = file_path
                dest_dir = os.path.join(abs_folder, category, ym_folder)
                dest_path = os.path.join(dest_dir, filename)
                plan_steps.append({
                    "action": "move",
                    "source": file_path,
                    "destination": dest_path,
                    "category": category,
                    "dest_folder": ym_folder,
                    "size_bytes": os.path.getsize(file_path)
                })

        return {
            "target_folder": abs_folder,
            "total_files": len(files_to_scan),
            "moves_count": sum(1 for s in plan_steps if s["action"] == "move"),
            "duplicates_count": sum(1 for s in plan_steps if s["action"] == "recycle_duplicate"),
            "steps": plan_steps
        }

    def apply_cleanup(self, dry_run_plan: Dict[str, Any]) -> tuple[Dict[str, Any], str]:
        """
        Applies the plan, moving files and sending duplicates to the recycle bin.
        Returns execution summary and undo_token.
        """
        steps = dry_run_plan.get("steps", [])
        undo_token = f"undo-{uuid.uuid4().hex[:12]}"
        undo_ledger = []
        executed_count = 0
        recycled_count = 0

        for step in steps:
            action = step.get("action")
            src = step.get("source")

            if not os.path.exists(src):
                continue

            if action == "move":
                dest = step.get("destination")
                os.makedirs(os.path.dirname(dest), exist_ok=True)
                # Handle collision if destination already exists
                final_dest = dest
                if os.path.exists(dest) and dest != src:
                    base, ext = os.path.splitext(dest)
                    final_dest = f"{base}_{uuid.uuid4().hex[:4]}{ext}"

                shutil.move(src, final_dest)
                undo_ledger.append({"original_src": src, "moved_dest": final_dest})
                executed_count += 1

            elif action == "recycle_duplicate":
                # Send to recycle bin (never permanent delete)
                send2trash.send2trash(src)
                recycled_count += 1

        self._undo_history[undo_token] = undo_ledger

        summary = {
            "status": "completed",
            "undo_token": undo_token,
            "files_moved": executed_count,
            "duplicates_recycled": recycled_count
        }
        return summary, undo_token

    def undo_cleanup(self, undo_token: str) -> Dict[str, Any]:
        """
        Rolls back all file moves associated with the undo_token.
        """
        ledger = self._undo_history.get(undo_token)
        if not ledger:
            raise ValueError(f"Undo token '{undo_token}' not found or expired.")

        restored_count = 0
        for item in reversed(ledger):
            moved_dest = item["moved_dest"]
            orig_src = item["original_src"]
            if os.path.exists(moved_dest):
                os.makedirs(os.path.dirname(orig_src), exist_ok=True)
                shutil.move(moved_dest, orig_src)
                restored_count += 1

        # Remove from history
        self._undo_history.pop(undo_token, None)

        return {
            "status": "rolled_back",
            "undo_token": undo_token,
            "files_restored": restored_count
        }

cleanup_organizer = CleanupOrganizer()
