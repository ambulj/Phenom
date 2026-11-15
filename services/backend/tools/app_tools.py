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
import urllib.parse
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


# ==============================================================================
# Application Allowlist & Safe Launch (Task 6G.1)
# ==============================================================================

APPROVED_APP_NAMES = {
    "notepad", "calc", "calculator", "brave", "chrome", "msedge", "edge",
    "firefox", "code", "vscode", "spotify", "slack", "discord", "obsidian",
    "explorer"
}

APPROVED_APP_EXES = {
    "notepad.exe", "calc.exe", "brave.exe", "chrome.exe", "msedge.exe",
    "firefox.exe", "code.exe", "code.cmd", "spotify.exe", "slack.exe",
    "discord.exe", "obsidian.exe", "explorer.exe"
}

PROHIBITED_URL_CHARS = set("&|;\"'^%<>\r\n`$")

def is_app_allowlisted(name: str, resolved_path: str) -> bool:
    clean = name.strip().lower().replace(".exe", "")
    if clean in APPROVED_APP_NAMES:
        return True
    base = os.path.basename(resolved_path).lower()
    if base in APPROVED_APP_EXES or base.replace(".exe", "") in APPROVED_APP_NAMES:
        return True
    return False

def validate_url(url: str) -> str:
    clean_url = url.strip()
    if not (clean_url.startswith("http://") or clean_url.startswith("https://")):
        raise PermissionError(f"Prohibited URL scheme for open_app: '{clean_url}'. Only http/https supported.")
    if any(c in PROHIBITED_URL_CHARS for c in clean_url):
        raise PermissionError(f"Prohibited shell characters detected in URL: '{clean_url}'")
    parsed = urllib.parse.urlparse(clean_url)
    if not parsed.netloc:
        raise PermissionError(f"Invalid URL structure: '{clean_url}'")
    return clean_url


@registry.register(
    name="open_app",
    tier=0,
    description="Launch an application or open a web URL (strictly allowlisted)",
    args_schema=OpenAppArgs,
    preview_fn=lambda a: f"Launch application or URL: '{a.get('app_name')}'" + (f" with args '{a.get('url_or_args')}'" if a.get('url_or_args') else ""),
    can_remember_per_folder=False
)
def open_app(app_name: str, url_or_args: Optional[str] = None) -> Dict[str, Any]:
    clean_name = app_name.strip()
    resolved = resolve_application_path(app_name)

    # Check if target is a web URL
    is_url = clean_name.startswith("http://") or clean_name.startswith("https://") or resolved.startswith("http://") or resolved.startswith("https://")

    if is_url:
        target_url = validate_url(resolved if (resolved.startswith("http://") or resolved.startswith("https://")) else clean_name)
        
        # 1. Primary: Native OS ShellExecute (zero cmd.exe / PowerShell string interpolation)
        try:
            if hasattr(os, "startfile"):
                os.startfile(target_url)
                return {
                    "app_name": clean_name,
                    "resolved_path": target_url,
                    "launched": True,
                    "message": f"Successfully opened {clean_name}"
                }
        except Exception:
            pass

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

    # Application launching - strictly enforce allowlist before execution
    if not is_app_allowlisted(clean_name, resolved):
        raise PermissionError(
            f"Application '{app_name}' (resolved: '{resolved}') is not in the approved application allowlist. "
            f"Approved applications: {sorted(APPROVED_APP_NAMES)}"
        )

    # Quoting & Argument Safety: validate args if provided
    safe_args = []
    is_chromium = any(b in clean_name.lower() or b in os.path.basename(resolved).lower() for b in ("brave", "chrome", "msedge", "firefox"))
    if is_chromium:
        safe_args.extend(["--new-window", "--disable-gpu", "--disable-extensions"])
    if url_or_args:
        # Prevent shell breakout characters in url_or_args
        for bad_char in ["&", "|", ";", "\n", "\r", "`", "$"]:
            if bad_char in url_or_args:
                raise PermissionError(f"Prohibited character '{bad_char}' detected in application arguments.")
        safe_args.extend(url_or_args.strip().split())

    # Build safe command line using subprocess.list2cmdline (never raw shell string concatenation)
    full_cmd_list = [resolved] + safe_args
    cmd_to_run = subprocess.list2cmdline(full_cmd_list)

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

    # 2. Secondary method: os.startfile with safe argument string
    try:
        if hasattr(os, "startfile"):
            args_str = subprocess.list2cmdline(safe_args) if safe_args else ""
            if args_str:
                os.startfile(resolved, arguments=args_str)
            else:
                os.startfile(resolved)
            return {
                "app_name": clean_name,
                "resolved_path": resolved,
                "launched": True,
                "message": f"Successfully launched {clean_name}"
            }
    except Exception:
        pass

    # 3. Tertiary method: Subprocess list fallback (never shell=True)
    proc = subprocess.Popen(full_cmd_list)
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


# ==========================================
# WSL / Kali Linux Execution Tools
# ==========================================

class RunWslCommandArgs(BaseModel):
    command: str = Field(..., description="Linux/Kali command to execute in WSL (e.g. 'uname -a', 'nmap 127.0.0.1', 'which sqlmap')")
    distro: Optional[str] = Field(default=None, description="Target WSL distribution name (e.g. 'kali-linux', 'Ubuntu'). Defaults to default distribution.")
    timeout_seconds: Optional[int] = Field(default=30, description="Execution timeout in seconds.")

def run_wsl_command_preview(args: Dict[str, Any]) -> str:
    cmd = args.get("command", "")
    distro = args.get("distro", "default")
    return f"Execute Linux/Kali command in WSL ({distro}): {cmd}"

@registry.register(
    name="run_wsl_command",
    tier=1,
    description="Executes a Linux or Kali Linux command inside Windows Subsystem for Linux (WSL/WSL2) and returns output.",
    args_schema=RunWslCommandArgs,
    preview_fn=run_wsl_command_preview,
    can_remember_per_folder=False
)
def run_wsl_command(command: str, distro: Optional[str] = None, timeout_seconds: int = 30) -> Dict[str, Any]:
    cmd_args = ["wsl"]
    if distro:
        cmd_args.extend(["-d", distro])
    cmd_args.extend(["bash", "-c", command])

    try:
        proc = subprocess.run(cmd_args, capture_output=True, text=True, timeout=timeout_seconds)
        return {
            "command": command,
            "distro": distro or "default",
            "returncode": proc.returncode,
            "stdout": proc.stdout.strip(),
            "stderr": proc.stderr.strip(),
            "success": proc.returncode == 0
        }
    except subprocess.TimeoutExpired:
        return {
            "command": command,
            "distro": distro or "default",
            "returncode": -1,
            "stdout": "",
            "stderr": f"Command timed out after {timeout_seconds} seconds",
            "success": False
        }
    except Exception as exc:
        return {
            "command": command,
            "distro": distro or "default",
            "returncode": -1,
            "stdout": "",
            "stderr": str(exc),
            "success": False
        }
