"""
Dynamic Extensions Package Exports.
"""

from services.backend.extensions.ast_auditor import ASTSafetyAuditor
from services.backend.extensions.extension_manager import DynamicExtensionManager

# Global singleton instance
dynamic_extension_manager = DynamicExtensionManager()

__all__ = [
    "ASTSafetyAuditor",
    "DynamicExtensionManager",
    "dynamic_extension_manager",
]
