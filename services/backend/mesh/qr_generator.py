"""
QR Code Generator for Phenom P2P Mesh
Generates QR matrices and renders standalone SVG and base64 PNG images
for zero-config pairing on the Cyber HUD / Companion displays.
"""

import base64
import io
from typing import List
from PIL import Image, ImageDraw
import qrcode
from qrcode.constants import ERROR_CORRECT_M


def generate_qr_matrix(text: str) -> List[List[bool]]:
    """
    Generate a 2D boolean grid (matrix) for the given text.
    True represents a dark module, False represents a light module.
    """
    qr = qrcode.QRCode(
        version=None,  # Automatic version selection
        error_correction=ERROR_CORRECT_M,
        box_size=1,
        border=0
    )
    qr.add_data(text)
    qr.make(fit=True)
    matrix = qr.get_matrix()
    # Convert to pure bool list
    return [[bool(cell) for cell in row] for row in matrix]


def render_qr_svg(matrix: List[List[bool]], box_size: int = 8, border: int = 4) -> str:
    """
    Render a boolean matrix into a lightweight standalone SVG string.
    """
    matrix_size = len(matrix)
    total_modules = matrix_size + (border * 2)
    viewbox_dim = total_modules * box_size

    rects: List[str] = []
    for r, row in enumerate(matrix):
        for c, cell in enumerate(row):
            if cell:
                x = (c + border) * box_size
                y = (r + border) * box_size
                rects.append(f'<rect x="{x}" y="{y}" width="{box_size}" height="{box_size}" fill="#000000" />')

    rects_str = "".join(rects)
    svg = (
        f'<svg xmlns="http://www.w3.org/2000/svg" version="1.1" '
        f'width="{viewbox_dim}" height="{viewbox_dim}" viewBox="0 0 {viewbox_dim} {viewbox_dim}">'
        f'<rect width="100%" height="100%" fill="#ffffff"/>'
        f'{rects_str}'
        f'</svg>'
    )
    return svg


def render_qr_base64_png(matrix: List[List[bool]], box_size: int = 8, border: int = 4) -> str:
    """
    Render a boolean matrix into a base64-encoded PNG data URI using Pillow.
    Returns: data:image/png;base64,...
    """
    matrix_size = len(matrix)
    total_modules = matrix_size + (border * 2)
    img_dim = total_modules * box_size

    # Create white canvas (RGB)
    img = Image.new("RGB", (img_dim, img_dim), color="white")
    draw = ImageDraw.Draw(img)

    for r, row in enumerate(matrix):
        for c, cell in enumerate(row):
            if cell:
                x0 = (c + border) * box_size
                y0 = (r + border) * box_size
                x1 = x0 + box_size - 1
                y1 = y0 + box_size - 1
                draw.rectangle([x0, y0, x1, y1], fill="black")

    buffer = io.BytesIO()
    img.save(buffer, format="PNG")
    encoded = base64.b64encode(buffer.getvalue()).decode("ascii")
    return f"data:image/png;base64,{encoded}"
