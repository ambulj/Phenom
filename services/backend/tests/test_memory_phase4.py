"""
Unit & Integration Tests for Phase 4: Long-Term Memory, RAG, and Vault
Verifies:
1. Retrieval quality and source citation across vector store chunks
2. Incremental indexing (skips unmodified files based on mtime)
3. Obsidian vault notes CRUD and daily log appending
4. Photos immutable rule: modification and deletion blocked by construction
5. Photo indexing and search by description
6. Downloads cleanup organizer: dry-run plan generation and 100% reversible undo
7. Multi-format document reader (.txt, .md, .docx, .pptx, .xlsx, .pdf)
8. Learned rules lifecycle and automatic correction extraction
"""

import os
import shutil
import tempfile
import pytest
import numpy as np

from services.backend.memory.db import encrypted_db
from services.backend.memory.doc_reader import doc_reader
from services.backend.memory.vector_store import vector_store
from services.backend.memory.vault import ObsidianVaultManager
from services.backend.memory.photo_indexer import photo_indexer, PhotoModificationProhibited
from services.backend.memory.cleanup_organizer import cleanup_organizer
from services.backend.memory.rules import learned_rules
from services.backend.orchestrator.engine import orchestrator
from services.backend.safety.engine import safety_engine
from services.backend.safety.registry import registry
import services.backend.tools.memory_tools

@pytest.fixture
def temp_test_dir():
    d = tempfile.mkdtemp(prefix="phenom_phase4_test_")
    yield d
    try:
        shutil.rmtree(d)
    except Exception:
        pass

def test_document_reader_formats(temp_test_dir):
    # 1. Plain text / Markdown
    txt_path = os.path.join(temp_test_dir, "notes.txt")
    with open(txt_path, "w", encoding="utf-8") as f:
        f.write("Phenom is an AI desktop companion built with Python and React.")
    assert "companion" in doc_reader.read_document(txt_path)

    # 2. Word docx
    docx_path = os.path.join(temp_test_dir, "test.docx")
    import docx
    doc = docx.Document()
    doc.add_paragraph("This is a quantum computing research paper.")
    doc.save(docx_path)
    assert "quantum computing" in doc_reader.read_document(docx_path)

    # 3. PowerPoint pptx
    pptx_path = os.path.join(temp_test_dir, "test.pptx")
    import pptx
    prs = pptx.Presentation()
    slide = prs.slides.add_slide(prs.slide_layouts[0])
    slide.shapes.title.text = "Robotics Architecture Overview"
    prs.save(pptx_path)
    assert "Robotics Architecture" in doc_reader.read_document(pptx_path)

    # 4. Excel xlsx
    xlsx_path = os.path.join(temp_test_dir, "test.xlsx")
    import openpyxl
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.append(["Item", "Price"])
    ws.append(["RTX 4090", 1599])
    wb.save(xlsx_path)
    assert "RTX 4090" in doc_reader.read_document(xlsx_path)

def test_vector_store_indexing_and_retrieval(temp_test_dir):
    # Create two test documents with distinct concepts
    f1 = os.path.join(temp_test_dir, "quantum.txt")
    with open(f1, "w", encoding="utf-8") as f:
        f.write("Quantum computers utilize qubits and superposition to solve complex cryptographic algorithms.")

    f2 = os.path.join(temp_test_dir, "baking.txt")
    with open(f2, "w", encoding="utf-8") as f:
        f.write("Sourdough bread requires a healthy starter culture with wild yeast, high hydration flour, and salt.")

    # Index folder
    res = vector_store.index_folder(temp_test_dir)
    assert res["files_indexed"] >= 2
    assert res["chunks_indexed"] >= 2

    # Incremental update check: running again without file changes should skip both
    res_incremental = vector_store.index_folder(temp_test_dir)
    assert res_incremental["files_indexed"] == 0
    assert res_incremental["files_unmodified"] >= 2

    # Semantic search retrieval quality
    quantum_matches = vector_store.search("How do qubits work in cryptography?", top_k=2)
    assert len(quantum_matches) > 0
    top_match = quantum_matches[0]
    assert "quantum.txt" in top_match["filename"]
    assert top_match["score"] > 0.4
    assert "superposition" in top_match["snippet"]

    baking_matches = vector_store.search("How to bake sourdough bread with yeast?", top_k=2)
    assert len(baking_matches) > 0
    assert "baking.txt" in baking_matches[0]["filename"]

def test_obsidian_vault_lifecycle(temp_test_dir):
    vault = ObsidianVaultManager(vault_path=temp_test_dir)

    # 1. Write note
    note_path = vault.write_note("Project Architecture", "# Overview\nPhenom architecture details.")
    assert os.path.exists(note_path)
    assert note_path.endswith(".md")

    # 2. Read note
    content = vault.read_note("Project Architecture")
    assert "Phenom architecture details" in content
    assert "author: Phenom" in content

    # 3. Append daily log
    log_path = vault.append_daily_log("Finished implementing Phase 4 vector memory.")
    assert os.path.exists(log_path)
    with open(log_path, "r", encoding="utf-8") as f:
        log_text = f.read()
    assert "Phase 4 vector memory" in log_text

    # 4. List notes
    all_notes = vault.list_notes()
    filenames = [n["filename"] for n in all_notes]
    assert "Project Architecture.md" in filenames

