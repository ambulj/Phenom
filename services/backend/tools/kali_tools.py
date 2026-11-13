"""
Phenom Kali Linux Cyber Warfare Integration Module
Provides first-class execution and management of major Kali Linux security tools:
1. Information Gathering & Recon (nmap, masscan, rustscan, amass, sublist3r, dnsrecon, whois, dig, netdiscover, theHarvester)
2. Vulnerability Analysis (nikto, lynis, nmap NSE)
3. Web Application Auditing (sqlmap, gobuster, ffuf, dirb, wpscan, whatweb, commix)
4. Password & Credential Auditing (hashcat, john, hydra, medusa, cewl, crunch)
5. Wireless Security Auditing (aircrack-ng, airgeddon, wifite, kismet, reaver, macchanger)
6. Exploitation & Payloads (msfconsole, msfvenom, searchsploit)
7. Sniffing & Spoofing (wireshark, tshark, tcpdump, bettercap, responder, mitmproxy)
8. Reverse Engineering & Binary Analysis (ghidra, radare2, rizin, gdb, binwalk, checksec, strings, objdump)
9. Forensics & Incident Response (volatility, foremost, chkrootkit, rkhunter)
10. GUI Kali Apps via Windows 11 WSLg (Burp Suite, Wireshark, Ghidra, OWASP ZAP, Armitage, Win-KeX)
"""

import os
import shutil
import subprocess
from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field

from services.backend.safety.registry import registry
from services.backend.safety.guardian import guardian
from services.backend.tools.app_tools import _launch_on_default_desktop
from services.backend.cyber.kali_bridge import kali_bridge

