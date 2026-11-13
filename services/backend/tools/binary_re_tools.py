"""
Phenom Binary Reverse Engineering & Frida DBI Tool Suite
Registers:
1. analyze_binary_disassembly (Tier 0) - Disassembles target PE/ELF binary, extracting symbols & dangerous APIs
2. scan_binary_rop_gadgets (Tier 0) - Scans executable text sections for Return-Oriented Programming (ROP) gadgets
3. instrument_process_with_frida (Tier 1) - Injects non-destructive telemetry hooks into target process memory
4. inspect_frida_hook_telemetry (Tier 0) - Inspects intercepted API calls and decrypted in-flight buffers
"""

from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field

from services.backend.safety.registry import registry
from services.backend.cyber.binary_analyzer import binary_analyzer
from services.backend.cyber.frida_instrumentation import frida_engine


# 1. Analyze Binary Disassembly
class AnalyzeDisassemblyArgs(BaseModel):
    file_path: str = Field(..., description="Absolute path to the PE or ELF binary to disassemble")
    max_instructions: Optional[int] = Field(default=50, description="Maximum number of instructions to disassemble")


@registry.register(
    name="analyze_binary_disassembly",
    tier=0,
    description="Disassembles executable sections of Windows PE (.exe/.dll) or Linux ELF binaries, auditing security mitigations and dangerous imported APIs.",
    args_schema=AnalyzeDisassemblyArgs,
    preview_fn=lambda a: f"Disassemble binary '{a.get('file_path')}' and audit security mitigations",
    can_remember_per_folder=False
)
def analyze_binary_disassembly(file_path: str, max_instructions: int = 50) -> Dict[str, Any]:
    return binary_analyzer.disassemble_binary(file_path, max_instructions=max_instructions)


# 2. Scan Binary ROP Gadgets
class ScanROPGadgetsArgs(BaseModel):
    file_path: str = Field(..., description="Absolute path to the binary to scan for ROP gadgets")
    max_gadgets: Optional[int] = Field(default=25, description="Maximum number of gadgets to extract")


@registry.register(
    name="scan_binary_rop_gadgets",
    tier=0,
    description="Scans executable text sections of a binary for Return-Oriented Programming (ROP) gadgets (e.g. pop rdi; ret, syscall).",
    args_schema=ScanROPGadgetsArgs,
    preview_fn=lambda a: f"Scan binary '{a.get('file_path')}' for ROP execution gadgets",
    can_remember_per_folder=False
)
def scan_binary_rop_gadgets(file_path: str, max_gadgets: int = 25) -> Dict[str, Any]:
    return binary_analyzer.scan_rop_gadgets(file_path, max_gadgets=max_gadgets)


# 3. Instrument Process With Frida
class InstrumentProcessArgs(BaseModel):
    pid: int = Field(..., description="Target process ID to attach Frida telemetry hooks to")
    hook_profile: Optional[str] = Field(default="DEFAULT_SECURITY_HOOKS", description="Telemetry hook profile to attach")


def instrument_preview(args: Dict[str, Any]) -> str:
    return f"Attach dynamic binary instrumentation (Frida) to PID {args.get('pid')} (Profile: {args.get('hook_profile', 'DEFAULT')})"


@registry.register(
    name="instrument_process_with_frida",
    tier=1,
    description="Attaches non-destructive Frida dynamic binary instrumentation hooks to a target process to intercept memory allocations and network sockets.",
    args_schema=InstrumentProcessArgs,
    preview_fn=instrument_preview,
    can_remember_per_folder=False
)
def instrument_process_with_frida(pid: int, hook_profile: str = "DEFAULT_SECURITY_HOOKS") -> Dict[str, Any]:
    return frida_engine.instrument_process(pid, hook_profile=hook_profile)


# 4. Inspect Frida Hook Telemetry
class InspectFridaTelemetryArgs(BaseModel):
    pid: Optional[int] = Field(default=None, description="Optional target process ID to filter telemetry events")
    limit: Optional[int] = Field(default=20, description="Maximum number of captured events to retrieve")


@registry.register(
    name="inspect_frida_hook_telemetry",
    tier=0,
    description="Retrieves live intercepted API calls, syscall arguments, and decrypted memory buffer telemetry from active Frida sessions.",
    args_schema=InspectFridaTelemetryArgs,
    preview_fn=lambda a: f"Retrieve Frida dynamic hook telemetry for PID {a.get('pid') or 'all'}",
    can_remember_per_folder=False
)
def inspect_frida_hook_telemetry(pid: Optional[int] = None, limit: int = 20) -> List[Dict[str, Any]]:
    return frida_engine.get_hook_telemetry(pid=pid, limit=limit)
