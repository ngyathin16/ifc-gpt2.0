"""
Semantic void + fill helpers for doors and windows.
Uses ifcopenshell.api.feature.add_feature to cut the host wall opening,
then fills it with the door/window element.
"""
from __future__ import annotations

import math

import numpy as np

import ifcopenshell
import ifcopenshell.api
import ifcopenshell.api.feature
import ifcopenshell.api.geometry
import ifcopenshell.api.root
import ifcopenshell.util.placement


def _wall_direction(host_wall) -> tuple[np.ndarray, float]:
    """Return (unit_direction_2d, angle_rad) of the wall from its ObjectPlacement.

    Extracts the wall's local X-axis from its 4×4 world matrix.
    Falls back to X-axis [1, 0] if placement cannot be read.
    """
    try:
        mat = ifcopenshell.util.placement.get_local_placement(
            host_wall.ObjectPlacement
        )
        direction = np.array([mat[0][0], mat[1][0]], dtype=float)  # column 0 = local X in world XY
        length = np.linalg.norm(direction)
        if length > 1e-6:
            direction /= length
        else:
            direction = np.array([1.0, 0.0])
    except Exception:
        direction = np.array([1.0, 0.0])
    angle = math.atan2(float(direction[1]), float(direction[0]))
    return direction, angle


def _wall_origin(host_wall) -> np.ndarray:
    """Return the wall's world-space origin (translation column of placement)."""
    try:
        mat = ifcopenshell.util.placement.get_local_placement(
            host_wall.ObjectPlacement
        )
        return np.array([mat[0][3], mat[1][3], mat[2][3]], dtype=float)
    except Exception:
        return np.zeros(3)


def create_opening_in_wall(
    ifc: ifcopenshell.file,
    contexts: dict,
    host_wall,
    distance_along_wall: float,
    sill_height: float,
    width: float,
    height: float,
    wall_thickness: float = 0.3,
    name: str = "Opening",
) -> object:
    """
    Create an IfcOpeningElement in a wall at a given distance along the wall axis.

    The opening is positioned in *world coordinates* using the host wall's
    direction vector so it works for walls in any orientation.

    Args:
        host_wall: The IfcWall to cut.
        distance_along_wall: Distance from the wall start to the opening center.
        sill_height: Height from the wall base to the opening bottom.
        width: Opening width in metres.
        height: Opening height in metres.
        wall_thickness: Depth of the opening void (should exceed wall thickness).

    Returns:
        The IfcOpeningElement entity.
    """
    opening = ifcopenshell.api.root.create_entity(
        ifc, ifc_class="IfcOpeningElement", name=name,
    )

    # Opening geometry — a box matching the void dimensions
    opening_rep = ifcopenshell.api.geometry.add_wall_representation(
        ifc,
        context=contexts["body"],
        length=width,
        height=height,
        thickness=wall_thickness + 0.1,  # slightly larger to ensure clean cut
    )
    ifcopenshell.api.geometry.assign_representation(
        ifc, product=opening, representation=opening_rep,
    )

    # Compute wall direction and build a world-space placement
    direction, angle = _wall_direction(host_wall)
    origin = _wall_origin(host_wall)
    cos_a = math.cos(angle)
    sin_a = math.sin(angle)

    # Opening center along wall axis, offset by -width/2 for wall-rep convention
    offset_along = distance_along_wall - width / 2.0
    world_x = origin[0] + offset_along * cos_a
    world_y = origin[1] + offset_along * sin_a
    world_z = origin[2] + sill_height

    matrix = np.array([
        [cos_a, -sin_a, 0.0, world_x],
        [sin_a,  cos_a, 0.0, world_y],
        [0.0,    0.0,   1.0, world_z],
        [0.0,    0.0,   0.0, 1.0],
    ])
    # Shift slightly into the wall along the wall's perpendicular (-Y local)
    perp_offset = -0.05
    matrix[0][3] += perp_offset * (-sin_a)
    matrix[1][3] += perp_offset * cos_a

    ifcopenshell.api.geometry.edit_object_placement(
        ifc, product=opening, matrix=matrix,
    )

    # Cut the void in the host wall
    ifcopenshell.api.feature.add_feature(
        ifc, feature=opening, element=host_wall,
    )

    return opening


def fill_opening(
    ifc: ifcopenshell.file,
    opening,
    filling_element,
) -> None:
    """
    Fill an existing IfcOpeningElement with a door or window element.
    Creates the IfcRelFillsElement relationship.
    """
    ifc.create_entity(
        "IfcRelFillsElement",
        GlobalId=ifcopenshell.guid.new(),
        RelatingOpeningElement=opening,
        RelatedBuildingElement=filling_element,
    )
