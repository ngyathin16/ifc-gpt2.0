"""
Apartment unit assembly: creates a rectangular unit with perimeter walls,
interior partition for a bathroom, a front door, and windows.
"""
from __future__ import annotations

import ifcopenshell
import ifcopenshell.api
import ifcopenshell.api.aggregate
import ifcopenshell.api.root
import ifcopenshell.api.spatial

from building_blocks.primitives.wall import create_wall
from building_blocks.primitives.door import create_door
from building_blocks.primitives.window import create_window
from building_blocks.primitives.slab import create_slab
from building_blocks.psets import apply_space_common_pset


def create_apartment_unit(
    ifc: ifcopenshell.file,
    contexts: dict,
    storey,
    origin: tuple[float, float] = (0.0, 0.0),
    width: float = 6.0,
    depth: float = 8.0,
    height: float = 3.0,
    wall_thickness: float = 0.2,
    partition_thickness: float = 0.1,
    door_width: float = 0.9,
    door_height: float = 2.1,
    window_width: float = 1.5,
    window_height: float = 1.2,
    window_sill: float = 0.9,
    include_bathroom: bool = True,
    bathroom_depth: float = 2.5,
    include_floor_slab: bool = False,
    name_prefix: str = "Apt",
) -> dict:
    """
    Create a complete apartment unit layout.

    Layout:
    - Rectangular perimeter with exterior walls
    - Front door on the south wall
    - Windows on the south wall (flanking the door)
    - Optional bathroom partition at the north end

    Args:
        origin: (x, y) bottom-left corner.
        width: Unit width (X).
        depth: Unit depth (Y).
        height: Floor-to-ceiling height.
        wall_thickness: Exterior wall thickness.
        partition_thickness: Interior wall thickness.
        include_bathroom: Add a bathroom partition at the rear.
        bathroom_depth: Y dimension of the bathroom.

    Returns:
        {"walls": [...], "doors": [...], "windows": [...],
         "spaces": [...], "slab": ... or None}
    """
    ox, oy = origin
    t = wall_thickness

    # Perimeter corners
    p_sw = (ox, oy)
    p_se = (ox + width, oy)
    p_ne = (ox + width, oy + depth)
    p_nw = (ox, oy + depth)

    walls = []
    doors = []
    windows = []
    spaces = []

    # South wall (front — door + windows)
    south = create_wall(
        ifc, contexts, storey,
        p1=p_sw, p2=p_se,
        height=height, thickness=t,
        name=f"{name_prefix}_WallS", is_external=True,
    )
    walls.append(south)

    # East wall
    walls.append(create_wall(
        ifc, contexts, storey,
        p1=p_se, p2=p_ne,
        height=height, thickness=t,
        name=f"{name_prefix}_WallE", is_external=True,
    ))

    # North wall
    walls.append(create_wall(
        ifc, contexts, storey,
        p1=p_ne, p2=p_nw,
        height=height, thickness=t,
        name=f"{name_prefix}_WallN", is_external=True,
    ))

    # West wall
    walls.append(create_wall(
        ifc, contexts, storey,
        p1=p_nw, p2=p_sw,
        height=height, thickness=t,
        name=f"{name_prefix}_WallW", is_external=True,
    ))

    # Front door (centered on south wall)
    front_door = create_door(
        ifc, contexts, storey,
        host_wall=south,
        distance_along_wall=width / 2.0,
        sill_height=0.0,
        width=door_width,
        height=door_height,
        name=f"{name_prefix}_FrontDoor",
        wall_thickness=t,
    )
    doors.append(front_door)

    # Windows on south wall (one on each side of door if room allows)
    door_center = width / 2.0
    left_window_pos = door_center - door_width / 2.0 - window_width / 2.0 - 0.3
    right_window_pos = door_center + door_width / 2.0 + window_width / 2.0 + 0.3

    if left_window_pos > window_width / 2.0 + 0.2:
        windows.append(create_window(
            ifc, contexts, storey,
            host_wall=south,
            distance_along_wall=left_window_pos,
            sill_height=window_sill,
            width=window_width,
            height=window_height,
            name=f"{name_prefix}_WinL",
            wall_thickness=t,
        ))

    if right_window_pos < width - window_width / 2.0 - 0.2:
        windows.append(create_window(
            ifc, contexts, storey,
            host_wall=south,
            distance_along_wall=right_window_pos,
            sill_height=window_sill,
            width=window_width,
            height=window_height,
            name=f"{name_prefix}_WinR",
            wall_thickness=t,
        ))

    # Living space
    living_space = ifcopenshell.api.root.create_entity(
        ifc, ifc_class="IfcSpace", name=f"{name_prefix}_Living",
        predefined_type="INTERNAL",
    )
    ifcopenshell.api.aggregate.assign_object(
        ifc, products=[living_space], relating_object=storey,
    )
    apply_space_common_pset(ifc, living_space, reference=name_prefix, category="LIVINGROOM")
    spaces.append(living_space)

    # Bathroom partition
    if include_bathroom and bathroom_depth < depth - 1.0:
        partition_y = oy + depth - bathroom_depth
        part_wall = create_wall(
            ifc, contexts, storey,
            p1=(ox + t, partition_y),
            p2=(ox + width - t, partition_y),
            height=height, thickness=partition_thickness,
            name=f"{name_prefix}_Partition", is_external=False,
        )
        walls.append(part_wall)

        # Bathroom door
        bath_door = create_door(
            ifc, contexts, storey,
            host_wall=part_wall,
            distance_along_wall=(width - 2 * t) / 2.0,
            sill_height=0.0,
            width=0.8,
            height=2.1,
            name=f"{name_prefix}_BathDoor",
            wall_thickness=partition_thickness,
        )
        doors.append(bath_door)

        # Bathroom space
        bath_space = ifcopenshell.api.root.create_entity(
            ifc, ifc_class="IfcSpace", name=f"{name_prefix}_Bathroom",
            predefined_type="INTERNAL",
        )
        ifcopenshell.api.aggregate.assign_object(
            ifc, products=[bath_space], relating_object=storey,
        )
        apply_space_common_pset(ifc, bath_space, reference=name_prefix, category="BATHROOM")
        spaces.append(bath_space)

    # Optional floor slab
    slab = None
    if include_floor_slab:
        slab_pts = [
            (ox + t, oy + t),
            (ox + width - t, oy + t),
            (ox + width - t, oy + depth - t),
            (ox + t, oy + depth - t),
        ]
        slab = create_slab(
            ifc, contexts, storey,
            boundary_points=slab_pts,
            depth=0.2,
            elevation=0.0,
            name=f"{name_prefix}_Floor",
        )

    return {
        "walls": walls,
        "doors": doors,
        "windows": windows,
        "spaces": spaces,
        "slab": slab,
    }
