"""
Parametric stair author using IfcStairFlight + profile extrusion for treads.
"""
from __future__ import annotations

import math

import numpy as np

import ifcopenshell
import ifcopenshell.api
import ifcopenshell.api.geometry
import ifcopenshell.api.root
import ifcopenshell.api.spatial
from building_blocks.psets import apply_stair_common_pset


def create_stair(
    ifc: ifcopenshell.file,
    contexts: dict,
    storey,
    start_point: tuple[float, float],
    direction: tuple[float, float] = (1.0, 0.0),
    width: float = 1.2,
    num_risers: int = 18,
    riser_height: float = 0.175,
    tread_depth: float = 0.25,
    elevation: float = 0.0,
    name: str = "Stair",
    fire_rating: str | None = None,
) -> object:
    """
    Create an IfcStairFlight with stepped mesh geometry.

    The stair is built as a series of box-shaped treads stacked vertically.
    The stair runs from start_point in the given direction.

    Args:
        start_point: (x, y) position of the stair base.
        direction: (dx, dy) unit direction vector for the stair run.
        width: Stair width perpendicular to the run direction.
        num_risers: Number of risers (treads = num_risers for the flight).
        riser_height: Height of each riser in metres.
        tread_depth: Going/depth of each tread in metres.

    Returns:
        The newly created IfcStairFlight entity.
    """
    stair = ifcopenshell.api.root.create_entity(
        ifc, ifc_class="IfcStairFlight", name=name,
    )

    # Normalize direction
    dx, dy = direction
    length = math.sqrt(dx * dx + dy * dy)
    if length > 0:
        dx, dy = dx / length, dy / length

    # Perpendicular direction for width
    px, py = -dy, dx

    # Build stepped mesh: each tread is a box
    vertices = []
    faces = []

    for i in range(num_risers):
        z_bottom = i * riser_height
        z_top = (i + 1) * riser_height
        x_start = i * tread_depth
        x_end = (i + 1) * tread_depth

        # 8 vertices per tread box
        base_idx = len(vertices)
        hw = width / 2.0

        # Bottom face (4 vertices)
        vertices.append([x_start, -hw, z_bottom])  # 0
        vertices.append([x_end,   -hw, z_bottom])  # 1
        vertices.append([x_end,    hw, z_bottom])  # 2
        vertices.append([x_start,  hw, z_bottom])  # 3
        # Top face (4 vertices)
        vertices.append([x_start, -hw, z_top])     # 4
        vertices.append([x_end,   -hw, z_top])     # 5
        vertices.append([x_end,    hw, z_top])     # 6
        vertices.append([x_start,  hw, z_top])     # 7

        b = base_idx
        # 6 faces per tread box
        faces.append([b+0, b+3, b+2, b+1])  # bottom
        faces.append([b+4, b+5, b+6, b+7])  # top
        faces.append([b+0, b+1, b+5, b+4])  # front
        faces.append([b+2, b+3, b+7, b+6])  # back
        faces.append([b+0, b+4, b+7, b+3])  # left
        faces.append([b+1, b+2, b+6, b+5])  # right

    # Create mesh representation
    body_rep = ifcopenshell.api.geometry.add_mesh_representation(
        ifc,
        context=contexts["body"],
        vertices=[vertices],
        faces=[faces],
    )
    ifcopenshell.api.geometry.assign_representation(ifc, product=stair, representation=body_rep)

    # Placement — rotate to align with direction, position at start_point
    angle = math.atan2(dy, dx)
    cos_a = math.cos(angle)
    sin_a = math.sin(angle)
    matrix = np.array([
        [cos_a, -sin_a, 0.0, start_point[0]],
        [sin_a,  cos_a, 0.0, start_point[1]],
        [0.0,    0.0,   1.0, elevation],
        [0.0,    0.0,   0.0, 1.0],
    ])
    ifcopenshell.api.geometry.edit_object_placement(ifc, product=stair, matrix=matrix)

    ifcopenshell.api.spatial.assign_container(ifc, products=[stair], relating_structure=storey)

    apply_stair_common_pset(
        ifc, stair,
        fire_rating=fire_rating,
        number_of_risers=num_risers,
        riser_height=riser_height,
        tread_length=tread_depth,
    )

    return stair
