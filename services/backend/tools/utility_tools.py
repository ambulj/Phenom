"""
Phenom Utilities & PDF Engine
Provides:
1. Local PDF Splitter & Merger via pypdf (100% offline, zero cloud uploads)
2. Sandboxed Math Calculator (AST-validated, zero arbitrary code execution)
"""

import os
import ast
import math
import operator
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field
import pypdf
from services.backend.safety.registry import registry

# ==========================================
# 1. Local PDF Splitter & Merger Tools
# ==========================================

class PdfSplitArgs(BaseModel):
    pdf_path: str = Field(description="Absolute path to the source PDF file")
    start_page: int = Field(description="Starting page number (1-indexed)")
    end_page: int = Field(description="Ending page number (1-indexed, inclusive)")
    output_path: Optional[str] = Field(default=None, description="Optional destination path for the extracted PDF")

@registry.register(
    name="pdf_split_pages",
    tier=1,
    description="Extracts a range of pages from a PDF document and saves as a new PDF locally",
    args_schema=PdfSplitArgs,
    preview_fn=lambda a: f"Extract pages {a.get('start_page')}–{a.get('end_page')} from {os.path.basename(str(a.get('pdf_path')))}"
)
def pdf_split_pages(pdf_path: str, start_page: int, end_page: int, output_path: Optional[str] = None) -> Dict[str, Any]:
    if not os.path.exists(pdf_path):
        return {"status": "error", "message": f"Source PDF not found: {pdf_path}"}

    reader = pypdf.PdfReader(pdf_path)
    total_pages = len(reader.pages)

    start_idx = max(0, start_page - 1)
    end_idx = min(total_pages, end_page)

    if start_idx >= end_idx:
        return {"status": "error", "message": f"Invalid page range: {start_page} to {end_page} (PDF has {total_pages} pages)"}

    writer = pypdf.PdfWriter()
    for i in range(start_idx, end_idx):
        writer.add_page(reader.pages[i])

    if not output_path:
        base, ext = os.path.splitext(pdf_path)
        output_path = f"{base}_pages_{start_page}_to_{end_page}{ext}"

    os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
    with open(output_path, "wb") as f:
        writer.write(f)

    return {
        "status": "success",
        "output_path": output_path,
        "extracted_pages": f"{start_page}–{end_page}",
        "total_pages_in_result": end_idx - start_idx
    }

class PdfMergeArgs(BaseModel):
    pdf_paths: List[str] = Field(description="List of paths to PDF files to combine in order")
    output_path: str = Field(description="Destination path for the merged PDF")

@registry.register(
    name="pdf_merge_files",
    tier=1,
    description="Combines multiple PDF documents into a single document locally",
    args_schema=PdfMergeArgs,
    preview_fn=lambda a: f"Merge {len(a.get('pdf_paths', []))} PDF files into {os.path.basename(str(a.get('output_path')))}"
)
def pdf_merge_files(pdf_paths: List[str], output_path: str) -> Dict[str, Any]:
    if not pdf_paths or len(pdf_paths) < 2:
        return {"status": "error", "message": "At least 2 PDF files are required to merge"}

    writer = pypdf.PdfWriter()
    merged_count = 0

    for path in pdf_paths:
        if not os.path.exists(path):
            return {"status": "error", "message": f"PDF file not found: {path}"}
        reader = pypdf.PdfReader(path)
        for page in reader.pages:
            writer.add_page(page)
        merged_count += 1

    os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
    with open(output_path, "wb") as f:
        writer.write(f)

    return {
        "status": "success",
        "output_path": output_path,
        "files_merged": merged_count,
        "total_pages": len(writer.pages)
    }

# ==========================================
# 2. Sandboxed Python Math Calculator
# ==========================================

SAFE_OPERATORS = {
    ast.Add: operator.add,
    ast.Sub: operator.sub,
    ast.Mult: operator.mul,
    ast.Div: operator.truediv,
    ast.FloorDiv: operator.floordiv,
    ast.Mod: operator.mod,
    ast.Pow: operator.pow,
    ast.USub: operator.neg,
    ast.UAdd: operator.pos,
}

SAFE_FUNCTIONS = {
    "sqrt": math.sqrt,
    "sin": math.sin,
    "cos": math.cos,
    "tan": math.tan,
    "log": math.log,
    "log10": math.log10,
    "exp": math.exp,
    "abs": abs,
    "round": round,
    "ceil": math.ceil,
    "floor": math.floor,
    "pi": math.pi,
    "e": math.e,
}

def _eval_node(node):
    if isinstance(node, ast.Constant):
        return node.value
    elif isinstance(node, ast.BinOp):
        op = SAFE_OPERATORS.get(type(node.op))
        if not op:
            raise ValueError(f"Unsupported operator: {type(node.op).__name__}")
        left = _eval_node(node.left)
        right = _eval_node(node.right)
        return op(left, right)
    elif isinstance(node, ast.UnaryOp):
        op = SAFE_OPERATORS.get(type(node.op))
        if not op:
            raise ValueError(f"Unsupported unary operator: {type(node.op).__name__}")
        return op(_eval_node(node.operand))
    elif isinstance(node, ast.Call):
        func_name = getattr(node.func, "id", None)
        if func_name not in SAFE_FUNCTIONS:
            raise ValueError(f"Disallowed function call: {func_name}")
        args = [_eval_node(a) for a in node.args]
        func = SAFE_FUNCTIONS[func_name]
        return func(*args)
    elif isinstance(node, ast.Name):
        if node.id in SAFE_FUNCTIONS:
            return SAFE_FUNCTIONS[node.id]
        raise ValueError(f"Disallowed variable or identifier: {node.id}")
    else:
        raise ValueError(f"Unsupported AST node: {type(node).__name__}")

class SafeCalculateArgs(BaseModel):
    expression: str = Field(description="Mathematical expression to evaluate (e.g. 'sqrt(144) + 12 * 3.5')")

@registry.register(
    name="safe_calculate",
    tier=0,
    description="Evaluates mathematical expressions and formulas safely without arbitrary code execution",
    args_schema=SafeCalculateArgs,
    preview_fn=lambda a: f"Calculate expression: {a.get('expression')}"
)
def safe_calculate(expression: str) -> Dict[str, Any]:
    try:
        expr_clean = expression.strip()
        parsed = ast.parse(expr_clean, mode="eval")
        result = _eval_node(parsed.body)
        return {
            "status": "success",
            "expression": expr_clean,
            "result": result
        }
    except Exception as e:
        return {
            "status": "error",
            "expression": expression,
            "message": str(e)
        }
