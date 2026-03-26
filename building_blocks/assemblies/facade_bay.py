"""
Facade bay assembly: creates a wall segment with evenly-spaced windows,
optionally with a spandrel beam above and below.
"""
from __future__ import annotations

import ifcopenshell

from building_blocks.primitives.wall import create_wall
from building_blocks.primitives.window import create_window
from building_blocks.primitives.beam import create_beam


def create_facade_bay(
    ifc: ifcopenshell.file,
    contexts: dict,
    storey,
    p1: tuple[float, float],
    p2: tuple[float, float],
    height: float = 3.0,
    wall_thickness: float = 0.25,
    num_windows: int = 3,
    window_width: float = 1.5,
    window_height: float = 1.2,
    window_sill: float = 0.9,
    window_spacing: float | None = None,
    include_spandrel_beam: bool = False,
    beam_width: float = 0.2,
    beam_depth: float = 0.3,
    wall_type=None,
    name_prefix: str = "Facade",
) -> dict:
    """
    Create a facade bay: a wall segment with evenly-distributed windows.

    Windows are distributed evenly along the wall length, respecting edge
    margins. Optionally adds a spandrel beam at the top of the wall.

    Args:
        p1, p2: Wall start and end points (x, y).
        height: Wall height.
        wall_thickness: Wall thickness.
        num_windows: Number of windows to place.
        window_width: Width of each window.
        window_height: Height of each window.
        window_sill: Sill height above floor.
        window_spacing: Override spacing between window centers.
                        If None, auto-calculated from wall length.
        include_spandrel_beam: Add a beam at the wall top.
        beam_width/depth: Spandrel beam dimensions.

    Returns:
        {"wall": ..., "windows": [...], "beam": ... or None}
    """
    import math

    dx = p2[0] - p1[0]
    dy = p2[1] - p1[1]
    wall_length = math.sqrt(dx * dx + dy * dy)

    # Create the wall
    wall = create_wall(
        ifc, contexts, storey,
        p1=p1, p2=p2,
        height=height,
        thickness=wall_thickness,
        name=f"{name_prefix}_Wall",
        wall_type=wall_type,
        is_external=True,
    )

    # Distribute windows
    windows = []
    if num_windows > 0 and wall_length > window_width:
        if window_spacing is None:
            total_window = num_windows * window_width
            remaining = wall_length - total_window
            gap = remaining / (num_windows + 1)
            spacing = gap + window_width
            first_center = gap + window_width / 2.0
        else:
            spacing = window_spacing
            total_span = spacing * (num_windows - 1) if num_windows > 1 else 0.0
            first_center = (wall_length - total_span) / 2.0

        for i in range(num_windows):
            dist_along = first_center + i * spacing
            if dist_along - window_width / 2.0 < 0.1:
                continue
            if dist_along + window_width / 2.0 > wall_length - 0.1:
                continue

            win = create_window(
                ifc, contexts, storey,
                host_wall=wall,
                distance_along_wall=dist_along,
                sill_height=window_sill,
                width=window_width,
                height=window_height,
                name=f"{name_prefix}_Win_{i}",
                wall_thickness=wall_thickness,
            )
            windows.append(win)

    # Optional spandrel beam
    beam = None
    if include_spandrel_beam:
        beam = create_beam(
            ifc, contexts, storey,
            p1=p1, p2=p2,
            elevation=height,
            width=beam_width,
            depth=beam_depth,
            name=f"{name_prefix}_Spandrel",
        )

    return {
        "wall": wall,
        "windows": windows,
        "beam": beam,
    }
