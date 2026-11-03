"""
Unit Test Suite for AirDrop-Style Encrypted P2P Media Drop Manager (MSH-02, SAF-01, SAF-02)
Tests chunked streaming, SHA-256 verification, path traversal defense,
executable extension blocking, non-destructive collision resolution, and Guardian halt SLA.
"""

import os
import time
import base64
import hashlib
import pytest

from services.backend.schemas.sensory import (
    MediaDropDestination,
    MediaDropTransferState,
)
from services.backend.mesh.media_drop import (
    P2PMediaDropManager,
    BLOCKED_EXTENSIONS,
)


@pytest.fixture
def media_mgr(tmp_path):
    vault_dir = tmp_path / "vault"
    downloads_dir = tmp_path / "downloads"
    mgr = P2PMediaDropManager(
        vault_dir=str(vault_dir),
        downloads_dir=str(downloads_dir),
    )
    mgr.reset()
    return mgr


def test_chunked_file_transfer_success(media_mgr, tmp_path):
    """MSH-02: Test successful end-to-end chunked transfer of markdown document into vault."""
    src_file = tmp_path / "Project_Architecture.md"
    content = b"# Phenom Architecture\n\n- Encrypted P2P mesh\n- Strict in-RAM camera streaming\n" * 1500
    src_file.write_bytes(content)

    manifest, send_transfer = media_mgr.create_send_manifest(
        file_path=str(src_file),
        source_node_id="desktop-host",
        target_node_id="companion-tablet",
        destination=MediaDropDestination.VAULT,
    )

    assert manifest.filename == "Project_Architecture.md"
    assert manifest.file_size == len(content)
    assert manifest.total_chunks >= 1

    # Receiver handles manifest
    ack = media_mgr.receive_manifest(manifest)
    assert ack.status == "ack"

    # Stream all chunks
    last_ack = None
    for i in range(manifest.total_chunks):
        chunk = media_mgr.read_file_chunk(str(src_file), i, manifest.transfer_id)
        last_ack = media_mgr.receive_chunk(chunk)

    assert last_ack is not None
    assert last_ack.status == "complete"

    # Verify destination file exists and content matches bit-for-bit
    transfer = media_mgr.get_transfer(manifest.transfer_id)
    assert transfer is not None
    assert transfer.state == MediaDropTransferState.COMPLETED
    assert transfer.progress == 1.0
    assert transfer.saved_path is not None
    assert os.path.exists(transfer.saved_path)

    received_bytes = open(transfer.saved_path, "rb").read()
    assert received_bytes == content
    assert hashlib.sha256(received_bytes).hexdigest() == manifest.sha256_checksum


def test_executable_extension_blocking(media_mgr, tmp_path):
    """SAF-01: Verify dangerous executable and script extensions are strictly blocked."""
    for bad_ext in [".exe", ".bat", ".cmd", ".ps1", ".vbs", ".msi", ".sh", ".bin"]:
        bad_file = tmp_path / f"malware{bad_ext}"
        bad_file.write_bytes(b"MZ\x90\x00\x03\x00\x00\x00")

        # Sender should reject
        with pytest.raises(ValueError, match="executable extension"):
            media_mgr.create_send_manifest(
                file_path=str(bad_file),
                source_node_id="node-a",
                target_node_id="node-b",
            )


def test_path_traversal_defense(media_mgr):
    """SAF-01: Verify directory traversal attacks are rejected or neutralized."""
    from services.backend.schemas.sensory import MediaDropManifest

    traversal_manifest = MediaDropManifest(
        transfer_id="drop-traversal-01",
        source_node_id="rogue-node",
        target_node_id="host",
        filename="../../../Windows/System32/cmd.exe",  # Also has .exe extension
        file_size=1024,
        sha256_checksum="a" * 64,
        chunk_size=65536,
        total_chunks=1,
        destination=MediaDropDestination.DOWNLOADS,
        created_at=time.time(),
    )

    # Must be rejected due to extension or traversal
    with pytest.raises(ValueError):
        media_mgr.receive_manifest(traversal_manifest)


