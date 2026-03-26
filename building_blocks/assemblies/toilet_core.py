"""
Toilet core assembly: creates a rectangular wet-room enclosure with
partition walls, a door opening, and an IfcSpace for the room.
"""
from __future__ import annotations

import ifcopenshell
import ifcopenshell.api
import ifcopenshell.api.aggregate
import ifcopenshell.api.root
import ifcopenshell.api.spatial

from building_blocks.primitives.wall import create_wall
from building_blocks.primitives.door import create_door
from building_blocks.primitives.slab import create_slab
from building_blocks.psets import apply_space_common_pset


def create_toilet_core(
    ifc: ifcopenshell.file,
    contexts: dict,
    storey,
    origin: tuple[float, float] = (0.0, 0.0),
    width: float = 2.0,
    depth: float = 2.5,
    height: float = 3.0,
    wall_thickness: float = 0.1,
    door_width: float = 0.8,
    door_height: float = 2.1,
    include_floor_slab: bool = False,
    name_prefix: str = "Toilet",
) -> dict:
    """
    Create a toilet/wet-room enclosure with four walls and a door.

    The door is placed on the wall closest to the origin (south wall),
    centered along its length.

    Args:
        origin: (x, y) bottom-left corner of the enclosure.
        width: Interior width (X direction).
        depth: Interior depth (Y direction).
        height: Wall height.
        wall_thickness: Partition wall thickness.
        door_width: Door opening width.
        door_height: Door opening height.
        include_floor_slab: Whether to add a floor slab.

    Returns:
        {"walls": [...], "door": ..., "space": ..., "slab": ... or None}
    """
    ox, oy = origin
    w = width
    d = depth
    t = wall_thickness

    # Four corners (exterior)
    p_sw = (ox, oy)
    p_se = (ox + w + 2 * t, oy)
    p_ne = (ox + w + 2 * t, oy + d + 2 * t)
    p_nw = (ox, oy + d + 2 * t)

    walls = []

    # South wall (with door)
    south_wall = create_wall(
        ifc, contexts, storey,
        p1=p_sw, p2=p_se,
        height=height, thickness=t,
        name=f"{name_prefix}_WallS", is_external=False,
    )
    walls.append(south_wall)

    # East wall
    walls.append(create_wall(
        ifc, contexts, storey,
        p1=p_se, p2=p_ne,
        height=height, thickness=t,
        name=f"{name_prefix}_WallE", is_external=False,
    ))

    # North wall
    walls.append(create_wall(
        ifc, contexts, storey,
        p1=p_ne, p2=p_nw,
        height=height, thickness=t,
        name=f"{name_prefix}_WallN", is_external=False,
    ))

    # West wall
    walls.append(create_wall(
        ifc, contexts, storey,
        p1=p_nw, p2=p_sw,
        height=height, thickness=t,
        name=f"{name_prefix}_WallW", is_external=False,
    ))

    # Door centered on south wall
    south_len = w + 2 * t
    door_pos = south_len / 2.0
    door = create_door(
        ifc, contexts, storey,
        host_wall=south_wall,
        distance_along_wall=door_pos,
        sill_height=0.0,
        width=door_width,
        height=door_height,
        name=f"{name_prefix}_Door",
        wall_thickness=t,
    )

    # IfcSpace for the room
    space = ifcopenshell.api.root.create_entity(
        ifc, ifc_class="IfcSpace", name=f"{name_prefix}_Space",
        predefined_type="INTERNAL",
    )
    ifcopenshell.api.aggregate.assign_object(
        ifc, products=[space], relating_object=storey,
    )
    apply_space_common_pset(ifc, space, reference=name_prefix, category="TOILET")

    # Optional floor slab
    slab = None
    if include_floor_slab:
        interior_pts = [
            (ox + t, oy + t),
            (ox + t + w, oy + t),
            (ox + t + w, oy + t + d),
            (ox + t, oy + t + d),
        ]
        slab = create_slab(
            ifc, contexts, storey,
            boundary_points=interior_pts,
            depth=0.1,
            elevation=0.0,
            name=f"{name_prefix}_Floor",
        )

    return {
        "walls": walls,
        "door": door,
        "space": space,
        "slab": slab,
    }
