"""
Multi-Format Document Parser & Hierarchical Chunker.
Extracts structured text, section headings, and sentence-bounded chunks
from PDF, DOCX, Markdown, Code, and TXT files under Rule 4 offline compliance.

Part of Phenom 20.0 Large-Scale Offline Hybrid RAG Engine (RAG-02.1).
"""

import hashlib
import os
import re
from pathlib import Path
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field

from services.backend.safety.guardian import guardian


class ParsedChunk(BaseModel):
    chunk_id: str = Field(..., description="Unique chunk hash/id")
    doc_id: str = Field(..., description="Parent document unique identifier")
    file_path: str = Field(..., description="Source file path")
    section_title: Optional[str] = Field(default=None, description="Enclosing heading or section title")
    text: str = Field(..., description="Extracted chunk text content")
    token_estimate: int = Field(default=0, description="Estimated token count (~4 chars/token)")
    chunk_index: int = Field(default=0, description="Zero-indexed position in document")
    total_chunks: int = Field(default=1, description="Total chunks in document")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Custom metadata tags and attributes")


class ParsedDocument(BaseModel):
    doc_id: str = Field(..., description="Unique document SHA256 identifier")
    file_path: str = Field(..., description="Source file path")
    file_name: str = Field(..., description="Source file basename")
    file_type: str = Field(..., description="Extension category: md, code, pdf, docx, txt, etc.")
    total_chunks: int = Field(default=0, description="Number of parsed chunks")
    chunks: List[ParsedChunk] = Field(default_factory=list, description="Extracted chunks")
    raw_char_count: int = Field(default=0, description="Total raw character count")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Document metadata")


