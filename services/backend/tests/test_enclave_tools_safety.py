"""
Tests for Biometric Enclave Tool Safety Governance (SAF-01, SAF-02).
Verifies ToolRegistry registration, preview outputs, and Guardian kill switch lockdown.
"""

import pytest
from services.backend.safety.guardian import guardian
from services.backend.safety.registry import registry
from services.backend.schemas.biometrics import (
    BiometricAuthMethod,
    WorkspacePartitionType,
)
from services.backend.security import biometric_enclave_manager
import services.backend.tools.enclave_tools as enc_tools


def test_enclave_tools_registered_in_registry():
    expected_tools = {
        "enclave_get_status": 0,
        "enclave_unlock_partition": 1,
        "enclave_lock_partition": 1,
        "enclave_lease_credential": 1,
        "enclave_revoke_lease": 1,
    }

    for tool_name, expected_tier in expected_tools.items():
        assert tool_name in registry._tools, f"Tool {tool_name} not registered in ToolRegistry"
        assert registry._tools[tool_name].tier == expected_tier, (
            f"Tool {tool_name} has tier {registry._tools[tool_name].tier}, expected {expected_tier}"
        )


def test_enclave_tier_0_queries_execute():
    res = enc_tools.enclave_get_status()
    assert res["status"] == "success"
    assert "enclave_state" in res
    assert res["enclave_state"]["hardware_tpm_present"] is True


def test_enclave_tier_1_controls_with_preview():
    # Verify previews
    unlock_tool = registry._tools["enclave_unlock_partition"]
    preview_u = unlock_tool.preview_fn({"partition_type": "PERSONAL", "auth_method": "WINDOWS_HELLO_PIN"})
    assert "Unlock encrypted workspace partition 'PERSONAL'" in preview_u

    lock_tool = registry._tools["enclave_lock_partition"]
    preview_l = lock_tool.preview_fn({"partition_type": "PROFESSIONAL"})
    assert "Lock workspace partition 'PROFESSIONAL'" in preview_l
    assert "zero-wipe master key" in preview_l

    lease_tool = registry._tools["enclave_lease_credential"]
    preview_lease = lease_tool.preview_fn({"target_service": "github_token", "ttl_seconds": 45})
    assert "Lease ephemeral credential for 'github_token'" in preview_lease
    assert "TTL: 45s" in preview_lease

    # Execute Tier 1 calls
    token_str = "pin-" + "hello-9999"
    unlock_res = enc_tools.enclave_unlock_partition(
        partition_type=WorkspacePartitionType.PERSONAL,
        auth_token=token_str,
        auth_method=BiometricAuthMethod.WINDOWS_HELLO_PIN,
    )
    assert unlock_res["status"] == "success"
    assert unlock_res["partition"]["status"] == "UNLOCKED"

    lease_res = enc_tools.enclave_lease_credential(target_service="test_svc", ttl_seconds=30)
    assert lease_res["status"] == "success"
    lease_id = lease_res["lease_id"]

    revoke_res = enc_tools.enclave_revoke_lease(lease_id=lease_id)
    assert revoke_res["status"] == "success"
    assert revoke_res["revoked"] is True

    lock_res = enc_tools.enclave_lock_partition(partition_type=WorkspacePartitionType.PERSONAL)
    assert lock_res["status"] == "success"
    assert lock_res["partition"]["status"] == "LOCKED"


def test_enclave_tools_fail_closed_under_guardian_halt():
    try:
        guardian.trigger("Enclave Safety Test Halt")

        with pytest.raises(PermissionError, match="Guardian kill switch is active"):
            enc_tools.enclave_unlock_partition(
                partition_type=WorkspacePartitionType.PERSONAL,
                auth_token="dummy-pin",
            )

        with pytest.raises(PermissionError, match="Guardian kill switch is active"):
            enc_tools.enclave_lease_credential(target_service="test_svc")

        with pytest.raises(PermissionError, match="Guardian kill switch is active"):
            enc_tools.enclave_revoke_lease(lease_id="fake-lease")
    finally:
        guardian.resume()
        biometric_enclave_manager.resume()
