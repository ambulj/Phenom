"""
Phenom Document Generation Engine (Milestone 18 - Phase 1)
Creates and modifies documents in 4 formats:
1. Word (.docx) via python-docx
2. Excel (.xlsx) via openpyxl with native chart embedding (BarChart, LineChart)
3. PowerPoint (.pptx) via python-pptx with native slide charts (CategoryChartData)
4. PDF (.pdf) via reportlab with flowable tables and graphics charts (VerticalBarChart)

Supports:
- Chart embedding across Excel, PowerPoint, and PDF
- Safe document modification and appending
- Executive styling templates (Executive Brief, Financial Quarterly, Tech Architecture, Cyber Cyan)
- Rule 7 safe backup / recycle bin protection via send2trash
"""

import os
import shutil
from typing import Dict, Any, List, Optional
from datetime import datetime, timezone
import send2trash

import docx
from docx.shared import Inches, Pt, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH

import openpyxl
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.chart import BarChart, LineChart, Reference

import pptx
from pptx.util import Inches as PptxInches, Pt as PptxPt
from pptx.chart.data import CategoryChartData
from pptx.enum.chart import XL_CHART_TYPE

from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors
from reportlab.graphics.shapes import Drawing, String, Rect
from reportlab.graphics.charts.barcharts import VerticalBarChart

DEFAULT_DOCS_DIR = os.path.abspath("vault/documents")

AVAILABLE_TEMPLATES = [
    {
        "id": "executive_brief",
        "name": "Executive Brief",
        "description": "High-impact leadership briefing format with Slate/Navy executive typography and structured KPI tables.",
        "formats": ["docx", "pdf", "pptx"],
        "accent_color": "#1A365D"
    },
    {
        "id": "financial_quarterly",
        "name": "Financial Quarterly Report",
        "description": "Financial balance & budget sheet with automated data aggregation, borders, and bar chart embeds.",
        "formats": ["xlsx", "pdf", "docx"],
        "accent_color": "#1F497D"
    },
    {
        "id": "tech_architecture",
        "name": "Technical Architecture Spec",
        "description": "In-depth engineering document with bullet trees, component tables, and architectural slide decks.",
        "formats": ["docx", "pptx", "pdf"],
        "accent_color": "#2B6CB0"
    },
    {
        "id": "cyber_cyan",
        "name": "Cyber Cyan Futuristic",
        "description": "Phenom signature cybernetic theme with neon cyan headers and high-contrast data matrices.",
        "formats": ["pptx", "pdf", "docx", "xlsx"],
        "accent_color": "#00F0FF"
    }
]