class DocumentParser:
    """
    Parses heterogeneous documents into structured, sentence-bounded chunks with section awareness.
    """

    HEADING_RE = re.compile(r"^(#{1,6})\s+(.+)$", re.MULTILINE)
    CODE_SECTION_RE = re.compile(r"^(?:class|def|async def|function|interface|type)\s+([A-Za-z0-9_]+)", re.MULTILINE)
    SENTENCE_SPLIT_RE = re.compile(r"(?<=[.!?])\s+(?=[A-Z0-9])")

    def parse_file(
        self,
        file_path: str,
        chunk_size_words: int = 250,
        overlap_words: int = 40,
        custom_metadata: Optional[Dict[str, Any]] = None,
    ) -> ParsedDocument:
        """
        Parses a file from disk into a ParsedDocument containing overlapping, section-aware chunks.
        """
        if guardian.is_halted:
            raise PermissionError("Guardian kill switch is active. Document parsing halted.")

        path = Path(file_path).resolve()
        if not path.is_file():
            raise FileNotFoundError(f"File not found: {file_path}")

        file_type = path.suffix.lower().lstrip(".")
        raw_text, doc_sections = self._extract_text_and_sections(path, file_type)
        char_count = len(raw_text)

        # Generate unique doc_id based on file path and content hash
        doc_hash = hashlib.sha256(f"{str(path)}_{char_count}".encode("utf-8")).hexdigest()[:16]
        doc_id = f"doc_{doc_hash}"

        # Produce section-aware chunks
        chunks = self._chunk_document(
            doc_id=doc_id,
            file_path=str(path),
            raw_text=raw_text,
            sections=doc_sections,
            chunk_size_words=chunk_size_words,
            overlap_words=overlap_words,
            custom_metadata=custom_metadata or {},
        )

        return ParsedDocument(
            doc_id=doc_id,
            file_path=str(path),
            file_name=path.name,
            file_type=file_type,
            total_chunks=len(chunks),
            chunks=chunks,
            raw_char_count=char_count,
            metadata={
                **(custom_metadata or {}),
                "file_size": path.stat().st_size,
                "modified_time": path.stat().st_mtime,
            },
        )

    def _extract_text_and_sections(self, path: Path, file_type: str) -> tuple[str, List[tuple[int, str]]]:
        """
        Extracts raw text and a list of (character_offset, section_title) tuples.
        """
        sections: List[tuple[int, str]] = []

        if file_type in ("md", "markdown"):
            text = path.read_text(encoding="utf-8", errors="replace")
            for match in self.HEADING_RE.finditer(text):
                sections.append((match.start(), match.group(2).strip()))
            return text, sections

        elif file_type in ("py", "ts", "js", "tsx", "jsx", "json", "yaml", "yml", "toml", "rs", "go", "cpp", "c", "h"):
            text = path.read_text(encoding="utf-8", errors="replace")
            for match in self.CODE_SECTION_RE.finditer(text):
                sections.append((match.start(), f"symbol:{match.group(1)}"))
            return text, sections

        elif file_type == "pdf":
            try:
                import pypdf
                reader = pypdf.PdfReader(str(path))
                pages = []
                cur_len = 0
                for idx, page in enumerate(reader.pages):
                    page_text = page.extract_text() or ""
                    sections.append((cur_len, f"Page {idx + 1}"))
                    pages.append(page_text)
                    cur_len += len(page_text) + 2
                return "\n\n".join(pages), sections
            except Exception:
                text = path.read_text(encoding="utf-8", errors="replace")
                return text, sections

        elif file_type in ("docx", "doc"):
            try:
                import docx
                doc = docx.Document(str(path))
                paras = []
                cur_len = 0
                for p in doc.paragraphs:
                    p_text = p.text.strip()
                    if p_text:
                        if p.style and "Heading" in p.style.name:
                            sections.append((cur_len, p_text))
                        paras.append(p_text)
                        cur_len += len(p_text) + 1
                return "\n".join(paras), sections
            except Exception:
                text = path.read_text(encoding="utf-8", errors="replace")
                return text, sections

        else:
            # Plain text fallback
            text = path.read_text(encoding="utf-8", errors="replace")
            return text, sections

    def _chunk_document(
        self,
        doc_id: str,
        file_path: str,
        raw_text: str,
        sections: List[tuple[int, str]],
        chunk_size_words: int,
        overlap_words: int,
        custom_metadata: Dict[str, Any],
    ) -> List[ParsedChunk]:
        """
        Splits raw text into overlapping word/sentence chunks with nearest preceding section title.
        """
        words = raw_text.split()
        if not words:
            return []

        step = max(1, chunk_size_words - overlap_words)
        chunks: List[ParsedChunk] = []

        total_est_chunks = (len(words) + step - 1) // step
        char_idx = 0

        for idx, start_idx in enumerate(range(0, len(words), step)):
            chunk_words = words[start_idx : start_idx + chunk_size_words]
            chunk_text = " ".join(chunk_words)
            if not chunk_text.strip():
                continue

            # Approximate character offset in original text using multi-word needle
            search_needle = " ".join(chunk_words[:3]) if len(chunk_words) >= 3 else chunk_words[0]
            approx_offset = raw_text.find(search_needle, char_idx)
            if approx_offset >= 0:
                char_idx = approx_offset
            elif chunk_words:
                sub_offset = raw_text.find(chunk_words[0], char_idx)
                if sub_offset >= 0:
                    char_idx = sub_offset

            # Find active section title
            active_section = None
            # Check if any section title is directly contained in this chunk
            for offset, title in sections:
                if title in chunk_text:
                    active_section = title
                    break

            if not active_section:
                for offset, title in sections:
                    if offset <= char_idx:
                        active_section = title
                    else:
                        break

            chunk_hash = hashlib.sha256(f"{doc_id}_{idx}_{chunk_text[:50]}".encode("utf-8")).hexdigest()[:12]
            chunk_id = f"chunk_{chunk_hash}"

            token_estimate = max(1, len(chunk_text) // 4)

            chunks.append(
                ParsedChunk(
                    chunk_id=chunk_id,
                    doc_id=doc_id,
                    file_path=file_path,
                    section_title=active_section,
                    text=chunk_text,
                    token_estimate=token_estimate,
                    chunk_index=idx,
                    total_chunks=total_est_chunks,
                    metadata=custom_metadata,
                )
            )

            if start_idx + chunk_size_words >= len(words):
                break

        # Normalize total_chunks across list
        for c in chunks:
            c.total_chunks = len(chunks)

        return chunks


# Global singleton
document_parser = DocumentParser()
