"""
FloorPlan2IFC end-to-end pipeline.

Orchestrates: ingest → scale → detect → vectorise → plan_builder.

Usage:
    from floorplan.pipeline import floorplan_to_plan
    plan_dict = floorplan_to_plan(image_bytes, filename="plan.pdf")
"""
from __future__ import annotations

import logging
from typing import Any

import numpy as np

from floorplan.detect import detect_elements
from floorplan.ingest import load_image, load_image_from_bytes
from floorplan.plan_builder import build_plan
from floorplan.scale import detect_scale
from floorplan.vectorise import vectorise

logger = logging.getLogger(__name__)


def floorplan_to_plan(
    image_bytes: bytes,
    filename: str = "plan.pdf",
    num_storeys: int = 1,
    floor_to_floor_height: float = 3.0,
    dpi: int = 300,
    detection_backend: str = "opencv",
) -> dict[str, Any]:
    """Full pipeline: image bytes → BuildingPlan dict.

    Args:
        image_bytes: Raw file bytes (PDF or image).
        filename: Original filename (used to detect PDF vs image).
        num_storeys: How many storeys to replicate the detected floor plan.
        floor_to_floor_height: Height between storey elevations in metres.
        dpi: DPI used for PDF rasterisation.
        detection_backend: "opencv", "vlm", or "yolo".

    Returns:
        A dict matching the BuildingPlan schema, plus a "floorplan_metadata"
        key with scale info and detection stats.
    """
    # 1. Ingest
    logger.info("FloorPlan2IFC: ingesting %s (%d bytes)", filename, len(image_bytes))
    image = load_image_from_bytes(image_bytes, filename)

    return floorplan_to_plan_from_array(
        image,
        num_storeys=num_storeys,
        floor_to_floor_height=floor_to_floor_height,
        dpi=dpi,
        detection_backend=detection_backend,
    )


def floorplan_to_plan_from_array(
    image: np.ndarray,
    num_storeys: int = 1,
    floor_to_floor_height: float = 3.0,
    dpi: int = 300,
    detection_backend: str = "opencv",
) -> dict[str, Any]:
    """Full pipeline from a numpy image array → BuildingPlan dict.

    Useful for testing when you already have the image loaded.
    """
    h, w = image.shape[:2]
    logger.info("FloorPlan2IFC: image %dx%d", w, h)

    # 2. Scale detection
    scale_info = detect_scale(image, dpi=dpi)
    px_per_m = scale_info["px_per_m"]
    logger.info(
        "FloorPlan2IFC: scale 1:%d (%.1f px/m, method=%s, conf=%.2f)",
        scale_info["scale_denominator"], px_per_m,
        scale_info["method"], scale_info["confidence"],
    )

    # 3. Element detection
    detection = detect_elements(image, backend=detection_backend)

    # 4. Vectorise (pixel → metres, Y-flip)
    vectorised = vectorise(detection, px_per_m=px_per_m)

    # 5. Build plan
    plan = build_plan(
        vectorised,
        num_storeys=num_storeys,
        floor_to_floor_height=floor_to_floor_height,
        description=f"Floor plan imported from image ({w}x{h}px, 1:{scale_info['scale_denominator']})",
    )

    # Attach metadata for the frontend
    plan["floorplan_metadata"] = {
        "scale": scale_info,
        "image_size_px": [w, h],
        "image_size_m": [vectorised.image_width_m, vectorised.image_height_m],
        "detection_backend": detection_backend,
        "detected_walls": len(vectorised.walls),
        "detected_openings": len(vectorised.openings),
        "detected_rooms": len(vectorised.rooms),
        "detected_columns": len(vectorised.columns),
    }

    return plan


def floorplan_to_plan_from_path(
    file_path: str,
    num_storeys: int = 1,
    floor_to_floor_height: float = 3.0,
    dpi: int = 300,
    detection_backend: str = "opencv",
) -> dict[str, Any]:
    """Convenience: load from a file path and run the full pipeline."""
    from pathlib import Path

    path = Path(file_path)
    image = load_image(path)
    return floorplan_to_plan_from_array(
        image,
        num_storeys=num_storeys,
        floor_to_floor_height=floor_to_floor_height,
        dpi=dpi,
        detection_backend=detection_backend,
    )
