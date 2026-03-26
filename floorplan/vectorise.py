"""
Pixel-to-metre coordinate conversion and Y-axis flip.

Floor plan images use top-left origin, Y increases downward.
IFC uses bottom-left origin, Y increases upward.

The Y-axis flip happens EXACTLY ONCE here — never in the VLM prompt,
the detection merge, or the plan builder.
"""
from __future__ import annotations

import logging
import math
from dataclasses import dataclass, field

from floorplan.detect import (
    DetectedColumn,
    DetectedOpening,
    DetectedRoom,
    DetectedWall,
    DetectionResult,
)

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Vectorised (metre-space) data classes
# ---------------------------------------------------------------------------

@dataclass
class VectorWall:
    """A wall segment in metres (IFC coordinate space)."""
    x1: float
    y1: float
    x2: float
    y2: float
    thickness: float = 0.2
    is_external: bool = True

    @property
    def length(self) -> float:
        return math.hypot(self.x2 - self.x1, self.y2 - self.y1)


@dataclass
class VectorOpening:
    """A door or window in metres."""
    opening_type: str  # "door" | "window"
    cx: float
    cy: float
    width: float
    height: float


@dataclass
class VectorRoom:
    """A labelled room in metres."""
    label: str
    cx: float
    cy: float
    contour: list[tuple[float, float]] = field(default_factory=list)


@dataclass
class VectorColumn:
    """A structural column in metres."""
    cx: float
    cy: float
    size: float = 0.3


@dataclass
class VectorisedPlan:
    """All detected elements converted to metre coordinates."""
    walls: list[VectorWall] = field(default_factory=list)
    openings: list[VectorOpening] = field(default_factory=list)
    rooms: list[VectorRoom] = field(default_factory=list)
    columns: list[VectorColumn] = field(default_factory=list)
    scale_info: dict = field(default_factory=dict)
    image_width_m: float = 0.0
    image_height_m: float = 0.0


# ---------------------------------------------------------------------------
# Core conversion
# ---------------------------------------------------------------------------

def flip_y(y_px: float, h_total_px: int) -> float:
    """Flip Y-axis from image space (top-left origin) to IFC space (bottom-left origin).

    This function is called EXACTLY ONCE in the pipeline.
    """
    return h_total_px - y_px


def vectorise(
    detection: DetectionResult,
    px_per_m: float,
    default_wall_thickness: float = 0.2,
    default_storey_height: float = 3.0,
) -> VectorisedPlan:
    """Convert pixel-space detections to metre-space IFC coordinates.

    Args:
        detection: DetectionResult from detect_elements().
        px_per_m: Pixels per real-world metre (from scale detection).
        default_wall_thickness: Assumed wall thickness in metres.
        default_storey_height: Assumed storey height in metres.

    Returns:
        VectorisedPlan with all elements in metres, Y-flipped for IFC.
    """
    h_px = detection.image_height
    w_px = detection.image_width

    image_width_m = w_px / px_per_m
    image_height_m = h_px / px_per_m

    # Convert walls
    walls: list[VectorWall] = []
    for w in detection.walls:
        x1_m = w.x1 / px_per_m
        y1_m = flip_y(w.y1, h_px) / px_per_m
        x2_m = w.x2 / px_per_m
        y2_m = flip_y(w.y2, h_px) / px_per_m

        # Snap near-axis-aligned walls
        x1_m, y1_m = _snap_point(x1_m, y1_m)
        x2_m, y2_m = _snap_point(x2_m, y2_m)

        # Skip degenerate walls
        length = math.hypot(x2_m - x1_m, y2_m - y1_m)
        if length < 0.3:  # Skip walls shorter than 30cm
            continue

        thickness = w.thickness_px / px_per_m
        if thickness < 0.05:
            thickness = default_wall_thickness

        walls.append(VectorWall(
            x1=round(x1_m, 3),
            y1=round(y1_m, 3),
            x2=round(x2_m, 3),
            y2=round(y2_m, 3),
            thickness=round(min(max(thickness, 0.1), 0.5), 3),
            is_external=w.is_external,
        ))

    # Convert openings
    openings: list[VectorOpening] = []
    for o in detection.openings:
        cx_m = o.cx / px_per_m
        cy_m = flip_y(o.cy, h_px) / px_per_m
        width_m = o.width_px / px_per_m
        height_m = o.height_px / px_per_m

        # Clamp to reasonable dimensions
        width_m = min(max(width_m, 0.6), 3.0)
        if o.opening_type == "door":
            height_m = min(max(height_m, 1.8), 2.4)
        else:
            height_m = min(max(height_m, 0.6), 2.0)

        openings.append(VectorOpening(
            opening_type=o.opening_type,
            cx=round(cx_m, 3),
            cy=round(cy_m, 3),
            width=round(width_m, 3),
            height=round(height_m, 3),
        ))

    # Convert rooms
    rooms: list[VectorRoom] = []
    for r in detection.rooms:
        cx_m = r.cx / px_per_m
        cy_m = flip_y(r.cy, h_px) / px_per_m
        contour_m = [
            (round(px / px_per_m, 3), round(flip_y(py, h_px) / px_per_m, 3))
            for px, py in r.contour_px
        ]
        rooms.append(VectorRoom(
            label=r.label,
            cx=round(cx_m, 3),
            cy=round(cy_m, 3),
            contour=contour_m,
        ))

    # Convert columns
    columns: list[VectorColumn] = []
    for c in detection.columns:
        cx_m = c.cx / px_per_m
        cy_m = flip_y(c.cy, h_px) / px_per_m
        size_m = c.size_px / px_per_m
        columns.append(VectorColumn(
            cx=round(cx_m, 3),
            cy=round(cy_m, 3),
            size=round(max(size_m, 0.2), 3),
        ))

    logger.info(
        "Vectorised: %d walls, %d openings, %d rooms, %d columns (%.1f x %.1f m)",
        len(walls), len(openings), len(rooms), len(columns),
        image_width_m, image_height_m,
    )

    return VectorisedPlan(
        walls=walls,
        openings=openings,
        rooms=rooms,
        columns=columns,
        scale_info={},
        image_width_m=round(image_width_m, 3),
        image_height_m=round(image_height_m, 3),
    )


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_SNAP_TOLERANCE = 0.05  # 5cm snap tolerance


def _snap_point(x: float, y: float) -> tuple[float, float]:
    """Snap coordinates to nearest 5cm grid for cleaner geometry."""
    grid = 0.05
    return round(x / grid) * grid, round(y / grid) * grid
