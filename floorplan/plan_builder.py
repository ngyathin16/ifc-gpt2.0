"""
Convert vectorised floor plan elements into a BuildingPlan JSON dict.

This is the final stage of the FloorPlan2IFC pipeline. It takes metre-space
geometry from vectorise.py and produces a dict that matches the
agent.schemas.BuildingPlan Pydantic model, ready to be fed into the
build node or the /api/build-from-plan endpoint.
"""
from __future__ import annotations

import logging
import math
from typing import Any

from building_blocks.mic_catalog import (
    classify_room,
    get_opening_defaults,
    get_typical_dims,
)
from floorplan.vectorise import VectorisedPlan, VectorWall

logger = logging.getLogger(__name__)

# Default architectural parameters
DEFAULT_WALL_HEIGHT = 3.0
DEFAULT_FLOOR_TO_FLOOR = 3.0
DEFAULT_SLAB_DEPTH = 0.2
DEFAULT_DOOR_WIDTH = 0.9
DEFAULT_DOOR_HEIGHT = 2.1
DEFAULT_WINDOW_WIDTH = 1.2
DEFAULT_WINDOW_HEIGHT = 1.5
DEFAULT_WINDOW_SILL = 0.9


def build_plan(
    vectorised: VectorisedPlan,
    num_storeys: int = 1,
    floor_to_floor_height: float = DEFAULT_FLOOR_TO_FLOOR,
    wall_height: float = DEFAULT_WALL_HEIGHT,
    description: str = "Floor plan imported from image",
) -> dict[str, Any]:
    """Convert a VectorisedPlan into a BuildingPlan-compatible dict.

    Args:
        vectorised: Output from vectorise().
        num_storeys: Number of storeys to replicate the floor plan across.
        floor_to_floor_height: Height between storey elevations.
        wall_height: Wall height within each storey.
        description: Human-readable description for the plan.

    Returns:
        A dict matching the BuildingPlan schema, ready for model_validate().
    """
    # 1. Storeys
    storeys = []
    for i in range(num_storeys):
        storeys.append({
            "storey_ref": f"S{i}",
            "name": _storey_name(i, num_storeys),
            "elevation": round(i * floor_to_floor_height, 3),
            "floor_to_floor_height": floor_to_floor_height,
        })

    # 2. Types
    types = [
        {"type_ref": "ext_wall_type", "ifc_class": "IfcWallType", "preset": "exterior_wall"},
        {"type_ref": "int_wall_type", "ifc_class": "IfcWallType", "preset": "interior_wall"},
    ]

    # 3. Elements — replicated per storey
    elements: list[dict[str, Any]] = []
    wall_junctions: list[dict[str, Any]] = []

    for si, storey_def in enumerate(storeys):
        storey_ref = storey_def["storey_ref"]

        # Walls
        wall_refs: list[str] = []
        for wi, wall in enumerate(vectorised.walls):
            wall_ref = f"W{si}_{wi}"
            wall_refs.append(wall_ref)
            elements.append({
                "element_type": "wall",
                "wall_ref": wall_ref,
                "component_id": "exterior_wall" if wall.is_external else "interior_wall",
                "storey_ref": storey_ref,
                "start_point": [wall.x1, wall.y1],
                "end_point": [wall.x2, wall.y2],
                "height": wall_height,
                "thickness": wall.thickness,
                "is_external": wall.is_external,
                "wall_type_ref": "ext_wall_type" if wall.is_external else "int_wall_type",
            })

        # Wall junctions — connect walls that share endpoints
        junctions = _find_wall_junctions(vectorised.walls, si)
        wall_junctions.extend(junctions)

        # Floor slab — use bounding box of all walls as boundary
        slab_boundary = _compute_slab_boundary(vectorised.walls)
        if slab_boundary and len(slab_boundary) >= 3:
            elements.append({
                "element_type": "slab",
                "storey_ref": storey_ref,
                "boundary_points": slab_boundary,
                "depth": DEFAULT_SLAB_DEPTH,
                "elevation": 0.0,
                "slab_type": "FLOOR",
            })

        # Openings — assign to nearest wall
        for oi, opening in enumerate(vectorised.openings):
            nearest_wall_idx = _find_nearest_wall(
                opening.cx, opening.cy, vectorised.walls,
            )
            if nearest_wall_idx is None:
                continue
            wall = vectorised.walls[nearest_wall_idx]
            wall_ref = f"W{si}_{nearest_wall_idx}"
            dist_along = _distance_along_wall(
                opening.cx, opening.cy, wall,
            )

            if opening.opening_type == "door":
                elements.append({
                    "element_type": "door",
                    "storey_ref": storey_ref,
                    "host_wall_ref": wall_ref,
                    "distance_along_wall": round(dist_along, 3),
                    "sill_height": 0.0,
                    "width": opening.width,
                    "height": opening.height,
                    "operation_type": "SINGLE_SWING_LEFT",
                })
            else:
                elements.append({
                    "element_type": "window",
                    "storey_ref": storey_ref,
                    "host_wall_ref": wall_ref,
                    "distance_along_wall": round(dist_along, 3),
                    "sill_height": DEFAULT_WINDOW_SILL,
                    "width": opening.width,
                    "height": opening.height,
                    "partition_type": "SINGLE_PANEL",
                })

        # Columns
        for ci, col in enumerate(vectorised.columns):
            elements.append({
                "element_type": "column",
                "column_ref": f"C{si}_{ci}",
                "storey_ref": storey_ref,
                "position": [col.cx, col.cy],
                "base_elevation": 0.0,
                "height": wall_height,
                "profile_type": "RECTANGULAR",
                "width": col.size,
                "depth": col.size,
            })

    # 4. Roof on top storey
    if num_storeys > 0:
        top_storey_ref = f"S{num_storeys - 1}"
        roof_boundary = _compute_slab_boundary(vectorised.walls)
        if roof_boundary and len(roof_boundary) >= 3:
            elements.append({
                "element_type": "roof",
                "storey_ref": top_storey_ref,
                "boundary_points": roof_boundary,
                "roof_type": "FLAT",
                "ridge_height": 0.0,
                "thickness": 0.25,
            })

    # 5. Rooms metadata — enriched with MiC category and opening defaults
    rooms = []
    for room in vectorised.rooms:
        category = classify_room(room.label)
        mic_dims = get_typical_dims(category)
        opening_defaults = get_opening_defaults(category)
        room_entry: dict[str, Any] = {
            "label": room.label,
            "category": category,
            "cx": room.cx,
            "cy": room.cy,
            "expected_doors": opening_defaults["doors"],
            "expected_windows": opening_defaults["windows"],
        }
        if mic_dims:
            room_entry["typical_width_m"] = mic_dims.width_m
            room_entry["typical_depth_m"] = mic_dims.depth_m
        rooms.append(room_entry)

    plan = {
        "description": description,
        "site": {"name": "Default Site"},
        "building": {"name": "Building A", "building_type": "Imported"},
        "storeys": storeys,
        "types": types,
        "elements": elements,
        "wall_junctions": wall_junctions,
        "rooms": rooms,
    }

    logger.info(
        "Built plan: %d storeys, %d elements, %d junctions",
        len(storeys), len(elements), len(wall_junctions),
    )
    return plan


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _storey_name(index: int, total: int) -> str:
    if index == 0:
        return "Ground Floor"
    if total > 1 and index == total - 1:
        return f"Level {index} (Top)"
    return f"Level {index}"


