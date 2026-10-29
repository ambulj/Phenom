"""
Phenom Doctor Tool (System & Toolchain Diagnostic Checker)
Codified in Rounds 45 & 50.

Performs automated health checks on:
1. Python environment (version >= 3.10)
2. PyTorch CUDA & GPU VRAM availability
3. Node.js & npm toolchains
4. Git version control binary
5. Ripgrep (rg.exe) search engine
6. Ollama local inference endpoint
7. Windows Credential Manager accessibility
8. Storage free space (NVMe / C:\\)
9. Host system RAM headroom

Tier 0: Pure analytical read-only diagnostic tool.
"""

import os
import shutil
import subprocess
import sys
import psutil
from typing import Dict, Any, Optional
from pydantic import BaseModel, Field
from services.backend.safety.registry import registry

class PhenomDoctorArgs(BaseModel):
    detailed: bool = Field(default=False, description="Whether to include full system paths and verbose metrics.")

def phenom_doctor_preview(args: Dict[str, Any]) -> str:
    return "Execute 'phenom doctor' system toolchain and hardware diagnostic check."

class PhenomDoctor:
    def __init__(self, ollama_url: str = "http://127.0.0.1:11434"):
        self.ollama_url = ollama_url

    def check_python(self) -> Dict[str, Any]:
        ver = sys.version_info
        status = "OK" if ver >= (3, 10) else "WARN"
        return {
            "name": "Python Environment",
            "status": status,
            "version": f"{ver.major}.{ver.minor}.{ver.micro}",
            "executable": sys.executable,
            "details": "Python 3.10+ required for modern async & typing features."
        }

    def check_cuda(self) -> Dict[str, Any]:
        try:
            import torch
            cuda_avail = torch.cuda.is_available()
            if cuda_avail:
                device_count = torch.cuda.device_count()
                device_name = torch.cuda.get_device_name(0)
                props = torch.cuda.get_device_properties(0)
                vram_gb = round(props.total_memory / (1024 ** 3), 2)
                return {
                    "name": "CUDA GPU Acceleration",
                    "status": "OK",
                    "available": True,
                    "device": device_name,
                    "device_count": device_count,
                    "vram_total_gb": vram_gb,
                    "details": f"{device_name} with {vram_gb} GB VRAM detected."
                }
            else:
                return {
                    "name": "CUDA GPU Acceleration",
                    "status": "WARN",
                    "available": False,
                    "details": "CUDA not detected in PyTorch. Running in CPU mode."
                }
        except ImportError:
            return {
                "name": "CUDA GPU Acceleration",
                "status": "WARN",
                "available": False,
                "details": "PyTorch not installed or unavailable in current environment."
            }

    def check_node(self) -> Dict[str, Any]:
        try:
            node_out = subprocess.run(["node", "-v"], capture_output=True, text=True, timeout=3)
            node_ver = node_out.stdout.strip() if node_out.returncode == 0 else None
            npm_out = subprocess.run(["npm", "-v"], capture_output=True, text=True, timeout=3)
            npm_ver = npm_out.stdout.strip() if npm_out.returncode == 0 else None

            if node_ver and npm_ver:
                return {
                    "name": "Node.js & npm Toolchain",
                    "status": "OK",
                    "node_version": node_ver,
                    "npm_version": npm_ver,
                    "details": f"Node {node_ver}, npm {npm_ver} installed."
                }
            return {
                "name": "Node.js & npm Toolchain",
                "status": "WARN",
                "details": "Node.js or npm not detected in PATH."
            }
        except Exception as e:
            return {
                "name": "Node.js & npm Toolchain",
                "status": "WARN",
                "details": f"Failed to check Node: {str(e)}"
            }

    def check_git(self) -> Dict[str, Any]:
        try:
            git_out = subprocess.run(["git", "--version"], capture_output=True, text=True, timeout=3)
            if git_out.returncode == 0:
                return {
                    "name": "Git Version Control",
                    "status": "OK",
                    "version": git_out.stdout.strip(),
                    "details": git_out.stdout.strip()
                }
            return {
                "name": "Git Version Control",
                "status": "FAIL",
                "details": "Git command returned non-zero exit code."
            }
        except Exception as e:
            return {
                "name": "Git Version Control",
                "status": "FAIL",
                "details": f"Git binary not found in PATH: {str(e)}"
            }

    def check_ripgrep(self) -> Dict[str, Any]:
        rg_path = shutil.which("rg") or shutil.which("rg.exe")
        if rg_path:
            try:
                out = subprocess.run([rg_path, "--version"], capture_output=True, text=True, timeout=3)
                ver_line = out.stdout.splitlines()[0] if out.stdout else "Ripgrep installed"
                return {
                    "name": "Ripgrep Search Engine",
                    "status": "OK",
                    "path": rg_path,
                    "version": ver_line,
                    "details": "Native sub-10ms ripgrep search engine available."
                }
            except Exception:
                pass
        return {
            "name": "Ripgrep Search Engine",
            "status": "WARN",
            "path": None,
            "details": "Ripgrep (rg.exe) not found on PATH. Falling back to Python regex scanner."
        }

    def check_disk(self) -> Dict[str, Any]:
        try:
            usage = shutil.disk_usage("C:\\")
            free_gb = round(usage.free / (1024 ** 3), 2)
            total_gb = round(usage.total / (1024 ** 3), 2)
            status = "OK" if free_gb >= 10.0 else "WARN"
            return {
                "name": "Disk Space (C:)",
                "status": status,
                "free_gb": free_gb,
                "total_gb": total_gb,
                "details": f"{free_gb} GB free out of {total_gb} GB."
            }
        except Exception as e:
            return {
                "name": "Disk Space (C:)",
                "status": "WARN",
                "details": f"Could not inspect disk usage: {str(e)}"
            }

    def check_memory(self) -> Dict[str, Any]:
        try:
            mem = psutil.virtual_memory()
            avail_gb = round(mem.available / (1024 ** 3), 2)
            total_gb = round(mem.total / (1024 ** 3), 2)
            status = "OK" if avail_gb >= 2.0 else "WARN"
            return {
                "name": "Host Memory (RAM)",
                "status": status,
                "available_gb": avail_gb,
                "total_gb": total_gb,
                "percent_used": mem.percent,
                "details": f"{avail_gb} GB available ({mem.percent}% used) out of {total_gb} GB."
            }
        except Exception as e:
            return {
                "name": "Host Memory (RAM)",
                "status": "WARN",
                "details": f"Could not inspect memory: {str(e)}"
            }

    def check_credential_manager(self) -> Dict[str, Any]:
        try:
            from services.backend.remote.credentials import get_credential
            # Safe probe
            _ = get_credential("phenom_health_probe_nonexistent")
            return {
                "name": "Windows Credential Manager",
                "status": "OK",
                "details": "Windows Credential Manager integration responsive and secure."
            }
        except Exception as e:
            return {
                "name": "Windows Credential Manager",
                "status": "WARN",
                "details": f"Credential Manager probe warning: {str(e)}"
            }

    def check_ollama(self) -> Dict[str, Any]:
        try:
            import urllib.request
            req = urllib.request.Request(f"{self.ollama_url}/api/version", method="GET")
            with urllib.request.urlopen(req, timeout=1.5) as resp:
                if resp.status == 200:
                    data = resp.read().decode("utf-8")
                    return {
                        "name": "Ollama Local Inference",
                        "status": "OK",
                        "endpoint": self.ollama_url,
                        "details": f"Ollama service active: {data.strip()}"
                    }
        except Exception:
            pass
        return {
            "name": "Ollama Local Inference",
            "status": "WARN",
            "endpoint": self.ollama_url,
            "details": "Ollama local inference server not responding at 127.0.0.1:11434."
        }

    def run_all(self, detailed: bool = False) -> Dict[str, Any]:
        checks = [
            self.check_python(),
            self.check_cuda(),
            self.check_node(),
            self.check_git(),
            self.check_ripgrep(),
            self.check_disk(),
            self.check_memory(),
            self.check_credential_manager(),
            self.check_ollama()
        ]

        fail_count = sum(1 for c in checks if c["status"] == "FAIL")
        warn_count = sum(1 for c in checks if c["status"] == "WARN")
        ok_count = sum(1 for c in checks if c["status"] == "OK")

        if fail_count > 0:
            overall = "CRITICAL"
        elif warn_count > 0:
            overall = "DEGRADED"
        else:
            overall = "HEALTHY"

        summary = f"Phenom Doctor: {overall} ({ok_count} OK, {warn_count} Warnings, {fail_count} Failures)"

        return {
            "overall_health": overall,
            "summary": summary,
            "ok_count": ok_count,
            "warn_count": warn_count,
            "fail_count": fail_count,
            "checks": checks
        }

@registry.register(
    name="phenom_doctor",
    tier=0,
    preview_fn=phenom_doctor_preview,
    args_schema=PhenomDoctorArgs,
    description="Inspects local host environment health, CUDA GPU, disk space, memory, Git, Node, and Ollama toolchains."
)
def run_phenom_doctor(detailed: bool = False) -> Dict[str, Any]:
    doctor = PhenomDoctor()
    return doctor.run_all(detailed=detailed)
