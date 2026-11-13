"""
Phenom Autonomous Multi-Vector Red-Team Pipeline Tool Suite
Registers:
1. execute_red_team_campaign (Tier 1) - Runs multi-vector automated security campaign
2. get_red_team_history (Tier 0) - Retrieves previous campaign executions and AAR reports
"""

from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field

from services.backend.safety.registry import registry
from services.backend.cyber.red_team_pipeline import red_team_pipeline


class ExecuteCampaignArgs(BaseModel):
    campaign_type: str = Field(
        default="FULL",
        description="Type of campaign to run: 'FULL', 'LOOPBACK', 'SUBNET', or 'HONEYPOT'"
    )
    target_scope: str = Field(
        default="127.0.0.1",
        description="Target IP address or subnet (must be within authorized lab safe-mode boundaries)"
    )


def execute_campaign_preview(args: Dict[str, Any]) -> str:
    c_type = args.get("campaign_type", "FULL")
    target = args.get("target_scope", "127.0.0.1")
    return f"Launch Autonomous Red-Team Campaign [{c_type}] against safe-mode scope `{target}`"


@registry.register(
    name="execute_red_team_campaign",
    tier=1,
    description="Orchestrates an autonomous multi-vector red-team campaign (loopback audit, subnet asset discovery, honeypot simulation, and Obsidian AAR synthesis).",
    args_schema=ExecuteCampaignArgs,
    preview_fn=execute_campaign_preview,
    can_remember_per_folder=False
)
def execute_red_team_campaign(
    campaign_type: str = "FULL",
    target_scope: str = "127.0.0.1"
) -> Dict[str, Any]:
    return red_team_pipeline.execute_campaign(
        campaign_type=campaign_type,
        target_scope=target_scope
    )


class RedTeamHistoryArgs(BaseModel):
    pass


@registry.register(
    name="get_red_team_history",
    tier=0,
    description="Retrieves the chronological audit log of all completed autonomous red-team campaigns.",
    args_schema=RedTeamHistoryArgs,
    preview_fn=lambda a: "Retrieve red-team campaign history",
    can_remember_per_folder=False
)
def get_red_team_history() -> List[Dict[str, Any]]:
    return red_team_pipeline.get_campaign_history()