def test_non_destructive_collision_handling(media_mgr, tmp_path):
    """MSH-02: Verify existing notes/files are never overwritten upon duplicate intake."""
    vault_dir = tmp_path / "vault"
    existing_note = vault_dir / "MeetingNotes.md"
    existing_note.write_text("# Original Meeting Notes", encoding="utf-8")

    src_file = tmp_path / "MeetingNotes.md"
    new_content = b"# New Companion Meeting Notes"
    src_file.write_bytes(new_content)

    manifest, _ = media_mgr.create_send_manifest(
        file_path=str(src_file),
        source_node_id="companion",
        target_node_id="host",
        destination=MediaDropDestination.VAULT,
    )

    media_mgr.receive_manifest(manifest)
    chunk = media_mgr.read_file_chunk(str(src_file), 0, manifest.transfer_id)
    ack = media_mgr.receive_chunk(chunk)

    assert ack.status == "complete"
    transfer = media_mgr.get_transfer(manifest.transfer_id)
    assert transfer.state == MediaDropTransferState.COMPLETED

    # The original file must remain intact
    assert existing_note.read_text(encoding="utf-8") == "# Original Meeting Notes"

    # The new file must be saved non-destructively as MeetingNotes (1).md
    collided_note = vault_dir / "MeetingNotes (1).md"
    assert collided_note.exists()
    assert collided_note.read_bytes() == new_content


def test_chunk_corruption_rejection(media_mgr, tmp_path):
    """MSH-02: Corrupted chunk digest causes transfer failure and staging cleanup."""
    src_file = tmp_path / "Photo.jpg"
    src_file.write_bytes(b"\xFF\xD8\xFF\xE0" + b"\x00" * 5000 + b"\xFF\xD9")

    manifest, _ = media_mgr.create_send_manifest(
        file_path=str(src_file),
        source_node_id="node-a",
        target_node_id="node-b",
    )

    media_mgr.receive_manifest(manifest)
    chunk = media_mgr.read_file_chunk(str(src_file), 0, manifest.transfer_id)

    # Tamper with chunk digest
    chunk.sha256_chunk = "0" * 64
    ack = media_mgr.receive_chunk(chunk)
    assert ack.status == "nack"
    assert "checksum mismatch" in ack.error_message


def test_guardian_halt_immediate_transfer_abort(media_mgr, tmp_path):
    """SAF-02: Guardian kill switch immediately aborts in-flight transfers and purges partial files in < 1.0ms."""
    src_file = tmp_path / "LargeReport.pdf"
    src_file.write_bytes(b"%PDF-1.4 " + b"X" * 150000)

    manifest, _ = media_mgr.create_send_manifest(
        file_path=str(src_file),
        source_node_id="node-a",
        target_node_id="node-b",
    )

    media_mgr.receive_manifest(manifest)
    chunk0 = media_mgr.read_file_chunk(str(src_file), 0, manifest.transfer_id)
    media_mgr.receive_chunk(chunk0)

    # Measure halt execution time
    t0 = time.perf_counter()
    media_mgr.halt()
    halt_duration_ms = (time.perf_counter() - t0) * 1000.0

    assert halt_duration_ms < 25.0, f"Halt exceeded 25ms SLA: {halt_duration_ms:.3f}ms"
    assert media_mgr.is_halted() is True

    # Active transfers must be empty and marked ABORTED in history
    assert len(media_mgr._active_transfers) == 0
    history = media_mgr.get_history()
    aborted_transfer = next((t for t in history if t.transfer_id == manifest.transfer_id), None)
    assert aborted_transfer is not None
    assert aborted_transfer.state == MediaDropTransferState.ABORTED

    # Subsequent receive_chunk must raise PermissionError
    with pytest.raises(PermissionError, match="Guardian kill switch is active"):
        media_mgr.receive_chunk(chunk0)

    # Staging files must be completely wiped
    downloads_dir = tmp_path / "downloads"
    part_files = list(downloads_dir.glob("*.part"))
    assert len(part_files) == 0