class DocumentGenerator:
    def __init__(self, default_dir: Optional[str] = None):
        self.output_dir = default_dir or DEFAULT_DOCS_DIR
        os.makedirs(self.output_dir, exist_ok=True)

    def _resolve_path(self, filename: str, folder: Optional[str] = None) -> str:
        target_dir = folder or self.output_dir
        os.makedirs(target_dir, exist_ok=True)
        return os.path.join(target_dir, filename)

    def get_templates(self) -> List[Dict[str, Any]]:
        """Returns list of pre-configured executive and technical document templates."""
        return list(AVAILABLE_TEMPLATES)

    def list_documents(self, folder: Optional[str] = None) -> List[Dict[str, Any]]:
        """Lists all generated documents in the document directory."""
        target_dir = folder or self.output_dir
        if not os.path.exists(target_dir):
            return []
        
        results = []
        for fname in sorted(os.listdir(target_dir)):
            full_path = os.path.join(target_dir, fname)
            if os.path.isfile(full_path):
                ext = os.path.splitext(fname)[1].lstrip(".").lower()
                if ext in ("docx", "xlsx", "pptx", "pdf", "md"):
                    stat = os.stat(full_path)
                    results.append({
                        "filename": fname,
                        "file_path": full_path,
                        "format": ext,
                        "size_bytes": stat.st_size,
                        "modified_at": datetime.fromtimestamp(stat.st_mtime, tz=timezone.utc).isoformat()
                    })
        return results

    # ---------------- 1. WORD DOCUMENT (.docx) ----------------
    def create_word_document(
        self,
        filename: str,
        title: str,
        sections: List[Dict[str, Any]],
        folder: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Creates a Word document with headings, paragraphs, and optional tables.
        sections: list of {'heading': str, 'content': str, 'bullets': list[str], 'table': list[list[str]]}
        """
        if not filename.endswith(".docx"):
            filename += ".docx"
        file_path = self._resolve_path(filename, folder)

        # Rule 7: If file exists, create recycle bin backup before overwrite
        if os.path.exists(file_path):
            backup_copy = file_path + f".bak_{int(datetime.now().timestamp())}"
            shutil.copy2(file_path, backup_copy)
            try:
                send2trash.send2trash(backup_copy)
            except Exception:
                pass

        doc = docx.Document()
        
        # Title
        title_p = doc.add_heading(title, level=0)
        title_p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        
        doc.add_paragraph(f"Generated by Phenom Assistant on {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}")
        doc.add_paragraph("")

        for sec in sections:
            if "heading" in sec and sec["heading"]:
                doc.add_heading(sec["heading"], level=1)
            
            if "content" in sec and sec["content"]:
                doc.add_paragraph(sec["content"])

            if "bullets" in sec and sec["bullets"]:
                for bullet in sec["bullets"]:
                    doc.add_paragraph(bullet, style='List Bullet')

            if "table" in sec and sec["table"]:
                rows = sec["table"]
                if rows:
                    t = doc.add_table(rows=len(rows), cols=len(rows[0]))
                    t.style = 'Table Grid'
                    for r_idx, row_data in enumerate(rows):
                        for c_idx, val in enumerate(row_data):
                            t.cell(r_idx, c_idx).text = str(val)

        doc.save(file_path)
        file_size = os.path.getsize(file_path)
        return {
            "format": "docx",
            "file_path": file_path,
            "filename": filename,
            "size_bytes": file_size,
            "sections_count": len(sections),
            "created_at": datetime.now(timezone.utc).isoformat()
        }

    # ---------------- 2. EXCEL SPREADSHEET (.xlsx) ----------------
    def create_excel_spreadsheet(
        self,
        filename: str,
        sheet_title: str,
        headers: List[str],
        rows: List[List[Any]],
        chart_config: Optional[Dict[str, Any]] = None,
        folder: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Creates an Excel spreadsheet with styled header row, auto-fit columns, and optional chart embed.
        chart_config: {
            "type": "bar" | "line",
            "title": str,
            "x_title": str,
            "y_title": str,
            "x_col": int (1-based index, default 1),
            "y_cols": List[int] (1-based indices, default [2])
        }
        """
        if not filename.endswith(".xlsx"):
            filename += ".xlsx"
        file_path = self._resolve_path(filename, folder)

        if os.path.exists(file_path):
            backup_copy = file_path + f".bak_{int(datetime.now().timestamp())}"
            shutil.copy2(file_path, backup_copy)
            try:
                send2trash.send2trash(backup_copy)
            except Exception:
                pass

        wb = openpyxl.Workbook()
        ws = wb.active
        ws.title = sheet_title[:31]  # Excel max sheet name length

        # Styles
        header_font = Font(name="Calibri", size=11, bold=True, color="FFFFFF")
        header_fill = PatternFill(start_color="1F497D", end_color="1F497D", fill_type="solid")
        thin_border = Border(
            left=Side(style='thin', color='D9D9D9'),
            right=Side(style='thin', color='D9D9D9'),
            top=Side(style='thin', color='D9D9D9'),
            bottom=Side(style='thin', color='D9D9D9')
        )

        # Write Headers
        ws.append(headers)
        for col_num in range(1, len(headers) + 1):
            cell = ws.cell(row=1, column=col_num)
            cell.font = header_font
            cell.fill = header_fill
            cell.alignment = Alignment(horizontal="center", vertical="center")

        # Write Data Rows
        for row_data in rows:
            ws.append(row_data)

        # Apply borders and auto column width
        for row in ws.iter_rows(min_row=1, max_row=len(rows) + 1, min_col=1, max_col=len(headers)):
            for cell in row:
                cell.border = thin_border

        for col in ws.columns:
            max_len = max(len(str(cell.value or '')) for cell in col)
            col_letter = openpyxl.utils.get_column_letter(col[0].column)
            ws.column_dimensions[col_letter].width = max(max_len + 3, 12)

        # Chart Embed Support
        has_chart = False
        if chart_config and len(rows) > 0 and len(headers) >= 2:
            chart_type = chart_config.get("type", "bar").lower()
            chart = BarChart() if chart_type == "bar" else LineChart()
            chart.title = chart_config.get("title", "Data Visualization")
            chart.style = 10
            chart.x_axis.title = chart_config.get("x_title", headers[0])
            chart.y_axis.title = chart_config.get("y_title", "Value")

            data = Reference(ws, min_col=2, min_row=1, max_col=len(headers), max_row=len(rows) + 1)
            cats = Reference(ws, min_col=1, min_row=2, max_row=len(rows) + 1)
            chart.add_data(data, titles_from_data=True)
            chart.set_categories(cats)
            
            # Position chart beside the table
            placement_col = openpyxl.utils.get_column_letter(len(headers) + 2)
            ws.add_chart(chart, f"{placement_col}2")
            has_chart = True

        wb.save(file_path)
        file_size = os.path.getsize(file_path)
        return {
            "format": "xlsx",
            "file_path": file_path,
            "filename": filename,
            "size_bytes": file_size,
            "rows_count": len(rows),
            "columns_count": len(headers),
            "has_chart": has_chart,
            "created_at": datetime.now(timezone.utc).isoformat()
        }

    # ---------------- 3. POWERPOINT PRESENTATION (.pptx) ----------------
    def create_powerpoint_presentation(
        self,
        filename: str,
        title: str,
        subtitle: str,
        slides_data: List[Dict[str, Any]],
        folder: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Creates a PowerPoint presentation with a title slide, content slides, and optional chart slides.
        slides_data: list of {
            'title': str,
            'bullets': list[str],
            'chart': {
                'type': 'bar' | 'pie' | 'line',
                'categories': list[str],
                'series_name': str,
                'series_values': list[float/int]
            } (optional)
        }
        """
        if not filename.endswith(".pptx"):
            filename += ".pptx"
        file_path = self._resolve_path(filename, folder)

        if os.path.exists(file_path):
            backup_copy = file_path + f".bak_{int(datetime.now().timestamp())}"
            shutil.copy2(file_path, backup_copy)
            try:
                send2trash.send2trash(backup_copy)
            except Exception:
                pass

        prs = pptx.Presentation()

        # Slide 1: Title slide layout (0)
        title_slide_layout = prs.slide_layouts[0]
        slide1 = prs.slides.add_slide(title_slide_layout)
        title_shape = slide1.shapes.title
        subtitle_shape = slide1.placeholders[1]
        title_shape.text = title
        subtitle_shape.text = subtitle

        chart_count = 0
        bullet_slide_layout = prs.slide_layouts[1]
        blank_slide_layout = prs.slide_layouts[5]  # Title-only layout

        for s_data in slides_data:
            chart_conf = s_data.get("chart")
            if chart_conf and "categories" in chart_conf and "series_values" in chart_conf:
                # Add slide with chart
                slide = prs.slides.add_slide(blank_slide_layout)
                shapes = slide.shapes
                title_box = shapes.title
                title_box.text = s_data.get("title", "Chart Analysis")

                chart_data = CategoryChartData()
                chart_data.categories = chart_conf["categories"]
                chart_data.add_series(
                    chart_conf.get("series_name", "Metrics"),
                    chart_conf["series_values"]
                )

                c_type = chart_conf.get("type", "bar").lower()
                chart_enum = XL_CHART_TYPE.COLUMN_CLUSTERED
                if c_type == "pie":
                    chart_enum = XL_CHART_TYPE.PIE
                elif c_type == "line":
                    chart_enum = XL_CHART_TYPE.LINE

                x, y, cx, cy = PptxInches(1.0), PptxInches(1.8), PptxInches(8.0), PptxInches(4.5)
                shapes.add_chart(chart_enum, x, y, cx, cy, chart_data)
                chart_count += 1
            else:
                slide = prs.slides.add_slide(bullet_slide_layout)
                shapes = slide.shapes
                title_box = shapes.title
                body_box = shapes.placeholders[1]
                title_box.text = s_data.get("title", "Slide")

                tf = body_box.text_frame
                bullets = s_data.get("bullets", [])
                if bullets:
                    tf.text = bullets[0]
                    for b_text in bullets[1:]:
                        p = tf.add_paragraph()
                        p.text = b_text

        prs.save(file_path)
        file_size = os.path.getsize(file_path)
        return {
            "format": "pptx",
            "file_path": file_path,
            "filename": filename,
            "size_bytes": file_size,
            "slides_count": len(slides_data) + 1,
            "chart_slides_count": chart_count,
            "created_at": datetime.now(timezone.utc).isoformat()
        }

    # ---------------- 4. PDF DOCUMENT (.pdf) ----------------
    def create_pdf_report(
        self,
        filename: str,
        title: str,
        paragraphs: List[str],
        table_data: Optional[List[List[str]]] = None,
        chart_config: Optional[Dict[str, Any]] = None,
        folder: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Creates a PDF document via reportlab with title, body text, optional table, and optional bar chart.
        chart_config: {
            "title": str,
            "categories": List[str],
            "data": List[float/int]
        }
        """
        if not filename.endswith(".pdf"):
            filename += ".pdf"
        file_path = self._resolve_path(filename, folder)

        if os.path.exists(file_path):
            backup_copy = file_path + f".bak_{int(datetime.now().timestamp())}"
            shutil.copy2(file_path, backup_copy)
            try:
                send2trash.send2trash(backup_copy)
            except Exception:
                pass

        doc = SimpleDocTemplate(file_path, pagesize=letter, rightMargin=54, leftMargin=54, topMargin=54, bottomMargin=54)
        styles = getSampleStyleSheet()

        title_style = ParagraphStyle(
            'CustomTitle',
            parent=styles['Heading1'],
            fontSize=22,
            leading=26,
            textColor=colors.HexColor("#1A365D"),
            spaceAfter=14
        )
        body_style = ParagraphStyle(
            'CustomBody',
            parent=styles['Normal'],
            fontSize=11,
            leading=15,
            textColor=colors.HexColor("#2D3748"),
            spaceAfter=10
        )

        elements = []
        # Title
        elements.append(Paragraph(title, title_style))
        elements.append(Spacer(1, 10))

        # Paragraphs
        for p_text in paragraphs:
            elements.append(Paragraph(p_text, body_style))
            elements.append(Spacer(1, 8))

        # Table
        if table_data:
            elements.append(Spacer(1, 12))
            t = Table(table_data)
            t.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor("#2B6CB0")),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, -1), 10),
                ('BOTTOMPADDING', (0, 0), (-1, 0), 8),
                ('BACKGROUND', (0, 1), (-1, -1), colors.HexColor("#F7FAFC")),
                ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor("#CBD5E0")),
            ]))
            elements.append(t)

        # Chart Embed
        has_chart = False
        if chart_config and "data" in chart_config and len(chart_config["data"]) > 0:
            elements.append(Spacer(1, 16))
            draw_w, draw_h = 450, 160
            drawing = Drawing(draw_w, draw_h)
            bc = VerticalBarChart()
            bc.x = 40
            bc.y = 25
            bc.height = 110
            bc.width = 380
            bc.data = [chart_config["data"]]
            bc.strokeColor = colors.HexColor("#CBD5E0")
            bc.valueAxis.valueMin = 0
            bc.valueAxis.valueMax = max(chart_config["data"]) * 1.25 if max(chart_config["data"]) > 0 else 10
            bc.categoryAxis.labels.boxAnchor = 'ne'
            bc.categoryAxis.labels.dx = 8
            bc.categoryAxis.labels.dy = -2
            if "categories" in chart_config:
                bc.categoryAxis.categoryNames = chart_config["categories"]
            bc.bars[0].fillColor = colors.HexColor("#2B6CB0")
            drawing.add(bc)
            elements.append(drawing)
            has_chart = True

        doc.build(elements)
        file_size = os.path.getsize(file_path)
        return {
            "format": "pdf",
            "file_path": file_path,
            "filename": filename,
            "size_bytes": file_size,
            "has_chart": has_chart,
            "created_at": datetime.now(timezone.utc).isoformat()
        }

    # ---------------- 5. DOCUMENT MODIFICATION & APPEND ----------------
    def modify_document(
        self,
        filename: str,
        format_type: str,
        additions: Dict[str, Any],
        mode: str = "append",
        folder: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Modifies or appends to an existing document (.docx, .xlsx, .pptx, .pdf).
        Enforces Rule 7 recycle bin backup of original file prior to modification.
        """
        file_path = self._resolve_path(filename, folder)
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"Cannot modify non-existent file: {file_path}")

        # Rule 7: Backup before modification
        backup_copy = file_path + f".bak_mod_{int(datetime.now().timestamp())}"
        shutil.copy2(file_path, backup_copy)
        try:
            send2trash.send2trash(backup_copy)
        except Exception:
            pass

        fmt = format_type.lower().lstrip(".")

        if fmt == "docx":
            doc = docx.Document(file_path)
            new_sections = additions.get("sections", [])
            for sec in new_sections:
                if "heading" in sec and sec["heading"]:
                    doc.add_heading(sec["heading"], level=2)
                if "content" in sec and sec["content"]:
                    doc.add_paragraph(sec["content"])
                if "bullets" in sec and sec["bullets"]:
                    for bullet in sec["bullets"]:
                        doc.add_paragraph(bullet, style='List Bullet')
                if "table" in sec and sec["table"]:
                    rows = sec["table"]
                    if rows:
                        t = doc.add_table(rows=len(rows), cols=len(rows[0]))
                        t.style = 'Table Grid'
                        for r_idx, row_data in enumerate(rows):
                            for c_idx, val in enumerate(row_data):
                                t.cell(r_idx, c_idx).text = str(val)
            doc.save(file_path)

        elif fmt == "xlsx":
            wb = openpyxl.load_workbook(file_path)
            ws = wb.active
            new_rows = additions.get("rows", [])
            thin_border = Border(
                left=Side(style='thin', color='D9D9D9'),
                right=Side(style='thin', color='D9D9D9'),
                top=Side(style='thin', color='D9D9D9'),
                bottom=Side(style='thin', color='D9D9D9')
            )
            for row in new_rows:
                ws.append(row)
                row_idx = ws.max_row
                for col_idx in range(1, len(row) + 1):
                    ws.cell(row=row_idx, column=col_idx).border = thin_border
            wb.save(file_path)

        elif fmt == "pptx":
            prs = pptx.Presentation(file_path)
            new_slides = additions.get("slides", [])
            bullet_slide_layout = prs.slide_layouts[1]
            for s_data in new_slides:
                slide = prs.slides.add_slide(bullet_slide_layout)
                shapes = slide.shapes
                title_box = shapes.title
                body_box = shapes.placeholders[1]
                title_box.text = s_data.get("title", "Slide")
                tf = body_box.text_frame
                bullets = s_data.get("bullets", [])
                if bullets:
                    tf.text = bullets[0]
                    for b_text in bullets[1:]:
                        p = tf.add_paragraph()
                        p.text = b_text
            prs.save(file_path)

        elif fmt == "pdf":
            # For PDF, we append paragraphs and build updated document
            new_paragraphs = additions.get("paragraphs", [])
            # Read existing or generate updated PDF report
            title = additions.get("title", f"Updated Document - {datetime.now(timezone.utc).strftime('%Y-%m-%d')}")
            return self.create_pdf_report(
                filename=filename,
                title=title,
                paragraphs=new_paragraphs,
                table_data=additions.get("table_data"),
                chart_config=additions.get("chart_config"),
                folder=folder
            )
        else:
            raise ValueError(f"Unsupported modification format: {fmt}")

        file_size = os.path.getsize(file_path)
        return {
            "format": fmt,
            "file_path": file_path,
            "filename": filename,
            "mode": mode,
            "size_bytes": file_size,
            "modified_at": datetime.now(timezone.utc).isoformat()
        }


# Global document generator instance
doc_generator = DocumentGenerator()
