"""
Unit and Integration Tests for Phenom 6-8 GB VRAM & 50 GB Storage Governance (Task 7d)
Verifies:
1. Process RAM memory footprint < 1000 MB idle.
2. VRAM allocation ~4.85 GB steady-state, offloaded to < 100 MB during gaming mode.
3. 15-minute idle timeout auto-unload policy.
4. Storage manager directory quotas and audit metrics.
5. Strict FIFO eviction down to target watermark without corrupting vector index or SQLCipher DB.
6. Model router cloud fallback adaptation when gaming mode is active.
"""

import os
import time
import pytest
import asyncio
from services.backend.resource.vram_manager import VRAMManager
from services.backend.resource.storage_manager import StorageManager
from services.backend.router.router import ModelRouter

def test_idle_ram_under_1gb():
    vram_mgr = VRAMManager()
    profile = vram_mgr.get_memory_profile()
    assert profile["idle_ram_under_1gb"] is True
    assert profile["process_ram_mb"] < 1000.0

@pytest.mark.asyncio
async def test_vram_allocation_steady_state_and_gaming_offload():
    vram_mgr = VRAMManager()
    
    # Warmup model
    res = await vram_mgr.warmup_model()
    assert res["status"] == "loaded"
    assert vram_mgr.is_loaded_in_vram is True
    assert vram_mgr.vram_allocated_mb == 4850.0

    # Simulate gaming process detection
    vram_mgr.gaming_mode_active = True
    vram_mgr.detected_game_name = "cyberpunk2077.exe"
    unload_res = await vram_mgr.unload_model(reason="gaming_process_detected")

    assert unload_res["status"] == "unloaded"
    assert vram_mgr.is_loaded_in_vram is False
    assert vram_mgr.vram_allocated_mb < 100.0
    assert unload_res["vram_allocated_mb"] == 50.0

    # Ensure warmup is blocked while gaming mode is active
    blocked = await vram_mgr.warmup_model()
    assert blocked["status"] == "blocked"
    assert blocked["reason"] == "gaming_mode_active"

@pytest.mark.asyncio
async def test_vram_idle_timeout_eviction():
    vram_mgr = VRAMManager(idle_timeout_seconds=0.05)
    await vram_mgr.warmup_model()
    assert vram_mgr.is_loaded_in_vram is True

    # Sleep past idle timeout
    await asyncio.sleep(0.08)
    evicted = await vram_mgr.check_idle_timeout()
    assert evicted is True
    assert vram_mgr.is_loaded_in_vram is False
    assert vram_mgr.vram_allocated_mb < 100.0

def test_storage_manager_audit_and_partitions(tmp_path):
    mgr = StorageManager(data_root=str(tmp_path / "phenom_data"), total_cap_bytes=1000000, prune_watermark_bytes=800000)
    audit = mgr.audit_storage()

    assert audit["total_used_bytes"] == 0
    assert audit["used_percentage"] == 0.0
    assert audit["needs_pruning"] is False
    assert os.path.exists(mgr.snapshots_dir)
    assert os.path.exists(mgr.voice_store_dir)
    assert os.path.exists(mgr.vector_db_dir)

def test_storage_fifo_pruning_and_protection_invariants(tmp_path):
    root = str(tmp_path / "phenom_data")
    mgr = StorageManager(data_root=root, total_cap_bytes=50000, prune_watermark_bytes=40000)

    # Protected database and vector index
    with open(mgr.db_path, "wb") as f:
        f.write(b"SQLCIPHER_DB_CONTENT" * 50) # 1000 bytes
    vector_file = os.path.join(mgr.vector_db_dir, "vector_store.bin")
    with open(vector_file, "wb") as f:
        f.write(b"VECTOR_INDEX_CONTENT" * 100) # 2000 bytes

    # Populate 5 snapshot files with ascending timestamps
    base_t = time.time() - 10000
    for i in range(5):
        snap_path = os.path.join(mgr.snapshots_dir, f"snap_{i}.bin")
        with open(snap_path, "wb") as f:
            f.write(b"\xff" * 10000) # 10,000 bytes each -> 50,000 bytes total
        mtime = base_t + (i * 100)
        os.utime(snap_path, (mtime, mtime))

    pre_audit = mgr.audit_storage()
    # Total = 1000 + 2000 + 50000 = 53000 bytes (> 40000 watermark)
    assert pre_audit["needs_pruning"] is True

    # Execute pruning to 35000 bytes
    prune_res = mgr.prune_if_needed(target_bytes=35000)
    assert prune_res["status"] == "pruned"
    assert prune_res["files_evicted"] >= 2
    assert prune_res["post_prune_used_bytes"] <= 40000

    # Protected assets invariant
    assert os.path.exists(mgr.db_path)
    assert os.path.exists(vector_file)
    assert prune_res["vector_index_intact"] is True
    assert prune_res["db_intact"] is True

    # Oldest snapshot (snap_0.bin) must be evicted, newest (snap_4.bin) retained
    rem_snaps = os.listdir(mgr.snapshots_dir)
    assert "snap_0.bin" not in rem_snaps
    assert "snap_4.bin" in rem_snaps

@pytest.mark.asyncio
async def test_router_cloud_fallback_during_gaming_mode():
    from services.backend.resource.vram_manager import vram_manager
    router = ModelRouter()

    # Configure mock cloud approval handler
    approval_called = False
    async def mock_handler(req_id, text, tokens):
        nonlocal approval_called
        approval_called = True
        return True

    router.set_cloud_approval_handler(mock_handler)

    # Set gaming mode active
    vram_manager.gaming_mode_active = True
    vram_manager.detected_game_name = "unrealengine.exe"

    try:
        model, backend, meta = await router.route_request(
            "Tell me a creative story about space exploration",
            manual_privacy_override="shareable"
        )
        assert backend == "cloud"
        assert approval_called is True
        assert "Gaming mode active" in meta["routing_reason"]
    finally:
        vram_manager.gaming_mode_active = False
        vram_manager.detected_game_name = None