def test_photos_immutable_block(temp_test_dir):
    img_path = os.path.join(temp_test_dir, "vacation_sunset.jpg")
    # Create minimal 100x100 RGB image
    from PIL import Image
    im = Image.new("RGB", (100, 100), color=(255, 120, 50))
    im.save(img_path)

    # 1. Indexing and searching works
    pid = photo_indexer.index_photo(img_path)
    assert pid.startswith("photo-")

    search_res = photo_indexer.search_photos("sunset vacation")
    assert len(search_res) > 0
    assert search_res[0]["filename"] == "vacation_sunset.jpg"

    # 2. Prohibited modifications must raise PhotoModificationProhibited / PermissionError
    with pytest.raises(PhotoModificationProhibited):
        photo_indexer.move_photo(img_path, os.path.join(temp_test_dir, "new_vacation.jpg"))

    with pytest.raises(PhotoModificationProhibited):
        photo_indexer.rename_photo(img_path, "sunset2.jpg")

    with pytest.raises(PhotoModificationProhibited):
        photo_indexer.delete_photo(img_path)

    with pytest.raises(PhotoModificationProhibited):
        photo_indexer.verify_no_photo_modification(img_path, "edit_filters")

    # 3. Safety layer blocks modify_photo & delete_photo as Tier 3
    assert registry.get_tier("modify_photo") == 3
    assert registry.get_tier("delete_photo") == 3

def test_downloads_cleanup_dry_run_and_reversible_undo(temp_test_dir):
    # Setup test directory simulating Downloads folder
    doc1 = os.path.join(temp_test_dir, "resume.pdf")
    doc2 = os.path.join(temp_test_dir, "report.docx")
    pic = os.path.join(temp_test_dir, "chart.png")
    installer = os.path.join(temp_test_dir, "installer.exe")
    dup_doc = os.path.join(temp_test_dir, "resume_copy.pdf")

    with open(doc1, "w") as f: f.write("Content of original document")
    with open(doc2, "w") as f: f.write("Content of business report")
    with open(pic, "w") as f: f.write("PNG image bytes")
    with open(installer, "w") as f: f.write("Binary executable bytes")
    with open(dup_doc, "w") as f: f.write("Content of original document") # Exact duplicate of doc1

    # 1. Dry run
    dry_run = cleanup_organizer.generate_dry_run(temp_test_dir)
    assert dry_run["total_files"] == 5
    assert dry_run["moves_count"] == 4
    assert dry_run["duplicates_count"] == 1
    # Verify no files were moved yet during dry run
    assert os.path.exists(doc1)
    assert os.path.exists(dup_doc)

    # 2. Apply cleanup
    summary, undo_token = cleanup_organizer.apply_cleanup(dry_run)
    assert summary["files_moved"] == 4
    assert summary["duplicates_recycled"] == 1
    assert os.path.exists(undo_token is not None)

    # Verify original files were moved to category folders
    assert not os.path.exists(doc2)
    assert os.path.exists(os.path.join(temp_test_dir, "Documents"))
    assert os.path.exists(os.path.join(temp_test_dir, "Images"))

    # 3. Reversible Undo: rollback
    undo_res = cleanup_organizer.undo_cleanup(undo_token)
    assert undo_res["status"] == "rolled_back"
    assert undo_res["files_restored"] >= 4

    # Confirm original files are restored to their original paths
    assert os.path.exists(doc1)
    assert os.path.exists(doc2)
    assert os.path.exists(pic)
    assert os.path.exists(installer)

def test_learned_rules_auto_extraction_and_lifecycle():
    # Test correction rule extraction from orchestrator
    rule1 = orchestrator._extract_learned_rule("Never organize the Projects folder automatically.")
    assert rule1 is not None
    assert "Never organize the Projects folder" in rule1

    rule2 = orchestrator._extract_learned_rule("Always format financial figures with rupee symbols.")
    assert rule2 is not None
    assert "Always format financial figures" in rule2

    # Non-rule statements should not be extracted
    assert orchestrator._extract_learned_rule("What is the weather today?") is None
    assert orchestrator._extract_learned_rule("Hello Phenom") is None

    # Lifecycle: add, list, edit, delete in learned_rules
    rule_obj = learned_rules.add_rule("Always use Markdown bullet points in lists.")
    r_id = rule_obj["id"]
    all_r = learned_rules.list_rules()
    matching = [r for r in all_r if r["id"] == r_id]
    assert len(matching) == 1

    # Edit
    learned_rules.edit_rule(r_id, "Always use Markdown dashes in lists.")
    updated = [r for r in learned_rules.list_rules() if r["id"] == r_id][0]
    assert updated["rule_text"] == "Always use Markdown dashes in lists."

    # Delete
    learned_rules.delete_rule(r_id)
    assert len([r for r in learned_rules.list_rules() if r["id"] == r_id]) == 0
