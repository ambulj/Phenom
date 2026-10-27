"""
Phenom Safety Layer Execution Engine
Enforces the 4-tier security model from SAFETY.md.
No tool call ever bypasses this module.
"""

import asyncio
import os
from typing import Dict, Any, Optional, Callable, Awaitable
from services.backend.schemas.protocol import RiskTier, DecisionType
from services.backend.safety.registry import registry, ToolDefinition
from services.backend.safety.action_log import action_log
from services.backend.safety.approvals import approvals
from services.backend.safety.guardian import guardian

# Confirmation callback hook set by WebSocket server
# Signature: async def request_confirmation(request_id, tool, tier, preview, args, can_remember, folder_path, timeout) -> (decision, remember_choice)
ConfirmationHandler = Callable[
    [str, str, RiskTier, str, Dict[str, Any], bool, Optional[str], int],
    Awaitable[tuple[str, bool]]
]

class SafetyExecutionEngine:
    def __init__(self):
        self._confirmation_handler: Optional[ConfirmationHandler] = None
        self._remote_confirmation_handler: Optional[ConfirmationHandler] = None
        self._tier3_allowlist: set[str] = set() # Empty by default per SAFETY.md section 6

    def set_confirmation_handler(self, handler: ConfirmationHandler):
        self._confirmation_handler = handler

    def set_remote_confirmation_handler(self, handler: ConfirmationHandler):
        self._remote_confirmation_handler = handler

    async def execute_tool(
        self,
        tool_name: str,
        raw_args: Dict[str, Any],
        source: str = "desktop",
        target_folder: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        The central gateway for tool execution.
        Validates, classifies, prompts for confirmation when necessary, executes, and logs.
        """
        # Guard 1: Kill Switch
        if guardian.is_halted:
            action_log.log_action(
                tool=tool_name,
                tier=registry.get_tier(tool_name),
                args=raw_args,
                decision="denied",
                result_status="FAILED",
                source=source,
                error="Guardian kill switch is active. All tool executions halted."
            )
            raise PermissionError("Guardian kill switch is active. Operation halted.")

        # Guard 2: Registry Lookup
        tool_def: Optional[ToolDefinition] = registry.get(tool_name)
        if tool_def is None:
            # Unknown tools default to Tier 3 and are blocked per SAFETY.md
            action_log.log_action(
                tool=tool_name,
                tier=3,
                args=raw_args,
                decision="blocked",
                result_status="BLOCKED",
                source=source,
                error=f"Unregistered tool '{tool_name}' classified as Tier 3 and blocked."
            )
            raise PermissionError(f"Tool '{tool_name}' is not registered and is blocked under Tier 3.")

        tier = tool_def.tier

        # Validate arguments using tool's Pydantic schema
        try:
            validated_args = tool_def.args_schema(**raw_args).model_dump()
        except Exception as e:
            action_log.log_action(
                tool=tool_name,
                tier=tier,
                args=raw_args,
                decision="auto" if tier == 0 else "denied",
                result_status="FAILED",
                source=source,
                error=f"Schema validation error: {e}"
            )
            raise ValueError(f"Invalid arguments for {tool_name}: {e}")

        # Guard 3: Tier 3 Blocked Check
        if tier == 3:
            if source == "telegram":
                action_log.log_action(
                    tool=tool_name,
                    tier=3,
                    args=validated_args,
                    decision="blocked",
                    result_status="BLOCKED",
                    source=source,
                    error="Tier 3 actions cannot be approved remotely. Physical desktop typed confirmation is required."
                )
                raise PermissionError(f"Tier 3 tool '{tool_name}' cannot be approved remotely.")

            if tool_name not in self._tier3_allowlist:
                action_log.log_action(
                    tool=tool_name,
                    tier=3,
                    args=validated_args,
                    decision="blocked",
                    result_status="BLOCKED",
                    source=source,
                    error="Tier 3 operation blocked by default. Not in SAFETY.md allowlist."
                )
                raise PermissionError(f"Tier 3 tool '{tool_name}' is blocked by default.")

        # Guard 4: Tier 0 (Read-Only) -> Auto-run
        if tier == 0:
            return await self._run_and_log(tool_def, validated_args, decision="auto", source=source)

        # Guard 5: Tier 1 (Reversible) -> Check Remembered Approvals
        # Determine target folder if applicable
        folder_for_approval = target_folder or validated_args.get("path") or validated_args.get("dest") or validated_args.get("src")
        if folder_for_approval and os.path.isfile(folder_for_approval):
            folder_for_approval = os.path.dirname(folder_for_approval)

        if tier == 1 and approvals.is_remembered(tool_name, tier, folder_for_approval):
            return await self._run_and_log(tool_def, validated_args, decision="auto", source=source)

        # Guard 6: Tier 1 or Tier 2 Confirmation
        preview_text = tool_def.generate_preview(validated_args)
        req_id = f"conf-{tool_name}-{os.urandom(4).hex()}"
        can_remember = (tier == 1) and bool(folder_for_approval)

        handler_to_use = (
            self._remote_confirmation_handler
            if (source == "telegram" and self._remote_confirmation_handler)
            else self._confirmation_handler
        )

        if not handler_to_use:
            # Without confirmation handler, cannot proceed for Tier 1 or Tier 2
            action_log.log_action(
                tool=tool_name,
                tier=tier,
                args=validated_args,
                decision="denied",
                result_status="FAILED",
                source=source,
                error="Confirmation required but no confirmation handler registered."
            )
            raise PermissionError(f"Action requires confirmation (Tier {tier}), but confirmation handler is unavailable.")

        try:
            decision, remember_choice = await handler_to_use(
                req_id,
                tool_name,
                tier,
                preview_text,
                validated_args,
                can_remember,
                folder_for_approval,
                120  # 120s timeout per SAFETY.md
            )
        except asyncio.TimeoutError:
            action_log.log_action(
                tool=tool_name,
                tier=tier,
                args=validated_args,
                decision="timeout",
                result_status="DENIED_TIMEOUT",
                source=source,
                error="Confirmation timed out after 120 seconds."
            )
            raise TimeoutError("Confirmation timed out after 120 seconds. Action denied.")

        if decision != "approved":
            action_log.log_action(
                tool=tool_name,
                tier=tier,
                args=validated_args,
                decision="denied",
                result_status="DENIED_BY_USER",
                source=source
            )
            raise PermissionError("Action was denied by the user.")

        # If user approved and chose to remember for this folder (Tier 1 only)
        if remember_choice and can_remember and folder_for_approval:
            approvals.remember(tool_name, tier, folder_for_approval)

        return await self._run_and_log(tool_def, validated_args, decision="approved", source=source)

    async def _run_and_log(
        self,
        tool_def: ToolDefinition,
        args: Dict[str, Any],
        decision: DecisionType,
        source: str
    ) -> Dict[str, Any]:
        try:
            if asyncio.iscoroutinefunction(tool_def.handler_fn):
                result = await tool_def.handler_fn(**args)
            else:
                result = tool_def.handler_fn(**args)

            action_log.log_action(
                tool=tool_def.name,
                tier=tool_def.tier,
                args=args,
                decision=decision,
                result_status="SUCCESS",
                source=source
            )
            return {"status": "success", "result": result}
        except Exception as e:
            action_log.log_action(
                tool=tool_def.name,
                tier=tool_def.tier,
                args=args,
                decision=decision,
                result_status="ERROR",
                source=source,
                error=str(e)
            )
            raise e

# Global Safety Engine instance
safety_engine = SafetyExecutionEngine()
