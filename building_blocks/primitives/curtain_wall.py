"""
Curtain wall author using IfcCurtainWall.
Creates a planar curtain wall with mullion/transom grid.
"""
from __future__ import annotations

import math

import numpy as np

import ifcopenshell
import ifcopenshell.api
import ifcopenshell.api.geometry
import ifcopenshell.api.root
import ifcopenshell.api.spatial


def create_curtain_wall(
    ifc: ifcopenshell.file,
    contexts: dict,
    storey,
    p1: tuple[float, float],
    p2: tuple[float, float],
    elevation: float = 0.0,
    height: float = 3.0,
    thickness: float = 0.15,
    name: str = "Curtain Wall",
) -> object:
    """
    Create an IfcCurtainWall between two 2D points.

    The curtain wall is represented as a thin planar element.
    For detailed mullion/transom subdivision, use assemblies.

    Args:
        p1, p2: (x, y) start and end points in plan.
        elevation: Z elevation of the curtain wall base.
        height: Wall height in metres.
        thickness: Wall panel thickness in metres.

    Returns:
        The newly created IfcCurtainWall entity.
    """
    cw = ifcopenshell.api.root.create_entity(
        ifc, ifc_class="IfcCurtainWall", name=name,
    )

    # Calculate length
    dx = p2[0] - p1[0]
    dy = p2[1] - p1[1]
    length = math.sqrt(dx * dx + dy * dy)
    angle = math.atan2(dy, dx)

    # Use wall representation for the panel
    body_rep = ifcopenshell.api.geometry.add_wall_representation(
        ifc,
        context=contexts["body"],
        length=length,
        height=height,
        thickness=thickness,
    )
    ifcopenshell.api.geometry.assign_representation(ifc, product=cw, representation=body_rep)

    # Placement
    cos_a = math.cos(angle)
    sin_a = math.sin(angle)
    matrix = np.array([
        [cos_a, -sin_a, 0.0, p1[0]],
        [sin_a,  cos_a, 0.0, p1[1]],
        [0.0,    0.0,   1.0, elevation],
        [0.0,    0.0,   0.0, 1.0],
    ])
    ifcopenshell.api.geometry.edit_object_placement(ifc, product=cw, matrix=matrix)

    ifcopenshell.api.spatial.assign_container(ifc, products=[cw], relating_structure=storey)

    return cw
