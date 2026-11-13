"""
Phenom CHRONO-CYBER Tool Registry
Registers:
1. execute_chrono_campaign (Tier 1) - Runs 5-stage autonomous red-team campaign DAG
2. get_campaign_dag_status (Tier 0) - Queries live status of an autonomous campaign
3. generate_mitre_debrief (Tier 0) - Synthesizes structured MITRE ATT&CK executive debrief
"""

from typing import Dict, Any, Optional
from pydantic import BaseModel, Field

from services.backend.safety.registry import registry
from services.backend.cyber.chrono_cyber import chrono_cyber


# 1. Execute Chrono Campaign
class ExecuteChronoArgs(BaseModel):
    campaign_name: str = Field(..., description="Name of the red-team operation (e.g. 'Operation Cerberus')")
    target_scope: Optional[str] = Field(default="127.0.0.1", description="Authorized local target scope (must satisfy Safe-Mode)")
    autonomous_lab_mode: Optional[bool] = Field(default=True, description="Execute all 5 stages end-to-end without stopping")


def chrono_preview(args: Dict[str, Any]) -> str:
    name = args.get("campaign_name", "campaign")
    target = args.get("target_scope", "127.0.0.1")
    return f"Execute 5-stage autonomous red-team campaign '{name}' against scope '{target}'"


@registry.register(
    name="execute_chrono_campaign",
    tier=1,
    description="Orchestrates a 5-stage autonomous red-team campaign (Recon -> Initial Access -> PrivEsc -> Persistence -> MITRE Debrief) against authorized lab targets.",
    args_schema=ExecuteChronoArgs,
    preview_fn=chrono_preview,
    can_remember_per_folder=False
)
def execute_chrono_campaign(
    campaign_name: str,
    target_scope: str = "127.0.0.1",
    autonomous_lab_mode: bool = True
) -> Dict[str, Any]:
    return chrono_cyber.execute_campaign(
        campaign_name=campaign_name,
        target_scope=target_scope,
        autonomous_lab_mode=autonomous_lab_mode
    )


# 2. Get Campaign DAG Status
class GetCampaignStatusArgs(BaseModel):
    run_id: str = Field(..., description="Unique campaign execution identifier")


@registry.register(
    name="get_campaign_dag_status",
    tier=0,
    description="Queries the active stage, completion percentage, and discovered findings of an autonomous red-team campaign.",
    args_schema=GetCampaignStatusArgs,
    preview_fn=lambda a: f"Query status of campaign run '{a.get('run_id')}'",
    can_remember_per_folder=False
)
def get_campaign_dag_status(run_id: str) -> Optional[Dict[str, Any]]:
    return chrono_cyber.get_campaign_status(run_id=run_id)


# 3. Generate MITRE Debrief
class GenerateDebriefArgs(BaseModel):
    run_id: str = Field(..., description="Campaign run identifier to synthesize debrief for")


@registry.register(
    name="generate_mitre_debrief",
    tier=0,
    description="Synthesizes an executive MITRE ATT&CK v15 matrix debrief detailing attack vectors, privilege escalation paths, and remediations.",
    args_schema=GenerateDebriefArgs,
    preview_fn=lambda a: f"Generate MITRE ATT&CK debrief for campaign '{a.get('run_id')}'",
    can_remember_per_folder=False
)
def generate_mitre_debrief(run_id: str) -> Dict[str, Any]:
    return chrono_cyber.generate_mitre_debrief(run_id=run_id)
