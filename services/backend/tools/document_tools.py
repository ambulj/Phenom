"""
Phenom Autonomous Document Tools (Milestone 18 - Phase 1)
Wraps DocumentGenerator into formal Safety Engine ToolDefinitions:
- generate_document (Tier 1): Generates or modifies .docx, .xlsx, .pptx, or .pdf with diff preview
- get_document_templates (Tier 0): Returns available styling templates
- list_generated_documents (Tier 0): Enumerates documents in vault/documents/
"""

import os
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field

from services.backend.safety.registry import registry
from services.backend.safety.guardian import guardian
from services.backend.integrations.doc_generator import doc_generator, DEFAULT_DOCS_DIR


class GenerateDocumentArgs(BaseModel):
    filename: str = Field(description="Target file name with or without extension, e.g., 'Q4_Financial_Report.xlsx'")
    format: str = Field(default="docx", description="Document format: 'docx', 'xlsx', 'pptx', or 'pdf'")
    title: str = Field(default="Phenom Document", description="Primary document or presentation title")
    subtitle: Optional[str] = Field(default=None, description="Subtitle for presentation or document")
    sections: Optional[List[Dict[str, Any]]] = Field(
        default=None,
        description="Sections for Word docx: [{'heading': str, 'content': str, 'bullets': list[str], 'table': list[list[str]]}]"
    )
    headers: Optional[List[str]] = Field(
        default=None,
        description="Column header titles for Excel spreadsheet"
    )
    rows: Optional[List[List[Any]]] = Field(
        default=None,
        description="Data rows for Excel spreadsheet"
    )
    slides_data: Optional[List[Dict[str, Any]]] = Field(
        default=None,
        description="Slide configurations for PowerPoint: [{'title': str, 'bullets': list[str], 'chart': dict}]"
    )
    paragraphs: Optional[List[str]] = Field(
        default=None,
        description="Body text paragraphs for PDF report"
    )
    table_data: Optional[List[List[str]]] = Field(
        default=None,
        description="Structured table data matrix for PDF report"
    )
    chart_config: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Native chart embedding configuration (type, title, categories, series/data)"
    )
    mode: str = Field(
        default="create",
        description="Operation mode: 'create' (new file), 'modify' (update sections), or 'append' (add to existing)"
    )
    template: Optional[str] = Field(
        default=None,
        description="Optional template identifier (executive_brief, financial_quarterly, tech_architecture, cyber_cyan)"
    )
    folder: Optional[str] = Field(
        default=None,
        description="Target directory override (defaults to vault/documents)"
    )


def generate_diff_preview(args: Dict[str, Any]) -> str:
    """
    Tier 1 Diff Preview Generator for Document Operations.
    Computes human-readable diff preview showing targets, file status, additions, and chart inclusion.
    """
    filename = args.get("filename", "unnamed_document")
    fmt = args.get("format", "docx").lower().lstrip(".")
    mode = args.get("mode", "create").lower()
    folder = args.get("folder") or DEFAULT_DOCS_DIR
    target_path = os.path.join(folder, filename if filename.endswith(f".{fmt}") else f"{filename}.{fmt}")
    
    exists = os.path.exists(target_path)
    file_state = "OVERWRITE_PREVIEW" if (exists and mode == "create") else ("APPEND_PREVIEW" if exists else "CREATE_NEW")
    
    details = []
    if fmt == "docx":
        sec_count = len(args.get("sections") or [])
        details.append(f"+{sec_count} sections")
    elif fmt == "xlsx":
        r_count = len(args.get("rows") or [])
        c_count = len(args.get("headers") or [])
        details.append(f"+{r_count} rows, {c_count} columns")
    elif fmt == "pptx":
        s_count = len(args.get("slides_data") or [])
        details.append(f"+{s_count} slides")
    elif fmt == "pdf":
        p_count = len(args.get("paragraphs") or [])
        details.append(f"+{p_count} paragraphs")

    if args.get("chart_config"):
        c_type = args["chart_config"].get("type", "bar")
        details.append(f"chart_embed={c_type}")

    diff_summary = ", ".join(details) if details else "standard structure"
    action_verb = "Modify" if mode in ("modify", "append") else "Generate"

    return (
        f"[Tier 1] {action_verb} {fmt.upper()} Document: '{filename}' [{file_state}] "
        f"({diff_summary}). Target: {target_path}"
    )


