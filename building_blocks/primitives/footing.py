"""
Parametric footing author using IfcFooting + profile extrusion.
Supports strip and pad footing types.
"""
from __future__ import annotations

import numpy as np

import ifcopenshell
import ifcopenshell.api
import ifcopenshell.api.geometry
import ifcopenshell.api.root
import ifcopenshell.api.spatial


def create_footing(
    ifc: ifcopenshell.file,
    contexts: dict,
    storey,
    position: tuple[float, float],
    width: float = 1.0,
    length: float = 1.0,
    depth: float = 0.5,
    elevation: float = -0.5,
    name: str = "Footing",
    predefined_type: str = "PAD_FOOTING",
) -> object:
    """
    Create an IfcFooting at a given position.

    Args:
        position: (x, y) centre of the footing in plan.
        width: Footing width (X direction) in metres.
        length: Footing length (Y direction) in metres.
        depth: Footing depth (Z) in metres.
        elevation: Z elevation of the footing top.
        predefined_type: PAD_FOOTING, STRIP_FOOTING, etc.

    Returns:
        The newly created IfcFooting entity.
    """
    footing = ifcopenshell.api.root.create_entity(
        ifc, ifc_class="IfcFooting", name=name, predefined_type=predefined_type,
    )

    # Use a rectangular profile extruded to depth
    profile = ifc.create_entity(
        "IfcRectangleProfileDef",
        ProfileType="AREA",
        ProfileName=f"{name}_profile",
        XDim=width,
        YDim=length,
    )

    body_rep = ifcopenshell.api.geometry.add_profile_representation(
        ifc,
        context=contexts["body"],
        profile=profile,
        depth=depth,
    )
    ifcopenshell.api.geometry.assign_representation(ifc, product=footing, representation=body_rep)

    # Placement — position at (x, y, elevation - depth) so top is at elevation
    matrix = np.eye(4)
    matrix[0][3] = position[0]
    matrix[1][3] = position[1]
    matrix[2][3] = elevation - depth
    ifcopenshell.api.geometry.edit_object_placement(ifc, product=footing, matrix=matrix)

    ifcopenshell.api.spatial.assign_container(ifc, products=[footing], relating_structure=storey)

    return footing