# Standard Kali Linux Toolkit Taxonomy
KALI_TOOL_CATALOG: Dict[str, Dict[str, Any]] = {
    # 1. Information Gathering & Recon
    "nmap": {"category": "Recon", "binary": "nmap", "gui": False, "desc": "Network exploration, port discovery, and service fingerprinting"},
    "masscan": {"category": "Recon", "binary": "masscan", "gui": False, "desc": "Mass IP port scanner for large-scale address spaces"},
    "rustscan": {"category": "Recon", "binary": "rustscan", "gui": False, "desc": "High-speed modern port scanner with Nmap integration"},
    "amass": {"category": "Recon", "binary": "amass", "gui": False, "desc": "In-depth DNS enumeration and network attack surface mapping"},
    "sublist3r": {"category": "Recon", "binary": "sublist3r", "gui": False, "desc": "Subdomain enumeration tool using OSINT"},
    "dnsrecon": {"category": "Recon", "binary": "dnsrecon", "gui": False, "desc": "DNS reconnaissance, zone transfers, and cache snooping"},
    "whois": {"category": "Recon", "binary": "whois", "gui": False, "desc": "Domain registration and IP block lookup"},
    "dig": {"category": "Recon", "binary": "dig", "gui": False, "desc": "DNS lookup utility for nameserver and record interrogation"},
    "netdiscover": {"category": "Recon", "binary": "netdiscover", "gui": False, "desc": "Active/passive ARP reconnaissance scanner for local subnets"},
    "theharvester": {"category": "Recon", "binary": "theHarvester", "gui": False, "desc": "E-mail, subdomain, and employee name gatherer via OSINT"},

    # 2. Vulnerability Analysis
    "nikto": {"category": "Vulnerability Analysis", "binary": "nikto", "gui": False, "desc": "Web server vulnerability scanner for dangerous files/CGI"},
    "lynis": {"category": "Vulnerability Analysis", "binary": "lynis", "gui": False, "desc": "Security auditing and system hardening scan for Unix/Linux"},

    # 3. Web Applications
    "sqlmap": {"category": "Web Applications", "binary": "sqlmap", "gui": False, "desc": "Automated SQL injection detection and database takeover tool"},
    "gobuster": {"category": "Web Applications", "binary": "gobuster", "gui": False, "desc": "Directory, DNS subdomain, and virtual host brute-forcer"},
    "ffuf": {"category": "Web Applications", "binary": "ffuf", "gui": False, "desc": "Fast web fuzzer written in Go for parameters and endpoints"},
    "dirb": {"category": "Web Applications", "binary": "dirb", "gui": False, "desc": "Web content scanner for hidden directories and paths"},
    "wpscan": {"category": "Web Applications", "binary": "wpscan", "gui": False, "desc": "Blackbox WordPress vulnerability and plugin scanner"},
    "whatweb": {"category": "Web Applications", "binary": "whatweb", "gui": False, "desc": "Web technologies and CMS fingerprinting scanner"},
    "commix": {"category": "Web Applications", "binary": "commix", "gui": False, "desc": "Automated command injection and exploitation tool"},

    # 4. Password & Credential Auditing
    "hashcat": {"category": "Password Attacks", "binary": "hashcat", "gui": False, "desc": "GPU-accelerated password recovery engine (supports RTX CUDA)"},
    "john": {"category": "Password Attacks", "binary": "john", "gui": False, "desc": "John the Ripper hash cracking and password security audit tool"},
    "hydra": {"category": "Password Attacks", "binary": "hydra", "gui": False, "desc": "High-speed network login cracker supporting 50+ protocols"},
    "medusa": {"category": "Password Attacks", "binary": "medusa", "gui": False, "desc": "Speedy, parallel, modular login brute-forcer"},
    "cewl": {"category": "Password Attacks", "binary": "cewl", "gui": False, "desc": "Custom wordlist generator spidering target websites"},
    "crunch": {"category": "Password Attacks", "binary": "crunch", "gui": False, "desc": "Wordlist generator based on custom character patterns"},

    # 5. Wireless Security Auditing
    "aircrack-ng": {"category": "Wireless Attacks", "binary": "aircrack-ng", "gui": False, "desc": "802.11 WEP and WPA/WPA2-PSK key cracking program"},
    "wifite": {"category": "Wireless Attacks", "binary": "wifite", "gui": False, "desc": "Automated wireless network auditor targeting WPS, WPA, WEP"},
    "airgeddon": {"category": "Wireless Attacks", "binary": "airgeddon", "gui": False, "desc": "Multi-use bash script for wireless network security audits"},
    "macchanger": {"category": "Wireless Attacks", "binary": "macchanger", "gui": False, "desc": "Network interface MAC address viewing and spoofing utility"},

    # 6. Exploitation & Payloads
    "msfconsole": {"category": "Exploitation", "binary": "msfconsole", "gui": False, "desc": "Metasploit Framework interactive console and exploit runner"},
    "msfvenom": {"category": "Exploitation", "binary": "msfvenom", "gui": False, "desc": "Metasploit standalone payload generator and encoder"},
    "searchsploit": {"category": "Exploitation", "binary": "searchsploit", "gui": False, "desc": "Offline search utility for Exploit-DB archives"},

    # 7. Sniffing & Spoofing
    "tcpdump": {"category": "Sniffing & Spoofing", "binary": "tcpdump", "gui": False, "desc": "CLI network packet analyzer and pcap capture engine"},
    "tshark": {"category": "Sniffing & Spoofing", "binary": "tshark", "gui": False, "desc": "CLI version of Wireshark for automated packet dissection"},
    "bettercap": {"category": "Sniffing & Spoofing", "binary": "bettercap", "gui": False, "desc": "Swiss army knife for 802.11, BLE, and Ethernet MITM testing"},
    "responder": {"category": "Sniffing & Spoofing", "binary": "responder", "gui": False, "desc": "LLMNR, NBT-NS, and MDNS poisoner and credential collector"},
    "mitmproxy": {"category": "Sniffing & Spoofing", "binary": "mitmproxy", "gui": False, "desc": "Interactive TLS-capable intercepting HTTP/HTTPS proxy"},

    # 8. Reverse Engineering & Binary Analysis
    "radare2": {"category": "Reverse Engineering", "binary": "radare2", "gui": False, "desc": "UNIX-like reverse engineering framework and commandline toolset"},
    "gdb": {"category": "Reverse Engineering", "binary": "gdb", "gui": False, "desc": "GNU Project Debugger for low-level memory and crash inspection"},
    "binwalk": {"category": "Reverse Engineering", "binary": "binwalk", "gui": False, "desc": "Firmware analysis tool for extracting embedded files and code"},
    "checksec": {"category": "Reverse Engineering", "binary": "checksec", "gui": False, "desc": "ELF binary security property checker (NX, ASLR, Canaries)"},
    "strings": {"category": "Reverse Engineering", "binary": "strings", "gui": False, "desc": "Find and print printable character sequences in binaries"},

    # 9. Forensics & Incident Response
    "foremost": {"category": "Forensics", "binary": "foremost", "gui": False, "desc": "File carver recovering lost files based on headers and footers"},
    "chkrootkit": {"category": "Forensics", "binary": "chkrootkit", "gui": False, "desc": "Locally checks for signs of rootkits and system compromises"},

    # 10. Native GUI Applications via Windows 11 WSLg
    "burpsuite": {"category": "Web Applications (GUI)", "binary": "burpsuite", "gui": True, "desc": "Burp Suite professional web security testing platform GUI"},
    "wireshark": {"category": "Sniffing & Spoofing (GUI)", "binary": "wireshark", "gui": True, "desc": "Wireshark graphical network packet analyzer"},
    "ghidra": {"category": "Reverse Engineering (GUI)", "binary": "ghidra", "gui": True, "desc": "NSA Ghidra software reverse engineering suite GUI"},
    "zaproxy": {"category": "Web Applications (GUI)", "binary": "zaproxy", "gui": True, "desc": "OWASP Zed Attack Proxy web application scanner GUI"},
    "kex": {"category": "Desktop Environment (GUI)", "binary": "kex", "gui": True, "desc": "Kali Linux Win-KeX full graphical desktop for Windows 11"},
}