@registry.register(
    name="generate_document",
    tier=1,
    description="Synthesize or modify Word, Excel, PowerPoint, or PDF documents with executive styling and charts",
    args_schema=GenerateDocumentArgs,
    preview_fn=generate_diff_preview
)
def generate_document(
    filename: str,
    format: str = "docx",
    title: str = "Phenom Document",
    subtitle: Optional[str] = None,
    sections: Optional[List[Dict[str, Any]]] = None,
    headers: Optional[List[str]] = None,
    rows: Optional[List[List[Any]]] = None,
    slides_data: Optional[List[Dict[str, Any]]] = None,
    paragraphs: Optional[List[str]] = None,
    table_data: Optional[List[List[str]]] = None,
    chart_config: Optional[Dict[str, Any]] = None,
    mode: str = "create",
    template: Optional[str] = None,
    folder: Optional[str] = None
) -> Dict[str, Any]:
    """
    Tier 1 handler for autonomous document creation and modification.
    Enforces Guardian freeze check, Rule 7 recycle bin on overwrite, and Rule 4 privacy.
    """
    if guardian.is_halted:
        raise RuntimeError("Operation halted by Guardian Kill Switch")

    fmt = format.lower().lstrip(".")
    mode = mode.lower()

    if mode in ("modify", "append"):
        # Map parameters into additions dictionary
        additions: Dict[str, Any] = {
            "title": title,
            "sections": sections or [],
            "rows": rows or [],
            "slides": slides_data or [],
            "paragraphs": paragraphs or [],
            "table_data": table_data,
            "chart_config": chart_config
        }
        res = doc_generator.modify_document(
            filename=filename,
            format_type=fmt,
            additions=additions,
            mode=mode,
            folder=folder
        )
        return {
            "status": "success",
            "action": "modify_document",
            "details": res
        }

    # Otherwise CREATE mode
    if fmt == "docx":
        secs = sections or [
            {"heading": "Executive Summary", "content": "Autonomous executive brief generated by Phenom."},
            {"heading": "Key Directives", "bullets": ["Operational stability maintained", "Sovereign knowledge engine active"]}
        ]
        res = doc_generator.create_word_document(
            filename=filename,
            title=title,
            sections=secs,
            folder=folder
        )
    elif fmt == "xlsx":
        h = headers or ["Category", "Metric", "Status"]
        r = rows or [["Core Engine", 100, "Optimal"], ["Knowledge Vault", 98, "Synced"]]
        res = doc_generator.create_excel_spreadsheet(
            filename=filename,
            sheet_title=title,
            headers=h,
            rows=r,
            chart_config=chart_config,
            folder=folder
        )
    elif fmt == "pptx":
        s = slides_data or [
            {"title": "System Overview", "bullets": ["Milestone 18.0 Architecture", "Autonomous Document Engine", "Deep Obsidian Integration"]},
            {"title": "Key Benchmarks", "bullets": ["Guardian Freeze < 25ms", "Rule 7 Recycle Bin Enforcement", "100% Type-Safe"]}
        ]
        res = doc_generator.create_powerpoint_presentation(
            filename=filename,
            title=title,
            subtitle=subtitle or "Phenom Autonomous Presentation",
            slides_data=s,
            folder=folder
        )
    elif fmt == "pdf":
        p = paragraphs or [
            "This comprehensive executive summary was formulated autonomously by Phenom.",
            "All metrics adhere strictly to zero cloud egress and local cryptographic memory models."
        ]
        res = doc_generator.create_pdf_report(
            filename=filename,
            title=title,
            paragraphs=p,
            table_data=table_data,
            chart_config=chart_config,
            folder=folder
        )
    else:
        raise ValueError(f"Unsupported document format '{format}'. Expected docx, xlsx, pptx, or pdf.")

    return {
        "status": "success",
        "action": "generate_document",
        "details": res
    }


class GetTemplatesArgs(BaseModel):
    pass


@registry.register(
    name="get_document_templates",
    tier=0,
    description="Retrieve available document styling templates for executive presentations and reports",
    args_schema=GetTemplatesArgs,
    preview_fn=lambda a: "List available executive document templates"
)
def get_document_templates() -> List[Dict[str, Any]]:
    """Returns all pre-defined executive templates."""
    return doc_generator.get_templates()


class ListDocumentsArgs(BaseModel):
    folder: Optional[str] = Field(default=None, description="Optional folder path to scan")


@registry.register(
    name="list_generated_documents",
    tier=0,
    description="List all generated documents in the vault documents archive",
    args_schema=ListDocumentsArgs,
    preview_fn=lambda a: f"List documents in {a.get('folder') or 'vault/documents'}"
)
def list_generated_documents(folder: Optional[str] = None) -> List[Dict[str, Any]]:
    """Lists files in vault/documents."""
    return doc_generator.list_documents(folder)
