"""
Parametric door author using IfcDoor + door representation.
Automatically cuts an opening in the host wall and fills it.
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
from building_blocks.psets import apply_door_common_pset
from building_blocks.primitives.opening import (
    create_opening_in_wall,
    fill_opening,
    _wall_direction,
    _wall_origin,
)


def create_door(
    ifc: ifcopenshell.file,
    contexts: dict,
    storey,
    host_wall,
    distance_along_wall: float,
    sill_height: float = 0.0,
    width: float = 0.9,
    height: float = 2.1,
    operation_type: str = "SINGLE_SWING_LEFT",
    name: str = "Door",
    door_type=None,
    fire_rating: str | None = None,
    is_external: bool = False,
    wall_thickness: float = 0.2,
) -> object:
    """
    Create an IfcDoor placed in a host wall at a given distance along the wall.

    Creates an opening in the host wall, generates door geometry using
    add_door_representation, and fills the opening.

    Args:
        host_wall: The IfcWall to host the door.
        distance_along_wall: Distance from wall start to door center.
        sill_height: Height of the door sill (usually 0.0).
        width: Door width in metres.
        height: Door height in metres.
        operation_type: SINGLE_SWING_LEFT, SINGLE_SWING_RIGHT, DOUBLE_DOOR_SINGLE_SWING, etc.

    Returns:
        The newly created IfcDoor entity.
    """
    # Create the opening void in the wall
    opening = create_opening_in_wall(
        ifc, contexts, host_wall,
        distance_along_wall=distance_along_wall,
        sill_height=sill_height,
        width=width,
        height=height,
        wall_thickness=wall_thickness,
        name=f"{name}_Opening",
    )

    # Create the door entity
    door = ifcopenshell.api.root.create_entity(ifc, ifc_class="IfcDoor", name=name)

    # Door geometry
    door_rep = ifcopenshell.api.geometry.add_door_representation(
        ifc,
        context=contexts["body"],
        overall_height=height,
        overall_width=width,
        operation_type=operation_type,
    )
    ifcopenshell.api.geometry.assign_representation(ifc, product=door, representation=door_rep)

    # Position door at the opening location (wall-direction aware)
    direction, angle = _wall_direction(host_wall)
    origin = _wall_origin(host_wall)
    cos_a = math.cos(angle)
    sin_a = math.sin(angle)

    offset_along = distance_along_wall - width / 2.0
    world_x = origin[0] + offset_along * cos_a
    world_y = origin[1] + offset_along * sin_a
    world_z = origin[2] + sill_height

    matrix = np.array([
        [cos_a, -sin_a, 0.0, world_x],
        [sin_a,  cos_a, 0.0, world_y],
        [0.0,    0.0,   1.0, world_z],
        [0.0,    0.0,   0.0, 1.0],
    ])
    ifcopenshell.api.geometry.edit_object_placement(ifc, product=door, matrix=matrix)

    # Fill the opening with the door
    fill_opening(ifc, opening, door)

    # Spatial containment
    ifcopenshell.api.spatial.assign_container(ifc, products=[door], relating_structure=storey)

    if door_type is not None:
        ifcopenshell.api.type.assign_type(ifc, related_objects=[door], relating_type=door_type)

    # Standard Pset
    apply_door_common_pset(ifc, door, fire_rating=fire_rating, is_external=is_external)

    return door
