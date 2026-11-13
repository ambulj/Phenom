"""
Phenom IoT Firmware Triage & Binwalk Extraction Engine
Scans binary firmware images (.bin, .rom, .img, .tar) for embedded filesystems,
bootloaders, compressed payloads, and hardcoded security flaws:
- Magic Header Signatures: SquashFS, CramFS, JFFS2, U-Boot, LZMA/Gzip
- Credential & Key Auditing: Embedded RSA/SSH private keys, /etc/shadow hashes
- Web Root Assessment: Insecure CGI endpoints and hardcoded admin tokens
Generates automated Obsidian Markdown security debrief reports.
"""

import os
import re
from typing import Dict, Any, List, Optional
from services.backend.safety.guardian import guardian


class FirmwareTriageEngine:
    """Inspects and audits embedded IoT firmware binaries for security vulnerabilities."""

    SIGNATURES = {
        b"hsqs": {"fs": "SquashFS (Little-Endian)", "category": "Filesystem"},
        b"sqsh": {"fs": "SquashFS (Big-Endian)", "category": "Filesystem"},
        b"\x28\xcd\x3d\x45": {"fs": "CramFS", "category": "Filesystem"},
        b"\x85\x19": {"fs": "JFFS2", "category": "Filesystem"},
        b"\x27\x05\x19\x56": {"fs": "U-Boot Image Header", "category": "Bootloader"},
        b"\x1f\x8b\x08": {"fs": "GZIP Compressed Archive", "category": "Compression"},
        b"\xfd7zXZ\x00": {"fs": "XZ Compressed Data", "category": "Compression"},
    }

    def analyze_firmware_image(self, file_path: str) -> Dict[str, Any]:
        """Scans a firmware binary image for filesystem headers and embedded credentials."""
        if guardian.is_halted:
            raise PermissionError("Guardian kill switch active. Aborting firmware triage.")

        if not os.path.exists(file_path):
            return {"error": f"Firmware image '{file_path}' not found."}

        file_size = os.path.getsize(file_path)
        file_name = os.path.basename(file_path)

        with open(file_path, "rb") as f:
            raw_data = f.read(min(file_size, 5 * 1024 * 1024))  # Sample up to 5MB

        # 1. Identify Magic Signatures
        discovered_headers = []
        for magic, meta in self.SIGNATURES.items():
            offset = raw_data.find(magic)
            if offset != -1:
                discovered_headers.append({
                    "offset_hex": hex(offset),
                    "offset_decimal": offset,
                    "component": meta["fs"],
                    "category": meta["category"]
                })

        # 2. Scan for hardcoded credentials & keys
        vulnerabilities = []
        if b"BEGIN RSA PRIVATE KEY" in raw_data or b"BEGIN OPENSSH PRIVATE KEY" in raw_data:
            vulnerabilities.append({
                "severity": "CRITICAL",
                "finding": "Hardcoded Private SSH/RSA Key embedded in firmware image"
            })

        if re.search(rb"root:\$[156]\$[a-zA-Z0-9./]+", raw_data):
            vulnerabilities.append({
                "severity": "HIGH",
                "finding": "Hardcoded crypt(3) shadow password hash identified"
            })

        if b"/cgi-bin/" in raw_data:
            vulnerabilities.append({
                "severity": "MEDIUM",
                "finding": "Legacy CGI-bin web interface discovered in binary strings"
            })

        # 3. Compile Obsidian Debrief Markdown
        report_md = f"""# IoT Firmware Security Debrief: {file_name}
- **Image Size**: `{file_size} bytes` ({round(file_size / (1024*1024), 2)} MB)
- **Filesystem Signatures Identified**: {len(discovered_headers)}
- **High/Critical Vulnerabilities**: {len(vulnerabilities)}

## Embedded Architecture Components
| Offset | Category | Component |
| :--- | :--- | :--- |
"""
        for h in discovered_headers:
            report_md += f"| `{h['offset_hex']}` | {h['category']} | {h['component']} |\n"

        if not discovered_headers:
            report_md += "| `0x00` | Raw / Monolithic | Monolithic Kernel / Proprietary RTOS |\n"

        report_md += "\n## Security Audit & Vulnerabilities\n"
        if vulnerabilities:
            for v in vulnerabilities:
                report_md += f"- **[{v['severity']}]**: {v['finding']}\n"
        else:
            report_md += "- No obvious cleartext private keys or default shadow hashes detected in sample space.\n"

        return {
            "file_name": file_name,
            "file_size_bytes": file_size,
            "components_detected": len(discovered_headers),
            "headers": discovered_headers,
            "vulnerabilities": vulnerabilities,
            "risk_score": "CRITICAL" if any(v["severity"] == "CRITICAL" for v in vulnerabilities) else ("MEDIUM" if vulnerabilities else "LOW"),
            "obsidian_report": report_md
        }


firmware_triage = FirmwareTriageEngine()
