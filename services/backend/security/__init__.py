"""
Security Enclave Package Exports.
"""

from services.backend.security.credential_leaser import EphemeralCredentialLeaser
from services.backend.security.biometric_enclave import BiometricEnclaveManager

# Global singleton instance
biometric_enclave_manager = BiometricEnclaveManager()

__all__ = [
    "EphemeralCredentialLeaser",
    "BiometricEnclaveManager",
    "biometric_enclave_manager",
]
