"""
Phenom Coding Agent Safety Module
Enforces workspace isolation, pre-execution snapshotting, typosquatting protection,
and process-tree lifecycle control under the Guardian kill switch.
"""

from services.backend.coding.workspace import WorkspaceManager, IsolatedWorkspace, workspace_manager
from services.backend.coding.typosquat_guard import TyposquatGuard, PackageSecurityReport, typosquat_guard
from services.backend.coding.runner import CodeRunner, ExecutionResult, code_runner

__all__ = [
    "WorkspaceManager",
    "IsolatedWorkspace",
    "workspace_manager",
    "TyposquatGuard",
    "PackageSecurityReport",
    "typosquat_guard",
    "CodeRunner",
    "ExecutionResult",
    "code_runner",
]
