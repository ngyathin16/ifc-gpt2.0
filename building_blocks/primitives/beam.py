"""
Parametric beam author using IfcBeam + profile extrusion.
Beams run from p1 to p2 at a given elevation. Supports rectangular and I-section profiles.
"""
from __future__ import annotations

import math

import numpy as np

import ifcopenshell
import ifcopenshell.api
import ifcopenshell.api.geometry
import ifcopenshell.api.root
import ifcopenshell.api.spatial
import ifcopenshell.api.type
from building_blocks.psets import apply_beam_common_pset


def create_beam(
    ifc: ifcopenshell.file,
    contexts: dict,
    storey,
    p1: tuple[float, float],
    p2: tuple[float, float],
    elevation: float = 3.0,
    profile_type: str = "I_SECTION",  # "RECTANGULAR" | "I_SECTION"
    width: float = 0.2,
    depth: float = 0.4,
    name: str = "Beam",
    beam_type=None,
    fire_rating: str | None = None,
) -> object:
    """
    Create an IfcBeam between two 2D points at a given elevation.

    The beam is authored using add_profile_representation for the body
    and add_axis_representation for the axis. The beam is oriented along
    the line from p1 to p2.
    """
    beam = ifcopenshell.api.root.create_entity(ifc, ifc_class="IfcBeam", name=name)

    # Calculate beam length and angle
    dx = p2[0] - p1[0]
    dy = p2[1] - p1[1]
    length = math.sqrt(dx * dx + dy * dy)
    angle = math.atan2(dy, dx)

    # Build the profile
    if profile_type == "RECTANGULAR":
        profile = ifc.create_entity(
            "IfcRectangleProfileDef",
            ProfileType="AREA",
            ProfileName=f"{name}_profile",
            XDim=width,
            YDim=depth,
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

    # Profile representation — extrude along beam length
    body_rep = ifcopenshell.api.geometry.add_profile_representation(
        ifc,
        context=contexts["body"],
        profile=profile,
        depth=length,
    )
    ifcopenshell.api.geometry.assign_representation(ifc, product=beam, representation=body_rep)

    # Placement — position at p1 with extrusion (local Z) along beam direction.
    # add_profile_representation extrudes along local Z, so we orient:
    #   local X = (-sin_a, cos_a, 0) — perpendicular to beam (profile width)
    #   local Y = (0, 0, 1)          — vertical up (profile depth)
    #   local Z = (cos_a, sin_a, 0)  — along beam direction (extrusion)
    cos_a = math.cos(angle)
    sin_a = math.sin(angle)
    matrix = np.array([
        [-sin_a, 0.0, cos_a, p1[0]],
        [ cos_a, 0.0, sin_a, p1[1]],
        [  0.0,  1.0,  0.0,  elevation],
        [  0.0,  0.0,  0.0,  1.0],
    ])
    ifcopenshell.api.geometry.edit_object_placement(ifc, product=beam, matrix=matrix)

    ifcopenshell.api.spatial.assign_container(ifc, products=[beam], relating_structure=storey)

    if beam_type is not None:
        ifcopenshell.api.type.assign_type(ifc, related_objects=[beam], relating_type=beam_type)

    # Standard Pset
    apply_beam_common_pset(ifc, beam, fire_rating=fire_rating)

    return beam
