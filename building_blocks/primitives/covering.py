"""
Covering author using IfcCovering for ceilings, floorings, and cladding.
"""
from __future__ import annotations

import numpy as np

import ifcopenshell
import ifcopenshell.api
import ifcopenshell.api.geometry
import ifcopenshell.api.root
import ifcopenshell.api.spatial


def create_covering(
    ifc: ifcopenshell.file,
    contexts: dict,
    storey,
    boundary_points: list[tuple[float, float]],
    thickness: float = 0.02,
    elevation: float = 0.0,
    name: str = "Covering",
    predefined_type: str = "CEILING",  # CEILING | FLOORING | CLADDING | ROOFING
) -> object:
    """
    Create an IfcCovering from a 2D polyline boundary.

    Args:
        boundary_points: List of (x, y) tuples defining the covering outline.
        thickness: Covering thickness in metres.
        elevation: Z elevation of the covering bottom.
        predefined_type: CEILING, FLOORING, CLADDING, or ROOFING.

    Returns:
        The newly created IfcCovering entity.
    """
    covering = ifcopenshell.api.root.create_entity(
        ifc, ifc_class="IfcCovering", name=name, predefined_type=predefined_type,
    )

    # Use slab representation for the covering geometry
    body_rep = ifcopenshell.api.geometry.add_slab_representation(
        ifc,
        context=contexts["body"],
        depth=thickness,
        polyline=boundary_points,
    )
    ifcopenshell.api.geometry.assign_representation(
        ifc, product=covering, representation=body_rep,
    )

    # Placement
    matrix = np.eye(4)
    matrix[2][3] = elevation
    ifcopenshell.api.geometry.edit_object_placement(ifc, product=covering, matrix=matrix)

    ifcopenshell.api.spatial.assign_container(ifc, products=[covering], relating_structure=storey)

    return covering