# ==========================================
# 1. Execute Kali CLI Tool
# ==========================================

class ExecuteKaliToolArgs(BaseModel):
    tool: str = Field(..., description="Name of the Kali tool (e.g. 'nmap', 'sqlmap', 'gobuster', 'hashcat', 'aircrack-ng', 'searchsploit')")
    arguments: str = Field(..., description="Command-line arguments (e.g. '-sV 192.168.1.1', '-u \"http://target\" --batch', '-w wordlist.txt capture.cap')")
    distro: Optional[str] = Field(default=None, description="Target WSL distro (defaults to 'kali-linux' or default WSL)")
    timeout_seconds: Optional[int] = Field(default=60, description="Execution timeout in seconds")

def execute_kali_tool_preview(args: Dict[str, Any]) -> str:
    tool = args.get("tool", "")
    arguments = args.get("arguments", "")
    distro = args.get("distro") or "kali-linux/wsl"
    return f"Execute Kali Linux tool in {distro}: `{tool} {arguments}`"

@registry.register(
    name="execute_kali_tool",
    tier=1,
    description="Executes a Kali Linux security tool (Nmap, SQLMap, Gobuster, Aircrack-ng, Hashcat, Metasploit, etc.) inside WSL/WSL2 and returns formatted results.",
    args_schema=ExecuteKaliToolArgs,
    preview_fn=execute_kali_tool_preview,
    can_remember_per_folder=False
)
def execute_kali_tool(tool: str, arguments: str, distro: Optional[str] = None, timeout_seconds: int = 60) -> Dict[str, Any]:
    tool_key = tool.lower().strip()
    cmd = f"{tool_key} {arguments}".strip()
    
    cmd_args = ["wsl"]
    if distro:
        cmd_args.extend(["-d", distro])
    cmd_args.extend(["bash", "-c", cmd])

    meta = KALI_TOOL_CATALOG.get(tool_key, {})

    try:
        proc = subprocess.run(cmd_args, capture_output=True, text=True, timeout=timeout_seconds)
        return {
            "tool": tool_key,
            "category": meta.get("category", "General Security"),
            "command": cmd,
            "distro": distro or "default",
            "returncode": proc.returncode,
            "stdout": proc.stdout.strip(),
            "stderr": proc.stderr.strip(),
            "success": proc.returncode == 0
        }
    except subprocess.TimeoutExpired:
        return {
            "tool": tool_key,
            "category": meta.get("category", "General Security"),
            "command": cmd,
            "distro": distro or "default",
            "returncode": -1,
            "stdout": "",
            "stderr": f"Execution timed out after {timeout_seconds}s",
            "success": False
        }
    except Exception as exc:
        return {
            "tool": tool_key,
            "category": meta.get("category", "General Security"),
            "command": cmd,
            "distro": distro or "default",
            "returncode": -1,
            "stdout": "",
            "stderr": str(exc),
            "success": False
        }


