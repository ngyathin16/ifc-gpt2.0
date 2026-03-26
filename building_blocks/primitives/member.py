"""
Generic structural member author using IfcMember + profile extrusion.
Used for bracing, purlins, and other structural elements.
"""
from __future__ import annotations

import math

import numpy as np

import ifcopenshell
import ifcopenshell.api
import ifcopenshell.api.geometry
import ifcopenshell.api.root
import ifcopenshell.api.spatial


def create_member(
    ifc: ifcopenshell.file,
    contexts: dict,
    storey,
    p1: tuple[float, float, float],
    p2: tuple[float, float, float],
    profile_type: str = "RECTANGULAR",
    width: float = 0.1,
    depth: float = 0.1,
    radius: float = 0.05,
    name: str = "Member",
    predefined_type: str = "BRACE",
) -> object:
    """
    Create an IfcMember between two 3D points.

    Args:
        p1, p2: (x, y, z) start and end points.
        profile_type: "RECTANGULAR" or "CIRCULAR".
        width, depth: Dimensions for rectangular profile.
        radius: Radius for circular profile.
        predefined_type: BRACE, PURLIN, STUD, etc.

    Returns:
        The newly created IfcMember entity.
    """
    member = ifcopenshell.api.root.create_entity(
        ifc, ifc_class="IfcMember", name=name, predefined_type=predefined_type,
    )

    # Calculate length
    dx = p2[0] - p1[0]
    dy = p2[1] - p1[1]
    dz = p2[2] - p1[2]
    length = math.sqrt(dx * dx + dy * dy + dz * dz)

    # Build profile
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
    else:
        raise ValueError(f"Unknown profile_type: {profile_type}")

    body_rep = ifcopenshell.api.geometry.add_profile_representation(
        ifc,
        context=contexts["body"],
        profile=profile,
        depth=length,
    )
    ifcopenshell.api.geometry.assign_representation(ifc, product=member, representation=body_rep)

    # Build rotation matrix to align local Z axis with the member direction
    if length > 0:
        dir_vec = np.array([dx, dy, dz]) / length
    else:
        dir_vec = np.array([0.0, 0.0, 1.0])

    # Find rotation from Z axis to dir_vec
    z_axis = np.array([0.0, 0.0, 1.0])
    cross = np.cross(z_axis, dir_vec)
    dot = np.dot(z_axis, dir_vec)

    if np.linalg.norm(cross) < 1e-10:
        if dot > 0:
            rot = np.eye(3)
        else:
            rot = np.diag([1.0, -1.0, -1.0])
    else:
        cross_norm = cross / np.linalg.norm(cross)
        angle = math.acos(max(-1.0, min(1.0, dot)))
        K = np.array([
            [0, -cross_norm[2], cross_norm[1]],
            [cross_norm[2], 0, -cross_norm[0]],
            [-cross_norm[1], cross_norm[0], 0],
        ])
        rot = np.eye(3) + math.sin(angle) * K + (1 - math.cos(angle)) * (K @ K)

    matrix = np.eye(4)
    matrix[:3, :3] = rot
    matrix[0][3] = p1[0]
    matrix[1][3] = p1[1]
    matrix[2][3] = p1[2]
    ifcopenshell.api.geometry.edit_object_placement(ifc, product=member, matrix=matrix)

    ifcopenshell.api.spatial.assign_container(ifc, products=[member], relating_structure=storey)

    return member
