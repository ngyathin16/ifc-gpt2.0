"""
Ramp author using IfcRamp with inclined slab geometry.
"""
from __future__ import annotations

import math

import numpy as np

import ifcopenshell
import ifcopenshell.api
import ifcopenshell.api.geometry
import ifcopenshell.api.root
import ifcopenshell.api.spatial


def create_ramp(
    ifc: ifcopenshell.file,
    contexts: dict,
    storey,
    start_point: tuple[float, float],
    direction: tuple[float, float] = (1.0, 0.0),
    width: float = 1.5,
    length: float = 6.0,
    rise: float = 0.5,
    thickness: float = 0.2,
    name: str = "Ramp",
    predefined_type: str = "STRAIGHT_RUN_RAMP",
) -> object:
    """
    Create an IfcRamp with inclined slab geometry.

    Args:
        start_point: (x, y) of the ramp base.
        direction: (dx, dy) unit direction for the ramp run.
        width: Ramp width in metres.
        length: Ramp run length in metres.
        rise: Total height rise in metres.
        thickness: Ramp slab thickness in metres.
        predefined_type: STRAIGHT_RUN_RAMP, TWO_STRAIGHT_RUN_RAMP, etc.

    Returns:
        The newly created IfcRamp entity.
    """
    ramp = ifcopenshell.api.root.create_entity(
        ifc, ifc_class="IfcRamp", name=name, predefined_type=predefined_type,
    )

    # Build inclined mesh
    hw = width / 2.0
    vertices = [
        # Bottom face
        [0.0, -hw, 0.0],           # 0: start-left bottom
        [length, -hw, rise],        # 1: end-left bottom
        [length,  hw, rise],        # 2: end-right bottom
        [0.0,  hw, 0.0],           # 3: start-right bottom
        # Top face (offset by thickness in Z)
        [0.0, -hw, thickness],
        [length, -hw, rise + thickness],
        [length,  hw, rise + thickness],
        [0.0,  hw, thickness],
    ]
    faces = [
        [0, 3, 2, 1],  # bottom
        [4, 5, 6, 7],  # top
        [0, 1, 5, 4],  # left
        [2, 3, 7, 6],  # right
        [0, 4, 7, 3],  # start
        [1, 2, 6, 5],  # end
    ]

    body_rep = ifcopenshell.api.geometry.add_mesh_representation(
        ifc,
        context=contexts["body"],
        vertices=[vertices],
        faces=[faces],
    )
    ifcopenshell.api.geometry.assign_representation(ifc, product=ramp, representation=body_rep)

    # Placement — rotate to align with direction
    dx, dy = direction
    angle = math.atan2(dy, dx)
    cos_a = math.cos(angle)
    sin_a = math.sin(angle)
    matrix = np.array([
        [cos_a, -sin_a, 0.0, start_point[0]],
        [sin_a,  cos_a, 0.0, start_point[1]],
        [0.0,    0.0,   1.0, 0.0],
        [0.0,    0.0,   0.0, 1.0],
    ])
    ifcopenshell.api.geometry.edit_object_placement(ifc, product=ramp, matrix=matrix)

    ifcopenshell.api.spatial.assign_container(ifc, products=[ramp], relating_structure=storey)

    return ramp
