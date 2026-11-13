"""
Phenom Autonomous Red-vs-Blue Cyber War Game & Hardening Tool Suite
Registers:
1. execute_cyber_wargame (Tier 1) - Runs a multi-round Red vs Blue duel generating countermeasures
2. generate_firewall_hardening_script (Tier 0) - Synthesizes Windows netsh / Linux iptables firewall rules
3. get_wargame_history (Tier 0) - Retrieves history of completed war game simulations and AAR debriefs
"""

from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field

from services.backend.safety.registry import registry
from services.backend.cyber.cyber_wargame import cyber_wargame


# 1. Execute War Game
class WargameArgs(BaseModel):
    target_scope: str = Field(default="127.0.0.1", description="Target IP or hostname for simulated evaluation")
    simulated_scenario: str = Field(default="web_server", description="Target scenario: web_server, api_gateway, or local_workstation")

@registry.register(
    name="execute_cyber_wargame",
    tier=1,
    description="Orchestrates an autonomous 3-round Red-vs-Blue duel on an isolated local target to generate defensive mitigations and an Obsidian AAR.",
    args_schema=WargameArgs,
    preview_fn=lambda a: f"Execute Red-vs-Blue cyber war game on {a.get('target_scope', '127.0.0.1')} ({a.get('simulated_scenario', 'web_server')})",
    can_remember_per_folder=False
)
def execute_cyber_wargame(target_scope: str = "127.0.0.1", simulated_scenario: str = "web_server") -> Dict[str, Any]:
    return cyber_wargame.execute_wargame_simulation(target_scope=target_scope, simulated_scenario=simulated_scenario)


# 2. Firewall Script Generator
class FirewallScriptArgs(BaseModel):
    blocked_ports: List[int] = Field(description="List of port numbers to block")
    platform: str = Field(default="windows", description="Target platform: 'windows' or 'linux'")

@registry.register(
    name="generate_firewall_hardening_script",
    tier=0,
    description="Synthesizes copyable Windows netsh or Linux iptables firewall commands to block vulnerable ports.",
    args_schema=FirewallScriptArgs,
    preview_fn=lambda a: f"Synthesize {a.get('platform', 'windows')} firewall rules for ports {a.get('blocked_ports', [])}",
    can_remember_per_folder=False
)
def generate_firewall_hardening_script(blocked_ports: List[int], platform: str = "windows") -> Dict[str, Any]:
    return cyber_wargame.generate_firewall_hardening_script(blocked_ports=blocked_ports, platform=platform)


# 3. History
class WargameHistoryArgs(BaseModel):
    pass

@registry.register(
    name="get_wargame_history",
    tier=0,
    description="Retrieves the history of completed cyber war game simulations and after-action reports.",
    args_schema=WargameHistoryArgs,
    preview_fn=lambda a: "Retrieve cyber war game history",
    can_remember_per_folder=False
)
def get_wargame_history() -> List[Dict[str, Any]]:
    return cyber_wargame.get_wargame_history()
