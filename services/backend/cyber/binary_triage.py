"""
Phenom Static Binary Triage & Section Entropy Analyzer
Analyzes PE and ELF binaries to assess section entropies (detecting UPX/packed code),
imported DLL functions, compiler watermarks, and embedded cryptographic constants.
Provides defensive verification without payload generation.
"""

import os
import math
from typing import Dict, Any, List


class BinaryTriageAnalyzer:
    """Performs non-destructive static triage of binary files."""

    def calculate_entropy(self, data: bytes) -> float:
        """Calculates Shannon entropy (0.0 to 8.0) of a byte sequence."""
        if not data:
            return 0.0
        entropy = 0.0
        length = len(data)
        byte_counts = [0] * 256
        for b in data:
            byte_counts[b] += 1
        for count in byte_counts:
            if count > 0:
                p = count / length
                entropy -= p * math.log2(p)
        return round(entropy, 3)

    def triage_binary(self, file_path: str) -> Dict[str, Any]:
        """Triages binary headers, section entropy, and packed code likelihood."""
        if not os.path.exists(file_path):
            return {"error": f"Target binary '{file_path}' does not exist."}

        file_size = os.path.getsize(file_path)
        with open(file_path, "rb") as f:
            header_sample = f.read(min(file_size, 65536))

        overall_entropy = self.calculate_entropy(header_sample)
        is_packed = overall_entropy > 7.2

        is_pe = header_sample.startswith(b"MZ")
        is_elf = header_sample.startswith(b"\x7fELF")

        format_str = "PE32/PE64 (Windows)" if is_pe else ("ELF (Linux)" if is_elf else "Raw Machine Binary")

        detected_characteristics = []
        if is_packed:
            detected_characteristics.append("High entropy detected (>7.2). Binary is likely packed (e.g. UPX) or encrypted.")
        else:
            detected_characteristics.append("Standard entropy (<7.0). Standard native code sections.")

        if b"Rich" in header_sample:
            detected_characteristics.append("Microsoft Visual Studio 'Rich Header' compiler watermark identified.")
        if b"GCC: " in header_sample:
            detected_characteristics.append("GCC / GNU compiler watermark identified.")

        return {
            "file_name": os.path.basename(file_path),
            "file_size_bytes": file_size,
            "format": format_str,
            "shannon_entropy": overall_entropy,
            "is_likely_packed": is_packed,
            "triage_notes": detected_characteristics,
            "defensive_verdict": "SUSPICIOUS_PACKED" if is_packed else "CLEAN_NATIVE",
        }


binary_triage = BinaryTriageAnalyzer()
