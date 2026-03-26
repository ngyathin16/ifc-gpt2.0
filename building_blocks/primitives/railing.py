"""
Railing author using IfcRailing + IfcSweptDiskSolid representation.
Supports handrail paths defined by 3D polyline.
"""
from __future__ import annotations

import ifcopenshell
import ifcopenshell.api
import ifcopenshell.api.geometry
import ifcopenshell.api.root
import ifcopenshell.api.spatial


def create_railing(
    ifc: ifcopenshell.file,
    contexts: dict,
    storey,
    path_points: list[tuple[float, float, float]],
    height: float = 1.0,
    railing_diameter: float = 0.05,
    name: str = "Railing",
    predefined_type: str = "WALL_MOUNTED_HANDRAIL",
) -> object:
    """
    Create an IfcRailing along a 3D path.

    Builds the geometry as an IfcSweptDiskSolid (circular tube) along a
    polyline offset upward by *height*.

    Args:
        path_points: List of (x, y, z) tuples defining the base path.
        height: Railing height above the base path in metres.
        railing_diameter: Diameter of the railing profile.
        predefined_type: WALL_MOUNTED_HANDRAIL, GUARDRAIL, BALUSTRADE, etc.

    Returns:
        The newly created IfcRailing entity.
    """
    railing = ifcopenshell.api.root.create_entity(
        ifc, ifc_class="IfcRailing", name=name, predefined_type=predefined_type,
    )

    # Offset path points upward by railing height
    rail_path = [(p[0], p[1], p[2] + height) for p in path_points]

    # Build an IfcSweptDiskSolid along the polyline
    ifc_points = [
        ifc.create_entity("IfcCartesianPoint", Coordinates=[float(c) for c in pt])
        for pt in rail_path
    ]
    polyline = ifc.create_entity("IfcPolyline", Points=ifc_points)

    swept = ifc.create_entity(
        "IfcSweptDiskSolid",
        Directrix=polyline,
        Radius=railing_diameter / 2.0,
    )

    railing_rep = ifc.create_entity(
        "IfcShapeRepresentation",
        ContextOfItems=contexts["body"],
        RepresentationIdentifier="Body",
        RepresentationType="SweptSolid",
        Items=[swept],
    )

    ifcopenshell.api.geometry.assign_representation(
        ifc, product=railing, representation=railing_rep,
    )

    ifcopenshell.api.spatial.assign_container(
        ifc, products=[railing], relating_structure=storey,
    )

    return railing
