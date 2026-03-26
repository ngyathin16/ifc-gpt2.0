"""
Parametric window author using IfcWindow + window representation.
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
from building_blocks.psets import apply_window_common_pset
from building_blocks.primitives.opening import (
    create_opening_in_wall,
    fill_opening,
    _wall_direction,
    _wall_origin,
)


def create_window(
    ifc: ifcopenshell.file,
    contexts: dict,
    storey,
    host_wall,
    distance_along_wall: float,
    sill_height: float = 0.9,
    width: float = 1.2,
    height: float = 1.5,
    partition_type: str = "SINGLE_PANEL",
    name: str = "Window",
    window_type=None,
    fire_rating: str | None = None,
    is_external: bool = True,
    wall_thickness: float = 0.2,
) -> object:
    """
    Create an IfcWindow placed in a host wall at a given distance along the wall.

    Creates an opening in the host wall, generates window geometry using
    add_window_representation, and fills the opening.

    Args:
        host_wall: The IfcWall to host the window.
        distance_along_wall: Distance from wall start to window center.
        sill_height: Height of the window sill above the floor.
        width: Window width in metres.
        height: Window height in metres.
        partition_type: SINGLE_PANEL, DOUBLE_PANEL_VERTICAL, TRIPLE_PANEL_VERTICAL, etc.

    Returns:
        The newly created IfcWindow entity.
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

    # Create the window entity
    window = ifcopenshell.api.root.create_entity(ifc, ifc_class="IfcWindow", name=name)

    # Window geometry
    window_rep = ifcopenshell.api.geometry.add_window_representation(
        ifc,
        context=contexts["body"],
        overall_height=height,
        overall_width=width,
        partition_type=partition_type,
    )
    ifcopenshell.api.geometry.assign_representation(ifc, product=window, representation=window_rep)

    # Position window at the opening location (wall-direction aware)
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
    ifcopenshell.api.geometry.edit_object_placement(ifc, product=window, matrix=matrix)

    # Fill the opening with the window
    fill_opening(ifc, opening, window)

    # Spatial containment
    ifcopenshell.api.spatial.assign_container(ifc, products=[window], relating_structure=storey)

    if window_type is not None:
        ifcopenshell.api.type.assign_type(ifc, related_objects=[window], relating_type=window_type)

    # Standard Pset
    apply_window_common_pset(ifc, window, fire_rating=fire_rating, is_external=is_external)

    return window
