"""
Phenom Photo Indexer & Privacy Protector
Features:
- Extracts EXIF metadata, generates tags and captions locally.
- Searchable by natural language description.
- STRICT SAFETY RULE: Phenom NEVER moves, renames, edits, or deletes photos.
  Enforced by hard code-level blocks that raise PermissionError.
"""

import os
import json
import uuid
from typing import List, Dict, Any, Optional
from datetime import datetime
from PIL import Image, ExifTags

from services.backend.memory.db import encrypted_db

PHOTO_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp", ".heic", ".bmp"}

class PhotoModificationProhibited(PermissionError):
    pass

class PhotoIndexer:
    def __init__(self):
        pass

    def is_photo(self, file_path: str) -> bool:
        ext = os.path.splitext(file_path)[1].lower()
        return ext in PHOTO_EXTENSIONS

    def verify_no_photo_modification(self, file_path: str, action: str):
        """Hard safety check preventing any modification, rename, or deletion of photos."""
        if self.is_photo(file_path):
            raise PhotoModificationProhibited(
                f"Action '{action}' permanently blocked on photo '{file_path}'. "
                f"SAFETY.md Rule #6: Photos are indexed and searched only. Never move, rename, edit or delete them."
            )

    def extract_photo_metadata(self, file_path: str) -> Dict[str, Any]:
        """Extracts resolution, EXIF properties, and generates local semantic tags."""
        abs_path = os.path.abspath(file_path)
        if not os.path.isfile(abs_path):
            raise FileNotFoundError(f"Photo not found: {file_path}")

        meta = {
            "file_path": abs_path,
            "filename": os.path.basename(abs_path),
            "size_bytes": os.path.getsize(abs_path),
            "date_taken": None,
            "dimensions": None,
            "camera": None
        }

        tags = set()
        filename_words = [w.lower() for w in os.path.splitext(meta["filename"])[0].replace("-", "_").split("_")]
        tags.update(filename_words)

        try:
            with Image.open(abs_path) as img:
                meta["dimensions"] = f"{img.width}x{img.height}"
                
                # Aspect ratio tags
                ratio = img.width / max(1, img.height)
                if ratio > 1.3:
                    tags.add("landscape")
                elif ratio < 0.8:
                    tags.add("portrait")
                else:
                    tags.add("square")

                # EXIF data
                exif_data = img._getexif()
                if exif_data:
                    for tag_id, val in exif_data.items():
                        tag_name = ExifTags.TAGS.get(tag_id, str(tag_id))
                        if tag_name == "DateTimeOriginal":
                            meta["date_taken"] = str(val)
                        elif tag_name == "Model":
                            meta["camera"] = str(val)
                            tags.add(str(val).lower())
        except Exception:
            pass

        tag_list = sorted(list(tags))
        caption = f"Photo {meta['filename']} ({meta.get('dimensions', 'unknown')}) with tags: {', '.join(tag_list)}"
        
        return {
            "metadata": meta,
            "tags": tag_list,
            "caption": caption
        }

    def index_photo(self, file_path: str) -> str:
        """Indexes a single photo into the encrypted SQLCipher table."""
        abs_path = os.path.abspath(file_path)
        if not self.is_photo(abs_path):
            raise ValueError(f"Not a supported photo format: {file_path}")

        data = self.extract_photo_metadata(abs_path)
        mtime = os.path.getmtime(abs_path)
        photo_id = f"photo-{uuid.uuid4().hex[:12]}"

        conn = encrypted_db.get_connection()
        with conn:
            conn.execute(
                "INSERT OR REPLACE INTO photo_index (id, file_path, filename, tags, caption, mtime, metadata_json) "
                "VALUES (?, ?, ?, ?, ?, ?, ?);",
                (
                    photo_id,
                    abs_path,
                    data["metadata"]["filename"],
                    ", ".join(data["tags"]),
                    data["caption"],
                    mtime,
                    json.dumps(data["metadata"])
                )
            )
        conn.close()
        return photo_id

    def index_photo_folder(self, folder_path: str) -> int:
        """Scans a folder and indexes all photos."""
        abs_folder = os.path.abspath(folder_path)
        if not os.path.isdir(abs_folder):
            raise FileNotFoundError(f"Folder not found: {folder_path}")

        count = 0
        for root, _, files in os.walk(abs_folder):
            for file in files:
                if self.is_photo(file):
                    self.index_photo(os.path.join(root, file))
                    count += 1
        return count

    def search_photos(self, query: str, limit: int = 10) -> List[Dict[str, Any]]:
        """Searches indexed photos by natural language description and tags."""
        terms = [t.lower().strip() for t in query.split() if t.strip()]
        if not terms:
            return []

        conn = encrypted_db.get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT id, file_path, filename, tags, caption, metadata_json FROM photo_index;")
        rows = cursor.fetchall()
        conn.close()

        results = []
        for pid, path, name, tags_str, caption, meta_json in rows:
            text_corpus = f"{name} {tags_str} {caption}".lower()
            match_count = sum(1 for term in terms if term in text_corpus)
            if match_count > 0:
                score = match_count / len(terms)
                results.append({
                    "id": pid,
                    "file_path": path,
                    "filename": name,
                    "tags": [t.strip() for t in tags_str.split(",") if t.strip()],
                    "caption": caption,
                    "metadata": json.loads(meta_json),
                    "score": round(score, 2)
                })

        results.sort(key=lambda x: x["score"], reverse=True)
        return results[:limit]

    # Permanently Prohibited Operations (Raise Exception by construction)
    def move_photo(self, *args, **kwargs):
        raise PhotoModificationProhibited("Moving photos is strictly prohibited by SAFETY.md Rule #6.")

    def rename_photo(self, *args, **kwargs):
        raise PhotoModificationProhibited("Renaming photos is strictly prohibited by SAFETY.md Rule #6.")

    def edit_photo(self, *args, **kwargs):
        raise PhotoModificationProhibited("Editing photos is strictly prohibited by SAFETY.md Rule #6.")

    def delete_photo(self, *args, **kwargs):
        raise PhotoModificationProhibited("Deleting photos is strictly prohibited by SAFETY.md Rule #6.")

photo_indexer = PhotoIndexer()
