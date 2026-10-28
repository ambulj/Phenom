"""
Tests for Wave 1 Feature Implementations:
1. Windows Media & Playback Controller (Safety Layer Tier 1)
2. Safe Python Math/Formula Calculator (Tier 0)
3. Local PDF Split & Merge Engine (Tier 1)
4. Procedural Cinematic Sound Effects & Audio Ducking
5. Duplex Follow-Up Conversation Mode
"""

import os
import tempfile
import pytest
import pypdf
from services.backend.safety.engine import safety_engine
from services.backend.safety.registry import registry
from services.backend.tools.media_tools import control_media, duck_system_audio, unduck_system_audio
from services.backend.tools.utility_tools import safe_calculate, pdf_split_pages, pdf_merge_files
from services.backend.voice.sound_fx import sound_fx
from services.backend.voice.wake_word import wake_detector

@pytest.fixture(autouse=True)
def setup_confirmation_handler():
    async def auto_approve(req_id, tool, tier, prev, args, can_rem, f_path, timeout):
        return ("approved", False)
    safety_engine.set_confirmation_handler(auto_approve)
    yield
    safety_engine.set_confirmation_handler(None)

@pytest.mark.asyncio
async def test_media_control_registered_and_executable():
    # Verify tool is registered in Safety Registry as Tier 1
    tool_def = registry.get("control_media")
    assert tool_def is not None
    assert tool_def.tier == 1

    # Execute valid media actions
    res = await safety_engine.execute_tool("control_media", {"action": "play_pause"})
    assert res["status"] == "success"
    assert res["result"]["action"] == "play_pause"

    res_mute = await safety_engine.execute_tool("control_media", {"action": "mute"})
    assert res_mute["status"] == "success"

@pytest.mark.asyncio
async def test_audio_ducking_execution():
    # Verify duck and unduck routines execute cleanly without exceptions
    duck_system_audio()
    unduck_system_audio()

@pytest.mark.asyncio
async def test_safe_calculate_tool():
    # Verify math formulas evaluate accurately
    res1 = await safety_engine.execute_tool("safe_calculate", {"expression": "sqrt(144) + 12 * 3"})
    assert res1["status"] == "success"
    assert res1["result"]["result"] == 48.0

    res2 = await safety_engine.execute_tool("safe_calculate", {"expression": "2 ** 8 + round(pi, 2)"})
    assert res2["status"] == "success"
    assert res2["result"]["result"] == 256 + 3.14

    # Verify security: arbitrary code execution, os/sys access, and __import__ are blocked!
    res_insecure = await safety_engine.execute_tool("safe_calculate", {"expression": "__import__('os').system('dir')"})
    assert res_insecure["result"]["status"] == "error"
    assert "Disallowed" in res_insecure["result"]["message"]

@pytest.mark.asyncio
async def test_pdf_split_and_merge():
    # Create a temporary 3-page test PDF
    with tempfile.TemporaryDirectory() as tmpdir:
        pdf_path = os.path.join(tmpdir, "test_doc.pdf")
        writer = pypdf.PdfWriter()
        for i in range(3):
            writer.add_blank_page(width=200, height=200)
        with open(pdf_path, "wb") as f:
            writer.write(f)

        # 1. Test Split
        split_out = os.path.join(tmpdir, "split_out.pdf")
        res_split = await safety_engine.execute_tool("pdf_split_pages", {
            "pdf_path": pdf_path,
            "start_page": 1,
            "end_page": 2,
            "output_path": split_out
        })
        assert res_split["status"] == "success"
        assert os.path.exists(split_out)
        reader_split = pypdf.PdfReader(split_out)
        assert len(reader_split.pages) == 2

        # 2. Test Merge
        merge_out = os.path.join(tmpdir, "merged_out.pdf")
        res_merge = await safety_engine.execute_tool("pdf_merge_files", {
            "pdf_paths": [split_out, split_out],
            "output_path": merge_out
        })
        assert res_merge["status"] == "success"
        assert os.path.exists(merge_out)
        reader_merged = pypdf.PdfReader(merge_out)
        assert len(reader_merged.pages) == 4

def test_sound_fx_synthesis():
    # Verify all audio chimes synthesize without errors
    sound_fx.play_wake_chime()
    sound_fx.play_done_chime()
    sound_fx.play_error_chime()

def test_duplex_followup_window_state():
    wake_detector.enter_duplex_followup_window(timeout_seconds=2.0)
    assert wake_detector._duplex_active is True
    assert wake_detector._duplex_expiry_time > 0
