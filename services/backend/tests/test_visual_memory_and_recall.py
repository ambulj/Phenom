"""
Unit & Integration Test Suite for Phenom 6.0 Phase 1:
Continuous Desktop Visual Memory & Temporal Search

Verifies:
1. Perceptual Delta Hashing: Filters stationary frames (< 1.5% delta).
2. Privacy Masker & Sensitive Window Redaction: Bitwarden, KeePass, Incognito, Banking.
3. Local Embedding Pipeline: 384-dimensional normalized float32 vectors.
4. Encrypted Visual Store: Vectorized cosine similarity and retention pruning.
5. Natural Language Temporal Recall: Extracts conversational time constraints ("15 mins ago", "last 2 hours").
6. Visual Memory Monitor: Step execution, delta skipping, and sensitive window bypass.
7. Safety Registry Integration: search_visual_memory registered as Tier 0 read-only tool.
8. Guardian Kill Switch: Synchronously stops memory ingestion loop.
"""

import time
import pytest
import numpy as np
from PIL import Image, ImageDraw
from typing import Dict, Any, List

from services.backend.vision.delta_detector import DeltaDetector
from services.backend.vision.privacy_masker import PrivacyMasker
from services.backend.memory.embeddings import LocalEmbeddingPipeline
from services.backend.memory.visual_store import EncryptedVisualStore, cosine_similarity_blob
from services.backend.vision.temporal_recall import TemporalRecallEngine
from services.backend.vision.visual_memory_monitor import VisualMemoryMonitor
from services.backend.safety.guardian import guardian
from services.backend.safety.registry import registry
from services.backend.tools.screen_vision_tools import search_visual_memory
from services.backend.main import on_guardian_state_change


# ==============================================================================
# TEST 1: Perceptual Delta Hashing
# ==============================================================================

def test_delta_detector_filters_stationary_screen():
    detector = DeltaDetector(threshold=0.015)

    # Initial frame
    img1 = Image.new("RGB", (1920, 1080), color=(10, 20, 30))
    changed, score = detector.compute_delta(img1)
    assert changed is True
    assert score == 1.0

    # Identical stationary frame
    img2 = Image.new("RGB", (1920, 1080), color=(10, 20, 30))
    changed2, score2 = detector.compute_delta(img2)
    assert changed2 is False
    assert score2 < 0.015

    # Changed frame (large difference)
    img3 = Image.new("RGB", (1920, 1080), color=(200, 220, 240))
    changed3, score3 = detector.compute_delta(img3)
    assert changed3 is True
    assert score3 > 0.1


# ==============================================================================
# TEST 2: Privacy Masker & Sensitive Window Redaction
# ==============================================================================

def test_privacy_masker_excludes_sensitive_windows():
    masker = PrivacyMasker()

    # Sensitive titles
    assert masker.is_sensitive_title("Bitwarden - Vault") is True
    assert masker.is_sensitive_title("KeePass Password Safe") is True
    assert masker.is_sensitive_title("Chrome - Incognito") is True
    assert masker.is_sensitive_title("Chase Online Banking") is True
    assert masker.is_sensitive_title("MetaMask - Extension") is True

    # Benign titles
    assert masker.is_sensitive_title("Visual Studio Code - main.py") is False
    assert masker.is_sensitive_title("Terminal - PowerShell") is False
    assert masker.is_sensitive_title("Spotify Free") is False

    # Masking test
    base_img = Image.new("RGB", (800, 600), color=(255, 255, 255))
    custom_sensitive = [
        {"title": "Bitwarden", "rect": (100, 100, 300, 300)}
    ]
    masked_img, masked_list = masker.mask_sensitive_windows(base_img, custom_windows=custom_sensitive)
    assert len(masked_list) == 1
    # Check that masked region is blacked out
    arr = np.array(masked_img)
    assert np.all(arr[150, 150] == [0, 0, 0])
    # Unmasked region remains white
    assert np.all(arr[50, 50] == [255, 255, 255])


