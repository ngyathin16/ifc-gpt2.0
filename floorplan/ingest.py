"""
Floor plan image ingestion and normalisation.

Handles:
  - PDF rasterisation at 300 DPI via PyMuPDF
  - Direct image loading (PNG, JPEG, TIFF, BMP)
  - Normalisation: convert to RGB, clamp longest axis to MAX_PX
"""
from __future__ import annotations

import io
from pathlib import Path

import numpy as np
from PIL import Image

MAX_PX = 4096  # Clamp longest axis before VLM / OpenCV processing
DPI = 300


def load_image(file_path: str | Path) -> np.ndarray:
    """Load a floor plan from a file path (PDF or image) and return an RGB numpy array.

    For multi-page PDFs only the first page is used.

    Returns:
        np.ndarray of shape (H, W, 3), dtype uint8, RGB colour space.
    """
    file_path = Path(file_path)
    suffix = file_path.suffix.lower()

    if suffix == ".pdf":
        img = _rasterise_pdf(file_path)
    elif suffix in (".png", ".jpg", ".jpeg", ".tif", ".tiff", ".bmp", ".webp"):
        img = Image.open(file_path)
    else:
        raise ValueError(f"Unsupported file format: {suffix}")

    return _normalise(img)


def load_image_from_bytes(data: bytes, filename: str = "plan.pdf") -> np.ndarray:
    """Load a floor plan from raw bytes (e.g. an uploaded file).

    The *filename* hint is used to determine whether the data is a PDF.

    Returns:
        np.ndarray of shape (H, W, 3), dtype uint8, RGB colour space.
    """
    suffix = Path(filename).suffix.lower()

    if suffix == ".pdf":
        img = _rasterise_pdf_bytes(data)
    else:
        img = Image.open(io.BytesIO(data))

    return _normalise(img)


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _rasterise_pdf(pdf_path: Path) -> Image.Image:
    """Render the first page of a PDF at 300 DPI."""
    import fitz  # PyMuPDF

    doc = fitz.open(str(pdf_path))
    page = doc[0]
    mat = fitz.Matrix(DPI / 72, DPI / 72)
    pix = page.get_pixmap(matrix=mat, alpha=False)
    img = Image.frombytes("RGB", (pix.width, pix.height), pix.samples)
    doc.close()
    return img


def _rasterise_pdf_bytes(data: bytes) -> Image.Image:
    """Render the first page of a PDF (from bytes) at 300 DPI."""
    import fitz  # PyMuPDF

    doc = fitz.open(stream=data, filetype="pdf")
    page = doc[0]
    mat = fitz.Matrix(DPI / 72, DPI / 72)
    pix = page.get_pixmap(matrix=mat, alpha=False)
    img = Image.frombytes("RGB", (pix.width, pix.height), pix.samples)
    doc.close()
    return img


def _normalise(img: Image.Image) -> np.ndarray:
    """Convert to RGB uint8 and clamp to MAX_PX on the longest axis."""
    img = img.convert("RGB")

    w, h = img.size
    longest = max(w, h)
    if longest > MAX_PX:
        scale = MAX_PX / longest
        new_w = int(w * scale)
        new_h = int(h * scale)
        img = img.resize((new_w, new_h), Image.LANCZOS)

    return np.asarray(img, dtype=np.uint8)
