from pathlib import Path
from services.backend.scripts.audit_imports import (
    parse_requirements_file,
    collect_third_party_imports
)

def test_requirements_cover_all_backend_imports():
    backend_dir = Path(__file__).resolve().parent.parent
    req_files = [
        backend_dir / "requirements.txt",
        backend_dir / "requirements-windows.txt",
        backend_dir / "requirements-dev.txt",
    ]

    declared_packages = set()
    for rf in req_files:
        declared_packages.update(parse_requirements_file(rf))

    if "fastapi" in declared_packages:
        declared_packages.add("starlette")

    used_packages = collect_third_party_imports(backend_dir)
    missing = used_packages - declared_packages

    assert len(missing) == 0, f"Found imports not listed in requirements: {sorted(missing)}"
