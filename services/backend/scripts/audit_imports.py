"""
Audit third-party imports in services/backend/ against requirements files.
Uses Python's AST to extract all module imports, maps them to PyPI package names,
and ensures every third-party dependency is declared in requirements.
"""

import ast
import os
import re
import sys
from pathlib import Path
from typing import Set, Dict

# Mapping from Python import / module name to official PyPI distribution name
IMPORT_TO_PYPI: Dict[str, str] = {
    "PIL": "pillow",
    "bs4": "beautifulsoup4",
    "docx": "python-docx",
    "pptx": "python-pptx",
    "faster_whisper": "faster-whisper",
    "sentence_transformers": "sentence-transformers",
    "yt_dlp": "yt-dlp",
    "sqlcipher3": "sqlcipher3-wheels",
    "win32cred": "pywin32",
    "win32com": "pywin32",
    "pythoncom": "pywin32",
    "win32api": "pywin32",
    "win32con": "pywin32",
    "nest_asyncio": "nest-asyncio",
    "starlette": "fastapi",  # starlette is bundled/required by fastapi
}

def get_stdlib_modules() -> Set[str]:
    """Return set of standard library module names."""
    if hasattr(sys, "stdlib_module_names"):
        names = set(sys.stdlib_module_names)
    else:
        # Fallback for older python
        import distutils.sysconfig
        names = set(sys.builtin_module_names)
    # Common built-in/standard modules
    names.update({
        "sys", "os", "io", "re", "json", "time", "datetime", "math",
        "typing", "collections", "pathlib", "asyncio", "logging", "threading",
        "subprocess", "dataclasses", "abc", "contextlib", "inspect", "shutil",
        "hashlib", "hmac", "tempfile", "traceback", "uuid", "urllib", "sqlite3",
        "unittest", "unittest.mock", "gc", "socket", "platform", "signal",
        "ctypes", "functools", "itertools", "enum", "copy", "base64", "struct"
    })
    return names

def parse_requirements_file(path: Path) -> Set[str]:
    """Extract package names from a requirements file."""
    packages = set()
    if not path.is_file():
        return packages

    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            if line.startswith("-r"):
                # Recursive requirement
                sub_file = path.parent / line.split()[1]
                packages.update(parse_requirements_file(sub_file))
                continue
            # Extract package name before any version specifier or environment marker
            match = re.match(r"^([a-zA-Z0-9_\-\.]+)", line)
            if match:
                pkg = match.group(1).lower().replace("_", "-")
                packages.add(pkg)
    return packages

def collect_third_party_imports(backend_root: Path) -> Set[str]:
    """Walk all .py files in backend and extract third-party import package names."""
    stdlib = get_stdlib_modules()
    local_packages = {"services", "tests", "apps", "scripts"}
    imported_modules = set()

    for py_file in backend_root.rglob("*.py"):
        try:
            with open(py_file, "r", encoding="utf-8", errors="ignore") as f:
                tree = ast.parse(f.read(), filename=str(py_file))
        except Exception as e:
            print(f"Warning: could not parse {py_file}: {e}")
            continue

        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    top_name = alias.name.split(".")[0]
                    imported_modules.add(top_name)
            elif isinstance(node, ast.ImportFrom):
                if node.module and node.level == 0:
                    top_name = node.module.split(".")[0]
                    imported_modules.add(top_name)

    third_party_packages = set()
    for mod in imported_modules:
        if mod in stdlib or mod in local_packages or not mod:
            continue
        pypi_name = IMPORT_TO_PYPI.get(mod, mod.lower().replace("_", "-"))
        third_party_packages.add(pypi_name)

    return third_party_packages

def main() -> int:
    backend_dir = Path(__file__).resolve().parent.parent
    req_files = [
        backend_dir / "requirements.txt",
        backend_dir / "requirements-windows.txt",
        backend_dir / "requirements-dev.txt",
    ]

    declared_packages = set()
    for rf in req_files:
        declared_packages.update(parse_requirements_file(rf))

    # Also handle fastapi dependency on starlette
    if "fastapi" in declared_packages:
        declared_packages.add("starlette")

    used_packages = collect_third_party_imports(backend_dir)
    missing = used_packages - declared_packages

    print(f"Audited {len(used_packages)} third-party imports across {backend_dir}...")
    if missing:
        print(f"FAILED: Found {len(missing)} missing packages not declared in requirements files:")
        for pkg in sorted(missing):
            print(f"  - {pkg}")
        return 1

    print("SUCCESS: 0 missing dependencies! All third-party imports are covered by requirements.")
    return 0

if __name__ == "__main__":
    sys.exit(main())
