"""
Scale detection for floor plan images.

Two methods:
  1. OCR on scale annotation (e.g. "1:100", "Scale 1:50")
  2. Scale bar detection via HoughLinesP + OCR distance label

Fallback: 1:100 at 300 DPI ≈ 118.11 px/m.
"""
from __future__ import annotations

import logging
import re

import cv2
import numpy as np

logger = logging.getLogger(__name__)

# Known architectural scales — we snap OCR results to the nearest one
KNOWN_SCALES = [1, 2, 5, 10, 20, 25, 50, 100, 200, 500]

# Default fallback: 1:100 at 300 DPI
DEFAULT_SCALE_DENOMINATOR = 100
DEFAULT_DPI = 300
DEFAULT_PX_PER_M = DEFAULT_DPI / (0.0254 * DEFAULT_SCALE_DENOMINATOR)  # ~118.11


def detect_scale(image: np.ndarray, dpi: int = 300) -> dict:
    """Detect the drawing scale from a floor plan image.

    Tries OCR annotation first, then scale bar detection, then falls back to
    1:100 @ 300 DPI.

    Args:
        image: RGB uint8 numpy array (H, W, 3).
        dpi: Scanner DPI used when rasterising PDFs.

    Returns:
        {
            "scale_denominator": int,   # e.g. 100 for 1:100
            "px_per_m": float,          # pixels per real-world metre
            "method": str,              # "ocr_annotation" | "scale_bar" | "default"
            "confidence": float,        # 0.0–1.0
        }
    """
    # Method 1: OCR annotation
    result = _detect_scale_ocr(image, dpi)
    if result is not None:
        return result

    # Method 2: Scale bar
    result = _detect_scale_bar(image, dpi)
    if result is not None:
        return result

    # Fallback
    logger.warning("Scale detection failed — using default 1:100 @ %d DPI", dpi)
    px_per_m = dpi / (0.0254 * DEFAULT_SCALE_DENOMINATOR)
    return {
        "scale_denominator": DEFAULT_SCALE_DENOMINATOR,
        "px_per_m": px_per_m,
        "method": "default",
        "confidence": 0.0,
    }


def _detect_scale_ocr(image: np.ndarray, dpi: int) -> dict | None:
    """Try to read a scale annotation like '1:100' from the title block area."""
    try:
        import easyocr
    except ImportError:
        logger.warning("easyocr not available; skipping OCR scale detection")
        return None

    h, w = image.shape[:2]
    # Title block is typically in the bottom 20% of the drawing
    title_block = image[int(h * 0.8):, :]

    try:
        reader = easyocr.Reader(["en"], gpu=False, verbose=False)
        results = reader.readtext(title_block, detail=1)
    except Exception as e:
        logger.debug("EasyOCR failed: %s", e)
        return None

    # Search for scale patterns
    scale_pattern = re.compile(r"(?:scale\s*)?1\s*[:/]\s*(\d+)", re.IGNORECASE)
    for _, text, conf in results:
        m = scale_pattern.search(text)
        if m:
            raw_denom = int(m.group(1))
            # Snap to nearest known scale
            denom = _snap_to_known_scale(raw_denom)
            px_per_m = dpi / (0.0254 * denom)
            logger.info("OCR scale detected: 1:%d (raw=%d, conf=%.2f)", denom, raw_denom, conf)
            return {
                "scale_denominator": denom,
                "px_per_m": px_per_m,
                "method": "ocr_annotation",
                "confidence": min(float(conf), 1.0),
            }

    return None


def _detect_scale_bar(image: np.ndarray, dpi: int) -> dict | None:
    """Try to detect a scale bar in the lower third of the image."""
    try:
        import easyocr
    except ImportError:
        return None

    h, w = image.shape[:2]
    lower_third = image[int(h * 0.67):, :]

    # Convert to grayscale and detect edges
    gray = cv2.cvtColor(lower_third, cv2.COLOR_RGB2GRAY)
    edges = cv2.Canny(gray, 50, 150)

    # Detect long horizontal lines
    lines = cv2.HoughLinesP(
        edges, rho=1, theta=np.pi / 180,
        threshold=80, minLineLength=int(w * 0.05), maxLineGap=10,
    )
    if lines is None:
        return None

    # Find the longest near-horizontal line
    best_line = None
    best_len = 0
    for line in lines:
        x1, y1, x2, y2 = line[0]
        angle = abs(np.degrees(np.arctan2(y2 - y1, x2 - x1)))
        if angle < 5 or angle > 175:  # near-horizontal
            length = np.sqrt((x2 - x1) ** 2 + (y2 - y1) ** 2)
            if length > best_len:
                best_len = length
                best_line = (x1, y1, x2, y2)

    if best_line is None or best_len < 30:
        return None

    # Try to OCR the area around the scale bar for a distance label
    x1, y1, x2, y2 = best_line
    bar_region_y1 = max(0, min(y1, y2) - 40)
    bar_region_y2 = min(lower_third.shape[0], max(y1, y2) + 40)
    bar_region_x1 = max(0, min(x1, x2) - 20)
    bar_region_x2 = min(w, max(x1, x2) + 60)
    bar_region = lower_third[bar_region_y1:bar_region_y2, bar_region_x1:bar_region_x2]

    try:
        reader = easyocr.Reader(["en"], gpu=False, verbose=False)
        results = reader.readtext(bar_region, detail=1)
    except Exception:
        return None

    # Look for distance labels like "5m", "10 m", "0 5 10m"
    distance_pattern = re.compile(r"(\d+)\s*m(?:eter|etre)?s?\b", re.IGNORECASE)
    for _, text, conf in results:
        m = distance_pattern.search(text)
        if m:
            labelled_m = float(m.group(1))
            if labelled_m <= 0:
                continue
            px_per_m = best_len / labelled_m
            # Back-calculate scale denominator
            # px_per_m = dpi / (0.0254 * denom)  →  denom = dpi / (0.0254 * px_per_m)
            raw_denom = dpi / (0.0254 * px_per_m)
            denom = _snap_to_known_scale(int(round(raw_denom)))
            # Recalculate px_per_m from snapped scale
            px_per_m = dpi / (0.0254 * denom)
            logger.info(
                "Scale bar detected: bar_len=%.0fpx, label=%sm → 1:%d",
                best_len, m.group(1), denom,
            )
            return {
                "scale_denominator": denom,
                "px_per_m": px_per_m,
                "method": "scale_bar",
                "confidence": min(float(conf) * 0.8, 1.0),
            }

    return None


def _snap_to_known_scale(raw: int) -> int:
    """Snap a raw scale denominator to the nearest known architectural scale."""
    if raw <= 0:
        return DEFAULT_SCALE_DENOMINATOR
    closest = min(KNOWN_SCALES, key=lambda s: abs(s - raw))
    return closest
