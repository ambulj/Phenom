"""
Phenom Shared Partition Vault Tool Registry
Registers:
1. sync_shared_vault_state (Tier 1) - Upserts campaign execution state into shared dual-boot vault
2. query_shared_vault_records (Tier 0) - Queries threat actors or campaign history from shared vault
3. verify_vault_integrity (Tier 0) - Audits shared database integrity and synchronization posture
"""

from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field

from services.backend.safety.registry import registry
from services.backend.platform.shared_vault import shared_vault


# 1. Sync Shared Vault State
class SyncVaultStateArgs(BaseModel):
    run_id: str = Field(..., description="Unique campaign execution identifier")
    campaign_name: str = Field(..., description="Name of the red-team mission")
    target_scope: str = Field(..., description="Target host or subnet scope")
    current_stage: int = Field(..., description="Current kill-chain stage (1-5)")
    status: str = Field(..., description="Campaign status (RUNNING, COMPLETED, ABORTED)")
    findings: Optional[Dict[str, Any]] = Field(default_factory=dict, description="Discovered vulnerabilities and findings")


def sync_preview(args: Dict[str, Any]) -> str:
    name = args.get("campaign_name", "campaign")
    stage = args.get("current_stage", 1)
    status = args.get("status", "RUNNING")
    return f"Sync campaign '{name}' (Stage {stage}, Status: {status}) to shared dual-boot vault"


@registry.register(
    name="sync_shared_vault_state",
    tier=1,
    description="Synchronizes a red-team campaign execution state and findings into the encrypted shared partition vault.",
    args_schema=SyncVaultStateArgs,
    preview_fn=sync_preview,
    can_remember_per_folder=False
)
def sync_shared_vault_state(
    run_id: str,
    campaign_name: str,
    target_scope: str,
    current_stage: int,
    status: str,
    findings: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    return shared_vault.store_campaign_run(
        run_id=run_id,
        campaign_name=campaign_name,
        target_scope=target_scope,
        current_stage=current_stage,
        status=status,
        findings=findings or {}
    )


# 2. Query Shared Vault Records
class QueryVaultRecordsArgs(BaseModel):
    category: str = Field(default="threat_actors", description="Query category: 'threat_actors' or 'campaign'")
    search_term: Optional[str] = Field(default="", description="Search string or run_id")


@registry.register(
    name="query_shared_vault_records",
    tier=0,
    description="Queries threat actors or campaign runs from the encrypted shared dual-boot vault.",
    args_schema=QueryVaultRecordsArgs,
    preview_fn=lambda a: f"Query shared vault for category '{a.get('category', 'threat_actors')}'",
    can_remember_per_folder=False
)
def query_shared_vault_records(category: str = "threat_actors", search_term: str = "") -> Dict[str, Any]:
    if category == "campaign":
        record = shared_vault.get_campaign_run(search_term)
        return {"category": category, "record": record}
    else:
        actors = shared_vault.query_threat_actors(search_term)
        return {"category": category, "count": len(actors), "actors": actors}


# 3. Verify Vault Integrity
class VerifyVaultIntegrityArgs(BaseModel):
    pass


@registry.register(
    name="verify_vault_integrity",
    tier=0,
    description="Audits the database integrity, encryption state, and record counts of the shared dual-boot vault.",
    args_schema=VerifyVaultIntegrityArgs,
    preview_fn=lambda a: "Audit shared dual-boot vault database integrity and encryption",
    can_remember_per_folder=False
)
def verify_vault_integrity() -> Dict[str, Any]:
    return shared_vault.verify_vault_integrity()
