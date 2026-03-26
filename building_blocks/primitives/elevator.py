"""
Parametric elevator shaft author using IfcTransportElement + extruded box.
Creates a rectangular elevator shaft as a building element.
"""
from __future__ import annotations

import numpy as np

import ifcopenshell
import ifcopenshell.api
import ifcopenshell.api.geometry
import ifcopenshell.api.root
import ifcopenshell.api.spatial
import ifcopenshell.api.pset


def create_elevator_shaft(
    ifc: ifcopenshell.file,
    contexts: dict,
    storey,
    position: tuple[float, float],
    elevation: float = 0.0,
    width: float = 2.0,
    depth: float = 2.0,
    height: float = 3.0,
    name: str = "Elevator",
    fire_rating: str | None = None,
) -> object:
    """
    Create an IfcTransportElement representing an elevator shaft.

    The shaft is a simple extruded rectangular box placed at the given
    (x, y) position.  Width is along X, depth is along Y.

    Args:
        position: (x, y) centre of the shaft in plan.
        elevation: Z elevation of the shaft bottom (absolute).
        width: Shaft width along X in metres.
        depth: Shaft depth along Y in metres.
        height: Shaft height (floor-to-floor) in metres.
        name: Element name.
    """
    elevator = ifcopenshell.api.root.create_entity(
        ifc,
        ifc_class="IfcTransportElement",
        name=name,
        predefined_type="ELEVATOR",
    )

    # Rectangular profile for the shaft cross-section
    profile = ifc.create_entity(
        "IfcRectangleProfileDef",
        ProfileType="AREA",
        ProfileName=f"{name}_profile",
        XDim=width,
        YDim=depth,
    )

    # Extrude vertically by height
    body_rep = ifcopenshell.api.geometry.add_profile_representation(
        ifc,
        context=contexts["body"],
        profile=profile,
        depth=height,
    )
    ifcopenshell.api.geometry.assign_representation(
        ifc, product=elevator, representation=body_rep,
    )

    # Placement at (x, y, elevation)
    matrix = np.eye(4)
    matrix[0][3] = position[0]
    matrix[1][3] = position[1]
    matrix[2][3] = elevation
    ifcopenshell.api.geometry.edit_object_placement(
        ifc, product=elevator, matrix=matrix,
    )

    ifcopenshell.api.spatial.assign_container(
        ifc, products=[elevator], relating_structure=storey,
    )

    # Property set
    pset = ifcopenshell.api.pset.add_pset(
        ifc, product=elevator, name="Pset_TransportElementCommon",
    )
    props: dict = {"Reference": name, "CapacityByWeight": 1600.0}
    if fire_rating:
        props["FireRating"] = fire_rating
    ifcopenshell.api.pset.edit_pset(ifc, pset=pset, properties=props)

    return elevator
