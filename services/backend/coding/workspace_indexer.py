"""
Semantic Workspace Symbol Indexer (DEV-01.2).
Maintains an in-memory symbol table and call graph for the workspace with SHA256 file-hash
incremental invalidation and sub-10ms query latency.
"""

import os
import time
import hashlib
import fnmatch
from typing import Dict, List, Set, Optional, Any
from services.backend.coding.ast_parser import ast_parser, SymbolDefinition
from services.backend.safety.guardian import guardian

DEFAULT_EXCLUDE_PATTERNS = [
    "*.git*",
    "*node_modules*",
    "*__pycache__*",
    "*.venv*",
    "*dist*",
    "*release*",
    "*.pytest_cache*",
    "*.planning*",
    "*.system_generated*",
    "*brain*",
    "*.gemini*"
]

SUPPORTED_EXTENSIONS = {".py", ".ts", ".tsx", ".js", ".jsx"}


class WorkspaceIndexer:
    """In-memory semantic workspace symbol table and dependency call graph."""

    def __init__(self, root_dir: str = "c:/Phenom"):
        self.root_dir = os.path.abspath(root_dir)
        self._file_hashes: Dict[str, str] = {}
        self._symbols_by_name: Dict[str, List[SymbolDefinition]] = {}
        self._symbols_by_file: Dict[str, List[SymbolDefinition]] = {}
        self._reverse_call_graph: Dict[str, Set[str]] = {}
        self._last_index_time: float = 0.0
        self._total_symbols_indexed: int = 0

    def _should_exclude(self, rel_path: str) -> bool:
        norm = rel_path.replace("\\", "/")
        for pattern in DEFAULT_EXCLUDE_PATTERNS:
            if fnmatch.fnmatch(norm, pattern) or fnmatch.fnmatch(f"*/{norm}", pattern):
                return True
            parts = norm.split("/")
            for part in parts:
                if fnmatch.fnmatch(part, pattern.strip("*")):
                    return True
        return False

    def _compute_hash(self, file_path: str) -> str:
        try:
            with open(file_path, "rb") as f:
                return hashlib.sha256(f.read()).hexdigest()
        except Exception:
            return ""

    def index_workspace(self, max_files: int = 1500) -> Dict[str, Any]:
        """
        Scans and indexes workspace files incrementally.
        Skips unchanged files based on SHA256 hashes.
        Enforces Guardian kill switch check periodically (< 25.0ms SLA).
        """
        start = time.perf_counter()
        scanned_count = 0
        parsed_count = 0

        target_files: List[str] = []
        for root, dirs, files in os.walk(self.root_dir):
            if guardian.is_halted:
                raise PermissionError("Guardian kill switch is active. Indexing aborted.")

            rel_root = os.path.relpath(root, self.root_dir)
            if self._should_exclude(rel_root):
                continue

            for f in files:
                ext = os.path.splitext(f)[1].lower()
                if ext in SUPPORTED_EXTENSIONS:
                    full_p = os.path.join(root, f)
                    rel_p = os.path.relpath(full_p, self.root_dir)
                    if not self._should_exclude(rel_p):
                        target_files.append(full_p)
                        if len(target_files) >= max_files:
                            break
            if len(target_files) >= max_files:
                break

        for idx, file_path in enumerate(target_files):
            if idx % 25 == 0 and guardian.is_halted:
                raise PermissionError("Guardian kill switch is active. Indexing aborted.")

            scanned_count += 1
            cur_hash = self._compute_hash(file_path)
            if not cur_hash:
                continue

            prev_hash = self._file_hashes.get(file_path)
            if prev_hash == cur_hash:
                # File unchanged, keep cached symbols
                continue

            # File modified or new: parse and update
            self._file_hashes[file_path] = cur_hash
            new_symbols = ast_parser.parse_file(file_path)
            parsed_count += 1

            # Remove old file symbols from by_name index
            old_symbols = self._symbols_by_file.get(file_path, [])
            for sym in old_symbols:
                if sym.name in self._symbols_by_name:
                    self._symbols_by_name[sym.name] = [
                        s for s in self._symbols_by_name[sym.name] if s.file_path != file_path
                    ]
                    if not self._symbols_by_name[sym.name]:
                        del self._symbols_by_name[sym.name]

            # Register new symbols
            self._symbols_by_file[file_path] = new_symbols
            for sym in new_symbols:
                if sym.name not in self._symbols_by_name:
                    self._symbols_by_name[sym.name] = []
                self._symbols_by_name[sym.name].append(sym)

                # Update call graph
                for called_symbol in sym.calls:
                    if called_symbol not in self._reverse_call_graph:
                        self._reverse_call_graph[called_symbol] = set()
                    self._reverse_call_graph[called_symbol].add(f"{sym.name} ({sym.file_path}:{sym.line_number})")

        self._last_index_time = time.time()
        self._total_symbols_indexed = sum(len(syms) for syms in self._symbols_by_file.values())
        elapsed_ms = (time.perf_counter() - start) * 1000.0

        return {
            "status": "indexed",
            "files_scanned": scanned_count,
            "files_reparsed": parsed_count,
            "total_indexed_files": len(self._symbols_by_file),
            "total_symbols": self._total_symbols_indexed,
            "duration_ms": round(elapsed_ms, 2)
        }

    def lookup_symbol(self, name: str) -> List[Dict[str, Any]]:
        """Sub-10ms lookup for symbol definitions by name."""
        start = time.perf_counter()
        if guardian.is_halted:
            raise PermissionError("Guardian kill switch is active. Lookup aborted.")

        matches = self._symbols_by_name.get(name, [])
        if not matches:
            # Case-insensitive fallback
            lname = name.lower()
            for k, syms in self._symbols_by_name.items():
                if k.lower() == lname:
                    matches.extend(syms)

        results = [s.to_dict() for s in matches]
        elapsed_ms = (time.perf_counter() - start) * 1000.0
        return results

    def find_references(self, name: str) -> Dict[str, Any]:
        """Finds definitions and all known callers of a given symbol."""
        start = time.perf_counter()
        definitions = self.lookup_symbol(name)
        callers = sorted(list(self._reverse_call_graph.get(name, set())))

        elapsed_ms = (time.perf_counter() - start) * 1000.0
        return {
            "symbol": name,
            "definitions": definitions,
            "references": callers,
            "reference_count": len(callers),
            "lookup_duration_ms": round(elapsed_ms, 2)
        }

    def search_symbols(
        self,
        query: str,
        kind: Optional[str] = None,
        limit: int = 50
    ) -> List[Dict[str, Any]]:
        """Searches symbols matching substring pattern and optional kind."""
        start = time.perf_counter()
        lquery = query.lower()
        results: List[Dict[str, Any]] = []

        for name, sym_list in self._symbols_by_name.items():
            if lquery in name.lower():
                for sym in sym_list:
                    if kind and sym.kind.lower() != kind.lower():
                        continue
                    results.append(sym.to_dict())
                    if len(results) >= limit:
                        break
            if len(results) >= limit:
                break

        return results

    def get_stats(self) -> Dict[str, Any]:
        """Returns metadata and symbol counts."""
        kind_counts: Dict[str, int] = {}
        for sym_list in self._symbols_by_file.values():
            for s in sym_list:
                kind_counts[s.kind] = kind_counts.get(s.kind, 0) + 1

        return {
            "root_dir": self.root_dir,
            "indexed_files": len(self._symbols_by_file),
            "total_symbols": self._total_symbols_indexed,
            "unique_symbol_names": len(self._symbols_by_name),
            "symbols_by_kind": kind_counts,
            "call_graph_targets": len(self._reverse_call_graph),
            "last_index_time": self._last_index_time
        }


workspace_indexer = WorkspaceIndexer()
