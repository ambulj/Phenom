"""
Phenom Autonomous Cross-Subsystem Tactical DAG Tool Suite
Registers:
1. execute_perimeter_sweep (Tier 1) - Executes multi-subsystem tactical security sweep
2. get_tactical_sweep_history (Tier 0) - Retrieves previous tactical sweep execution debriefs
"""

from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field

from services.backend.safety.registry import registry
from services.backend.cyber.tactical_dag_orchestrator import tactical_dag


# 1. Execute Sweep
class PerimeterSweepArgs(BaseModel):
    target_host: str = Field(default="127.0.0.1", description="Target host to evaluate (defaults to 127.0.0.1)")

@registry.register(
    name="execute_perimeter_sweep",
    tier=1,
    description="Orchestrates an autonomous 5-stage security sweep across radio SIGINT, active sockets, Sigma SIEM, and canary tripwires.",
    args_schema=PerimeterSweepArgs,
    preview_fn=lambda a: f"Execute full perimeter tactical security sweep on {a.get('target_host', '127.0.0.1')}",
    can_remember_per_folder=False
)
def execute_perimeter_sweep(target_host: str = "127.0.0.1") -> Dict[str, Any]:
    return tactical_dag.execute_perimeter_security_sweep(target_host=target_host)


# 2. Get Sweep History
class SweepHistoryArgs(BaseModel):
    pass

@registry.register(
    name="get_tactical_sweep_history",
    tier=0,
    description="Retrieves the chronological audit log of all completed autonomous tactical security sweeps.",
    args_schema=SweepHistoryArgs,
    preview_fn=lambda a: "Retrieve tactical sweep history",
    can_remember_per_folder=False
)
def get_tactical_sweep_history() -> List[Dict[str, Any]]:
    return tactical_dag.get_sweep_history()