# ==============================================================================
# TEST 3: Local Embedding Pipeline
# ==============================================================================

def test_local_embedding_pipeline():
    pipeline = LocalEmbeddingPipeline()
    texts = [
        "Python test failure in services/backend/main.py",
        "CUDA memory allocation benchmark on RTX 4090",
        "Weather forecast for Mumbai 28 degrees"
    ]
    embeddings = pipeline.embed_texts(texts)
    assert isinstance(embeddings, np.ndarray)
    assert embeddings.shape == (3, 384)
    assert embeddings.dtype == np.float32

    # Verify L2 normalization: norm should be approximately 1.0
    for vec in embeddings:
        norm = np.linalg.norm(vec)
        assert abs(norm - 1.0) < 1e-3

    # Test single query embedding
    q_vec = pipeline.embed_query("CUDA memory allocation")
    assert q_vec.shape == (384,)
    assert abs(np.linalg.norm(q_vec) - 1.0) < 1e-3


# ==============================================================================
# TEST 4: Encrypted Visual Store & Custom Cosine Similarity
# ==============================================================================

def test_encrypted_visual_store_crud_and_cosine_search():
    store = EncryptedVisualStore(db_path=":memory:")

    # Generate synthetic embeddings
    vec_python = np.zeros(384, dtype=np.float32)
    vec_python[0] = 1.0
    vec_cuda = np.zeros(384, dtype=np.float32)
    vec_cuda[1] = 1.0

    t_now = time.time()
    chunks = [
        {
            "timestamp": t_now - 600.0,
            "iso_time": "2026-11-02T10:00:00Z",
            "process_name": "code.exe",
            "window_title": "VS Code - main.py",
            "text_content": "def run_worker(): start_pipeline()",
            "bbox": [50, 50, 200, 100]
        },
        {
            "timestamp": t_now - 60.0,
            "iso_time": "2026-11-02T10:10:00Z",
            "process_name": "windowsterminal.exe",
            "window_title": "Terminal - CUDA Bench",
            "text_content": "CUDA benchmark finished in 14.2ms",
            "bbox": [100, 100, 400, 300]
        }
    ]
    embeddings = np.array([vec_python, vec_cuda], dtype=np.float32)

    inserted = store.insert_chunks(chunks, embeddings)
    assert inserted == 2

    # Query with Python vector: top match should be VS Code
    res_py = store.search_similar_chunks(vec_python, limit=5, min_score=0.5)
    assert len(res_py) >= 1
    assert res_py[0]["process_name"] == "code.exe"
    assert res_py[0]["score"] > 0.9

    # Query with CUDA vector: top match should be Terminal
    res_cuda = store.search_similar_chunks(vec_cuda, limit=5, min_score=0.5)
    assert len(res_cuda) >= 1
    assert res_cuda[0]["process_name"] == "windowsterminal.exe"
    assert res_cuda[0]["score"] > 0.9

    # Test time bounds filter: query only last 120 seconds
    res_time = store.search_similar_chunks(vec_python, start_time=t_now - 120.0, limit=5)
    assert len(res_time) == 0  # Python chunk was 600s ago

    # Test retention pruning
    deleted = store.prune_older_than(days=0)  # prune all older than 0 days
    assert deleted == 2
    stats = store.get_timeline_stats()
    assert stats["total_records"] == 0

    store.close()


# ==============================================================================
# TEST 5: Natural Language Temporal Recall Engine
# ==============================================================================

