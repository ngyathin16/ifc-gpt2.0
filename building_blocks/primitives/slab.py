"""
Parametric slab author using IfcSlab + slab representation.
Supports arbitrary polyline boundaries for non-rectangular slabs.
"""
from __future__ import annotations

import numpy as np

import ifcopenshell
import ifcopenshell.api
import ifcopenshell.api.geometry
import ifcopenshell.api.root
import ifcopenshell.api.spatial
import ifcopenshell.api.type
from building_blocks.psets import apply_slab_common_pset


def create_slab(
    ifc: ifcopenshell.file,
    contexts: dict,
    storey,
    boundary_points: list[tuple[float, float]],
    depth: float = 0.2,
    elevation: float = 0.0,
    name: str = "Slab",
    slab_type=None,
    predefined_type: str = "FLOOR",
    fire_rating: str | None = None,
    is_external: bool = False,
) -> object:
    """
    Create an IfcSlab from a 2D polyline boundary at a given elevation.

    Args:
        boundary_points: List of (x, y) tuples defining the slab outline.
        depth: Slab thickness in metres.
        elevation: Z elevation of the slab bottom in metres.
        predefined_type: "FLOOR", "ROOF", or "LANDING".

    Returns:
        The newly created IfcSlab entity.
    """
    slab = ifcopenshell.api.root.create_entity(
        ifc, ifc_class="IfcSlab", name=name, predefined_type=predefined_type,
    )

    # Slab representation from polyline boundary
    body_rep = ifcopenshell.api.geometry.add_slab_representation(
        ifc,
        context=contexts["body"],
        depth=depth,
        polyline=boundary_points,
    )
    ifcopenshell.api.geometry.assign_representation(ifc, product=slab, representation=body_rep)

    # Placement
    matrix = np.eye(4)
    matrix[2][3] = elevation
    ifcopenshell.api.geometry.edit_object_placement(ifc, product=slab, matrix=matrix)

    ifcopenshell.api.spatial.assign_container(ifc, products=[slab], relating_structure=storey)

    if slab_type is not None:
        ifcopenshell.api.type.assign_type(ifc, related_objects=[slab], relating_type=slab_type)

    # Standard Pset
    apply_slab_common_pset(ifc, slab, fire_rating=fire_rating, is_external=is_external)

    return slab
