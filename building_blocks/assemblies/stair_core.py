"""
Stair core assembly: creates a stair enclosure with surrounding walls,
a stair flight, and railings on both sides.
"""
from __future__ import annotations

import math

import ifcopenshell

from building_blocks.primitives.wall import create_wall
from building_blocks.primitives.stair import create_stair
from building_blocks.primitives.railing import create_railing
from building_blocks.primitives.slab import create_slab


def create_stair_core(
    ifc: ifcopenshell.file,
    contexts: dict,
    storey,
    origin: tuple[float, float] = (0.0, 0.0),
    stair_width: float = 1.2,
    stair_length: float = 4.5,
    storey_height: float = 3.0,
    wall_thickness: float = 0.2,
    num_risers: int = 18,
    direction: tuple[float, float] = (1.0, 0.0),
    include_walls: bool = True,
    include_railings: bool = True,
    name_prefix: str = "StairCore",
) -> dict:
    """
    Create a complete stair core with enclosure walls, stair flight, and railings.

    The core is a rectangular enclosure containing a single straight stair flight.

    Args:
        origin: (x, y) of the bottom-left corner of the enclosure.
        stair_width: Width of the stair flight.
        stair_length: Length of the stair run (tread_depth * num_risers).
        storey_height: Floor-to-floor height.
        wall_thickness: Thickness of enclosure walls.
        num_risers: Number of risers in the stair flight.
        direction: Direction the stair runs in.
        include_walls: Whether to create enclosure walls.
        include_railings: Whether to create railings.

    Returns:
        {"stair": ..., "walls": [...], "railings": [...], "landing": ...}
    """
    ox, oy = origin
    dx, dy = direction
    length = math.sqrt(dx * dx + dy * dy)
    if length > 0:
        dx, dy = dx / length, dy / length
    px, py = -dy, dx  # perpendicular

    riser_height = storey_height / num_risers
    tread_depth = stair_length / num_risers

    # Enclosure dimensions
    enc_length = stair_length + wall_thickness

    walls = []
    if include_walls:
        # Left wall
        w_start = (ox + px * (-wall_thickness), oy + py * (-wall_thickness))
        w_end = (
            w_start[0] + dx * enc_length,
            w_start[1] + dy * enc_length,
        )
        walls.append(create_wall(
            ifc, contexts, storey,
            p1=w_start, p2=w_end,
            height=storey_height, thickness=wall_thickness,
            name=f"{name_prefix}_WallL", is_external=False,
        ))

        # Right wall
        w_start = (ox + px * stair_width, oy + py * stair_width)
        w_end = (
            w_start[0] + dx * enc_length,
            w_start[1] + dy * enc_length,
        )
        walls.append(create_wall(
            ifc, contexts, storey,
            p1=w_start, p2=w_end,
            height=storey_height, thickness=wall_thickness,
            name=f"{name_prefix}_WallR", is_external=False,
        ))

        # Back wall (closes the far end)
        bl = (
            ox + px * (-wall_thickness) + dx * enc_length,
            oy + py * (-wall_thickness) + dy * enc_length,
        )
        br = (
            ox + px * (stair_width + wall_thickness) + dx * enc_length,
            oy + py * (stair_width + wall_thickness) + dy * enc_length,
        )
        walls.append(create_wall(
            ifc, contexts, storey,
            p1=bl, p2=br,
            height=storey_height, thickness=wall_thickness,
            name=f"{name_prefix}_WallBack", is_external=False,
        ))

    # Stair flight
    stair = create_stair(
        ifc, contexts, storey,
        start_point=(ox, oy),
        direction=direction,
        width=stair_width,
        num_risers=num_risers,
        riser_height=riser_height,
        tread_depth=tread_depth,
        elevation=0.0,
        name=f"{name_prefix}_Flight",
    )

    railings = []
    if include_railings:
        # Left railing along stair
        left_base = [
            (ox + px * 0.05, oy + py * 0.05, 0.0),
            (
                ox + px * 0.05 + dx * stair_length,
                oy + py * 0.05 + dy * stair_length,
                storey_height,
            ),
        ]
        railings.append(create_railing(
            ifc, contexts, storey,
            path_points=left_base,
            height=0.9,
            name=f"{name_prefix}_RailL",
        ))

        # Right railing along stair
        right_base = [
            (ox + px * (stair_width - 0.05), oy + py * (stair_width - 0.05), 0.0),
            (
                ox + px * (stair_width - 0.05) + dx * stair_length,
                oy + py * (stair_width - 0.05) + dy * stair_length,
                storey_height,
            ),
        ]
        railings.append(create_railing(
            ifc, contexts, storey,
            path_points=right_base,
            height=0.9,
            name=f"{name_prefix}_RailR",
        ))

    # Landing slab at top
    land_origin = (ox + dx * stair_length, oy + dy * stair_length)
    land_pts = [
        (land_origin[0], land_origin[1]),
        (land_origin[0] + px * stair_width, land_origin[1] + py * stair_width),
        (
            land_origin[0] + px * stair_width + dx * stair_width,
            land_origin[1] + py * stair_width + dy * stair_width,
        ),
        (land_origin[0] + dx * stair_width, land_origin[1] + dy * stair_width),
    ]
    landing = create_slab(
        ifc, contexts, storey,
        boundary_points=land_pts,
        depth=0.15,
        elevation=storey_height,
        name=f"{name_prefix}_Landing",
        predefined_type="LANDING",
    )

    return {
        "stair": stair,
        "walls": walls,
        "railings": railings,
        "landing": landing,
    }