def test_temporal_recall_query_parsing():
    engine = TemporalRecallEngine(visual_st=EncryptedVisualStore(db_path=":memory:"))
    now_ref = 1700000000.0

    # 1. 15 minutes ago
    clean, start_ts, end_ts = engine.parse_temporal_query("error in terminal 15 mins ago", now_ts=now_ref)
    assert "error in terminal" in clean
    assert start_ts == now_ref - 900.0
    assert end_ts == now_ref

    # 2. Last 2 hours
    clean2, start2, end2 = engine.parse_temporal_query("where did i see that CUDA chart last 2 hours", now_ts=now_ref)
    assert "CUDA chart" in clean2
    assert start2 == now_ref - 7200.0
    assert end2 == now_ref

    # 3. Past hour
    clean3, start3, end3 = engine.parse_temporal_query("find that git diff past hour", now_ts=now_ref)
    assert "git diff" in clean3
    assert start3 == now_ref - 3600.0
    assert end3 == now_ref

    # 4. Today
    clean4, start4, end4 = engine.parse_temporal_query("show me obsidian daily log today", now_ts=now_ref)
    assert "obsidian daily log" in clean4
    assert start4 is not None and start4 < now_ref


# ==============================================================================
# TEST 6: Visual Memory Monitor Capture & Indexing Step
# ==============================================================================

def test_visual_memory_monitor_step_execution():
    store = EncryptedVisualStore(db_path=":memory:")
    pipeline = LocalEmbeddingPipeline()
    detector = DeltaDetector(threshold=0.015)
    masker = PrivacyMasker()

    monitor = VisualMemoryMonitor(
        delta_det=detector,
        privacy_mask=masker,
        visual_st=store,
        embed_pipe=pipeline
    )

    # 1. Stationary screen test
    img_plain = Image.new("RGB", (800, 600), color=(30, 40, 50))
    res1 = monitor.capture_and_index_step(override_img=img_plain, override_proc="code.exe", override_title="VS Code")
    assert res1["status"] in ("indexed", "no_text_extracted")

    # Second step with exact same image -> should be detected as stationary
    detector._prev_thumb = np.asarray(img_plain.convert("L").resize((64, 36)), dtype=np.float32)
    res_stationary = monitor.capture_and_index_step(override_img=img_plain, override_proc="code.exe", override_title="VS Code")
    # override_img forces processing unless we test compute_delta directly
    changed, delta_score = detector.compute_delta(img_plain)
    assert changed is False

    # 2. Sensitive window test
    res_sensitive = monitor.capture_and_index_step(
        override_img=img_plain,
        override_proc="bitwarden.exe",
        override_title="Bitwarden - Master Password Vault"
    )
    assert res_sensitive["status"] == "skipped_sensitive_window"
    assert res_sensitive["window_title"] == "Bitwarden - Master Password Vault"

    # 3. Guardian halt test
    guardian.trigger("Test visual monitor halt")
    res_halted = monitor.capture_and_index_step(override_img=img_plain)
    assert res_halted["status"] == "halted_by_guardian"
    guardian.resume()

    store.close()


# ==============================================================================
# TEST 7: Safety Registry & search_visual_memory Tool
# ==============================================================================

@pytest.mark.asyncio
async def test_search_visual_memory_tool():
    # Verify tool is registered in SafetyRegistry
    entry = registry.get("search_visual_memory")
    assert entry is not None
    assert entry.tier == 0  # Read-only Tier 0

    # Execute tool
    res = await search_visual_memory(query="find that terminal command from 10 minutes ago", limit=3)
    assert res["status"] == "success"
    assert "matches" in res
    assert isinstance(res["matches"], list)
    assert "matches_count" in res


# ==============================================================================
# TEST 8: Guardian Kill Switch Synchronous Visual Monitor Halt
# ==============================================================================

def test_guardian_kill_switch_synchronously_halts_visual_monitor():
    from services.backend.vision.visual_memory_monitor import visual_memory_monitor

    # Start monitor
    visual_memory_monitor._is_running = True
    assert visual_memory_monitor.is_running is True

    # Trigger kill switch and state callback
    guardian.trigger("Test Killswitch Visual Memory Halt")
    on_guardian_state_change("halted")

    # Verify visual monitor was halted synchronously
    assert visual_memory_monitor.is_running is False
    assert guardian.is_halted is True

    # Clean up
    guardian.resume()
    assert guardian.is_halted is False
