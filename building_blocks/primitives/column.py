"""
Parametric column author using IfcColumn + material profile set.
Supports rectangular, circular, and standard steel I-sections.
"""
from __future__ import annotations

import numpy as np

import ifcopenshell
import ifcopenshell.api
import ifcopenshell.api.geometry
import ifcopenshell.api.material
import ifcopenshell.api.root
import ifcopenshell.api.spatial
import ifcopenshell.api.type
from building_blocks.psets import apply_column_common_pset


def create_column(
    ifc: ifcopenshell.file,
    contexts: dict,
    storey,
    position: tuple[float, float],
    base_elevation: float = 0.0,
    height: float = 3.0,
    profile_type: str = "RECTANGULAR",  # "RECTANGULAR" | "CIRCULAR" | "I_SECTION"
    width: float = 0.3,    # for RECTANGULAR
    depth: float = 0.3,    # for RECTANGULAR; also depth for I_SECTION
    radius: float = 0.15,  # for CIRCULAR
    name: str = "Column",
    column_type=None,
    fire_rating: str | None = None,
) -> object:
    """
    Create an IfcColumn at a given (x, y) position extruded upward.

    The column is authored using add_profile_representation with an
    IfcRectangleProfileDef, IfcCircleProfileDef, or IfcIShapeProfileDef.
    """
    column = ifcopenshell.api.root.create_entity(ifc, ifc_class="IfcColumn", name=name)

    # Build the profile
    if profile_type == "RECTANGULAR":
        profile = ifc.create_entity(
            "IfcRectangleProfileDef",
            ProfileType="AREA",
            ProfileName=f"{name}_profile",
            XDim=width,
            YDim=depth,
        )
    elif profile_type == "CIRCULAR":
        profile = ifc.create_entity(
            "IfcCircleProfileDef",
            ProfileType="AREA",
            ProfileName=f"{name}_profile",
            Radius=radius,
        )
    elif profile_type == "I_SECTION":
        profile = ifc.create_entity(
            "IfcIShapeProfileDef",
            ProfileType="AREA",
            ProfileName=f"{name}_profile",
            OverallWidth=width,
            OverallDepth=depth,
            WebThickness=width * 0.05,
            FlangeThickness=depth * 0.08,
        )
    else:
        raise ValueError(f"Unknown profile_type: {profile_type}")

    # Profile representation extruded vertically
    body_rep = ifcopenshell.api.geometry.add_profile_representation(
        ifc,
        context=contexts["body"],
        profile=profile,
        depth=height,
    )
    ifcopenshell.api.geometry.assign_representation(ifc, product=column, representation=body_rep)

    # Placement at (x, y, base_elevation)
    matrix = np.eye(4)
    matrix[0][3] = position[0]
    matrix[1][3] = position[1]
    matrix[2][3] = base_elevation
    ifcopenshell.api.geometry.edit_object_placement(ifc, product=column, matrix=matrix)

    ifcopenshell.api.spatial.assign_container(ifc, products=[column], relating_structure=storey)

    if column_type is not None:
        ifcopenshell.api.type.assign_type(ifc, related_objects=[column], relating_type=column_type)

    # Standard Pset
    apply_column_common_pset(ifc, column, fire_rating=fire_rating)

    return column