def _compute_slab_boundary(walls: list[VectorWall]) -> list[list[float]]:
    """Compute a convex hull boundary from wall endpoints for the floor slab."""
    if not walls:
        return []

    import numpy as np

    points = []
    for w in walls:
        points.append([w.x1, w.y1])
        points.append([w.x2, w.y2])

    pts = np.array(points)
    if len(pts) < 3:
        return []

    # Use convex hull
    try:
        from shapely.geometry import MultiPoint
        hull = MultiPoint(pts).convex_hull
        if hull.geom_type == "Polygon":
            coords = list(hull.exterior.coords)[:-1]  # Drop closing point
            return [[round(x, 3), round(y, 3)] for x, y in coords]
    except Exception:
        pass

    # Fallback: bounding box
    min_x, min_y = pts.min(axis=0)
    max_x, max_y = pts.max(axis=0)
    return [
        [round(float(min_x), 3), round(float(min_y), 3)],
        [round(float(max_x), 3), round(float(min_y), 3)],
        [round(float(max_x), 3), round(float(max_y), 3)],
        [round(float(min_x), 3), round(float(max_y), 3)],
    ]


def _find_nearest_wall(
    cx: float, cy: float, walls: list[VectorWall],
) -> int | None:
    """Find the index of the wall closest to point (cx, cy)."""
    if not walls:
        return None

    best_idx = 0
    best_dist = float("inf")
    for i, w in enumerate(walls):
        dist = _point_to_segment_distance(cx, cy, w.x1, w.y1, w.x2, w.y2)
        if dist < best_dist:
            best_dist = dist
            best_idx = i

    return best_idx


def _point_to_segment_distance(
    px: float, py: float,
    x1: float, y1: float,
    x2: float, y2: float,
) -> float:
    """Perpendicular distance from point to line segment."""
    dx, dy = x2 - x1, y2 - y1
    length_sq = dx * dx + dy * dy
    if length_sq < 1e-9:
        return math.hypot(px - x1, py - y1)

    t = max(0.0, min(1.0, ((px - x1) * dx + (py - y1) * dy) / length_sq))
    proj_x = x1 + t * dx
    proj_y = y1 + t * dy
    return math.hypot(px - proj_x, py - proj_y)


def _distance_along_wall(cx: float, cy: float, wall: VectorWall) -> float:
    """Project point onto wall line and return distance from wall start."""
    dx, dy = wall.x2 - wall.x1, wall.y2 - wall.y1
    length = math.hypot(dx, dy)
    if length < 1e-9:
        return 0.0

    t = ((cx - wall.x1) * dx + (cy - wall.y1) * dy) / (length * length)
    t = max(0.0, min(1.0, t))
    return round(t * length, 3)


def _find_wall_junctions(
    walls: list[VectorWall],
    storey_index: int,
    tolerance: float = 0.15,
) -> list[dict[str, str]]:
    """Find pairs of walls that share an endpoint (within tolerance)."""
    junctions = []
    for i in range(len(walls)):
        for j in range(i + 1, len(walls)):
            endpoints_i = [(walls[i].x1, walls[i].y1), (walls[i].x2, walls[i].y2)]
            endpoints_j = [(walls[j].x1, walls[j].y1), (walls[j].x2, walls[j].y2)]
            for pi in endpoints_i:
                for pj in endpoints_j:
                    if math.hypot(pi[0] - pj[0], pi[1] - pj[1]) < tolerance:
                        junctions.append({
                            "wall_ref_1": f"W{storey_index}_{i}",
                            "wall_ref_2": f"W{storey_index}_{j}",
                        })
    return junctions
