"""
Structural grid assembly: places columns at grid intersections and
beams along grid lines between columns on a given storey.
"""
from __future__ import annotations

import ifcopenshell

from building_blocks.primitives.column import create_column
from building_blocks.primitives.beam import create_beam


def create_structural_grid(
    ifc: ifcopenshell.file,
    contexts: dict,
    storey,
    x_positions: list[float],
    y_positions: list[float],
    storey_height: float = 3.0,
    column_width: float = 0.3,
    column_depth: float = 0.3,
    beam_width: float = 0.2,
    beam_depth: float = 0.4,
    column_type=None,
    beam_type=None,
    name_prefix: str = "Grid",
) -> dict:
    """
    Create a regular structural grid of columns and beams.

    Places columns at every (x, y) intersection, then connects them
    with beams along X and Y grid lines at beam elevation (storey_height).

    Args:
        x_positions: Sorted list of X coordinates for grid lines.
        y_positions: Sorted list of Y coordinates for grid lines.
        storey_height: Height of the storey (column height / beam elevation).
        column_width/depth: Column cross-section dimensions.
        beam_width/depth: Beam cross-section dimensions.

    Returns:
        {"columns": [...], "beams": [...]} lists of created IFC entities.
    """
    columns = []
    beams = []

    # Place columns at every grid intersection
    for ix, x in enumerate(x_positions):
        for iy, y in enumerate(y_positions):
            col = create_column(
                ifc, contexts, storey,
                position=(x, y),
                base_elevation=0.0,
                height=storey_height,
                profile_type="RECTANGULAR",
                width=column_width,
                depth=column_depth,
                name=f"{name_prefix}_Col_{ix}_{iy}",
                column_type=column_type,
            )
            columns.append(col)

    beam_elev = storey_height

    # Beams along X direction (between adjacent X positions, for each Y)
    for iy, y in enumerate(y_positions):
        for ix in range(len(x_positions) - 1):
            x1 = x_positions[ix]
            x2 = x_positions[ix + 1]
            b = create_beam(
                ifc, contexts, storey,
                p1=(x1, y),
                p2=(x2, y),
                elevation=beam_elev,
                width=beam_width,
                depth=beam_depth,
                name=f"{name_prefix}_BeamX_{ix}_{iy}",
                beam_type=beam_type,
            )
            beams.append(b)

    # Beams along Y direction (between adjacent Y positions, for each X)
    for ix, x in enumerate(x_positions):
        for iy in range(len(y_positions) - 1):
            y1 = y_positions[iy]
            y2 = y_positions[iy + 1]
            b = create_beam(
                ifc, contexts, storey,
                p1=(x, y1),
                p2=(x, y2),
                elevation=beam_elev,
                width=beam_width,
                depth=beam_depth,
                name=f"{name_prefix}_BeamY_{ix}_{iy}",
                beam_type=beam_type,
            )
            beams.append(b)

    return {"columns": columns, "beams": beams}
