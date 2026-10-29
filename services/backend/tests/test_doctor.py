import pytest
from services.backend.tools.doctor import PhenomDoctor, run_phenom_doctor
from services.backend.safety.registry import registry

def test_phenom_doctor_tool_registered():
    tool = registry.get("phenom_doctor")
    assert tool is not None
    assert tool.tier == 0
    assert "phenom_doctor" in registry.list_all()

def test_phenom_doctor_individual_checks():
    doctor = PhenomDoctor()
    py_check = doctor.check_python()
    assert py_check["status"] == "OK"
    assert "3." in py_check["version"]

    git_check = doctor.check_git()
    assert git_check["status"] == "OK"
    assert "git version" in git_check["version"].lower()

    disk_check = doctor.check_disk()
    assert "free_gb" in disk_check
    assert disk_check["free_gb"] > 0

    mem_check = doctor.check_memory()
    assert "available_gb" in mem_check
    assert mem_check["available_gb"] > 0

def test_phenom_doctor_run_all():
    report = run_phenom_doctor(detailed=True)
    assert "overall_health" in report
    assert report["overall_health"] in ["HEALTHY", "DEGRADED", "CRITICAL"]
    assert "checks" in report
    assert len(report["checks"]) == 9
    assert report["ok_count"] >= 3