# ==========================================
# 2. Launch Kali GUI App via Windows 11 WSLg
# ==========================================

class LaunchKaliGuiArgs(BaseModel):
    app_name: str = Field(..., description="Name of the Kali GUI application (e.g. 'burpsuite', 'wireshark', 'ghidra', 'zaproxy', 'kex')")
    distro: Optional[str] = Field(default=None, description="Target WSL distribution name (defaults to 'kali-linux' or default)")

def launch_kali_gui_preview(args: Dict[str, Any]) -> str:
    app_name = args.get("app_name", "")
    distro = args.get("distro") or "kali-linux/wsl"
    return f"Launch graphical Kali application `{app_name}` on Windows 11 desktop via WSLg ({distro})"

@registry.register(
    name="launch_kali_gui",
    tier=0,
    description="Launches a graphical Kali Linux application (Burp Suite, Wireshark, Ghidra, OWASP ZAP, Win-KeX) on Windows 11 desktop with hardware accelerated WSLg.",
    args_schema=LaunchKaliGuiArgs,
    preview_fn=launch_kali_gui_preview,
    can_remember_per_folder=False
)
def launch_kali_gui(app_name: str, distro: Optional[str] = None) -> Dict[str, Any]:
    app_key = app_name.lower().strip()
    meta = KALI_TOOL_CATALOG.get(app_key, {})
    
    # Check if Windows native executable exists first (e.g. Windows native Wireshark or Burp Suite)
    native_win = shutil.which(app_key) or shutil.which(f"{app_key}.exe")
    if native_win:
        cmd_str = f'cmd.exe /c start "" "{native_win}"'
        pid = _launch_on_default_desktop(cmd_str)
        if pid:
            guardian.track_pid(pid)
            return {
                "app": app_key,
                "mode": "windows_native",
                "launched": True,
                "pid": pid,
                "message": f"Launched native Windows {app_key} window"
            }

    # Otherwise launch through WSLg
    distro_flag = f"-d {distro}" if distro else ""
    cmd_str = f'cmd.exe /c start "" wsl.exe {distro_flag} {app_key}'.strip()
    pid = _launch_on_default_desktop(cmd_str)
    if pid:
        guardian.track_pid(pid)
        return {
            "app": app_key,
            "mode": "wslg_gui",
            "launched": True,
            "pid": pid,
            "message": f"Launched {app_key} via Windows 11 WSLg"
        }
    return {
        "app": app_key,
        "mode": "wslg_gui",
        "launched": False,
        "pid": None,
        "message": f"Failed to spawn {app_key}"
    }


# ==========================================
# 3. Audit Kali Environment & Installed Tools
# ==========================================

class AuditKaliToolkitArgs(BaseModel):
    distro: Optional[str] = Field(default=None, description="WSL distribution to audit (defaults to default distribution)")

