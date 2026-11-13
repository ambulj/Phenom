"""
Phenom Active Cyber Deception & Canary Token Tool Suite
Registers:
1. start_cyber_honeypots (Tier 1) - Launches in-RAM SSH/Telnet/HTTP decoy listener sockets
2. stop_cyber_honeypots (Tier 0) - Halts all active honeypot listeners
3. generate_canary_token_file (Tier 1) - Generates decoy credential file (.env, JSON) with tracking tripwire
4. audit_canary_tripwires (Tier 0) - Checks for tampering, reads, or deletions of canary tokens
5. get_deception_intruder_logs (Tier 0) - Retrieves probe and intruder audit history
"""

from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field

from services.backend.safety.registry import registry
from services.backend.cyber.deception_enclave import deception_enclave


# 1. Start Honeypots
class StartHoneypotsArgs(BaseModel):
    ports: Optional[List[int]] = Field(default=None, description="Optional list of ports to bind (defaults to [2222, 2323, 8088])")

@registry.register(
    name="start_cyber_honeypots",
    tier=1,
    description="Launches lightweight in-RAM honeypot sockets (SSH 2222, Telnet 2323, HTTP 8088) to trap unauthorized network scanners.",
    args_schema=StartHoneypotsArgs,
    preview_fn=lambda a: f"Arm in-RAM deception honeypots on ports {a.get('ports') or [2222, 2323, 8088]}",
    can_remember_per_folder=False
)
def start_cyber_honeypots(ports: Optional[List[int]] = None) -> Dict[str, Any]:
    return deception_enclave.start_honeypots(ports=ports)


# 2. Stop Honeypots
class StopHoneypotsArgs(BaseModel):
    pass

@registry.register(
    name="stop_cyber_honeypots",
    tier=0,
    description="Shuts down all active honeypot listening sockets immediately.",
    args_schema=StopHoneypotsArgs,
    preview_fn=lambda a: "Stop all active deception honeypots",
    can_remember_per_folder=False
)
def stop_cyber_honeypots() -> Dict[str, Any]:
    return deception_enclave.stop_honeypots()


# 3. Generate Canary Token
class CanaryTokenArgs(BaseModel):
    token_type: str = Field(default="env", description="Type of canary file: 'env' or 'json'")
    target_dir: Optional[str] = Field(default=None, description="Directory path to plant canary file (defaults to current working directory)")

@registry.register(
    name="generate_canary_token_file",
    tier=1,
    description="Generates a uniquely tracked decoy credential file embedded with cryptographic checksum tripwires.",
    args_schema=CanaryTokenArgs,
    preview_fn=lambda a: f"Plant {a.get('token_type', 'env')} canary decoy token file in {a.get('target_dir', 'current workspace')}",
    can_remember_per_folder=False
)
def generate_canary_token_file(token_type: str = "env", target_dir: Optional[str] = None) -> Dict[str, Any]:
    return deception_enclave.generate_canary_token(token_type=token_type, target_dir=target_dir)


# 4. Check Canary Tripwires
class CheckCanariesArgs(BaseModel):
    pass

@registry.register(
    name="audit_canary_tripwires",
    tier=0,
    description="Audits all planted canary decoy files for tampering, unauthorized reads, or deletions.",
    args_schema=CheckCanariesArgs,
    preview_fn=lambda a: "Audit all active canary token tripwires",
    can_remember_per_folder=False
)
def audit_canary_tripwires() -> List[Dict[str, Any]]:
    return deception_enclave.check_canary_tripwires()


# 5. Get Intruder Logs
class GetIntruderLogsArgs(BaseModel):
    pass

@registry.register(
    name="get_deception_intruder_logs",
    tier=0,
    description="Retrieves chronological audit logs of all intercepted honeypot connections and canary tripwire alerts.",
    args_schema=GetIntruderLogsArgs,
    preview_fn=lambda a: "Retrieve deception enclave intruder logs",
    can_remember_per_folder=False
)
def get_deception_intruder_logs() -> List[Dict[str, Any]]:
    return deception_enclave.get_intruder_logs()
