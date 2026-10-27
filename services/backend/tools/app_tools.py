"""
Phenom Application Tools
Enables listing, launching, and terminating applications safely.
"""

import os
import subprocess
import psutil
from typing import List, Dict, Any
from pydantic import BaseModel, Field
from services.backend.safety.registry import registry
from services.backend.safety.guardian import guardian

class ListAppsArgs(BaseModel):
    filter_system: bool = Field(default=True, description="Filter out background system processes")

@registry.register(
    name="list_apps",
    tier=0,
    description="List active visible applications and processes",
    args_schema=ListAppsArgs,
    preview_fn=lambda a: "List running desktop applications"
)
def list_apps(filter_system: bool = True) -> List[Dict[str, Any]]:
    apps = []
    for proc in psutil.process_iter(['pid', 'name', 'cpu_percent', 'memory_info']):
        try:
            name = proc.info['name']
            pid = proc.info['pid']
            # Basic filter for system daemons if requested
            if filter_system and name.lower() in ("system idle process", "system", "registry", "smss.exe", "csrss.exe"):
                continue
            mem_mb = round(proc.info['memory_info'].rss / (1024 * 1024), 1) if proc.info['memory_info'] else 0
            apps.append({
                "pid": pid,
                "name": name,
                "memory_mb": mem_mb
            })
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            pass
    return apps[:100]

class OpenAppArgs(BaseModel):
    app_name: str = Field(description="Name or command of application to open (e.g. 'notepad', 'calc', 'spotify')")

@registry.register(
    name="open_app",
    tier=1,
    description="Launch an application",
    args_schema=OpenAppArgs,
    preview_fn=lambda a: f"Launch application: '{a.get('app_name')}'",
    can_remember_per_folder=False
)
def open_app(app_name: str) -> Dict[str, Any]:
    # Use Windows 'start' via powershell or os.startfile
    clean_name = app_name.strip()
    proc = subprocess.Popen(
        ["powershell", "-Command", f"Start-Process '{clean_name}'"],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE
    )
    guardian.track_pid(proc.pid)
    return {"app_name": clean_name, "launched": True, "launcher_pid": proc.pid}

class CloseAppArgs(BaseModel):
    app_name: str = Field(description="Name of the process to terminate (e.g. 'notepad.exe', 'calc.exe')")

@registry.register(
    name="close_app",
    tier=1,
    description="Terminate running application processes by name",
    args_schema=CloseAppArgs,
    preview_fn=lambda a: f"Terminate running application: '{a.get('app_name')}'",
    can_remember_per_folder=False
)
def close_app(app_name: str) -> Dict[str, Any]:
    target_name = app_name.lower().replace(".exe", "")
    terminated = 0
    for proc in psutil.process_iter(['pid', 'name']):
        try:
            pname = proc.info['name'].lower().replace(".exe", "")
            if pname == target_name:
                proc.terminate()
                terminated += 1
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            pass
    return {"app_name": app_name, "terminated_processes": terminated}
