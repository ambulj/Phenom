"""
Phenom Data Pipeline & Enclave Sandbox Tool Registrations (WKF-04)
Registers:
- encapsulate_untrusted_data (Tier 0)
- stage_enclave_diff_preview (Tier 1)
- commit_enclave_data_to_file (Tier 1)
"""

from typing import Dict, Any, Optional
from pydantic import BaseModel, Field

from services.backend.safety.registry import registry
from services.backend.security.taint_enclave import taint_enclave


class EncapsulateUntrustedDataArgs(BaseModel):
    raw_content: str = Field(description="Raw untrusted text extracted from web or external source")
    source: str = Field(description="Origin URL or identifier of the untrusted source")


class StageEnclaveDiffPreviewArgs(BaseModel):
    target_file_path: str = Field(description="Target workspace or Obsidian note path to update")
    proposed_content: str = Field(description="Sanitized content proposed to write into the file")
    taint_source: str = Field(description="Origin source of the proposed content")


class CommitEnclaveDataArgs(BaseModel):
    diff_id: str = Field(description="Unique staged diff identifier to commit to disk")


@registry.register(
    name="encapsulate_untrusted_data",
    tier=0,
    description="Encapsulates external web data into [UNTRUSTED_TAINT] enclave and neutralizes prompt injections.",
    args_schema=EncapsulateUntrustedDataArgs,
    preview_fn=lambda a: f"Encapsulate untrusted content from '{a.get('source')}' into taint enclave"
)
def encapsulate_untrusted_data(raw_content: str, source: str) -> Dict[str, Any]:
    payload = taint_enclave.encapsulate(raw_content, source)
    return payload.model_dump()


@registry.register(
    name="stage_enclave_diff_preview",
    tier=1,
    description="Calculates and broadcasts a side-by-side diff preview card to the desktop UI before modifying files.",
    args_schema=StageEnclaveDiffPreviewArgs,
    preview_fn=lambda a: f"Stage side-by-side diff preview for '{a.get('target_file_path')}' from '{a.get('taint_source')}'"
)
def stage_enclave_diff_preview(
    target_file_path: str,
    proposed_content: str,
    taint_source: str
) -> Dict[str, Any]:
    diff_payload = taint_enclave.stage_diff_preview(target_file_path, proposed_content, taint_source)
    return diff_payload.model_dump()


@registry.register(
    name="commit_enclave_data_to_file",
    tier=1,
    description="Applies an authorized staged diff to disk with Rule 7 recycle bin backup protection.",
    args_schema=CommitEnclaveDataArgs,
    preview_fn=lambda a: f"Commit authorized diff '{a.get('diff_id')}' to workspace file"
)
def commit_enclave_data_to_file(diff_id: str) -> Dict[str, Any]:
    return taint_enclave.commit_diff(diff_id)