@registry.register(
    name="audit_kali_toolkit",
    tier=0,
    description="Audits available Kali Linux tools across all 9 cybersecurity domains, reporting installed binaries, GPU CUDA support, and setup advice.",
    args_schema=AuditKaliToolkitArgs,
    preview_fn=lambda a: "Audit installed Kali Linux cybersecurity tools and WSL environment",
    can_remember_per_folder=False
)
def audit_kali_toolkit(distro: Optional[str] = None) -> Dict[str, Any]:
    # Check which tools are installed via which
    tool_names = list(KALI_TOOL_CATALOG.keys())
    check_script = " ".join([f"which {k} 2>/dev/null || echo 'MISSING_{k}';" for k in tool_names])
    
    cmd_args = ["wsl"]
    if distro:
        cmd_args.extend(["-d", distro])
    cmd_args.extend(["bash", "-c", check_script])

    installed = []
    missing = []

    try:
        res = subprocess.run(cmd_args, capture_output=True, text=True, timeout=15)
        lines = res.stdout.strip().split("\n")
        for line in lines:
            line = line.strip()
            if not line:
                continue
            if line.startswith("MISSING_"):
                k = line.replace("MISSING_", "")
                missing.append(k)
            else:
                # Path returned, extract basename
                bname = os.path.basename(line)
                installed.append(bname)
    except Exception as exc:
        return {"error": str(exc), "installed": [], "missing": tool_names}

    return {
        "distro": distro or "default",
        "total_cataloged": len(tool_names),
        "installed_count": len(installed),
        "missing_count": len(missing),
        "installed_tools": sorted(list(set(installed))),
        "missing_tools": sorted(list(set(missing))),
        "quick_install_command": "sudo apt update && sudo apt install -y kali-linux-default",
        "status": "ready" if len(installed) > 0 else "distro_needs_packages"
    }


# ==========================================
# 4. Safe-Mode Headless Kali Recon Tool
# ==========================================

class ExecuteKaliReconArgs(BaseModel):
    tool: str = Field(..., description="Security tool to execute (e.g. 'nmap', 'whatweb', 'nikto', 'masscan', 'tshark')")
    target: str = Field(default="127.0.0.1", description="Target host or IP address (must be in authorized lab/local subnet)")
    arguments: str = Field(default="", description="Command-line arguments (e.g. '-sV -T4 --top-ports 50')")
    distro: Optional[str] = Field(default=None, description="WSL distro name (defaults to 'kali-linux')")
    timeout_seconds: Optional[int] = Field(default=60, description="Execution timeout in seconds")

@registry.register(
    name="execute_kali_recon",
    tier=1,
    description="Executes a security tool inside Kali Linux WSL2 with Safe-Mode target validation, Guardian PID tracking, and returns structured telemetry.",
    args_schema=ExecuteKaliReconArgs,
    preview_fn=lambda a: f"Execute Safe-Mode Kali tool `{a.get('tool')}` against `{a.get('target', '127.0.0.1')}`",
    can_remember_per_folder=False
)
def execute_kali_recon(
    tool: str,
    target: str = "127.0.0.1",
    arguments: str = "",
    distro: Optional[str] = None,
    timeout_seconds: int = 60
) -> Dict[str, Any]:
    return kali_bridge.run_tool(
        tool=tool,
        arguments=arguments,
        target=target,
        distro=distro,
        timeout=timeout_seconds
    )


# ==========================================
# 5. Kali WSL Status & Safe-Mode Telemetry
# ==========================================

class GetKaliStatusArgs(BaseModel):
    pass

@registry.register(
    name="get_kali_status",
    tier=0,
    description="Queries the health of the Kali Linux WSL2 bridge, default distribution, and active safe-mode target boundaries.",
    args_schema=GetKaliStatusArgs,
    preview_fn=lambda a: "Query Kali Linux WSL2 bridge status and safe-mode bounds",
    can_remember_per_folder=False
)
def get_kali_status() -> Dict[str, Any]:
    return kali_bridge.get_status()


# ==========================================
# 6. Parse Raw Kali Tool Output
# ==========================================

class ParseKaliOutputArgs(BaseModel):
    tool: str = Field(..., description="Name of the tool ('nmap', 'whatweb', 'nikto', 'masscan', 'tshark', 'hashcat')")
    raw_output: str = Field(..., description="Raw console stdout to parse into structured JSON")

@registry.register(
    name="parse_kali_output",
    tier=0,
    description="Parses raw CLI security tool output (Nmap, WhatWeb, Nikto, Masscan, etc.) into typed structured telemetry.",
    args_schema=ParseKaliOutputArgs,
    preview_fn=lambda a: f"Parse raw console output for tool `{a.get('tool')}`",
    can_remember_per_folder=False
)
def parse_kali_output(tool: str, raw_output: str) -> Dict[str, Any]:
    return kali_bridge._parse_output(tool.lower().strip(), raw_output)

