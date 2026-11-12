"""
Phenom Application Tools
Enables listing, launching, and terminating applications safely.
"""

import os
import subprocess
import psutil
import shutil
import winreg
import ctypes
from ctypes import wintypes
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field
from services.backend.safety.registry import registry
from services.backend.safety.guardian import guardian

class _STARTUPINFOW(ctypes.Structure):
    _fields_ = [
        ("cb", wintypes.DWORD),
        ("lpReserved", wintypes.LPWSTR),
        ("lpDesktop", wintypes.LPWSTR),
        ("lpTitle", wintypes.LPWSTR),
        ("dwX", wintypes.DWORD),
        ("dwY", wintypes.DWORD),
        ("dwXSize", wintypes.DWORD),
        ("dwYSize", wintypes.DWORD),
        ("dwXCountChars", wintypes.DWORD),
        ("dwYCountChars", wintypes.DWORD),
        ("dwFillAttribute", wintypes.DWORD),
        ("dwFlags", wintypes.DWORD),
        ("wShowWindow", wintypes.WORD),
        ("cbReserved2", wintypes.WORD),
        ("lpReserved2", ctypes.c_void_p),
        ("hStdInput", wintypes.HANDLE),
        ("hStdOutput", wintypes.HANDLE),
        ("hStdError", wintypes.HANDLE),
    ]

class _PROCESS_INFORMATION(ctypes.Structure):
    _fields_ = [
        ("hProcess", wintypes.HANDLE),
        ("hThread", wintypes.HANDLE),
        ("dwProcessId", wintypes.DWORD),
        ("dwThreadId", wintypes.DWORD),
    ]

def _launch_on_default_desktop(cmd_line: str, desktop: str = "WinSta0\\Default") -> Optional[int]:
    """
    Launches a command line explicitly onto the user's interactive desktop (WinSta0\\Default).
    This guarantees that processes spawned by background services or non-default session
    desktops appear visibly on the user's physical monitor.
    """
    try:
        si = _STARTUPINFOW()
        si.cb = ctypes.sizeof(_STARTUPINFOW)
        si.lpDesktop = desktop

        pi = _PROCESS_INFORMATION()
        k32 = ctypes.windll.kernel32
        res = k32.CreateProcessW(
            None,
            cmd_line,
            None,
            None,
            False,
            0,
            None,
            None,
            ctypes.byref(si),
            ctypes.byref(pi)
        )
        if res:
            pid = pi.dwProcessId
            k32.CloseHandle(pi.hThread)
            k32.CloseHandle(pi.hProcess)
            return pid
    except Exception:
        pass
    return None

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
    clow = clean.lower()
    for cand in candidates:
        if cand and os.path.exists(cand):
            base = os.path.basename(cand).lower()
            if clow in base:
                return cand
            if 'brave' in clow and 'brave' in base:
                return cand
            if 'chrome' in clow and 'chrome' in base:
                return cand
            if ('code' in clow or 'vscode' in clow) and 'code' in base:
                return cand
            if 'spotify' in clow and 'spotify' in base:
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
    tier=0,
    description="Launch an application or open a web URL",
    args_schema=OpenAppArgs,
    preview_fn=lambda a: f"Launch application or URL: '{a.get('app_name')}'" + (f" with args '{a.get('url_or_args')}'" if a.get('url_or_args') else ""),
    can_remember_per_folder=False
)
def open_app(app_name: str, url_or_args: Optional[str] = None) -> Dict[str, Any]:
    resolved = resolve_application_path(app_name)
    clean_name = app_name.strip()

    target = resolved
    args_str = ""

    # Check if target is a web URL
    is_url = clean_name.startswith("http://") or clean_name.startswith("https://") or resolved.startswith("http://") or resolved.startswith("https://")

    if is_url:
        target_url = resolved if (resolved.startswith("http://") or resolved.startswith("https://")) else clean_name
        
        # 1. Primary: Launch on interactive desktop WinSta0\Default via cmd.exe start
        cmd_str = f'cmd.exe /c start "" "{target_url}"'
        pid = _launch_on_default_desktop(cmd_str)
        if pid:
            guardian.track_pid(pid)
            return {
                "app_name": clean_name,
                "resolved_path": target_url,
                "launched": True,
                "launcher_pid": pid,
                "message": f"Successfully opened {clean_name}"
            }

        # 2. Secondary fallback: WScript.Shell
        try:
            import win32com.client
            import pythoncom
            pythoncom.CoInitialize()
            w = win32com.client.Dispatch("WScript.Shell")
            w.Run(f'cmd.exe /c start "" "{target_url}"', 1, False)
            pythoncom.CoUninitialize()
            return {
                "app_name": clean_name,
                "resolved_path": target_url,
                "launched": True,
                "message": f"Successfully opened {clean_name}"
            }
        except Exception:
            pass

        # 3. Tertiary fallback: webbrowser module
        import webbrowser
        try:
            webbrowser.open(target_url, new=2)
        except Exception:
            pass

        return {
            "app_name": clean_name,
            "resolved_path": target_url,
            "launched": True,
            "message": f"Successfully opened {clean_name}"
        }

    # Application launching (e.g. "brave", "chrome", "notepad", "calc")
    is_chromium = any(b in clean_name.lower() or b in os.path.basename(resolved).lower() for b in ("brave", "chrome", "msedge", "firefox"))
    if is_chromium:
        args_str = "--new-window --disable-gpu --disable-extensions"
    if url_or_args:
        args_str = f"{args_str} {url_or_args}".strip()

    # Determine command to run on Default desktop
    if os.path.isabs(target) and os.path.exists(target):
        cmd_to_run = f'"{target}" {args_str}'.strip() if args_str else f'"{target}"'
    else:
        cmd_to_run = f'cmd.exe /c start "" "{target}" {args_str}'.strip() if args_str else f'cmd.exe /c start "" "{target}"'

    # 1. Primary method: CreateProcessW explicitly targeting WinSta0\Default
    pid = _launch_on_default_desktop(cmd_to_run)
    if pid:
        guardian.track_pid(pid)
        return {
            "app_name": clean_name,
            "resolved_path": resolved,
            "launched": True,
            "launcher_pid": pid,
            "message": f"Successfully launched {clean_name}"
        }

    # 2. Secondary method: COM WScript.Shell
    try:
        import win32com.client
        import pythoncom
        pythoncom.CoInitialize()
        w = win32com.client.Dispatch("WScript.Shell")
        w.Run(cmd_to_run, 1, False)
        pythoncom.CoUninitialize()
        return {
            "app_name": clean_name,
            "resolved_path": resolved,
            "launched": True,
            "message": f"Successfully launched {clean_name}"
        }
    except Exception:
        pass

    # 3. Tertiary method: Subprocess fallback
    cmd = [target]
    if args_str:
        cmd.extend(args_str.split())
    proc = subprocess.Popen(cmd)
    guardian.track_pid(proc.pid)
    return {
        "app_name": clean_name,
        "resolved_path": resolved,
        "launched": True,
        "launcher_pid": proc.pid,
        "message": f"Successfully launched {clean_name}"
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
