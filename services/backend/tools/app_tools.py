"""
Phenom Application Tools
Enables listing, launching, and terminating applications safely.
"""

import os
import subprocess
import psutil
import shutil
import winreg
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field
from services.backend.safety.registry import registry
from services.backend.safety.guardian import guardian

def resolve_application_path(name: str) -> str:
    """Resolves an application name to an executable path via Windows Registry App Paths, PATH, or well-known locations."""
    clean = name.strip()
    if clean.startswith("http://") or clean.startswith("https://"):
        return clean

    # 1. Check Windows Registry App Paths (HKCU and HKLM)
    for root in (winreg.HKEY_CURRENT_USER, winreg.HKEY_LOCAL_MACHINE):
        for subkey in (
            f"SOFTWARE\\Microsoft\\Windows\\CurrentVersion\\App Paths\\{clean}.exe",
            f"SOFTWARE\\Microsoft\\Windows\\CurrentVersion\\App Paths\\{clean}"
        ):
            try:
                with winreg.OpenKey(root, subkey) as k:
                    val, _ = winreg.QueryValueEx(k, "")
                    if val and os.path.exists(val):
                        return val
            except Exception:
                pass

    # 2. Check system PATH via shutil.which
    which_path = shutil.which(clean) or shutil.which(f"{clean}.exe")
    if which_path:
        return which_path

    # 3. Check well-known install locations on Windows
    local_app_data = os.environ.get("LOCALAPPDATA", "")
    program_files = os.environ.get("ProgramFiles", "C:\\Program Files")
    program_files_x86 = os.environ.get("ProgramFiles(x86)", "C:\\Program Files (x86)")
    app_data = os.environ.get("APPDATA", "")

    candidates = [
        os.path.join(local_app_data, "BraveSoftware", "Brave-Browser", "Application", "brave.exe"),
        os.path.join(program_files, "BraveSoftware", "Brave-Browser", "Application", "brave.exe"),
        os.path.join(program_files, "Google", "Chrome", "Application", "chrome.exe"),
        os.path.join(program_files_x86, "Google", "Chrome", "Application", "chrome.exe"),
        os.path.join(local_app_data, "Programs", "Microsoft VS Code", "Code.exe"),
        os.path.join(app_data, "Spotify", "Spotify.exe"),
    ]
    for cand in candidates:
        if cand and os.path.exists(cand) and clean.lower() in os.path.basename(cand).lower():
            return cand

    return clean

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
    app_name: str = Field(description="Name or command of application to open, or web URL (e.g. 'brave', 'chrome', 'spotify', 'notepad', 'https://youtube.com')")
    url_or_args: Optional[str] = Field(default=None, description="Optional URL or arguments to pass to the application")

@registry.register(
    name="open_app",
    tier=1,
    description="Launch an application or open a web URL",
    args_schema=OpenAppArgs,
    preview_fn=lambda a: f"Launch application or URL: '{a.get('app_name')}'" + (f" with args '{a.get('url_or_args')}'" if a.get('url_or_args') else ""),
    can_remember_per_folder=False
)
def open_app(app_name: str, url_or_args: Optional[str] = None) -> Dict[str, Any]:
    resolved = resolve_application_path(app_name)
    clean_name = app_name.strip()

    # Browser window guarantee: if opening a browser directly without args, ensure --new-window
    if clean_name.lower() in ("brave", "chrome", "msedge", "firefox") and not url_or_args:
        url_or_args = "--new-window"

    # Explicitly target user interactive desktop (WinSta0\Default) so windows appear on monitor
    si = subprocess.STARTUPINFO()
    si.lpDesktop = "WinSta0\\Default"

    try:
        cmd_args = ["cmd.exe", "/c", "start", "", resolved]
        if url_or_args:
            cmd_args.append(str(url_or_args))
        proc = subprocess.Popen(cmd_args, startupinfo=si)
        guardian.track_pid(proc.pid)
        return {
            "app_name": clean_name,
            "resolved_path": resolved,
            "launched": True,
            "launcher_pid": proc.pid,
            "message": f"Successfully launched {clean_name}"
        }
    except Exception as e:
        proc = subprocess.Popen([resolved], startupinfo=si)
        guardian.track_pid(proc.pid)
        return {
            "app_name": clean_name,
            "resolved_path": resolved,
            "launched": True,
            "launcher_pid": proc.pid
        }

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
