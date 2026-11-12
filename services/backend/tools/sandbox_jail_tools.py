"""Safety-Wrapped Sovereign Sandbox Jail Tools.

Registers tools with ToolRegistry for AST code security auditing, sandboxed micro-jail
execution, and capability telemetry (Phase 24-02 SEC-04 / ENV-02).
"""

from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field

from services.backend.safety.registry import registry
from services.backend.sandbox.ast_security_visitor import code_security_auditor
from services.backend.sandbox.execution_jail import execution_jail


# ==========================================
# 1. Validate Code Security (Tier 0)
# ==========================================

class ValidateCodeSecurityArgs(BaseModel):
    source_code: str = Field(..., description="Python source code to audit for security violations")


def validate_code_security_preview(args: Dict[str, Any]) -> str:
    lines = args.get("source_code", "").splitlines()
    snippet = lines[0] if lines else "code"
    return f"Perform static AST security audit on code snippet: '{snippet[:50]}...'."


@registry.register(
    name="validate_code_security",
    tier=0,
    description="Audits source code trees for disallowed module imports, dangerous calls, and jail escape vectors.",
    args_schema=ValidateCodeSecurityArgs,
    preview_fn=validate_code_security_preview,
    can_remember_per_folder=False,
)
def handle_validate_code_security(source_code: str) -> Dict[str, Any]:
    verdict = code_security_auditor.audit_code(source_code=source_code)
    return verdict.model_dump()


# ==========================================
# 2. Execute In Sandbox Jail (Tier 1)
# ==========================================

class ExecuteInSandboxJailArgs(BaseModel):
    source_code: str = Field(..., description="Python source code to execute inside the isolated sandbox jail")
    timeout_seconds: Optional[float] = Field(
        default=2.0,
        description="Maximum execution runtime in seconds (default 2.0s)",
    )


def execute_in_sandbox_jail_preview(args: Dict[str, Any]) -> str:
    tout = args.get("timeout_seconds", 2.0)
    return f"Execute code inside isolated micro-sandbox jail (timeout: {tout}s, restricted builtins, no filesystem/sockets)."


@registry.register(
    name="execute_in_sandbox_jail",
    tier=1,
    description="Executes code in an ephemeral isolated sandbox jail with restricted builtins and execution timeouts.",
    args_schema=ExecuteInSandboxJailArgs,
    preview_fn=execute_in_sandbox_jail_preview,
    can_remember_per_folder=False,
)
def handle_execute_in_sandbox_jail(
    source_code: str,
    timeout_seconds: float = 2.0,
) -> Dict[str, Any]:
    res = execution_jail.execute_code(
        source_code=source_code,
        timeout_seconds=timeout_seconds,
    )
    return res.model_dump()


# ==========================================
# 3. Get Sandbox Telemetry (Tier 0)
# ==========================================

class GetSandboxTelemetryArgs(BaseModel):
    pass


def get_sandbox_telemetry_preview(args: Dict[str, Any]) -> str:
    return "Retrieve sandbox jail execution metrics, capability gates, and security statistics."


@registry.register(
    name="get_sandbox_telemetry",
    tier=0,
    description="Queries sandbox execution metrics, capability gates, and blocked security attempt counts.",
    args_schema=GetSandboxTelemetryArgs,
    preview_fn=get_sandbox_telemetry_preview,
    can_remember_per_folder=False,
)
def handle_get_sandbox_telemetry() -> Dict[str, Any]:
    return execution_jail.get_telemetry()
